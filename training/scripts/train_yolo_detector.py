from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import signal
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table

console = Console()
SUPPORTED_IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train YOLO11 fast traffic detector with headwear detection classes.")
    parser.add_argument("--config", type=Path, default=Path("configs/training.yaml"))
    parser.add_argument("--model-key", default="fast_detector")
    parser.add_argument("--weights-dir", type=Path, default=None)
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--vol-root", type=Path, default=None)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--device", type=str, default=None)
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def config_hash(cfg: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def resolve_path(path: str | Path, config_path: Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return (config_path.parent / p).resolve()


def read_data_yaml(data_yaml: Path) -> dict[str, Any]:
    if not data_yaml.exists():
        raise FileNotFoundError(f"YOLO data yaml not found: {data_yaml}")
    with data_yaml.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YOLO data yaml: {data_yaml}")
    return data


def class_names_from_yaml(data: dict[str, Any]) -> list[str]:
    names = data.get("names", [])
    if isinstance(names, dict):
        return [str(names[k]) for k in sorted(names, key=lambda x: int(x))]
    return [str(name) for name in names]


def split_dir(data_yaml: Path, data: dict[str, Any], split: str) -> Path | None:
    value = data.get(split)
    if value is None:
        return None
    root = data_yaml.parent / data.get("path", ".")
    value_path = Path(value)
    return value_path if value_path.is_absolute() else (root / value_path).resolve()


def label_path_for_image(image_path: Path) -> Path:
    parts = list(image_path.parts)
    if "images" in parts:
        idx = parts.index("images")
        parts[idx] = "labels"
        return Path(*parts).with_suffix(".txt")
    return image_path.with_suffix(".txt")


def validate_dataset(data_yaml: Path, required_classes: list[str]) -> dict[str, Any]:
    console.rule("[bold cyan]YOLO Dataset Validation")
    data = read_data_yaml(data_yaml)
    class_names = class_names_from_yaml(data)
    missing_classes = [name for name in required_classes if name not in class_names]
    if missing_classes:
        raise ValueError("Missing required detector classes: " + ", ".join(missing_classes))

    class_counts: Counter[str] = Counter()
    image_count = 0
    missing_labels = 0
    train_images: set[Path] = set()
    val_images: set[Path] = set()

    for split in ("train", "val"):
        directory = split_dir(data_yaml, data, split)
        if directory is None or not directory.exists():
            raise FileNotFoundError(f"Missing {split} image directory from {data_yaml}: {directory}")
        images = {p.resolve() for p in directory.rglob("*") if p.suffix.lower() in SUPPORTED_IMG_EXT}
        if split == "train":
            train_images = images
        else:
            val_images = images
        image_count += len(images)
        for image in images:
            label_path = label_path_for_image(image)
            if not label_path.exists():
                missing_labels += 1
                continue
            for line in label_path.read_text(encoding="utf-8").splitlines():
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                class_id = int(float(parts[0]))
                if class_id < len(class_names):
                    class_counts[class_names[class_id]] += 1

    overlap = train_images & val_images
    if overlap:
        raise ValueError(f"Train/val leakage detected: {len(overlap)} duplicate image paths")
    if image_count == 0:
        raise ValueError("No training/validation images found")

    table = Table(title="Detection Class Distribution")
    table.add_column("Class")
    table.add_column("Boxes", justify="right")
    for name in class_names:
        table.add_row(name, str(class_counts.get(name, 0)))
    console.print(table)
    if missing_labels:
        console.print(f"[yellow]{missing_labels} image(s) have no label file; YOLO will treat them as empty.[/yellow]")

    return {
        "data_yaml": str(data_yaml),
        "class_map": {i: name for i, name in enumerate(class_names)},
        "class_counts": dict(class_counts),
        "image_count": image_count,
        "missing_labels": missing_labels,
    }


def cuda_available() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except Exception:
        return False


def copy_weights(run_dir: Path, weights_dir: Path) -> dict[str, str]:
    weights_dir.mkdir(parents=True, exist_ok=True)
    copied: dict[str, str] = {}
    for name in ("best.pt", "last.pt"):
        src = run_dir / "weights" / name
        if src.exists():
            dst = weights_dir / name
            shutil.copy2(src, dst)
            copied[name] = str(dst)
    return copied


def build_manifest(
    cfg: dict[str, Any],
    model_key: str,
    model_cfg: dict[str, Any],
    run_dir: Path,
    dataset_info: dict[str, Any],
    copied_weights: dict[str, str],
) -> dict[str, Any]:
    return {
        "model_name": model_key,
        "model_arch": model_cfg.get("model", "yolo11s.pt"),
        "framework": "ultralytics",
        "task": "object_detection",
        "prediction_contract": cfg.get("runtime_contract", {}),
        "dataset": dataset_info,
        "confidence_threshold": model_cfg.get("confidence_threshold", 0.35),
        "iou_threshold": model_cfg.get("iou_threshold", 0.6),
        "config_hash": config_hash(cfg),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "weights": copied_weights,
    }


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    cfg = load_config(config_path)
    model_cfg = cfg.get(args.model_key)
    if not isinstance(model_cfg, dict):
        raise KeyError(f"Missing config section: {args.model_key}")

    def _handle_stop(signum, frame):
        raise KeyboardInterrupt(f"received signal {signum}")

    signal.signal(signal.SIGTERM, _handle_stop)

    data_yaml = resolve_path(model_cfg["data_yaml"], config_path)
    required_classes = cfg.get("traffic_classes", [])
    dataset_info = validate_dataset(data_yaml, required_classes)

    vol_root = args.vol_root
    default_run_root = vol_root / "runs" if vol_root else Path("runs")
    run_dir = args.run_dir or default_run_root / args.model_key
    run_dir = run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    weights_dir = args.weights_dir or (vol_root / "weights" / args.model_key if vol_root else run_dir / "exported_weights")
    weights_dir = weights_dir.resolve()

    from ultralytics import YOLO

    last_ckpt = run_dir / "weights" / "last.pt"
    if args.fresh or not last_ckpt.exists():
        model_path = model_cfg.get("model", "yolo11s.pt")
    else:
        model_path = str(last_ckpt)
    model = YOLO(model_path)

    epochs = args.epochs or model_cfg.get("epochs", 100)
    batch_size = args.batch_size or model_cfg.get("batch_size", 16)
    device = args.device or ("cuda:0" if cuda_available() else "cpu")

    console.rule(f"[bold magenta]Training {args.model_key}")
    console.print(f"data={data_yaml} epochs={epochs} batch={batch_size} device={device}")

    metrics: dict[str, Any] = {}
    copied_weights: dict[str, str] = {}
    try:
        results = model.train(
            data=str(data_yaml),
            epochs=epochs,
            batch=batch_size,
            imgsz=model_cfg.get("img_size", 640),
            patience=model_cfg.get("patience", 20),
            workers=model_cfg.get("workers", 8),
            device=device,
            project=str(run_dir.parent),
            name=run_dir.name,
            exist_ok=True,
            save=True,
            save_period=1,
            seed=cfg.get("project", {}).get("seed", 42),
            verbose=True,
        )
        raw_metrics = getattr(results, "results_dict", {}) or {}
        metrics = {str(k): float(v) for k, v in raw_metrics.items() if isinstance(v, (int, float))}
    except KeyboardInterrupt as exc:
        console.print(f"[yellow]Training interrupted: {exc}. Saving available artifacts.[/yellow]")
    finally:
        copied_weights = copy_weights(run_dir, weights_dir)
        atomic_json(run_dir / "metrics.json", metrics)
        manifest = build_manifest(cfg, args.model_key, model_cfg, run_dir, dataset_info, copied_weights)
        atomic_json(run_dir / "manifest.json", manifest)
        if weights_dir != run_dir:
            atomic_json(weights_dir / "manifest.json", manifest)
            atomic_json(weights_dir / "metrics.json", metrics)

    if "last.pt" not in copied_weights:
        console.print("[red]No last.pt checkpoint was produced.[/red]")
        sys.exit(1)
    console.print(f"[green]Done. Weights copied to {weights_dir}[/green]")


if __name__ == "__main__":
    main()
