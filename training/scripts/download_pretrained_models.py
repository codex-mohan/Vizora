"""Download pretrained model weights from Hugging Face Hub.

Reads the pretrained_models block from training.yaml, downloads each weight
file using huggingface_hub.hf_hub_download, mirrors to pipeline-conventional
paths, and writes a manifest JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

PIPELINE_MIRRORS: dict[str, list[str]] = {
    "fast_vehicle_yolo": ["fast_detector/best.pt"],
    "accuracy_vehicle_rtdetrv2": ["accuracy_detector/best.pth"],
    "review_vehicle_dfine": ["review_detector/best.pth"],
    "helmet_yolo11": ["helmet_detector/best.pt"],
}


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_model(
    repo_id: str,
    filename: str,
    dest_dir: Path,
    *,
    revision: str | None = None,
    token: str | None = None,
) -> Path:
    from huggingface_hub import hf_hub_download

    log.info("Downloading %s/%s -> %s", repo_id, filename, dest_dir)
    downloaded = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        revision=revision,
        token=token,
        local_dir=str(dest_dir),
        local_dir_use_symlinks=False,
    )
    return Path(downloaded)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download pretrained models from HF Hub")
    parser.add_argument("--config", required=True, help="Path to training.yaml")
    parser.add_argument(
        "--models",
        default="",
        help="Comma-separated model keys to download. Empty = all from config.",
    )
    parser.add_argument("--vol-root", default="/vol", help="Volume mount root")
    parser.add_argument("--token", default=None, help="HF token override")
    args = parser.parse_args()

    config = load_config(args.config)
    pretrained = config.get("pretrained_models", {})
    if not pretrained:
        log.error("No pretrained_models block in config")
        sys.exit(1)

    vol_root = Path(args.vol_root)
    pretrained_dir = vol_root / "weights" / "pretrained"
    pretrained_dir.mkdir(parents=True, exist_ok=True)

    requested = {m.strip() for m in args.models.split(",") if m.strip()} if args.models else set(pretrained.keys())

    manifest: dict = {
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "models": {},
    }

    errors: list[str] = []

    for key in requested:
        entry = pretrained.get(key)
        if not entry:
            log.error("Unknown pretrained model key: %s", key)
            errors.append(key)
            continue

        repo_id = entry["repo_id"]
        filename = entry["filename"]
        dest_subdir = pretrained_dir / key
        dest_subdir.mkdir(parents=True, exist_ok=True)

        try:
            downloaded_path = download_model(
                repo_id=repo_id,
                filename=filename,
                dest_dir=dest_subdir,
                revision=entry.get("revision"),
                token=args.token,
            )
        except Exception as exc:
            log.error("Failed to download %s: %s", key, exc)
            errors.append(key)
            continue

        file_hash = sha256_of(downloaded_path)
        manifest["models"][key] = {
            "repo_id": repo_id,
            "filename": filename,
            "local_path": str(downloaded_path.relative_to(vol_root)),
            "sha256": file_hash,
            "size_bytes": downloaded_path.stat().st_size,
            "model_class": entry.get("model_class", "unknown"),
            "notes": entry.get("notes", ""),
        }

        for mirror_rel in PIPELINE_MIRRORS.get(key, []):
            mirror_dest = vol_root / "weights" / mirror_rel
            mirror_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(downloaded_path, mirror_dest)
            log.info("Mirrored %s -> %s", downloaded_path.name, mirror_dest)

    manifest_path = pretrained_dir / "pretrained_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    log.info("Manifest written to %s", manifest_path)

    if errors:
        log.error("Failed models: %s", ", ".join(errors))
        sys.exit(1)

    log.info("All %d pretrained models downloaded successfully.", len(manifest["models"]))


if __name__ == "__main__":
    main()
