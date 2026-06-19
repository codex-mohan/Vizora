"""Upload runtime detector artifacts to Hugging Face Hub."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import yaml
from huggingface_hub import HfApi
from huggingface_hub.utils import HfHubHTTPError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_S = 5

MODEL_TYPE_META = {
    "fast_detector": {
        "task": "object-detection",
        "library": "ultralytics",
        "tags": ["object-detection", "traffic", "helmet", "headwear", "yolo11", "onnx", "tensorrt", "gridlock"],
        "description": "Fast YOLO11s traffic detector with vehicle, rider, and headwear bounding boxes.",
    },
    "accuracy_detector": {
        "task": "object-detection",
        "library": "rtdetrv2",
        "tags": ["object-detection", "traffic", "rtdetrv2", "onnx", "tensorrt", "gridlock"],
        "description": "Accuracy-profile RT-DETRv2 traffic detector for Indian traffic scenes.",
    },
    "plate": {
        "task": "object-detection",
        "library": "ultralytics",
        "tags": ["object-detection", "license-plate", "yolo11", "onnx", "tensorrt", "gridlock"],
        "description": "YOLO11 license plate detector for Indian traffic imagery.",
    },
    "seatbelt": {
        "task": "object-detection",
        "library": "ultralytics",
        "tags": ["object-detection", "seatbelt", "yolo11", "onnx", "tensorrt", "gridlock"],
        "description": "YOLO11 seatbelt detector with bounding boxes and confidence scores.",
    },
}

ALIASES = {"vehicle": "fast_detector", "fast": "fast_detector", "accuracy": "accuracy_detector"}


def normalize_model_type(value: str) -> str:
    return ALIASES.get(value, value)


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def retry(fn, *args, **kwargs):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except HfHubHTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (401, 403):
                log.error("Hugging Face authentication failed. Check HF_TOKEN.")
                sys.exit(1)
            if attempt == MAX_RETRIES:
                raise
            log.warning("Upload error attempt %d/%d: %s", attempt, MAX_RETRIES, exc)
            time.sleep(RETRY_DELAY_S)


def build_model_card(model_type: str, manifest: dict, repo_id: str) -> str:
    meta = MODEL_TYPE_META[model_type]
    files = "\n".join(f"- `{name}`" for name in manifest.get("files", []))
    hashes = "\n".join(f"- `{name}`: `{sha}`" for name, sha in manifest.get("file_hashes", {}).items())
    contract = manifest.get("runtime_contract", {})
    outputs = ", ".join(contract.get("outputs", []))
    return f"""---
license: mit
tags:
{chr(10).join(f"- {tag}" for tag in meta["tags"])}
pipeline_tag: object-detection
---

# {model_type}

{meta["description"]}

## Runtime Contract

Every prediction is expected to include: **{outputs}**.

## Files

{files}

## Export Status

```json
{json.dumps(manifest.get("export_status", {}), indent=2)}
```

## File Hashes

{hashes}

## Usage

Download the runtime artifact selected by the backend profile. Prefer TensorRT `.engine` on NVIDIA GPU, otherwise use ONNX.

Repository: https://huggingface.co/{repo_id}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload detector runtime artifacts to Hugging Face Hub")
    parser.add_argument("--config", required=True)
    parser.add_argument("--model-type", required=True, choices=[*MODEL_TYPE_META.keys(), *ALIASES.keys()])
    parser.add_argument("--artifacts-dir", default=None)
    parser.add_argument("--repo-id", default=None)
    parser.add_argument("--vol-root", default=None)
    parser.add_argument("--token", default=None)
    parser.add_argument("--private", action="store_true")
    args = parser.parse_args()

    model_type = normalize_model_type(args.model_type)
    config = load_config(args.config)
    token = args.token or os.environ.get("HF_TOKEN")
    if not token:
        log.error("No HF token provided. Use --token or set HF_TOKEN.")
        sys.exit(1)

    if args.artifacts_dir:
        artifacts_dir = Path(args.artifacts_dir)
    elif args.vol_root:
        artifacts_dir = Path(args.vol_root) / "releases" / model_type
    else:
        artifacts_dir = Path("artifacts") / model_type
    if not artifacts_dir.is_dir():
        log.error("Artifacts directory does not exist: %s", artifacts_dir)
        sys.exit(1)

    manifest_path = artifacts_dir / "manifest.json"
    if not manifest_path.exists():
        log.error("manifest.json not found in %s", artifacts_dir)
        sys.exit(1)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    repo_id = args.repo_id or config.get("hf_repos", {}).get(model_type)
    if not repo_id or repo_id.startswith("your-org"):
        log.error("No valid Hugging Face repo configured for %s.", model_type)
        sys.exit(1)

    api = HfApi(token=token)
    retry(api.create_repo, repo_id=repo_id, repo_type="model", private=args.private, exist_ok=True)

    for path in artifacts_dir.iterdir():
        if path.is_file():
            log.info("Uploading %s", path.name)
            retry(api.upload_file, path_or_fileobj=str(path), path_in_repo=path.name, repo_id=repo_id, repo_type="model")

    card = build_model_card(model_type, manifest, repo_id)
    retry(api.upload_file, path_or_fileobj=card.encode("utf-8"), path_in_repo="README.md", repo_id=repo_id, repo_type="model")
    print(f"https://huggingface.co/{repo_id}")


if __name__ == "__main__":
    main()
