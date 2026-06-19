"""Helmet and seatbelt classifiers using EfficientNetV2-S."""

from __future__ import annotations

from io import BytesIO

import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from torchvision.models import efficientnet_v2_s

from core.model_registry import ClassifierChoice, ClassifierConfig
from pipeline.contracts import BBox, DetectedObject, ObjectClass, PreprocessedImage

HEAD_RATIO = 0.25
DRIVER_WINDOW_RATIO = 0.4

PREPROCESS = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


class BinaryClassifierAdapter:
    def __init__(self, config: ClassifierConfig, positive_label: str, target_classes: set[ObjectClass]) -> None:
        self.config = config
        self.positive_label = positive_label
        self.target_classes = target_classes
        self._model = None

    @property
    def ready(self) -> bool:
        return self.config.choice != ClassifierChoice.DISABLED

    def classify(self, image: PreprocessedImage, detections: list[DetectedObject]) -> dict[str, float]:
        if not self.ready:
            return {}
        model = self._load_model()
        pil_image = Image.open(BytesIO(image.media.data)).convert("RGB")
        scores: dict[str, float] = {}
        for det in detections:
            if det.label not in self.target_classes:
                continue
            crop_box = self._get_crop_box(det, pil_image.size)
            crop = pil_image.crop(crop_box)
            if crop.size[0] < 10 or crop.size[1] < 10:
                continue
            tensor = PREPROCESS(crop).unsqueeze(0)
            with torch.no_grad():
                logits = model(tensor)
                prob = torch.sigmoid(logits).item()
            scores[det.id] = float(prob)
        return scores

    def _load_model(self):
        if self._model is not None:
            return self._model
        model = efficientnet_v2_s(weights="DEFAULT")
        model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, 1)
        if self.config.weights:
            from core.config import BACKEND_ROOT
            weight_path = BACKEND_ROOT / self.config.weights
            if weight_path.exists():
                state = torch.load(str(weight_path), map_location="cpu", weights_only=True)
                model.load_state_dict(state)
        model.eval()
        self._model = model
        return self._model

    def _get_crop_box(self, det: DetectedObject, img_size: tuple[int, int]) -> tuple[int, int, int, int]:
        img_w, img_h = img_size
        if self.positive_label == "helmet":
            return (
                max(0, int(det.bbox.x1)),
                max(0, int(det.bbox.y1)),
                min(img_w, int(det.bbox.x2)),
                min(img_h, int(det.bbox.y1 + (det.bbox.y2 - det.bbox.y1) * HEAD_RATIO)),
            )
        veh_w = det.bbox.x2 - det.bbox.x1
        return (
            max(0, int(det.bbox.x1)),
            max(0, int(det.bbox.y1)),
            min(img_w, int(det.bbox.x1 + veh_w * DRIVER_WINDOW_RATIO)),
            min(img_h, int(det.bbox.y2)),
        )


def build_helmet_classifier(config: ClassifierConfig) -> BinaryClassifierAdapter:
    return BinaryClassifierAdapter(config, positive_label="helmet", target_classes={ObjectClass.RIDER, ObjectClass.PEDESTRIAN, ObjectClass.DRIVER})


def build_seatbelt_classifier(config: ClassifierConfig) -> BinaryClassifierAdapter:
    return BinaryClassifierAdapter(config, positive_label="seatbelt", target_classes={ObjectClass.DRIVER, ObjectClass.RIDER})
