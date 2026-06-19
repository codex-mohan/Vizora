"""ByteTrack v2 tracker using Ultralytics built-in tracking."""

from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image
from ultralytics import YOLO

from core.model_registry import TrackerChoice, TrackerConfig
from pipeline.contracts import BBox, DetectedObject, ObjectClass, Point, ProcessingMode, Track

COCO_TO_OBJECT_CLASS = {
    "person": ObjectClass.PEDESTRIAN,
    "bicycle": ObjectClass.BICYCLE,
    "car": ObjectClass.CAR,
    "motorcycle": ObjectClass.MOTORCYCLE,
    "bus": ObjectClass.BUS,
    "truck": ObjectClass.TRUCK,
}


class TrackerAdapter:
    def __init__(self, config: TrackerConfig) -> None:
        self.config = config
        self._model = None

    def update(self, detections: list[DetectedObject], mode: ProcessingMode, image_bytes: bytes | None = None) -> list[Track]:
        if self.config.choice == TrackerChoice.DISABLED or mode == ProcessingMode.STILL_IMAGE:
            return self._detections_to_tracks(detections)

        if image_bytes is None:
            return self._detections_to_tracks(detections)

        model = self._load_model()
        pil_image = Image.open(BytesIO(image_bytes)).convert("RGB")
        results = model.track(np.asarray(pil_image), persist=True, verbose=False, tracker="bytetrack.yaml")
        if not results or not results[0].boxes or results[0].boxes.id is None:
            return self._detections_to_tracks(detections)

        tracks: list[Track] = []
        boxes = results[0].boxes
        names = results[0].names
        for box in boxes:
            track_id_val = int(box.id.item()) if box.id is not None else None
            if track_id_val is None:
                continue
            class_id = int(box.cls.item())
            class_name = str(names[class_id])
            label = COCO_TO_OBJECT_CLASS.get(class_name, ObjectClass.UNKNOWN)
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]
            tracks.append(Track(
                track_id=f"bt-{track_id_val}",
                object_id=f"det-{track_id_val}",
                label=label,
                bbox=BBox(x1=x1, y1=y1, x2=x2, y2=y2),
                confidence=float(box.conf.item()),
                trajectory=[Point(x=(x1 + x2) / 2, y=(y1 + y2) / 2)],
            ))
        return tracks

    def _detections_to_tracks(self, detections: list[DetectedObject]) -> list[Track]:
        return [
            Track(
                track_id=f"track-{d.id}",
                object_id=d.id,
                label=d.label,
                bbox=d.bbox,
                confidence=d.confidence,
            )
            for d in detections
        ]

    def _load_model(self):
        if self._model is not None:
            return self._model
        self._model = YOLO("yolo11n.pt")
        return self._model


def build_tracker(config: TrackerConfig) -> TrackerAdapter:
    return TrackerAdapter(config)
