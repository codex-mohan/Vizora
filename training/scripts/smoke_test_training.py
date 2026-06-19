"""Run smoke tests for detector training paths using synthetic data."""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import tempfile
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


def write_detection_dataset(root: Path, class_names: list[str], image_count: int, img_size: int) -> Path:
    data_dir = root / "data"
    for split in ("train", "val"):
        image_dir = data_dir / "images" / split
        label_dir = data_dir / "labels" / split
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        for idx in range(image_count):
            img = Image.new(
                "RGB",
                (img_size, img_size),
                color=(int(np.random.randint(0, 255)), int(np.random.randint(0, 255)), int(np.random.randint(0, 255))),
            )
            img.save(image_dir / f"{idx:06d}.jpg")
            cls = idx % len(class_names)
            label = label_dir / f"{idx:06d}.txt"
            label.write_text(f"{cls} 0.500000 0.500000 0.300000 0.300000\n", encoding="utf-8")
    data_yaml = data_dir / "data.yaml"
    data_yaml.write_text(
        yaml.safe_dump(
            {
                "path": str(data_dir),
                "train": "images/train",
                "val": "images/val",
                "nc": len(class_names),
                "names": {i: name for i, name in enumerate(class_names)},
            }
        ),
        encoding="utf-8",
    )
    return data_yaml


def write_temp_config(base: dict, tmp: Path, model_type: str, data_yaml: Path) -> Path:
    cfg = json.loads(json.dumps(base))
    if model_type == "fast_detector":
        cfg["fast_detector"]["data_yaml"] = str(data_yaml)
        cfg["fast_detector"]["epochs"] = cfg.get("smoke_test", {}).get("fast_detector", {}).get("epochs", 1)
        cfg["fast_detector"]["batch_size"] = 4
        cfg["fast_detector"]["workers"] = 0
    elif model_type == "plate":
        cfg["plate_detector"]["data_yaml"] = str(data_yaml)
        cfg["plate_detector"]["epochs"] = cfg.get("smoke_test", {}).get("plate", {}).get("epochs", 1)
        cfg["plate_detector"]["batch_size"] = 4
        cfg["plate_detector"]["workers"] = 0
    elif model_type == "seatbelt":
        cfg["seatbelt_detector"]["data_yaml"] = str(data_yaml)
        cfg["seatbelt_detector"]["epochs"] = cfg.get("smoke_test", {}).get("seatbelt", {}).get("epochs", 1)
        cfg["seatbelt_detector"]["batch_size"] = 4
        cfg["seatbelt_detector"]["workers"] = 0

    path = tmp / "training.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return path


def run_script(script_name: str, args: list[str]) -> bool:
    script = Path(__file__).resolve().parent / script_name
    completed = subprocess.run([sys.executable, str(script), *args], text=True, capture_output=True)
    if completed.returncode != 0:
        log.error("%s failed\nSTDOUT:\n%s\nSTDERR:\n%s", script_name, completed.stdout[-2000:], completed.stderr[-2000:])
        return False
    return True


def run_yolo_smoke(config: dict, tmp: Path, model_type: str, device: str) -> bool:
    if model_type == "fast_detector":
        class_names = config["traffic_classes"]
        data_yaml = write_detection_dataset(tmp, class_names, config.get("smoke_test", {}).get("fast_detector", {}).get("images", 16), 320)
        cfg_path = write_temp_config(config, tmp, model_type, data_yaml)
        return run_script(
            "train_yolo_detector.py",
            [
                "--config",
                str(cfg_path),
                "--model-key",
                "fast_detector",
                "--run-dir",
                str(tmp / "runs" / "fast_detector"),
                "--weights-dir",
                str(tmp / "weights" / "fast_detector"),
                "--device",
                device,
                "--fresh",
            ],
        )
    if model_type == "plate":
        data_yaml = write_detection_dataset(tmp, ["license_plate"], config.get("smoke_test", {}).get("plate", {}).get("images", 16), 320)
        cfg_path = write_temp_config(config, tmp, model_type, data_yaml)
        return run_script(
            "train_yolo_plate.py",
            [
                "--config",
                str(cfg_path),
                "--run-dir",
                str(tmp / "runs" / "plate"),
                "--weights-dir",
                str(tmp / "weights" / "plate"),
                "--device",
                device,
                "--fresh",
            ],
        )
    if model_type == "seatbelt":
        data_yaml = write_detection_dataset(tmp, config["seatbelt_classes"], config.get("smoke_test", {}).get("seatbelt", {}).get("images", 16), 320)
        cfg_path = write_temp_config(config, tmp, model_type, data_yaml)
        return run_script(
            "train_yolo_seatbelt_detector.py",
            [
                "--config",
                str(cfg_path),
                "--run-dir",
                str(tmp / "runs" / "seatbelt"),
                "--weights-dir",
                str(tmp / "weights" / "seatbelt"),
                "--device",
                device,
                "--fresh",
            ],
        )
    raise ValueError(model_type)


def run_accuracy_smoke(config: dict, tmp: Path) -> bool:
    cfg_path = tmp / "training.yaml"
    cfg_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return run_script(
        "train_rtdetrv2_detector.py",
        [
            "--config",
            str(cfg_path),
            "--run-dir",
            str(tmp / "runs" / "accuracy_detector"),
            "--weights-dir",
            str(tmp / "weights" / "accuracy_detector"),
            "--smoke",
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run detector smoke tests")
    parser.add_argument("--config", required=True)
    parser.add_argument("--models", default="fast_detector,accuracy_detector,plate,seatbelt")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    config = load_config(args.config)
    models = [normalize_model(m.strip()) for m in args.models.split(",") if m.strip()]
    unknown = [m for m in models if m not in VALID_MODELS]
    if unknown:
        log.error("Unknown model(s): %s", ", ".join(unknown))
        sys.exit(1)

    results: dict[str, bool] = {}
    for model_type in models:
        with tempfile.TemporaryDirectory(prefix=f"smoke_{model_type}_") as tmp_str:
            tmp = Path(tmp_str)
            log.info("Running smoke test: %s", model_type)
            try:
                if model_type == "accuracy_detector":
                    results[model_type] = run_accuracy_smoke(config, tmp)
                else:
                    results[model_type] = run_yolo_smoke(config, tmp, model_type, args.device)
            except Exception as exc:
                log.error("%s smoke failed with exception: %s", model_type, exc)
                results[model_type] = False

    print("\nSMOKE TEST RESULTS")
    for name, passed in results.items():
        print(f"  {name:18s}: {'PASS' if passed else 'FAIL'}")
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
