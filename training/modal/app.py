"""Modal GPU entrypoint for Gridlock detector training.

Examples:
    modal run modal/app.py::train_vehicle_detector_fast --config-path configs/training.yaml
    modal run modal/app.py::train_vehicle_detector_accuracy --config-path configs/training.yaml
    modal run modal/app.py::train_plate_detector --config-path configs/training.yaml
    modal run modal/app.py::train_seatbelt_detector --config-path configs/training.yaml
    modal run modal/app.py::export_runtime_artifacts --config-path configs/training.yaml --model-type fast_detector
    modal run modal/app.py::upload_to_hf --config-path configs/training.yaml --model-type fast_detector
    modal run modal/app.py::smoke_test_training --config-path configs/training.yaml
    modal run modal/app.py::smoke_test_weights --config-path configs/training.yaml --weights-dir /vol/weights
"""

from __future__ import annotations

import subprocess
import sys
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
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=TRAINING_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _result(name: str, completed: subprocess.CompletedProcess) -> dict:
    if completed.returncode != 0:
        return {
            "status": "error",
            "job": name,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-2000:],
            "stderr": completed.stderr[-4000:],
        }
    return {"status": "ok", "job": name, "stdout": completed.stdout[-2000:]}


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


@app.function(gpu=modal.gpu.L40S(count=1), timeout=86400, volumes={VOL_MOUNT: vol}, retries=0)
def train_vehicle_detector_fast(config_path: str, fresh: bool = False) -> dict:
    completed = _run_script(
        "train_yolo_detector.py",
        [*_common_args(config_path, "fast_detector", "fast_detector", fresh), "--model-key", "fast_detector"],
    )
    _commit_volume()
    return _result("train_vehicle_detector_fast", completed)


@app.function(gpu=modal.gpu.A100(count=1), timeout=86400, volumes={VOL_MOUNT: vol}, retries=0)
def train_vehicle_detector_accuracy(config_path: str, fresh: bool = False) -> dict:
    completed = _run_script(
        "train_rtdetrv2_detector.py",
        _common_args(config_path, "accuracy_detector", "accuracy_detector", fresh),
    )
    _commit_volume()
    return _result("train_vehicle_detector_accuracy", completed)


@app.function(gpu=modal.gpu.A10G(count=1), timeout=86400, volumes={VOL_MOUNT: vol}, retries=0)
def train_plate_detector(config_path: str, fresh: bool = False) -> dict:
    completed = _run_script("train_yolo_plate.py", _common_args(config_path, "plate", "plate", fresh))
    _commit_volume()
    return _result("train_plate_detector", completed)


@app.function(gpu=modal.gpu.A10G(count=1), timeout=43200, volumes={VOL_MOUNT: vol}, retries=0)
def train_seatbelt_detector(config_path: str, fresh: bool = False) -> dict:
    completed = _run_script("train_yolo_seatbelt_detector.py", _common_args(config_path, "seatbelt", "seatbelt", fresh))
    _commit_volume()
    return _result("train_seatbelt_detector", completed)


@app.function(gpu=modal.gpu.A10G(count=1), timeout=7200, volumes={VOL_MOUNT: vol}, retries=0)
def export_runtime_artifacts(config_path: str, model_type: str, skip_engine: bool = False) -> dict:
    args = ["--config", config_path, "--model-type", model_type, "--vol-root", VOL_MOUNT]
    if skip_engine:
        args.append("--skip-engine")
    completed = _run_script("export_artifacts.py", args)
    _commit_volume()
    return _result("export_runtime_artifacts", completed)


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
def main() -> None:
    print(__doc__)
