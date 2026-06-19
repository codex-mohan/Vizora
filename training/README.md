# Training Pipeline

Training lives here, separate from `backend/` and `frontend/`.

The runtime app should load ONNX/TensorRT artifacts from Hugging Face. Modal training still uses PyTorch and saves `best.pt`, `last.pt`, metrics, and manifests before exporting runtime artifacts.

## Detector-Only Model Plan

| Runtime role | Script | Output |
| --- | --- | --- |
| Fast traffic detector | `scripts/train_yolo_detector.py` | YOLO11s `.pt`, `.onnx`, optional `.engine` |
| Accuracy detector | `scripts/train_rtdetrv2_detector.py` | RT-DETRv2 `.pt`, `.onnx`, optional `.engine` |
| Plate detector | `scripts/train_yolo_plate.py` | YOLO11 plate `.pt`, `.onnx`, optional `.engine` |
| Seatbelt detector | `scripts/train_yolo_seatbelt_detector.py` | YOLO11 seatbelt `.pt`, `.onnx`, optional `.engine` |

Helmet/headwear is not a crop classifier anymore. It is included in the traffic detector as bounding-box classes:

`helmet`, `no_helmet`, `turban_pagdi`, `hat_cap`, `skull_cap`, `hood_scarf`, `construction_hardhat`, `unclear_head`.

Every detector prediction must include a bounding box, confidence score, class id, and class name.

## RT-DETRv2

The official RT-DETRv2 PyTorch code is vendored under:

`training/third_party/rtdetrv2_pytorch`

This keeps Modal training self-contained while staying small enough for the hackathon zip.

## Modal Commands

Run smoke tests first:

```powershell
cd training
modal run modal/app.py::smoke_test_training --config-path configs/training.yaml
```

Train:

```powershell
modal run modal/app.py::train_vehicle_detector_fast --config-path configs/training.yaml
modal run modal/app.py::train_plate_detector --config-path configs/training.yaml
modal run modal/app.py::train_vehicle_detector_accuracy --config-path configs/training.yaml
modal run modal/app.py::train_seatbelt_detector --config-path configs/training.yaml
```

Export and upload:

```powershell
modal run modal/app.py::export_runtime_artifacts --config-path configs/training.yaml --model-type fast_detector
modal run modal/app.py::export_runtime_artifacts --config-path configs/training.yaml --model-type plate
modal run modal/app.py::upload_to_hf --config-path configs/training.yaml --model-type fast_detector
modal run modal/app.py::upload_to_hf --config-path configs/training.yaml --model-type plate
```

## Modal Volume Layout

- `/vol/datasets/...`
- `/vol/runs/...`
- `/vol/weights/...`
- `/vol/releases/...`

Datasets, checkpoints, releases, and downloaded weights are intentionally gitignored.
