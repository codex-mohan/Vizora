"""Benchmark script: runs pipeline on sample images and computes metrics.

Usage:
    uv run python scripts/benchmark.py --input data/samples/ --annotations data/annotations/
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np


@dataclass
class StageLatency:
    preprocess_ms: float = 0.0
    detect_ms: float = 0.0
    classify_ms: float = 0.0
    anpr_ms: float = 0.0
    total_ms: float = 0.0


@dataclass
class ViolationMetrics:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


@dataclass
class OCRMetrics:
    exact_matches: int = 0
    total_chars: int = 0
    correct_chars: int = 0
    total_plates: int = 0

    @property
    def exact_match_accuracy(self) -> float:
        return self.exact_matches / self.total_plates if self.total_plates > 0 else 0.0

    @property
    def char_accuracy(self) -> float:
        return self.correct_chars / self.total_chars if self.total_chars > 0 else 0.0


@dataclass
class BenchmarkResult:
    per_violation: dict[str, ViolationMetrics] = field(default_factory=dict)
    ocr: OCRMetrics = field(default_factory=OCRMetrics)
    latencies: list[StageLatency] = field(default_factory=list)

    @property
    def avg_latency(self) -> StageLatency:
        if not self.latencies:
            return StageLatency()
        n = len(self.latencies)
        return StageLatency(
            preprocess_ms=sum(l.preprocess_ms for l in self.latencies) / n,
            detect_ms=sum(l.detect_ms for l in self.latencies) / n,
            classify_ms=sum(l.classify_ms for l in self.latencies) / n,
            anpr_ms=sum(l.anpr_ms for l in self.latencies) / n,
            total_ms=sum(l.total_ms for l in self.latencies) / n,
        )


def load_ground_truth(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_pipeline_on_image(image_path: Path) -> tuple[list[dict[str, Any]], str | None, StageLatency]:
    """Run the full pipeline on a single image. Returns (violations, plate_text, latency)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from pipeline.contracts import MediaInput, ProcessingMode

    latency = StageLatency()

    img = cv2.imread(str(image_path))
    if img is None:
        return [], None, latency

    _, buf = cv2.imencode(".jpg", img)
    image_bytes = buf.tobytes()

    media = MediaInput(
        filename=image_path.name,
        content_type="image/jpeg",
        data=image_bytes,
        mode=ProcessingMode.STILL_IMAGE,
    )

    try:
        from pipeline.infer import run_inference
        t0 = time.perf_counter()
        result = run_inference(media)
        latency.total_ms = (time.perf_counter() - t0) * 1000

        violations = [
            {
                "type": v.violation_type.value,
                "bbox": [v.bbox.x1, v.bbox.y1, v.bbox.x2, v.bbox.y2] if v.bbox else None,
                "confidence": v.confidence,
            }
            for v in result.violations
        ]
        plate_text = None
        if result.plates:
            best = max(result.plates, key=lambda p: p.confidence)
            plate_text = best.plate_text

        return violations, plate_text, latency

    except ImportError:
        return [], None, latency


def compute_iou(box_a: list[float], box_b: list[float]) -> float:
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def evaluate_violations(
    predicted: list[dict[str, Any]],
    ground_truth: list[dict[str, Any]],
    iou_threshold: float = 0.5,
) -> tuple[int, int, int]:
    tp, fp, fn = 0, 0, 0
    matched_gt: set[int] = set()

    for pred in predicted:
        pred_type = pred["type"]
        pred_bbox = pred.get("bbox")
        found = False
        for j, gt in enumerate(ground_truth):
            if j in matched_gt:
                continue
            if gt["type"] != pred_type:
                continue
            gt_bbox = gt.get("bbox")
            if pred_bbox and gt_bbox and compute_iou(pred_bbox, gt_bbox) >= iou_threshold:
                tp += 1
                matched_gt.add(j)
                found = True
                break
        if not found:
            fp += 1

    fn = len(ground_truth) - len(matched_gt)
    return tp, fp, fn


def char_accuracy(predicted: str, ground_truth: str) -> tuple[int, int]:
    correct = sum(1 for a, b in zip(predicted, ground_truth) if a == b)
    total = max(len(predicted), len(ground_truth))
    return correct, total


