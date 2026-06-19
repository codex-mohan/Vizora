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
    parser = argparse.ArgumentParser(description="Train YOLO11 seatbelt detector.")
    parser.add_argument("--config", type=Path, default=Path("configs/training.yaml"))
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


def class_names_from_yaml(data: dict[str, Any]) -> list[str]:
    names = data.get("names", [])
    if isinstance(names, dict):
        return [str(names[k]) for k in sorted(names, key=lambda x: int(x))]
    return [str(name) for name in names]


def label_path_for_image(image_path: Path) -> Path:
    parts = list(image_path.parts)
    if "images" in parts:
        idx = parts.index("images")
        parts[idx] = "labels"
        return Path(*parts).with_suffix(".txt")
    return image_path.with_suffix(".txt")


def validate_dataset(data_yaml: Path, required_classes: list[str]) -> dict[str, Any]:
    console.rule("[bold cyan]Seatbelt Dataset Validation")
    if not data_yaml.exists():
        raise FileNotFoundError(f"YOLO data yaml not found: {data_yaml}")
    with data_yaml.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    class_names = class_names_from_yaml(data)
    missing = [name for name in required_classes if name not in class_names]
    if missing:
        raise ValueError("Missing required seatbelt classes: " + ", ".join(missing))

    root = data_yaml.parent / data.get("path", ".")
    class_counts: Counter[str] = Counter()
    image_count = 0
    for split in ("train", "val"):
        value = data.get(split)
        if value is None:
            raise ValueError(f"Missing {split} split in {data_yaml}")
        split_dir = Path(value) if Path(value).is_absolute() else (root / value).resolve()
        if not split_dir.exists():
            raise FileNotFoundError(f"Missing {split} image directory: {split_dir}")
        images = [p for p in split_dir.rglob("*") if p.suffix.lower() in SUPPORTED_IMG_EXT]
        image_count += len(images)
        for image in images:
            label = label_path_for_image(image)
            if not label.exists():
                continue
            for line in label.read_text(encoding="utf-8").splitlines():
                parts = line.strip().split()
                if len(parts) >= 5:
                    class_id = int(float(parts[0]))
                    if class_id < len(class_names):
                        class_counts[class_names[class_id]] += 1

    if image_count == 0:
        raise ValueError("No seatbelt training/validation images found")

    table = Table(title="Seatbelt Class Distribution")
    table.add_column("Class")
    table.add_column("Boxes", justify="right")
    for name in class_names:
        table.add_row(name, str(class_counts.get(name, 0)))
    console.print(table)
    return {
        "data_yaml": str(data_yaml),
        "class_map": {i: name for i, name in enumerate(class_names)},
        "class_counts": dict(class_counts),
        "image_count": image_count,
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


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    cfg = load_config(config_path)
    model_cfg = cfg["seatbelt_detector"]

    def _handle_stop(signum, frame):
        raise KeyboardInterrupt(f"received signal {signum}")

    signal.signal(signal.SIGTERM, _handle_stop)

    data_yaml = Path(model_cfg["data_yaml"])
    if not data_yaml.is_absolute():
        data_yaml = (config_path.parent / data_yaml).resolve()
    dataset_info = validate_dataset(data_yaml, cfg.get("seatbelt_classes", []))

    vol_root = args.vol_root
    default_run_root = vol_root / "runs" if vol_root else Path("runs")
    run_dir = (args.run_dir or default_run_root / "seatbelt").resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    weights_dir = (args.weights_dir or (vol_root / "weights" / "seatbelt" if vol_root else run_dir / "exported_weights")).resolve()

    from ultralytics import YOLO

    last_ckpt = run_dir / "weights" / "last.pt"
    model_path = model_cfg.get("model", "yolo11s.pt") if args.fresh or not last_ckpt.exists() else str(last_ckpt)
    model = YOLO(model_path)

    epochs = args.epochs or model_cfg.get("epochs", 60)
    batch_size = args.batch_size or model_cfg.get("batch_size", 16)
    device = args.device or ("cuda:0" if cuda_available() else "cpu")
    metrics: dict[str, Any] = {}
    copied_weights: dict[str, str] = {}

    console.rule("[bold magenta]Training Seatbelt Detector")
    try:
        results = model.train(
            data=str(data_yaml),
            epochs=epochs,
            batch=batch_size,
            imgsz=model_cfg.get("img_size", 640),
            patience=model_cfg.get("patience", 15),
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
        manifest = {
            "model_name": "seatbelt",
            "model_arch": model_cfg.get("model", "yolo11s.pt"),
            "framework": "ultralytics",
            "task": "object_detection",
            "prediction_contract": cfg.get("runtime_contract", {}),
            "dataset": dataset_info,
            "confidence_threshold": model_cfg.get("confidence_threshold", 0.45),
            "iou_threshold": model_cfg.get("iou_threshold", 0.6),
            "config_hash": config_hash(cfg),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "run_dir": str(run_dir),
            "review_only_if_weak_data": model_cfg.get("review_only_if_weak_data", True),
            "weights": copied_weights,
        }
        atomic_json(run_dir / "manifest.json", manifest)
        atomic_json(weights_dir / "manifest.json", manifest)
        atomic_json(weights_dir / "metrics.json", metrics)

    if "last.pt" not in copied_weights:
        console.print("[red]No last.pt checkpoint was produced.[/red]")
        sys.exit(1)
    console.print(f"[green]Done. Weights copied to {weights_dir}[/green]")


if __name__ == "__main__":
    main()
