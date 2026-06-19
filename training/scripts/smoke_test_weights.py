"""Verify detector weights/runtime artifacts load."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

VALID_MODELS = ("fast_detector", "accuracy_detector", "plate", "seatbelt")
ALIASES = {"vehicle": "fast_detector", "fast": "fast_detector", "accuracy": "accuracy_detector"}


def normalize_model(value: str) -> str:
    return ALIASES.get(value, value)


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def expected_classes(config: dict, model_type: str) -> int:
    if model_type in ("fast_detector", "accuracy_detector"):
        return len(config.get("traffic_classes", []))
    if model_type == "plate":
        return 1
    if model_type == "seatbelt":
        return len(config.get("seatbelt_classes", []))
    return 0


def verify_yolo_pt(weights_path: Path, expected: int, model_type: str, device: str) -> bool:
    from ultralytics import YOLO

    model = YOLO(str(weights_path))
    result = model.predict(Image.new("RGB", (640, 640), color=(128, 128, 128)), device=device, verbose=False)[0]
    names = getattr(result, "names", {})
    if len(names) != expected:
        log.error("%s class count mismatch: expected %s got %s", model_type, expected, len(names))
        return False
    if not hasattr(result, "boxes"):
        log.error("%s result has no boxes collection", model_type)
        return False
    log.info("%s .pt load PASS with %d classes", model_type, len(names))
    return True


def verify_torch_checkpoint(weights_path: Path, model_type: str) -> bool:
    import torch

    checkpoint = torch.load(weights_path, map_location="cpu", weights_only=False)
    if checkpoint is None:
        log.error("%s checkpoint is empty", model_type)
        return False
    log.info("%s checkpoint structural load PASS", model_type)
    return True


def verify_onnx(onnx_path: Path, model_type: str) -> bool:
    import onnxruntime as ort

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    inputs = session.get_inputs()
    if not inputs:
        log.error("%s ONNX has no inputs", model_type)
        return False
    shape = [dim if isinstance(dim, int) else 640 for dim in inputs[0].shape]
    dummy = np.zeros(shape, dtype=np.float32)
    outputs = session.run(None, {inputs[0].name: dummy})
    if not outputs:
        log.error("%s ONNX returned no outputs", model_type)
        return False
    log.info("%s ONNX load PASS with %d output tensors", model_type, len(outputs))
    return True


def verify_model(config: dict, root: Path, model_type: str, device: str) -> bool:
    model_dir = root / model_type
    if not model_dir.exists():
        log.warning("Skipping %s: missing directory %s", model_type, model_dir)
        return True

    manifest_path = model_dir / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        outputs = manifest.get("runtime_contract", {}).get("outputs", [])
        required = {"bbox_xyxy", "confidence", "class_id", "class_name"}
        if not required.issubset(set(outputs)):
            log.error("%s manifest missing detector output contract: %s", model_type, outputs)
            return False

    expected = expected_classes(config, model_type)
    pt_candidates = list(model_dir.glob("*best*.pt")) or list(model_dir.glob("best.pt"))
    onnx_candidates = list(model_dir.glob("*.onnx"))

    ok = True
    if pt_candidates:
        if model_type in ("fast_detector", "plate", "seatbelt"):
            ok = verify_yolo_pt(pt_candidates[0], expected, model_type, device) and ok
        else:
            ok = verify_torch_checkpoint(pt_candidates[0], model_type) and ok
    if onnx_candidates:
        ok = verify_onnx(onnx_candidates[0], model_type) and ok
    if not pt_candidates and not onnx_candidates:
        log.error("%s has no .pt or .onnx artifacts in %s", model_type, model_dir)
        return False
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify detector weights/runtime artifacts")
    parser.add_argument("--config", required=True)
    parser.add_argument("--weights-dir", required=True)
    parser.add_argument("--models", default="fast_detector,accuracy_detector,plate,seatbelt")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    config = load_config(args.config)
    root = Path(args.weights_dir)
    if not root.exists():
        log.error("Weights directory does not exist: %s", root)
        sys.exit(1)

    results: dict[str, bool] = {}
    for model_type in [normalize_model(m.strip()) for m in args.models.split(",") if m.strip()]:
        if model_type not in VALID_MODELS:
            log.error("Unknown model: %s", model_type)
            sys.exit(1)
        try:
            results[model_type] = verify_model(config, root, model_type, args.device)
        except Exception as exc:
            log.error("%s verification failed: %s", model_type, exc)
            results[model_type] = False

    print("\nWEIGHTS VERIFICATION RESULTS")
    for name, passed in results.items():
        print(f"  {name:18s}: {'PASS' if passed else 'FAIL'}")
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
