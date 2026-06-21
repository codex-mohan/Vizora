from __future__ import annotations

import argparse
import json
import os
import re
import random
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from PIL import Image, ImageDraw
from rich.console import Console
from rich.table import Table

console = Console()
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

BMD45_CLASS_MAP = {
    "hatchback": "car",
    "sedan": "car",
    "suv": "car",
    "muv": "car",
    "van": "car",
    "bus": "bus",
    "mini-bus": "bus",
    "minibus": "bus",
    "truck": "truck",
    "lcv": "truck",
    "three-wheeler": "auto",
    "three wheeler": "auto",
    "two-wheeler": "motorcycle",
    "two wheeler": "motorcycle",
    "bicycle": "bicycle",
    "tempo-traveller": "bus",
    "tempo traveller": "bus",
}


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def normalise_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def ensure_clean_dir(path: Path, fresh: bool) -> None:
    if fresh and path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_data_yaml(root: Path, class_names: list[str]) -> Path:
    data_yaml = root / "data.yaml"
    data_yaml.write_text(
        yaml.safe_dump(
            {
                "path": str(root),
                "train": "images/train",
                "val": "images/val",
                "nc": len(class_names),
                "names": {i: name for i, name in enumerate(class_names)},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return data_yaml


def yolo_label_line(class_id: int, box: tuple[int, int, int, int], width: int, height: int) -> str:
    x1, y1, x2, y2 = box
    xc = ((x1 + x2) / 2) / width
    yc = ((y1 + y2) / 2) / height
    bw = (x2 - x1) / width
    bh = (y2 - y1) / height
    return f"{class_id} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}"


def coco_categories(class_names: list[str]) -> list[dict[str, Any]]:
    return [{"id": idx + 1, "name": name, "supercategory": "traffic"} for idx, name in enumerate(class_names)]


def make_synthetic_image(path: Path, boxes: list[tuple[int, tuple[int, int, int, int]]], class_names: list[str], size: int) -> None:
    rng = random.Random(path.stem)
    image = Image.new("RGB", (size, size), (rng.randint(20, 70), rng.randint(25, 80), rng.randint(35, 90)))
    draw = ImageDraw.Draw(image)
    for class_id, (x1, y1, x2, y2) in boxes:
        color = (
            80 + (class_id * 37) % 160,
            80 + (class_id * 67) % 160,
            80 + (class_id * 97) % 160,
        )
        draw.rectangle((x1, y1, x2, y2), outline=color, width=4)
        draw.text((x1 + 4, max(2, y1 - 14)), class_names[class_id][:18], fill=color)
    image.save(path, quality=92)


def synthetic_boxes(index: int, class_count: int, size: int) -> list[tuple[int, tuple[int, int, int, int]]]:
    rng = random.Random(index)
    boxes: list[tuple[int, tuple[int, int, int, int]]] = []
    for offset in range(1 + index % 3):
        class_id = (index + offset) % class_count
        w = rng.randint(size // 8, size // 3)
        h = rng.randint(size // 8, size // 3)
        x1 = rng.randint(8, size - w - 8)
        y1 = rng.randint(8, size - h - 8)
        boxes.append((class_id, (x1, y1, x1 + w, y1 + h)))
    return boxes


def generate_synthetic_detection_dataset(
    yolo_root: Path,
    coco_root: Path | None,
    class_names: list[str],
    image_count: int,
    image_size: int,
    fresh: bool,
) -> dict[str, Any]:
    ensure_clean_dir(yolo_root, fresh)
    if coco_root is not None:
        ensure_clean_dir(coco_root, fresh)

    split_counts = {
        "train": max(2, int(image_count * 0.8)),
        "val": max(2, image_count - max(2, int(image_count * 0.8))),
    }
    class_counts: dict[str, int] = {name: 0 for name in class_names}
    coco_payloads: dict[str, dict[str, Any]] = {}
    annotation_id = 1

    for split, count in split_counts.items():
        image_dir = yolo_root / "images" / split
        label_dir = yolo_root / "labels" / split
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)

        coco_images: list[dict[str, Any]] = []
        coco_annotations: list[dict[str, Any]] = []
        for idx in range(count):
            global_idx = idx if split == "train" else split_counts["train"] + idx
            image_name = f"{global_idx:06d}.jpg"
            image_path = image_dir / image_name
            boxes = synthetic_boxes(global_idx, len(class_names), image_size)
            make_synthetic_image(image_path, boxes, class_names, image_size)
            label_lines = [
                yolo_label_line(class_id, box, image_size, image_size)
                for class_id, box in boxes
            ]
            (label_dir / f"{global_idx:06d}.txt").write_text("\n".join(label_lines) + "\n", encoding="utf-8")

            image_id = global_idx + 1
            coco_images.append(
                {
                    "id": image_id,
                    "file_name": f"{split}/{image_name}",
                    "width": image_size,
                    "height": image_size,
                }
            )
            for class_id, box in boxes:
                x1, y1, x2, y2 = box
                class_counts[class_names[class_id]] += 1
                coco_annotations.append(
                    {
                        "id": annotation_id,
                        "image_id": image_id,
                        "category_id": class_id + 1,
                        "bbox": [x1, y1, x2 - x1, y2 - y1],
                        "area": (x2 - x1) * (y2 - y1),
                        "iscrowd": 0,
                    }
                )
                annotation_id += 1

        coco_payloads[split] = {
            "images": coco_images,
            "annotations": coco_annotations,
            "categories": coco_categories(class_names),
        }

    data_yaml = write_data_yaml(yolo_root, class_names)
    validation = validate_yolo_dataset(data_yaml)
    if coco_root is not None:
        for split, payload in coco_payloads.items():
            image_out = coco_root / "images" / split
            image_out.mkdir(parents=True, exist_ok=True)
            for image_path in (yolo_root / "images" / split).glob("*.jpg"):
                shutil.copy2(image_path, image_out / image_path.name)
            write_json(coco_root / "annotations" / f"instances_{split}.json", payload)

    return {
        "data_yaml": str(data_yaml),
        "coco_root": str(coco_root) if coco_root else None,
        "classes": class_names,
        "class_counts": class_counts,
        "image_count": sum(split_counts.values()),
        "validation": validation,
    }


def build_annotation_index(coco: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    annotations_by_image: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for annotation in coco.get("annotations", []):
        annotations_by_image[int(annotation["image_id"])].append(annotation)
    return annotations_by_image


def category_map_from_coco(coco: dict[str, Any], class_map: dict[str, str]) -> dict[int, str]:
    mapped: dict[int, str] = {}
    for category in coco.get("categories", []):
        category_id = int(category["id"])
        raw_name = str(category["name"])
        canonical = class_map.get(normalise_name(raw_name)) or class_map.get(raw_name)
        if canonical:
            mapped[category_id] = canonical
    return mapped


def resolve_image_path(image_root: Path, file_name: str) -> Path | None:
    candidate = image_root / file_name
    if candidate.exists():
        return candidate
    matches = list(image_root.rglob(Path(file_name).name))
    return matches[0] if matches else None


def convert_coco_split(
    split: str,
    coco_json: Path,
    image_root: Path,
    yolo_root: Path,
    coco_root: Path | None,
    class_names: list[str],
    class_map: dict[str, str],
    max_images: int | None,
    fresh: bool,
    min_box_area: float,
    min_box_side: float,
    max_aspect_ratio: float,
    drop_empty: bool,
) -> dict[str, Any]:
    if not coco_json.exists():
        raise FileNotFoundError(f"COCO annotation file not found: {coco_json}")
    with coco_json.open(encoding="utf-8") as f:
        source_coco = json.load(f)

    ensure_clean_dir(yolo_root / "images" / split, fresh=False)
    ensure_clean_dir(yolo_root / "labels" / split, fresh=False)
    if coco_root is not None:
        ensure_clean_dir(coco_root / "images" / split, fresh=False)
        ensure_clean_dir(coco_root / "annotations", fresh=False)

    category_map = category_map_from_coco(source_coco, class_map)
    class_to_id = {name: idx for idx, name in enumerate(class_names)}
    annotations_by_image = build_annotation_index(source_coco)
    converted_images: list[dict[str, Any]] = []
    converted_annotations: list[dict[str, Any]] = []
    class_counts: dict[str, int] = {name: 0 for name in class_names}
    missing_images = 0
    dropped_empty = 0
    skipped_unmapped = 0
    skipped_invalid = 0
    skipped_tiny = 0
    skipped_extreme_ratio = 0
    annotation_id = 1

    source_images = source_coco.get("images", [])
    if max_images is not None:
        source_images = source_images[:max_images]

    for image_index, image_info in enumerate(source_images):
        file_name = str(image_info["file_name"])
        source_image = resolve_image_path(image_root, file_name)
        if source_image is None:
            missing_images += 1
            continue

        width = int(image_info.get("width") or 0)
        height = int(image_info.get("height") or 0)
        if width <= 0 or height <= 0:
            with Image.open(source_image) as img:
                width, height = img.size

        dest_name = f"{Path(file_name).stem}_{image_index:06d}{source_image.suffix.lower()}"
        labels: list[str] = []
        image_annotations: list[dict[str, Any]] = []
        image_id = image_index + 1
        for annotation in annotations_by_image.get(int(image_info["id"]), []):
            canonical_class = category_map.get(int(annotation["category_id"]))
            if canonical_class not in class_to_id:
                skipped_unmapped += 1
                continue
            x, y, w, h = [float(v) for v in annotation["bbox"][:4]]
            if w <= 0 or h <= 0:
                skipped_invalid += 1
                continue
            class_id = class_to_id[canonical_class]
            x1 = max(0.0, min(width - 1.0, x))
            y1 = max(0.0, min(height - 1.0, y))
            x2 = max(0.0, min(float(width), x + w))
            y2 = max(0.0, min(float(height), y + h))
            if x2 <= x1 or y2 <= y1:
                skipped_invalid += 1
                continue
            clipped_w = x2 - x1
            clipped_h = y2 - y1
            area = clipped_w * clipped_h
            if clipped_w < min_box_side or clipped_h < min_box_side or area < min_box_area:
                skipped_tiny += 1
                continue
            aspect_ratio = max(clipped_w / clipped_h, clipped_h / clipped_w)
            if aspect_ratio > max_aspect_ratio:
                skipped_extreme_ratio += 1
                continue
            labels.append(yolo_label_line(class_id, (int(x1), int(y1), int(x2), int(y2)), width, height))
            class_counts[canonical_class] += 1
            image_annotations.append(
                {
                    "id": annotation_id,
                    "image_id": image_id,
                    "category_id": class_id + 1,
                    "bbox": [x1, y1, clipped_w, clipped_h],
                    "area": area,
                    "iscrowd": int(annotation.get("iscrowd", 0)),
                }
            )
            annotation_id += 1

        if drop_empty and not labels:
            dropped_empty += 1
            continue

        dest_image = yolo_root / "images" / split / dest_name
        shutil.copy2(source_image, dest_image)
        if coco_root is not None:
            shutil.copy2(source_image, coco_root / "images" / split / dest_name)
        (yolo_root / "labels" / split / f"{Path(dest_name).stem}.txt").write_text(
            "\n".join(labels) + ("\n" if labels else ""),
            encoding="utf-8",
        )
        converted_annotations.extend(image_annotations)
        converted_images.append({"id": image_id, "file_name": f"{split}/{dest_name}", "width": width, "height": height})

    if coco_root is not None:
        write_json(
            coco_root / "annotations" / f"instances_{split}.json",
            {
                "images": converted_images,
                "annotations": converted_annotations,
                "categories": coco_categories(class_names),
            },
        )

    return {
        "split": split,
        "source_json": str(coco_json),
        "image_root": str(image_root),
        "images": len(converted_images),
        "annotations": len(converted_annotations),
        "missing_images": missing_images,
        "dropped_empty_images": dropped_empty,
        "skipped_unmapped_annotations": skipped_unmapped,
        "skipped_invalid_annotations": skipped_invalid,
        "skipped_tiny_annotations": skipped_tiny,
        "skipped_extreme_ratio_annotations": skipped_extreme_ratio,
        "class_counts": class_counts,
    }


def convert_coco_dataset(
    train_json: Path,
    val_json: Path,
    train_images: Path,
    val_images: Path,
    yolo_root: Path,
    coco_root: Path | None,
    class_names: list[str],
    class_map: dict[str, str],
    max_train: int | None,
    max_val: int | None,
    fresh: bool,
    min_box_area: float,
    min_box_side: float,
    max_aspect_ratio: float,
    drop_empty: bool,
) -> dict[str, Any]:
    ensure_clean_dir(yolo_root, fresh)
    if coco_root is not None:
        ensure_clean_dir(coco_root, fresh)
    train_info = convert_coco_split(
        "train",
        train_json,
        train_images,
        yolo_root,
        coco_root,
        class_names,
        class_map,
        max_train,
        fresh,
        min_box_area,
        min_box_side,
        max_aspect_ratio,
        drop_empty,
    )
    val_info = convert_coco_split(
        "val",
        val_json,
        val_images,
        yolo_root,
        coco_root,
        class_names,
        class_map,
        max_val,
        fresh,
        min_box_area,
        min_box_side,
        max_aspect_ratio,
        drop_empty,
    )
    data_yaml = write_data_yaml(yolo_root, class_names)
    validation = validate_yolo_dataset(data_yaml)
    return {
        "data_yaml": str(data_yaml),
        "coco_root": str(coco_root) if coco_root else None,
        "train": train_info,
        "val": val_info,
        "validation": validation,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "quality_filters": {
            "min_box_area": min_box_area,
            "min_box_side": min_box_side,
            "max_aspect_ratio": max_aspect_ratio,
            "drop_empty": drop_empty,
        },
    }


def load_yolo_names(data: dict[str, Any]) -> list[str]:
    names = data.get("names")
    if isinstance(names, dict):
        return [str(names[key]) for key in sorted(names, key=lambda value: int(value))]
    if isinstance(names, list):
        return [str(name) for name in names]
    raise ValueError("YOLO data.yaml must contain names as a list or numeric-key dictionary.")


def resolve_yolo_path(dataset_root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else dataset_root / path


def label_dir_from_image_dir(image_dir: Path) -> Path:
    parts = list(image_dir.parts)
    if "images" in parts:
        parts[parts.index("images")] = "labels"
        return Path(*parts)
    return image_dir.parent.parent / "labels" / image_dir.name


def yolo_split_dirs(data_yaml: Path, data: dict[str, Any]) -> list[tuple[str, Path, Path]]:
    dataset_root = resolve_yolo_path(data_yaml.parent, str(data.get("path") or data_yaml.parent))
    split_dirs: list[tuple[str, Path, Path]] = []
    split_aliases = {"train": "train", "val": "val", "valid": "val", "test": "val"}
    for source_key, target_split in split_aliases.items():
        if source_key not in data:
            continue
        image_dir = resolve_yolo_path(dataset_root, str(data[source_key]))
        label_dir = label_dir_from_image_dir(image_dir)
        if image_dir.exists() and label_dir.exists():
            split_dirs.append((target_split, image_dir, label_dir))
    return split_dirs


def find_yolo_data_yamls(root: Path) -> list[Path]:
    candidates = [path for name in ("data.yaml", "dataset.yaml") for path in root.rglob(name)]
    return sorted({path.resolve() for path in candidates})


def build_config_class_map(source_cfg: dict[str, Any]) -> dict[str, str]:
    configured = source_cfg.get("class_map") or {}
    if not isinstance(configured, dict):
        raise ValueError(f"class_map must be a dictionary for {source_cfg.get('name') or source_cfg.get('ref')}")
    return {normalise_name(str(source)): str(target) for source, target in configured.items() if target}


def parse_yolo_box(line: str) -> tuple[int, float, float, float, float] | None:
    parts = line.strip().split()
    if len(parts) < 5:
        return None
    try:
        class_id = int(float(parts[0]))
        x_center, y_center, width, height = [float(value) for value in parts[1:5]]
    except ValueError:
        return None
    return class_id, x_center, y_center, width, height


def yolo_box_to_xyxy(box: tuple[int, float, float, float, float], image_width: int, image_height: int) -> tuple[float, float, float, float]:
    _, x_center, y_center, width, height = box
    x1 = (x_center - width / 2) * image_width
    y1 = (y_center - height / 2) * image_height
    x2 = (x_center + width / 2) * image_width
    y2 = (y_center + height / 2) * image_height
    return (
        max(0.0, min(float(image_width), x1)),
        max(0.0, min(float(image_height), y1)),
        max(0.0, min(float(image_width), x2)),
        max(0.0, min(float(image_height), y2)),
    )


def xyxy_to_yolo_line(class_id: int, box: tuple[float, float, float, float], image_width: int, image_height: int) -> str:
    x1, y1, x2, y2 = box
    x_center = ((x1 + x2) / 2) / image_width
    y_center = ((y1 + y2) / 2) / image_height
    width = (x2 - x1) / image_width
    height = (y2 - y1) / image_height
    return f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"


def validate_yolo_dataset(data_yaml: Path, min_boxes: int = 1) -> dict[str, Any]:
    if not data_yaml.exists():
        raise FileNotFoundError(f"YOLO data.yaml not found: {data_yaml}")
    with data_yaml.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    class_names = load_yolo_names(data)
    split_dirs = yolo_split_dirs(data_yaml, data)
    if not split_dirs:
        raise ValueError(f"No image/label split directories found in {data_yaml}")

    report = {
        "data_yaml": str(data_yaml),
        "classes": class_names,
        "images": 0,
        "label_files": 0,
        "boxes": 0,
        "empty_label_files": 0,
        "invalid_lines": 0,
        "missing_labels": 0,
        "out_of_range_class_ids": 0,
        "out_of_range_boxes": 0,
        "class_counts": {name: 0 for name in class_names},
    }
    image_suffixes = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    seen_label_files: set[Path] = set()

    for _, image_dir, label_dir in split_dirs:
        for image_path in sorted(path for path in image_dir.rglob("*") if path.suffix.lower() in image_suffixes):
            report["images"] += 1
            label_path = label_dir / f"{image_path.stem}.txt"
            if not label_path.exists():
                report["missing_labels"] += 1
                continue
            if label_path not in seen_label_files:
                report["label_files"] += 1
                seen_label_files.add(label_path)
            lines = [line for line in label_path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
            if not lines:
                report["empty_label_files"] += 1
            for line in lines:
                parsed = parse_yolo_box(line)
                if parsed is None:
                    report["invalid_lines"] += 1
                    continue
                class_id, x_center, y_center, width, height = parsed
                if class_id < 0 or class_id >= len(class_names):
                    report["out_of_range_class_ids"] += 1
                    continue
                if not (0.0 <= x_center <= 1.0 and 0.0 <= y_center <= 1.0 and 0.0 < width <= 1.0 and 0.0 < height <= 1.0):
                    report["out_of_range_boxes"] += 1
                    continue
                report["boxes"] += 1
                report["class_counts"][class_names[class_id]] += 1

    failures = {
        key: report[key]
        for key in ("invalid_lines", "missing_labels", "out_of_range_class_ids", "out_of_range_boxes")
        if report[key]
    }
    if failures:
        raise ValueError(f"YOLO dataset validation failed for {data_yaml}: {failures}")
    if report["boxes"] < min_boxes:
        raise ValueError(f"YOLO dataset validation failed for {data_yaml}: only {report['boxes']} boxes")
    return report


def merge_yolo_dataset(
    source_name: str,
    source_data_yaml: Path,
    target_root: Path,
    target_classes: list[str],
    class_map: dict[str, str],
    min_box_area: float,
    min_box_side: float,
    max_aspect_ratio: float,
) -> dict[str, Any]:
    if not source_data_yaml.exists():
        raise FileNotFoundError(f"YOLO data.yaml not found: {source_data_yaml}")
    with source_data_yaml.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    source_classes = load_yolo_names(data)
    target_to_id = {name: idx for idx, name in enumerate(target_classes)}
    split_dirs = yolo_split_dirs(source_data_yaml, data)
    if not split_dirs:
        raise ValueError(f"No YOLO image/label split directories found for {source_data_yaml}")

    summary = {
        "source": source_name,
        "data_yaml": str(source_data_yaml),
        "images": 0,
        "boxes": 0,
        "skipped_unmapped": 0,
        "skipped_invalid": 0,
        "skipped_tiny": 0,
        "skipped_extreme_ratio": 0,
        "class_counts": {name: 0 for name in target_classes},
    }
    image_suffixes = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    for split, image_dir, label_dir in split_dirs:
        out_image_dir = target_root / "images" / split
        out_label_dir = target_root / "labels" / split
        out_image_dir.mkdir(parents=True, exist_ok=True)
        out_label_dir.mkdir(parents=True, exist_ok=True)
        for source_image in sorted(path for path in image_dir.rglob("*") if path.suffix.lower() in image_suffixes):
            source_label = label_dir / f"{source_image.stem}.txt"
            if not source_label.exists():
                continue
            with Image.open(source_image) as img:
                image_width, image_height = img.size
            output_lines: list[str] = []
            for raw_line in source_label.read_text(encoding="utf-8", errors="ignore").splitlines():
                parsed = parse_yolo_box(raw_line)
                if parsed is None:
                    summary["skipped_invalid"] += 1
                    continue
                source_class_id = parsed[0]
                if source_class_id < 0 or source_class_id >= len(source_classes):
                    summary["skipped_invalid"] += 1
                    continue
                source_class = source_classes[source_class_id]
                target_class = class_map.get(normalise_name(source_class))
                if target_class not in target_to_id:
                    summary["skipped_unmapped"] += 1
                    continue
                x1, y1, x2, y2 = yolo_box_to_xyxy(parsed, image_width, image_height)
                width = x2 - x1
                height = y2 - y1
                if width <= 0 or height <= 0:
                    summary["skipped_invalid"] += 1
                    continue
                area = width * height
                if width < min_box_side or height < min_box_side or area < min_box_area:
                    summary["skipped_tiny"] += 1
                    continue
                aspect_ratio = max(width / height, height / width)
                if aspect_ratio > max_aspect_ratio:
                    summary["skipped_extreme_ratio"] += 1
                    continue
                target_class_id = target_to_id[target_class]
                output_lines.append(xyxy_to_yolo_line(target_class_id, (x1, y1, x2, y2), image_width, image_height))
                summary["boxes"] += 1
                summary["class_counts"][target_class] += 1

            if not output_lines:
                continue
            safe_source = normalise_name(source_name).replace("-", "_")
            dest_name = f"{safe_source}_{source_image.stem}{source_image.suffix.lower()}"
            shutil.copy2(source_image, out_image_dir / dest_name)
            (out_label_dir / f"{Path(dest_name).stem}.txt").write_text("\n".join(output_lines) + "\n", encoding="utf-8")
            summary["images"] += 1

    if summary["boxes"] == 0:
        raise ValueError(f"{source_name} produced zero mapped bounding boxes. Check class_map and label format.")
    write_data_yaml(target_root, target_classes)
    validate_yolo_dataset(target_root / "data.yaml")
    return summary


def prepare_kaggle_yolo_headwear(args: argparse.Namespace, cfg: dict[str, Any]) -> dict[str, Any]:
    from kaggle.api.kaggle_api_extended import KaggleApi

    target_root = args.output_root / "traffic-yolo"
    if args.fresh:
        ensure_clean_dir(target_root, fresh=True)
    else:
        target_root.mkdir(parents=True, exist_ok=True)

    sources = cfg.get("headwear_bbox_sources", [])
    selected_refs = set(args.refs or [])
    if selected_refs:
        sources = [source for source in sources if source.get("ref") in selected_refs]
    if not sources:
        raise ValueError("No headwear_bbox_sources configured or selected.")

    api = KaggleApi()
    api.authenticate()
    cache_root = args.download_dir or (args.output_root / "_kaggle_cache" / "headwear")
    cache_root.mkdir(parents=True, exist_ok=True)

    quality = cfg.get("dataset_quality", {})
    summaries: list[dict[str, Any]] = []
    for source in sources:
        if source.get("source_type") != "kaggle_yolo":
            continue
        ref = source["ref"]
        source_name = source.get("name") or ref.replace("/", "_")
        source_dir = cache_root / normalise_name(ref).replace("-", "_")
        source_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"Downloading Kaggle dataset {ref}...")
        api.dataset_download_files(ref, path=source_dir, unzip=True, quiet=False)
        data_yamls = find_yolo_data_yamls(source_dir)
        if not data_yamls:
            raise FileNotFoundError(f"{ref} did not expose a YOLO data.yaml/dataset.yaml after download.")
        class_map = build_config_class_map(source)
        source_summaries = [
            merge_yolo_dataset(
                source_name=source_name,
                source_data_yaml=data_yaml,
                target_root=target_root,
                target_classes=cfg["traffic_classes"],
                class_map=class_map,
                min_box_area=float(quality.get("min_box_area", 64.0)),
                min_box_side=float(quality.get("min_box_side", 4.0)),
                max_aspect_ratio=float(quality.get("max_aspect_ratio", 12.0)),
            )
            for data_yaml in data_yamls
        ]
        summaries.extend(source_summaries)

    manifest = {
        "kind": "headwear_bbox_merge",
        "warning": "Only bbox-capable YOLO sources are merged. Classification-only sources are rejected.",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target_data_yaml": str(target_root / "data.yaml"),
        "sources": summaries,
    }
    manifest["validation"] = validate_yolo_dataset(target_root / "data.yaml")
    write_json(target_root / "headwear_bbox_manifest.json", manifest)
    return manifest


def print_class_summary(title: str, class_counts: dict[str, int]) -> None:
    table = Table(title=title)
    table.add_column("Class")
    table.add_column("Boxes", justify="right")
    for name, count in class_counts.items():
        table.add_row(name, str(count))
    console.print(table)


def prepare_synthetic(args: argparse.Namespace, cfg: dict[str, Any]) -> dict[str, Any]:
    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    random.seed(cfg.get("project", {}).get("seed", 42))

    traffic = generate_synthetic_detection_dataset(
        output_root / "traffic-yolo",
        output_root / "traffic-coco",
        cfg["traffic_classes"],
        args.traffic_images,
        args.image_size,
        args.fresh,
    )
    plate = generate_synthetic_detection_dataset(
        output_root / "indian-license-plate",
        None,
        ["license_plate"],
        args.plate_images,
        args.image_size,
        args.fresh,
    )
    seatbelt = generate_synthetic_detection_dataset(
        output_root / "seatbelt-yolo",
        None,
        cfg["seatbelt_classes"],
        args.seatbelt_images,
        args.image_size,
        args.fresh,
    )
    manifest = {
        "kind": "synthetic",
        "warning": "Synthetic data validates pipeline plumbing only; do not report it as model accuracy.",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "datasets": {"traffic": traffic, "plate": plate, "seatbelt": seatbelt},
    }
    write_json(output_root / "dataset_manifest.json", manifest)
    print_class_summary("Synthetic traffic boxes", traffic["class_counts"])
    return manifest


def parse_class_map(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Class map must use source=target syntax: {value}")
        source, target = value.split("=", 1)
        parsed[normalise_name(source)] = target.strip()
    return parsed


def prepare_coco(args: argparse.Namespace, cfg: dict[str, Any]) -> dict[str, Any]:
    if args.target == "traffic":
        class_names = cfg["traffic_classes"]
        default_yolo = args.output_root / "traffic-yolo"
        default_coco = args.output_root / "traffic-coco"
    elif args.target == "plate":
        class_names = ["license_plate"]
        default_yolo = args.output_root / "indian-license-plate"
        default_coco = None
    else:
        class_names = cfg["seatbelt_classes"]
        default_yolo = args.output_root / "seatbelt-yolo"
        default_coco = None

    class_map = parse_class_map(args.class_map)
    result = convert_coco_dataset(
        args.train_json,
        args.val_json,
        args.train_images,
        args.val_images,
        args.yolo_root or default_yolo,
        args.coco_root if args.coco_root is not None else default_coco,
        class_names,
        class_map,
        args.max_train,
        args.max_val,
        args.fresh,
        args.min_box_area,
        args.min_box_side,
        args.max_aspect_ratio,
        not args.keep_empty,
    )
    write_json((args.yolo_root or default_yolo) / "conversion_manifest.json", result)
    return result


def download_hf_file(repo_id: str, filename: str, local_dir: Path, token: str | None) -> Path:
    from huggingface_hub import hf_hub_download

    return Path(
        hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            repo_type="dataset",
            token=token,
            local_dir=local_dir,
        )
    )


def select_bmd45_files(files: list[str], split_dir: str, annotation_json: dict[str, Any], max_images: int) -> list[str]:
    available = set(files)
    selected: list[str] = []
    for image in annotation_json.get("images", [])[:max_images]:
        candidate = f"{split_dir}/{image['file_name']}"
        if candidate in available:
            selected.append(candidate)
    return selected


def prepare_bmd45(args: argparse.Namespace, cfg: dict[str, Any]) -> dict[str, Any]:
    from huggingface_hub import HfApi

    token = os.environ.get(args.token_env)
    cache_dir = args.download_dir or (args.output_root / "_hf_cache" / "bmd45")
    cache_dir.mkdir(parents=True, exist_ok=True)

    api = HfApi(token=token)
    files = api.list_repo_files(args.repo_id, repo_type="dataset")
    train_ann_file = next((f for f in files if f.startswith("BMD-45-Train/") and f.endswith("_annotations.coco.json")), None)
    val_ann_file = next((f for f in files if f.startswith("BMD-45-Val/") and f.endswith("_annotations.coco.json")), None)
    if train_ann_file is None or val_ann_file is None:
        raise FileNotFoundError("Could not locate BMD-45 train/val COCO annotation files on Hugging Face.")

    train_ann = download_hf_file(args.repo_id, train_ann_file, cache_dir, token)
    val_ann = download_hf_file(args.repo_id, val_ann_file, cache_dir, token)
    with train_ann.open(encoding="utf-8") as f:
        train_coco = json.load(f)
    with val_ann.open(encoding="utf-8") as f:
        val_coco = json.load(f)

    selected_train = select_bmd45_files(files, "BMD-45-Train", train_coco, args.max_train)
    selected_val = select_bmd45_files(files, "BMD-45-Val", val_coco, args.max_val)
    console.print(f"Downloading BMD-45 sample: train={len(selected_train)} val={len(selected_val)}")
    for filename in selected_train + selected_val:
        download_hf_file(args.repo_id, filename, cache_dir, token)

    result = convert_coco_dataset(
        train_ann,
        val_ann,
        cache_dir / "BMD-45-Train",
        cache_dir / "BMD-45-Val",
        args.output_root / "traffic-yolo",
        args.output_root / "traffic-coco",
        cfg["traffic_classes"],
        BMD45_CLASS_MAP,
        args.max_train,
        args.max_val,
        args.fresh,
        args.min_box_area,
        args.min_box_side,
        args.max_aspect_ratio,
        not args.keep_empty,
    )
    result["source"] = args.repo_id
    result["note"] = "BMD-45 supplies vehicle classes only; headwear/person/seatbelt require custom labels or another source."
    write_json(args.output_root / "traffic-yolo" / "conversion_manifest.json", result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare canonical Gridlock training datasets.")
    parser.add_argument("--config", type=Path, default=Path("configs/training.yaml"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    synthetic = subparsers.add_parser("synthetic", help="Generate synthetic YOLO/COCO datasets for smoke tests.")
    synthetic.add_argument("--output-root", type=Path, required=True)
    synthetic.add_argument("--traffic-images", type=int, default=64)
    synthetic.add_argument("--plate-images", type=int, default=32)
    synthetic.add_argument("--seatbelt-images", type=int, default=32)
    synthetic.add_argument("--image-size", type=int, default=640)
    synthetic.add_argument("--fresh", action="store_true")

    coco = subparsers.add_parser("coco-to-yolo", help="Convert COCO annotations to canonical YOLO and optional COCO.")
    coco.add_argument("--target", choices=["traffic", "plate", "seatbelt"], required=True)
    coco.add_argument("--output-root", type=Path, required=True)
    coco.add_argument("--train-json", type=Path, required=True)
    coco.add_argument("--val-json", type=Path, required=True)
    coco.add_argument("--train-images", type=Path, required=True)
    coco.add_argument("--val-images", type=Path, required=True)
    coco.add_argument("--class-map", nargs="+", required=True)
    coco.add_argument("--yolo-root", type=Path, default=None)
    coco.add_argument("--coco-root", type=Path, default=None)
    coco.add_argument("--max-train", type=int, default=None)
    coco.add_argument("--max-val", type=int, default=None)
    coco.add_argument("--min-box-area", type=float, default=64.0)
    coco.add_argument("--min-box-side", type=float, default=4.0)
    coco.add_argument("--max-aspect-ratio", type=float, default=12.0)
    coco.add_argument("--keep-empty", action="store_true")
    coco.add_argument("--fresh", action="store_true")

    bmd = subparsers.add_parser("hf-bmd45", help="Download a BMD-45 sample from Hugging Face and convert it.")
    bmd.add_argument("--output-root", type=Path, required=True)
    bmd.add_argument("--repo-id", default="iisc-aim/BMD-45")
    bmd.add_argument("--token-env", default="HF_TOKEN")
    bmd.add_argument("--download-dir", type=Path, default=None)
    bmd.add_argument("--max-train", type=int, default=1600)
    bmd.add_argument("--max-val", type=int, default=400)
    bmd.add_argument("--min-box-area", type=float, default=64.0)
    bmd.add_argument("--min-box-side", type=float, default=4.0)
    bmd.add_argument("--max-aspect-ratio", type=float, default=12.0)
    bmd.add_argument("--keep-empty", action="store_true")
    bmd.add_argument("--fresh", action="store_true")

    kaggle_headwear = subparsers.add_parser(
        "kaggle-yolo-headwear",
        help="Download configured Kaggle YOLO headwear/helmet datasets and merge bbox labels into traffic-yolo.",
    )
    kaggle_headwear.add_argument("--output-root", type=Path, required=True)
    kaggle_headwear.add_argument("--download-dir", type=Path, default=None)
    kaggle_headwear.add_argument("--refs", nargs="*", default=None, help="Optional Kaggle refs to include from config.")
    kaggle_headwear.add_argument("--fresh", action="store_true")

    validate = subparsers.add_parser("validate-yolo", help="Validate a YOLO data.yaml uses canonical normalized bbox labels.")
    validate.add_argument("--data-yaml", type=Path, required=True)
    validate.add_argument("--min-boxes", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    if args.command == "synthetic":
        result = prepare_synthetic(args, cfg)
    elif args.command == "coco-to-yolo":
        result = prepare_coco(args, cfg)
    elif args.command == "hf-bmd45":
        result = prepare_bmd45(args, cfg)
    elif args.command == "kaggle-yolo-headwear":
        result = prepare_kaggle_yolo_headwear(args, cfg)
    elif args.command == "validate-yolo":
        result = validate_yolo_dataset(args.data_yaml, min_boxes=args.min_boxes)
    else:
        raise ValueError(args.command)
    console.print_json(json.dumps(result))


if __name__ == "__main__":
    main()
