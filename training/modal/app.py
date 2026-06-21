"""Modal GPU entrypoint for Gridlock detector training.

Examples:
    modal run modal/app.py::app.download_pretrained_models --config-path configs/training.yaml
    modal run modal/app.py::app.download_pretrained_models --config-path configs/training.yaml --models fast_vehicle_yolo,helmet_yolo11
    modal run modal/app.py::app.prepare_synthetic_datasets --config-path configs/training.yaml
    modal run modal/app.py::app.inspect_datasets --config-path configs/training.yaml
    modal run modal/app.py::app.train_vehicle_detector_fast --config-path configs/training.yaml
    modal run modal/app.py::app.train_vehicle_detector_accuracy --config-path configs/training.yaml
    modal run modal/app.py::app.train_plate_detector --config-path configs/training.yaml
    modal run modal/app.py::app.train_seatbelt_detector --config-path configs/training.yaml
    modal run modal/app.py::app.prepare_bmd45_sample --config-path configs/training.yaml --max-train 1600 --max-val 400
    modal run modal/app.py::app.prepare_headwear_bbox_sources --config-path configs/training.yaml
    modal run modal/app.py::app.validate_datasets --config-path configs/training.yaml
    modal run modal/app.py::app.export_runtime_artifacts --config-path configs/training.yaml --model-type fast_detector
    modal run modal/app.py::app.upload_to_hf --config-path configs/training.yaml --model-type fast_detector
    modal run modal/app.py::app.smoke_test_training --config-path configs/training.yaml
    modal run modal/app.py::app.smoke_test_weights --config-path configs/training.yaml --weights-dir /vol/weights
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import deque
from pathlib import Path

import modal

APP_NAME = "gridlock-training"
VOL_MOUNT = "/vol"
TRAINING_ROOT = "/root/training"

image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("git", "libgl1", "libglib2.0-0")
    .pip_install(
        "torch>=2.2",
        "torchvision>=0.17",
        "ultralytics>=8.1",
        "pyyaml>=6.0",
        "tqdm>=4.66",
        "Pillow>=10.0",
        "opencv-python-headless>=4.8",
        "numpy>=1.24",
        "scikit-learn>=1.3",
        "matplotlib>=3.8",
        "seaborn>=0.13",
        "huggingface_hub>=0.20",
        "kaggle>=1.6",
        "pydantic>=2.0",
        "rich>=13.0",
        "onnx>=1.16",
        "onnxruntime>=1.17",
    )
    .add_local_dir(
        local_path=str(Path(__file__).resolve().parent.parent),
        remote_path=TRAINING_ROOT,
    )
)

app = modal.App(name=APP_NAME, image=image)
vol = modal.Volume.from_name("gridlock-training-vol", create_if_missing=True)


def _run_script(script_name: str, args: list[str]) -> subprocess.CompletedProcess:
    script = Path(TRAINING_ROOT) / "scripts" / script_name
    command = [sys.executable, str(script), *args]
    print(f"[modal] running: {' '.join(command)}", flush=True)
    process = subprocess.Popen(
        command,
        cwd=TRAINING_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    tail: deque[str] = deque(maxlen=500)
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="", flush=True)
        tail.append(line)
    returncode = process.wait()
    print(f"[modal] {script_name} exited with code {returncode}", flush=True)
    return subprocess.CompletedProcess(command, returncode, stdout="".join(tail), stderr="")


def _result(name: str, completed: subprocess.CompletedProcess) -> dict:
    if completed.returncode != 0:
        raise RuntimeError(
            f"{name} failed with exit code {completed.returncode}.\n"
            f"Last output:\n{completed.stdout[-6000:]}"
        )
    return {"status": "ok", "job": name, "stdout_tail": completed.stdout[-4000:]}


def _commit_volume() -> None:
    try:
        vol.commit()
    except Exception:
        pass


def _common_args(config_path: str, weights_key: str, run_key: str, fresh: bool) -> list[str]:
    args = [
        "--config",
        config_path,
        "--weights-dir",
        f"{VOL_MOUNT}/weights/{weights_key}",
        "--run-dir",
        f"{VOL_MOUNT}/runs/{run_key}",
        "--vol-root",
        VOL_MOUNT,
    ]
    if fresh:
        args.append("--fresh")
    return args


def _count_files(root: Path, suffixes: tuple[str, ...]) -> int:
    if not root.exists():
        return 0
    return sum(1 for path in root.rglob("*") if path.is_file() and path.suffix.lower() in suffixes)


def _resolve_dataset_path(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def _label_dir_for(image_dir: Path) -> Path:
    parts = list(image_dir.parts)
    if "images" in parts:
        parts[parts.index("images")] = "labels"
        return Path(*parts)
    return image_dir.parent.parent / "labels" / image_dir.name


def _inspect_yolo_data_yaml(path: Path) -> dict:
    import yaml

    if not path.exists():
        return {"exists": False, "path": str(path)}
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    root = _resolve_dataset_path(path.parent, str(data.get("path") or path.parent))
    train_images = _resolve_dataset_path(root, str(data.get("train", "images/train")))
    val_images = _resolve_dataset_path(root, str(data.get("val", "images/val")))
    train_labels = _label_dir_for(train_images)
    val_labels = _label_dir_for(val_images)
    image_suffixes = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
    return {
        "exists": True,
        "path": str(path),
        "root": str(root),
        "classes": len(data.get("names", [])),
        "train_images": _count_files(train_images, image_suffixes),
        "train_labels": _count_files(train_labels, (".txt",)),
        "val_images": _count_files(val_images, image_suffixes),
        "val_labels": _count_files(val_labels, (".txt",)),
    }


def _assert_dataset_ready(name: str, report: dict) -> None:
    if not report.get("exists"):
        raise RuntimeError(f"{name} is missing: {report.get('path')}")
    if report.get("train_images", 0) == 0 or report.get("val_images", 0) == 0:
        raise RuntimeError(f"{name} has no train/val images: {report}")
    if report.get("train_labels", 0) == 0 or report.get("val_labels", 0) == 0:
        raise RuntimeError(f"{name} has no train/val labels: {report}")


@app.function(cpu=4, timeout=7200, volumes={VOL_MOUNT: vol}, retries=0)
def prepare_synthetic_datasets(
    config_path: str,
    traffic_images: int = 96,
    plate_images: int = 48,
    seatbelt_images: int = 48,
    fresh: bool = True,
) -> dict:
    args = [
        "--config",
        config_path,
        "synthetic",
        "--output-root",
        f"{VOL_MOUNT}/datasets",
        "--traffic-images",
        str(traffic_images),
        "--plate-images",
        str(plate_images),
        "--seatbelt-images",
        str(seatbelt_images),
    ]
    if fresh:
        args.append("--fresh")
    completed = _run_script("prepare_datasets.py", args)
    _commit_volume()
    return _result("prepare_synthetic_datasets", completed)


@app.function(cpu=8, timeout=21600, volumes={VOL_MOUNT: vol}, secrets=[modal.Secret.from_name("huggingface")], retries=0)
def prepare_bmd45_sample(
    config_path: str,
    max_train: int = 1600,
    max_val: int = 400,
    fresh: bool = True,
) -> dict:
    args = [
        "--config",
        config_path,
        "hf-bmd45",
        "--output-root",
        f"{VOL_MOUNT}/datasets",
        "--max-train",
        str(max_train),
        "--max-val",
        str(max_val),
    ]
    if fresh:
        args.append("--fresh")
    completed = _run_script("prepare_datasets.py", args)
    _commit_volume()
    return _result("prepare_bmd45_sample", completed)


@app.function(cpu=8, timeout=21600, volumes={VOL_MOUNT: vol}, secrets=[modal.Secret.from_name("kaggle")], retries=0)
def prepare_headwear_bbox_sources(
    config_path: str,
    refs_csv: str = "",
    fresh: bool = False,
) -> dict:
    args = [
        "--config",
        config_path,
        "kaggle-yolo-headwear",
        "--output-root",
        f"{VOL_MOUNT}/datasets",
    ]
    refs = [ref.strip() for ref in refs_csv.split(",") if ref.strip()]
    if refs:
        args.extend(["--refs", *refs])
    if fresh:
        args.append("--fresh")
    completed = _run_script("prepare_datasets.py", args)
    _commit_volume()
    return _result("prepare_headwear_bbox_sources", completed)


@app.function(cpu=2, timeout=600, volumes={VOL_MOUNT: vol}, retries=0)
def inspect_datasets(config_path: str) -> dict:
    import yaml

    config_file = Path(TRAINING_ROOT) / config_path
    with config_file.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    datasets = cfg["datasets"]
    report = {
        "traffic_yolo": _inspect_yolo_data_yaml(Path(datasets["traffic_yolo"])),
        "plate_yolo": _inspect_yolo_data_yaml(Path(datasets["plate_yolo"])),
        "seatbelt_yolo": _inspect_yolo_data_yaml(Path(datasets["seatbelt_yolo"])),
        "traffic_coco_train": {
            "exists": Path(datasets["traffic_coco_train"]).exists(),
            "path": datasets["traffic_coco_train"],
        },
        "traffic_coco_val": {
            "exists": Path(datasets["traffic_coco_val"]).exists(),
            "path": datasets["traffic_coco_val"],
        },
    }
    for name in ("traffic_yolo", "plate_yolo", "seatbelt_yolo"):
        _assert_dataset_ready(name, report[name])
    if not report["traffic_coco_train"]["exists"] or not report["traffic_coco_val"]["exists"]:
        raise RuntimeError(f"traffic COCO annotations are missing: {report}")
    print(json.dumps(report, indent=2), flush=True)
    return report


@app.function(cpu=2, timeout=1800, volumes={VOL_MOUNT: vol}, retries=0)
def validate_datasets(config_path: str) -> dict:
    import yaml

    config_file = Path(TRAINING_ROOT) / config_path
    with config_file.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    results: dict[str, dict] = {}
    for name, data_yaml in {
        "traffic_yolo": cfg["datasets"]["traffic_yolo"],
        "plate_yolo": cfg["datasets"]["plate_yolo"],
        "seatbelt_yolo": cfg["datasets"]["seatbelt_yolo"],
    }.items():
        completed = _run_script(
            "prepare_datasets.py",
            ["--config", config_path, "validate-yolo", "--data-yaml", data_yaml],
        )
        results[name] = _result(f"validate_{name}", completed)
    return results


@app.function(gpu="L40S", timeout=86400, volumes={VOL_MOUNT: vol}, retries=0)
def train_vehicle_detector_fast(config_path: str, fresh: bool = False) -> dict:
    completed = _run_script(
        "train_yolo_detector.py",
        [*_common_args(config_path, "fast_detector", "fast_detector", fresh), "--model-key", "fast_detector"],
    )
    _commit_volume()
    return _result("train_vehicle_detector_fast", completed)


@app.function(gpu="A100", timeout=86400, volumes={VOL_MOUNT: vol}, retries=0)
def train_vehicle_detector_accuracy(config_path: str, fresh: bool = False) -> dict:
    completed = _run_script(
        "train_rtdetrv2_detector.py",
        _common_args(config_path, "accuracy_detector", "accuracy_detector", fresh),
    )
    _commit_volume()
    return _result("train_vehicle_detector_accuracy", completed)


@app.function(gpu="A10G", timeout=86400, volumes={VOL_MOUNT: vol}, retries=0)
def train_plate_detector(config_path: str, fresh: bool = False) -> dict:
    completed = _run_script("train_yolo_plate.py", _common_args(config_path, "plate", "plate", fresh))
    _commit_volume()
    return _result("train_plate_detector", completed)


@app.function(gpu="A10G", timeout=43200, volumes={VOL_MOUNT: vol}, retries=0)
def train_seatbelt_detector(config_path: str, fresh: bool = False) -> dict:
    completed = _run_script("train_yolo_seatbelt_detector.py", _common_args(config_path, "seatbelt", "seatbelt", fresh))
    _commit_volume()
    return _result("train_seatbelt_detector", completed)


@app.function(gpu="A10G", timeout=7200, volumes={VOL_MOUNT: vol}, retries=0)
def export_runtime_artifacts(config_path: str, model_type: str, skip_engine: bool = False) -> dict:
    args = ["--config", config_path, "--model-type", model_type, "--vol-root", VOL_MOUNT]
    if skip_engine:
        args.append("--skip-engine")
    completed = _run_script("export_artifacts.py", args)
    _commit_volume()
    return _result("export_runtime_artifacts", completed)


@app.function(cpu=4, timeout=3600, volumes={VOL_MOUNT: vol}, secrets=[modal.Secret.from_name("huggingface")], retries=0)
def download_pretrained_models(
    config_path: str,
    models: str = "",
    token: str | None = None,
) -> dict:
    args = ["--config", config_path, "--vol-root", VOL_MOUNT]
    if models:
        args.extend(["--models", models])
    if token:
        args.extend(["--token", token])
    completed = _run_script("download_pretrained_models.py", args)
    _commit_volume()
    return _result("download_pretrained_models", completed)


@app.function(cpu=2, timeout=3600, volumes={VOL_MOUNT: vol}, secrets=[modal.Secret.from_name("huggingface")], retries=0)
def upload_to_hf(config_path: str, model_type: str, private: bool = False) -> dict:
    args = ["--config", config_path, "--model-type", model_type, "--vol-root", VOL_MOUNT]
    if private:
        args.append("--private")
    completed = _run_script("upload_to_hf.py", args)
    _commit_volume()
    return _result("upload_to_hf", completed)


@app.function(timeout=14400, volumes={VOL_MOUNT: vol}, retries=0)
def smoke_test_training(config_path: str) -> dict:
    completed = _run_script("smoke_test_training.py", ["--config", config_path, "--models", "fast_detector,accuracy_detector,plate,seatbelt"])
    _commit_volume()
    return _result("smoke_test_training", completed)


@app.function(timeout=3600, volumes={VOL_MOUNT: vol}, retries=0)
def smoke_test_weights(config_path: str, weights_dir: str = f"{VOL_MOUNT}/weights") -> dict:
    completed = _run_script("smoke_test_weights.py", ["--config", config_path, "--weights-dir", weights_dir])
    return _result("smoke_test_weights", completed)


@app.local_entrypoint()
def main(config_path: str = "configs/training.yaml", fresh: bool = False, job: str = "smoke"):
    if job == "prepare-synthetic":
        result = prepare_synthetic_datasets.remote(config_path, fresh=fresh)
    elif job == "prepare-bmd45":
        result = prepare_bmd45_sample.remote(config_path, fresh=fresh)
    elif job == "prepare-headwear":
        result = prepare_headwear_bbox_sources.remote(config_path, fresh=fresh)
    elif job == "inspect-datasets":
        result = inspect_datasets.remote(config_path)
    elif job == "validate-datasets":
        result = validate_datasets.remote(config_path)
    elif job == "smoke":
        result = smoke_test_training.remote(config_path)
    elif job == "fast":
        result = train_vehicle_detector_fast.remote(config_path, fresh=fresh)
    elif job == "plate":
        result = train_plate_detector.remote(config_path, fresh=fresh)
    elif job == "seatbelt":
        result = train_seatbelt_detector.remote(config_path, fresh=fresh)
    elif job == "accuracy":
        result = train_vehicle_detector_accuracy.remote(config_path, fresh=fresh)
    else:
        raise ValueError(f"Unknown job: {job}")
    print(result)
