"""Detection adapters."""

from __future__ import annotations

import logging
from io import BytesIO
from uuid import uuid4

import numpy as np
from PIL import Image
from ultralytics import YOLO

from core.config import BACKEND_ROOT
from core.model_registry import DetectorChoice, DetectorConfig
from pipeline.contracts import BBox, DetectedObject, ObjectClass, PreprocessedImage

logger = logging.getLogger(__name__)

COCO_TO_OBJECT_CLASS = {
    "person": ObjectClass.PEDESTRIAN,
    "bicycle": ObjectClass.BICYCLE,
    "car": ObjectClass.CAR,
    "motorcycle": ObjectClass.MOTORCYCLE,
    "bus": ObjectClass.BUS,
    "truck": ObjectClass.TRUCK,
}


YOLO_MODEL_NAMES = {
    DetectorChoice.YOLO11N: "yolo11n.pt",
    DetectorChoice.YOLO11S: "yolo11s.pt",
    DetectorChoice.YOLO11M: "yolo11m.pt",
    DetectorChoice.YOLO11X: "yolo11x.pt",
}


class DetectorAdapter:
    def __init__(self, config: DetectorConfig) -> None:
        self.config = config
        self._model = None
        self._is_dfine = False

    @property
    def ready(self) -> bool:
        if self.config.choice == DetectorChoice.DFINE_L:
            dfine_weights = BACKEND_ROOT / "models" / "detect" / "dfine_l.pth"
            return dfine_weights.exists() or self._has_dfine_repo()
        return self.config.choice in YOLO_MODEL_NAMES or bool(
            self.config.weights and (BACKEND_ROOT / self.config.weights).exists()
        )

    def detect(self, image: PreprocessedImage) -> list[DetectedObject]:
        if not self.ready:
            return []

        try:
            model = self._load_model()
            pil_image = Image.open(BytesIO(image.media.data)).convert("RGB")
            img_array = np.asarray(pil_image)

            if self._is_dfine:
                return self._detect_dfine(model, img_array, pil_image.size)
            else:
                return self._detect_yolo(model, img_array)
        except Exception as e:
            logger.warning("Detection failed: %s", e)
            return []

    def _detect_yolo(self, model: YOLO, img_array: np.ndarray) -> list[DetectedObject]:
        results = model.predict(
            img_array,
            conf=self.config.confidence_threshold,
            iou=self.config.iou_threshold,
            verbose=False,
        )
        if not results:
            return []

        detections: list[DetectedObject] = []
        names = results[0].names
        for box in results[0].boxes:
            class_id = int(box.cls.item())
            class_name = str(names[class_id])
            label = COCO_TO_OBJECT_CLASS.get(class_name)
            if label is None:
                continue
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            detections.append(
                DetectedObject(
                    id=f"det-{uuid4().hex}",
                    label=label,
                    bbox=BBox(x1=x1, y1=y1, x2=x2, y2=y2),
                    confidence=float(box.conf.item()),
                    metadata={"source_class": class_name, "model": self.config.choice.value},
                )
            )
        return self._infer_riders(detections)

    def _detect_dfine(self, model, img_array: np.ndarray, img_size: tuple[int, int]) -> list[DetectedObject]:
        import torch

        img_w, img_h = img_size
        img_tensor = torch.from_numpy(img_array).permute(2, 0, 1).float().div(255.0).unsqueeze(0)

        with torch.no_grad():
            outputs = model(img_tensor)

        detections: list[DetectedObject] = []
        if hasattr(outputs, "pred_boxes") and hasattr(outputs, "pred_logits"):
            logits = outputs.pred_logits[0]
            boxes = outputs.pred_boxes[0]
            scores = torch.softmax(logits, dim=-1)

            for i in range(scores.shape[0]):
                max_score, class_id = scores[i].max(dim=-1)
                if max_score.item() < self.config.confidence_threshold:
                    continue
                class_id_int = class_id.item()
                if class_id_int >= len(COCO_TO_OBJECT_CLASS):
                    continue
                class_name = list(COCO_TO_OBJECT_CLASS.keys())[class_id_int]
                label = COCO_TO_OBJECT_CLASS.get(class_name)
                if label is None:
                    continue

                cx, cy, w, h = boxes[i].tolist()
                x1 = (cx - w / 2) * img_w
                y1 = (cy - h / 2) * img_h
                x2 = (cx + w / 2) * img_w
                y2 = (cy + h / 2) * img_h

                detections.append(
                    DetectedObject(
                        id=f"det-{uuid4().hex}",
                        label=label,
                        bbox=BBox(x1=x1, y1=y1, x2=x2, y2=y2),
                        confidence=max_score.item(),
                        metadata={"source_class": class_name, "model": "dfine_l"},
                    )
                )
        return self._infer_riders(detections)

    def _load_model(self):
        if self._model is not None:
            return self._model

        if self.config.choice == DetectorChoice.DFINE_L:
            return self._load_dfine()

        if self.config.weights and (BACKEND_ROOT / self.config.weights).exists():
            model_path = str(BACKEND_ROOT / self.config.weights)
        else:
            model_path = YOLO_MODEL_NAMES[self.config.choice]
        self._model = YOLO(model_path)
        return self._model

    def _load_dfine(self):
        import torch

        dfine_weights = BACKEND_ROOT / "models" / "detect" / "dfine_l.pth"
        dfine_repo = BACKEND_ROOT / "third_party" / "D-FINE"

        if not dfine_weights.exists():
            logger.warning("D-FINE-L weights not found at %s, falling back to YOLO11x", dfine_weights)
            self._model = YOLO("yolo11x.pt")
            self._is_dfine = False
            return self._model

        if dfine_repo.exists():
            import sys
            sys.path.insert(0, str(dfine_repo / "src"))

        try:
            from src.models.dfine import DFINE

            model = DFINE(
                backbone="hgnetv2_l",
                num_classes=80,
                num_queries=300,
            )
            state = torch.load(str(dfine_weights), map_location="cpu", weights_only=True)
            model.load_state_dict(state, strict=False)
            model.eval()
            self._model = model
            self._is_dfine = True
            logger.info("D-FINE-L loaded from %s", dfine_weights)
        except Exception as e:
            logger.warning("Failed to load D-FINE-L: %s, falling back to YOLO11x", e)
            self._model = YOLO("yolo11x.pt")
            self._is_dfine = False

        return self._model

    def _has_dfine_repo(self) -> bool:
        return (BACKEND_ROOT / "third_party" / "D-FINE").exists()

    def _infer_riders(self, detections: list[DetectedObject]) -> list[DetectedObject]:
        motorcycles = [d for d in detections if d.label == ObjectClass.MOTORCYCLE]
        if not motorcycles:
            return detections

        updated: list[DetectedObject] = []
        for detection in detections:
            if detection.label != ObjectClass.PEDESTRIAN:
                updated.append(detection)
                continue
            if any(self._boxes_overlap(detection.bbox, bike.bbox) > 0.05 for bike in motorcycles):
                updated.append(detection.model_copy(update={"label": ObjectClass.RIDER}))
            else:
                updated.append(detection)
        return updated

    def _boxes_overlap(self, first: BBox, second: BBox) -> float:
        x1 = max(first.x1, second.x1)
        y1 = max(first.y1, second.y1)
        x2 = min(first.x2, second.x2)
        y2 = min(first.y2, second.y2)
        intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        if intersection == 0.0:
            return 0.0
        return intersection / max(first.area, 1.0)


def build_detector(config: DetectorConfig) -> DetectorAdapter:
    return DetectorAdapter(config)
