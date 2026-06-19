from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
from rich.console import Console
from rich.table import Table

console = Console()
ALIASES = {"vehicle": "fast_detector", "fast": "fast_detector", "accuracy": "accuracy_detector"}
YOLO_MODELS = {"fast_detector", "plate", "seatbelt"}


def normalize_model(value: str) -> str:
    return ALIASES.get(value, value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate detector models")
    parser.add_argument("--config", type=str, default="configs/training.yaml")
    parser.add_argument("--model-type", required=True, choices=["fast_detector", "accuracy_detector", "plate", "seatbelt", *ALIASES.keys()])
    parser.add_argument("--weights", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--conf-threshold", type=float, default=0.5)
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    parser.add_argument("--output-dir", default="evaluation_output")
    return parser.parse_args()


def measure_yolo_latency(model: Any, device: str) -> dict[str, float]:
    dummy = np.zeros((640, 640, 3), dtype=np.uint8)
    for _ in range(5):
        model.predict(dummy, device=device, verbose=False)
    times: list[float] = []
    for _ in range(30):
        start = time.perf_counter()
        model.predict(dummy, device=device, verbose=False)
        times.append((time.perf_counter() - start) * 1000)
    return {
        "mean_ms": float(np.mean(times)),
        "p50_ms": float(np.percentile(times, 50)),
        "p95_ms": float(np.percentile(times, 95)),
    }


def evaluate_yolo(args: argparse.Namespace, model_type: str, output_dir: Path) -> dict[str, Any]:
    import cv2
    from ultralytics import YOLO

    model = YOLO(args.weights)
    results = model.val(
        data=args.data,
        device=args.device,
        conf=args.conf_threshold,
        iou=args.iou_threshold,
        plots=False,
        verbose=False,
    )
    metrics: dict[str, Any] = {
        "mAP50": float(results.box.map50),
        "mAP50-95": float(results.box.map),
        "precision": float(results.box.mp),
        "recall": float(results.box.mr),
        "prediction_contract": ["bbox_xyxy", "confidence", "class_id", "class_name"],
        "per_class_ap": {},
        "latency": measure_yolo_latency(model, args.device),
    }
    names = results.names
    for cls_id, ap in enumerate(results.box.ap):
        name = names.get(cls_id, f"class_{cls_id}")
        metrics["per_class_ap"][name] = {"AP50-95": float(ap), "AP50": float(results.box.ap50[cls_id])}

    sample_dir = output_dir / "sample_predictions"
    sample_dir.mkdir(parents=True, exist_ok=True)
    images = list((Path(args.data).parent / "images" / "val").glob("*.*"))
    if not images:
        images = list(Path(args.data).rglob("*.jpg"))
    for idx, image in enumerate(images[:20]):
        pred = model.predict(str(image), conf=args.conf_threshold, verbose=False)[0]
        cv2.imwrite(str(sample_dir / f"sample_{idx:03d}.jpg"), pred.plot())
    return metrics


def main() -> None:
    args = parse_args()
    model_type = normalize_model(args.model_type)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if model_type in YOLO_MODELS:
        metrics = evaluate_yolo(args, model_type, output_dir)
    else:
        metrics = {
            "status": "blocked",
            "detail": "Use the official RT-DETRv2 eval tooling with COCO-format data for accuracy_detector.",
            "prediction_contract": ["bbox_xyxy", "confidence", "class_id", "class_name"],
        }

    result = {
        "model_type": model_type,
        "weights": str(Path(args.weights).resolve()),
        "data": args.data,
        "metrics": metrics,
    }
    (output_dir / "evaluation_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    table = Table(title=f"{model_type} Evaluation")
    table.add_column("Metric")
    table.add_column("Value")
    for key in ("mAP50", "mAP50-95", "precision", "recall", "status"):
        if key in metrics:
            table.add_row(key, str(metrics[key]))
    if "latency" in metrics:
        table.add_row("p95 latency", f"{metrics['latency']['p95_ms']:.1f} ms")
    console.print(table)


if __name__ == "__main__":
    main()
