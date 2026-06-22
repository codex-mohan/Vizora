"""Helmet and seatbelt detection using YOLO detectors."""

from __future__ import annotations

import logging
from io import BytesIO

import numpy as np
from PIL import Image
from ultralytics import YOLO

from core.model_registry import ClassifierChoice, ClassifierConfig
from pipeline.contracts import BBox, DetectedObject, ObjectClass, PreprocessedImage
from pipeline.device import get_device, use_half

logger = logging.getLogger(__name__)

HELMET_CLASSES = {
    "helmet": ObjectClass.HELMET,
    "no_helmet": ObjectClass.NO_HELMET,
    "motorcycle_helmet": ObjectClass.HELMET,
    "no_headwear": ObjectClass.NO_HELMET,
    "turban_pagdi": ObjectClass.TURBAN_PAGDI,
    "hat_cap": ObjectClass.HAT_CAP,
    "skull_cap": ObjectClass.SKULL_CAP,
    "hood_scarf": ObjectClass.HOOD_SCARF,
    "construction_hardhat": ObjectClass.CONSTRUCTION_HARDHAT,
    "unclear_head": ObjectClass.UNCLEAR_HEAD,
}

SEATBELT_CLASSES = {
    "seatbelt": ObjectClass.SEATBELT_VISIBLE,
    "seatbelt_visible": ObjectClass.SEATBELT_VISIBLE,
    "no_seatbelt": ObjectClass.NO_SEATBELT,
    "0": ObjectClass.SEATBELT_VISIBLE,
}


def _box_overlap(a: BBox, b: BBox) -> float:
    x1 = max(a.x1, b.x1)
    y1 = max(a.y1, b.y1)
    x2 = min(a.x2, b.x2)
    y2 = min(a.y2, b.y2)
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = max(1, (a.x2 - a.x1) * (a.y2 - a.y1))
    return inter / area_a


class YoloClassifierAdapter:
    """Runs a YOLO detector for helmet/seatbelt and matches to person detections."""

    def __init__(self, config: ClassifierConfig, class_map: dict[str, ObjectClass],
                 target_classes: set[ObjectClass], label: str) -> None:
        self.config = config
        self.class_map = class_map
        self.target_classes = target_classes
        self.label = label
        self._model = None

    @property
    def ready(self) -> bool:
        return self.config.choice != ClassifierChoice.DISABLED

    def classify(self, image: PreprocessedImage, detections: list[DetectedObject],
                 img_array: np.ndarray | None = None) -> dict[str, float]:
        if not self.ready:
            return {}
        model = self._load_model()
        if model is None:
            return {}

        if img_array is None:
            img_array = np.asarray(Image.open(BytesIO(image.media.data)).convert("RGB"))

        results = model.predict(
            img_array,
            conf=self.config.confidence_threshold,
            verbose=False,
            half=use_half(),
        )
        if not results:
            return {}

        person_dets = [d for d in detections if d.label in self.target_classes]
        if not person_dets:
            return {}

        found_items: list[tuple[BBox, float, str]] = []
        names = results[0].names
        for box in results[0].boxes:
            cls_name = str(names[int(box.cls.item())])
            if cls_name not in self.class_map:
                continue
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            conf = float(box.conf.item())
            found_items.append((BBox(x1=x1, y1=y1, x2=x2, y2=y2), conf, cls_name))

        scores: dict[str, float] = {}
        for person in person_dets:
            best_score = 0.0
            for item_box, item_conf, cls_name in found_items:
                overlap = _box_overlap(item_box, person.bbox)
                if overlap > 0.1 and item_conf > best_score:
                    best_score = item_conf
            if best_score > 0:
                scores[person.id] = best_score

        return scores

    def _load_model(self):
        if self._model is not None:
            return self._model
        if not self.config.weights:
            logger.warning("[%s] No weights configured", self.label)
            return None
        from core.config import BACKEND_ROOT
        weight_path = BACKEND_ROOT / self.config.weights
        if not weight_path.exists():
            logger.warning("[%s] Weights not found: %s", self.label, weight_path)
            return None
        self._model = YOLO(str(weight_path))
        self._model.to(get_device())
        logger.info("[%s] Loaded YOLO detector from %s", self.label, weight_path)
        return self._model


def build_helmet_classifier(config: ClassifierConfig) -> YoloClassifierAdapter:
    return YoloClassifierAdapter(
        config=config,
        class_map=HELMET_CLASSES,
        target_classes={ObjectClass.RIDER, ObjectClass.PEDESTRIAN, ObjectClass.DRIVER},
        label="helmet",
    )


def build_seatbelt_classifier(config: ClassifierConfig) -> YoloClassifierAdapter:
    return YoloClassifierAdapter(
        config=config,
        class_map=SEATBELT_CLASSES,
        target_classes={ObjectClass.DRIVER, ObjectClass.RIDER},
        label="seatbelt",
    )
