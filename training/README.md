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

Prepare smoke dataset structure first. This creates the exact folders referenced by `configs/training.yaml`:

```powershell
cd training
modal run modal/app.py::app.prepare_synthetic_datasets --config-path configs/training.yaml
modal run modal/app.py::app.inspect_datasets --config-path configs/training.yaml
```

Synthetic data is only for pipeline smoke tests. Run the smoke test immediately after this step:

```powershell
modal run modal/app.py::app.smoke_test_training --config-path configs/training.yaml
```

For real vehicle training, replace the synthetic traffic data with a high-quality BMD-45 sample from Hugging Face:

```powershell
modal secret create huggingface HF_TOKEN=<your-token>
modal run modal/app.py::app.prepare_bmd45_sample --config-path configs/training.yaml --max-train 1600 --max-val 400
modal run modal/app.py::app.inspect_datasets --config-path configs/training.yaml
```

BMD-45 supplies Indian CCTV vehicle boxes, not helmet/headwear/seatbelt labels. The converter maps only trustworthy vehicle classes and drops unmapped/invalid/tiny/extreme boxes so confusing labels do not poison training.

Merge bbox-capable helmet/headwear sources next. These must have real YOLO bounding boxes; classification-only folders are rejected:

```powershell
modal secret create kaggle KAGGLE_USERNAME=<your-kaggle-username> KAGGLE_KEY=<your-kaggle-api-key>
modal run modal/app.py::app.prepare_headwear_bbox_sources --config-path configs/training.yaml
modal run modal/app.py::app.inspect_datasets --config-path configs/training.yaml
modal run modal/app.py::app.validate_datasets --config-path configs/training.yaml
```

This step merges traffic helmet/no-helmet boxes plus hard-negative headwear boxes such as caps, scarves/kerchiefs, and construction hardhats into the same `traffic-yolo` class map.

Train:

```powershell
modal run modal/app.py::app.train_vehicle_detector_fast --config-path configs/training.yaml
modal run modal/app.py::app.train_plate_detector --config-path configs/training.yaml
modal run modal/app.py::app.train_vehicle_detector_accuracy --config-path configs/training.yaml
modal run modal/app.py::app.train_seatbelt_detector --config-path configs/training.yaml
```

Export and upload:

```powershell
modal run modal/app.py::app.export_runtime_artifacts --config-path configs/training.yaml --model-type fast_detector
modal run modal/app.py::app.export_runtime_artifacts --config-path configs/training.yaml --model-type plate
modal run modal/app.py::app.upload_to_hf --config-path configs/training.yaml --model-type fast_detector
modal run modal/app.py::app.upload_to_hf --config-path configs/training.yaml --model-type plate
```

## Dataset Quality Rules

- Do not train headwear classes from generic helmet datasets unless they explicitly label `turban_pagdi`, `hat_cap`, `skull_cap`, `hood_scarf`, `construction_hardhat`, and `unclear_head`.
- Use BMD-45 for vehicle classes only: `car`, `auto`, `bus`, `truck`, `motorcycle`, `bicycle`.
- Keep `person`, `rider`, and headwear classes in the class map, but treat them as custom-label-required until we annotate real images.
- Seatbelt remains review-heavy until we have CCTV/driver-window annotations with `seatbelt_visible`, `no_seatbelt`, `strap_like_false_positive`, `occluded_reflection`, and `unclear`.
- The converter rejects unmapped classes, invalid boxes, tiny boxes, extreme aspect ratios, and empty converted images by default.

## Modal Volume Layout

- `/vol/datasets/...`
- `/vol/runs/...`
- `/vol/weights/...`
- `/vol/releases/...`

Datasets, checkpoints, releases, and downloaded weights are intentionally gitignored.