def print_results(result: BenchmarkResult) -> None:
    print("\n" + "=" * 70)
    print("  VIZORA PIPELINE BENCHMARK RESULTS")
    print("=" * 70)

    print("\n--- Violation Detection Metrics ---")
    print(f"{'Type':<20} {'TP':>4} {'FP':>4} {'FN':>4} {'Prec':>7} {'Recall':>7} {'F1':>7}")
    print("-" * 60)
    for vtype, m in sorted(result.per_violation.items()):
        print(f"{vtype:<20} {m.tp:>4} {m.fp:>4} {m.fn:>4} {m.precision:>7.3f} {m.recall:>7.3f} {m.f1:>7.3f}")

    total_tp = sum(m.tp for m in result.per_violation.values())
    total_fp = sum(m.fp for m in result.per_violation.values())
    total_fn = sum(m.fn for m in result.per_violation.values())
    macro_p = sum(m.precision for m in result.per_violation.values()) / len(result.per_violation) if result.per_violation else 0
    macro_r = sum(m.recall for m in result.per_violation.values()) / len(result.per_violation) if result.per_violation else 0
    macro_f1 = sum(m.f1 for m in result.per_violation.values()) / len(result.per_violation) if result.per_violation else 0
    print("-" * 60)
    print(f"{'MACRO':<20} {total_tp:>4} {total_fp:>4} {total_fn:>4} {macro_p:>7.3f} {macro_r:>7.3f} {macro_f1:>7.3f}")

    print("\n--- Plate OCR Metrics ---")
    print(f"  Exact match accuracy: {result.ocr.exact_match_accuracy:.3f} ({result.ocr.exact_matches}/{result.ocr.total_plates})")
    print(f"  Character accuracy:   {result.ocr.char_accuracy:.3f} ({result.ocr.correct_chars}/{result.ocr.total_chars})")

    avg = result.avg_latency
    print("\n--- Average Latency (ms) ---")
    print(f"  Preprocess: {avg.preprocess_ms:>8.2f}")
    print(f"  Detect:     {avg.detect_ms:>8.2f}")
    print(f"  Classify:   {avg.classify_ms:>8.2f}")
    print(f"  ANPR:       {avg.anpr_ms:>8.2f}")
    print(f"  Total:      {avg.total_ms:>8.2f}")
    print("=" * 70)


def main() -> None:
    parser = argparse.ArgumentParser(description="Vizora pipeline benchmark")
    parser.add_argument("--input", type=str, required=True, help="Directory with sample images")
    parser.add_argument("--annotations", type=str, required=True, help="Directory with ground truth JSON files")
    parser.add_argument("--output", type=str, default="data/benchmark_results.json", help="Output JSON path")
    args = parser.parse_args()

    input_dir = Path(args.input)
    annotations_dir = Path(args.annotations)

    if not input_dir.exists():
        print(f"Input directory not found: {input_dir}")
        print("Add sample images to run the benchmark.")
        return

    image_files = sorted(
        [f for f in input_dir.iterdir() if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp")]
    )
    if not image_files:
        print(f"No images found in {input_dir}")
        print("Add .jpg/.png/.bmp files to run the benchmark.")
        return

    gt_path = annotations_dir / "ground_truth.json"
    if not gt_path.exists():
        print(f"Ground truth file not found: {gt_path}")
        print("Create a ground_truth.json file with violation annotations.")
        return

    ground_truth = load_ground_truth(gt_path)
    benchmark = BenchmarkResult()

    print(f"Running benchmark on {len(image_files)} images...")

    for img_path in image_files:
        gt = ground_truth.get(img_path.name)
        if gt is None:
            continue

        predicted_violations, predicted_plate, latency = run_pipeline_on_image(img_path)
        benchmark.latencies.append(latency)

        gt_violations = gt.get("violations", [])
        for pred in predicted_violations:
            vtype = pred["type"]
            if vtype not in benchmark.per_violation:
                benchmark.per_violation[vtype] = ViolationMetrics()
        for gt_v in gt_violations:
            vtype = gt_v["type"]
            if vtype not in benchmark.per_violation:
                benchmark.per_violation[vtype] = ViolationMetrics()

        tp, fp, fn = evaluate_violations(predicted_violations, gt_violations)
        if predicted_violations:
            by_type: dict[str, tuple[list[dict], list[dict]]] = {}
            for pred in predicted_violations:
                by_type.setdefault(pred["type"], ([], []))[0].append(pred)
            for gt_v in gt_violations:
                by_type.setdefault(gt_v["type"], ([], []))[1].append(gt_v)
            for vtype, (preds, gts) in by_type.items():
                t, f, n = evaluate_violations(preds, gts)
                m = benchmark.per_violation.setdefault(vtype, ViolationMetrics())
                m.tp += t
                m.fp += f
                m.fn += n
        else:
            for gt_v in gt_violations:
                m = benchmark.per_violation.setdefault(gt_v["type"], ViolationMetrics())
                m.fn += 1

        gt_plate = gt.get("plate_text")
        if gt_plate:
            benchmark.ocr.total_plates += 1
            if predicted_plate:
                if predicted_plate == gt_plate:
                    benchmark.ocr.exact_matches += 1
                c, t = char_accuracy(predicted_plate, gt_plate)
                benchmark.ocr.correct_chars += c
                benchmark.ocr.total_chars += t
            else:
                benchmark.ocr.total_chars += len(gt_plate)

    print_results(benchmark)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_data = {
        "per_violation": {
            k: {"precision": m.precision, "recall": m.recall, "f1": m.f1, "tp": m.tp, "fp": m.fp, "fn": m.fn}
            for k, m in benchmark.per_violation.items()
        },
        "ocr": {
            "exact_match_accuracy": benchmark.ocr.exact_match_accuracy,
            "char_accuracy": benchmark.ocr.char_accuracy,
            "exact_matches": benchmark.ocr.exact_matches,
            "total_plates": benchmark.ocr.total_plates,
        },
        "avg_latency_ms": {
            "preprocess": benchmark.avg_latency.preprocess_ms,
            "detect": benchmark.avg_latency.detect_ms,
            "classify": benchmark.avg_latency.classify_ms,
            "anpr": benchmark.avg_latency.anpr_ms,
            "total": benchmark.avg_latency.total_ms,
        },
        "num_images": len(image_files),
    }
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
