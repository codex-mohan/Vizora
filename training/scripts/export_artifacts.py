from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table

console = Console()

MODEL_META = {
    "fast_detector": {
        "config_key": "fast_detector",
        "best_name": "yolo11s_indian_traffic_best.pt",
        "last_name": "yolo11s_indian_traffic_last.pt",
        "onnx_name": "yolo11s_indian_traffic.onnx",
        "engine_name": "yolo11s_indian_traffic.engine",
        "ultralytics": True,
    },
    "accuracy_detector": {
        "config_key": "accuracy_detector",
        "best_name": "rtdetrv2_indian_traffic_best.pt",
        "last_name": "rtdetrv2_indian_traffic_last.pt",
        "onnx_name": "rtdetrv2_indian_traffic.onnx",
        "engine_name": "rtdetrv2_indian_traffic.engine",
        "ultralytics": False,
    },
    "plate": {
        "config_key": "plate_detector",
        "best_name": "yolo11_plate_india_best.pt",
        "last_name": "yolo11_plate_india_last.pt",
        "onnx_name": "yolo11_plate_india.onnx",
        "engine_name": "yolo11_plate_india.engine",
        "ultralytics": True,
    },
    "seatbelt": {
        "config_key": "seatbelt_detector",
        "best_name": "yolo11_seatbelt_best.pt",
        "last_name": "yolo11_seatbelt_last.pt",
        "onnx_name": "yolo11_seatbelt.onnx",
        "engine_name": "yolo11_seatbelt.engine",
        "ultralytics": True,
    },
}

ALIASES = {
    "vehicle": "fast_detector",
    "fast": "fast_detector",
    "accuracy": "accuracy_detector",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export detector artifacts for runtime.")
    parser.add_argument("--config", type=str, default="configs/training.yaml")
    parser.add_argument("--model-type", required=True, choices=[*MODEL_META.keys(), *ALIASES.keys()])
    parser.add_argument("--run-dir", type=str, default=None)
    parser.add_argument("--weights-dir", type=str, default=None)
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--vol-root", type=str, default=None)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--skip-engine", action="store_true")
    return parser.parse_args()


def normalize_model_type(value: str) -> str:
    return ALIASES.get(value, value)


def load_config(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_weight(base: Path, variant: str) -> Path | None:
    names = [f"{variant}.pt", f"{variant}.pth"]
    for name in names:
        candidate = base / name
        if candidate.exists():
            return candidate
    for pattern in (f"*{variant}*.pt", f"*{variant}*.pth"):
        matches = list(base.rglob(pattern))
        if matches:
            return matches[0]
    nested = base / "weights"
    if nested.exists():
        return find_weight(nested, variant)
    return None


def copy_if_exists(src: Path | None, dst: Path, file_hashes: dict[str, str], exported: list[str]) -> None:
    if src is None or not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    file_hashes[dst.name] = compute_sha256(dst)
    exported.append(dst.name)


def export_yolo(best_path: Path, output_dir: Path, meta: dict[str, Any], cfg: dict[str, Any], device: str, skip_engine: bool) -> dict[str, Any]:
    from ultralytics import YOLO

    export_cfg = cfg.get("export", {})
    model = YOLO(str(best_path))
    status: dict[str, Any] = {"onnx": "not_requested", "engine": "not_requested"}

    if export_cfg.get("include_onnx", True):
        try:
            onnx_path = Path(
                model.export(
                    format="onnx",
                    opset=export_cfg.get("opset", 17),
                    imgsz=cfg.get(meta["config_key"], {}).get("img_size", 640),
                    half=False,
                    dynamic=export_cfg.get("dynamic", False),
                    device=device,
                )
            )
            copy_if_exists(onnx_path, output_dir / meta["onnx_name"], {}, [])
            status["onnx"] = "ok"
        except Exception as exc:
            status["onnx"] = f"failed: {exc}"

    if export_cfg.get("include_engine", True) and not skip_engine:
        try:
            engine_path = Path(
                model.export(
                    format="engine",
                    imgsz=cfg.get(meta["config_key"], {}).get("img_size", 640),
                    half=export_cfg.get("half", True),
                    dynamic=export_cfg.get("dynamic", False),
                    device=device,
                )
            )
            copy_if_exists(engine_path, output_dir / meta["engine_name"], {}, [])
            status["engine"] = "ok"
        except Exception as exc:
            status["engine"] = f"skipped: {exc}"
    return status


def collect_runtime_hashes(output_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in output_dir.iterdir():
        if path.is_file() and path.name != "manifest.json":
            hashes[path.name] = compute_sha256(path)
    return hashes


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    model_type = normalize_model_type(args.model_type)
    meta = MODEL_META[model_type]
    vol_root = Path(args.vol_root) if args.vol_root else None

    if args.weights_dir:
        source_dir = Path(args.weights_dir)
    elif args.run_dir:
        source_dir = Path(args.run_dir)
    elif vol_root:
        source_dir = vol_root / "weights" / model_type
    else:
        source_dir = Path("runs") / model_type

    if args.output_dir:
        output_dir = Path(args.output_dir)
    elif vol_root:
        output_dir = vol_root / "releases" / model_type
    else:
        output_dir = Path("artifacts") / model_type
    output_dir.mkdir(parents=True, exist_ok=True)

    best = find_weight(source_dir, "best")
    last = find_weight(source_dir, "last")
    if best is None:
        console.print(f"[red]No best checkpoint found under {source_dir}[/red]")
        sys.exit(1)

    exported: list[str] = []
    file_hashes: dict[str, str] = {}
    copy_if_exists(best, output_dir / meta["best_name"], file_hashes, exported)
    copy_if_exists(last, output_dir / meta["last_name"], file_hashes, exported)

    export_status: dict[str, Any]
    if meta["ultralytics"]:
        export_status = export_yolo(best, output_dir, meta, config, args.device, args.skip_engine)
    else:
        existing_onnx = next(iter(source_dir.rglob("*.onnx")), None)
        existing_engine = next(iter(source_dir.rglob("*.engine")), None)
        copy_if_exists(existing_onnx, output_dir / meta["onnx_name"], file_hashes, exported)
        copy_if_exists(existing_engine, output_dir / meta["engine_name"], file_hashes, exported)
        export_status = {
            "onnx": "copied" if existing_onnx else "missing: export with official RT-DETRv2 deployment tools",
            "engine": "copied" if existing_engine else "missing: build TensorRT engine after ONNX export",
        }

    file_hashes.update(collect_runtime_hashes(output_dir))
    manifest = {
        "model_type": model_type,
        "runtime_contract": config.get("runtime_contract", {}),
        "source_dir": str(source_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "hf_repo": config.get("hf_repos", {}).get(model_type, ""),
        "export_status": export_status,
        "files": sorted(file_hashes),
        "file_hashes": file_hashes,
        "requires_runtime": ["onnx", "tensorrt"],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    table = Table(title="Runtime Export")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("model_type", model_type)
    table.add_row("source_dir", str(source_dir))
    table.add_row("output_dir", str(output_dir))
    table.add_row("files", ", ".join(sorted(file_hashes)))
    table.add_row("onnx", str(export_status.get("onnx")))
    table.add_row("engine", str(export_status.get("engine")))
    console.print(table)


if __name__ == "__main__":
    main()
