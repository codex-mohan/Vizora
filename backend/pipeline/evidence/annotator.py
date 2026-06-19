"""Evidence image annotator: draws bboxes, labels, face blur, plate redaction, watermark."""

from __future__ import annotations

import cv2
import numpy as np
from datetime import datetime

from pipeline.contracts import (
    BBox,
    DetectedObject,
    InferenceResult,
    ObjectClass,
    ViolationClass,
    ViolationPrediction,
)

VIOLATION_COLORS: dict[ViolationClass, tuple[int, int, int]] = {
    ViolationClass.HELMET: (0, 0, 255),
    ViolationClass.SEATBELT: (0, 140, 255),
    ViolationClass.TRIPLE_RIDE: (0, 255, 255),
    ViolationClass.WRONG_SIDE: (255, 0, 0),
    ViolationClass.STOP_LINE: (255, 0, 255),
    ViolationClass.RED_LIGHT: (0, 0, 255),
    ViolationClass.ILLEGAL_PARKING: (128, 0, 128),
}

DETECTION_COLORS: dict[ObjectClass, tuple[int, int, int]] = {
    ObjectClass.CAR: (255, 255, 0),
    ObjectClass.MOTORCYCLE: (0, 255, 0),
    ObjectClass.AUTO: (0, 255, 255),
    ObjectClass.BUS: (255, 0, 0),
    ObjectClass.TRUCK: (128, 128, 0),
    ObjectClass.RIDER: (0, 200, 0),
    ObjectClass.DRIVER: (0, 150, 0),
    ObjectClass.PEDESTRIAN: (200, 200, 200),
    ObjectClass.PLATE: (255, 255, 255),
}

_BLUR_KERNEL = (99, 99)
_BLUR_SIGMA = 30
_FONT = cv2.FONT_HERSHEY_SIMPLEX


class EvidenceAnnotator:
    """Draws annotated evidence images for violation packets."""

    def __init__(self, face_blur: bool = True, plate_redact: bool = True) -> None:
        self.face_blur = face_blur
        self.plate_redact = plate_redact

    def annotate(
        self,
        image: np.ndarray,
        result: InferenceResult,
        draw_detections: bool = True,
        draw_violations: bool = True,
        draw_plates: bool = True,
    ) -> np.ndarray:
        """Return annotated copy of *image* with all overlays."""
        annotated = image.copy()

        if draw_detections:
            for det in result.detections:
                self._draw_bbox(
                    annotated,
                    det.bbox,
                    det.label.value,
                    det.confidence,
                    DETECTION_COLORS.get(det.label, (200, 200, 200)),
                )

        if draw_violations:
            for viol in result.violations:
                if viol.bbox is not None:
                    color = VIOLATION_COLORS.get(viol.violation_type, (0, 0, 255))
                    label = f"! {viol.violation_type.value} ({viol.confidence:.0%})"
                    self._draw_bbox(annotated, viol.bbox, label, viol.confidence, color, thickness=3)

        if self.face_blur:
            for det in result.detections:
                if det.label in (ObjectClass.RIDER, ObjectClass.DRIVER, ObjectClass.PEDESTRIAN):
                    self._blur_region(annotated, det.bbox, blur_type="face")

        if self.plate_redact and draw_plates:
            for det in result.detections:
                if det.label == ObjectClass.PLATE:
                    self._redact_plate(annotated, det.bbox)

        self._add_watermark(annotated, result.camera_id, result.timestamp)

        if result.violations:
            annotated = self._add_summary_bar(annotated, result.violations)

        return annotated

    def _draw_bbox(
        self,
        img: np.ndarray,
        bbox: BBox,
        label: str,
        confidence: float,
        color: tuple[int, int, int],
        thickness: int = 2,
    ) -> None:
        h, w = img.shape[:2]
        x1, y1 = max(0, int(bbox.x1)), max(0, int(bbox.y1))
        x2, y2 = min(w, int(bbox.x2)), min(h, int(bbox.y2))

        cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)

        text = f"{label} {confidence:.0%}"
        font_scale = 0.5
        (tw, th), baseline = cv2.getTextSize(text, _FONT, font_scale, 1)

        label_y = max(y1 - th - 8, 0)
        cv2.rectangle(img, (x1, label_y), (x1 + tw + 8, y1), color, -1)
        cv2.putText(img, text, (x1 + 4, y1 - 4), _FONT, font_scale, (0, 0, 0), 1, cv2.LINE_AA)

    def _blur_region(self, img: np.ndarray, bbox: BBox, blur_type: str = "face") -> None:
        h, w = img.shape[:2]
        x1, y1 = max(0, int(bbox.x1)), max(0, int(bbox.y1))
        x2, y2 = min(w, int(bbox.x2)), min(h, int(bbox.y2))

        if blur_type == "face":
            face_h = (y2 - y1) // 3
            y2 = y1 + face_h

        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        if x2 <= x1 or y2 <= y1:
            return

        roi = img[y1:y2, x1:x2]
        if roi.size == 0:
            return

        img[y1:y2, x1:x2] = cv2.GaussianBlur(roi, _BLUR_KERNEL, _BLUR_SIGMA)

    def _redact_plate(self, img: np.ndarray, bbox: BBox) -> None:
        h, w = img.shape[:2]
        x1, y1 = max(0, int(bbox.x1)), max(0, int(bbox.y1))
        x2, y2 = min(w, int(bbox.x2)), min(h, int(bbox.y2))

        if x2 <= x1 or y2 <= y1:
            return

        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), -1)
        cv2.putText(
            img,
            "REDACTED",
            (x1 + 2, (y1 + y2) // 2 + 4),
            _FONT,
            0.4,
            (255, 255, 255),
            1,
        )

    def _add_watermark(self, img: np.ndarray, camera_id: str, timestamp: datetime) -> None:
        ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [f"Camera: {camera_id}", f"Time: {ts_str}", "VIZORA EVIDENCE"]

        font_scale = 0.5
        y_offset = 20
        for line in lines:
            cv2.putText(img, line, (11, y_offset + 1), _FONT, font_scale, (0, 0, 0), 2, cv2.LINE_AA)
            cv2.putText(img, line, (10, y_offset), _FONT, font_scale, (255, 255, 255), 1, cv2.LINE_AA)
            y_offset += 20

    def _add_summary_bar(
        self, img: np.ndarray, violations: list[ViolationPrediction]
    ) -> np.ndarray:
        h, w = img.shape[:2]
        bar_height = 30
        bar = np.full((bar_height, w, 3), 40, dtype=np.uint8)

        types = [v.violation_type.value for v in violations]
        summary = f"Violations: {', '.join(types)}"
        cv2.putText(bar, summary, (10, 20), _FONT, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

        return np.vstack([img, bar])


def annotate_evidence(
    image_bytes: bytes,
    result: InferenceResult,
    face_blur: bool = True,
    plate_redact: bool = True,
) -> bytes:
    """Take raw image bytes + inference result, return annotated PNG bytes."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image")

    annotator = EvidenceAnnotator(face_blur=face_blur, plate_redact=plate_redact)
    annotated = annotator.annotate(img, result)

    _, buffer = cv2.imencode(".png", annotated)
    return buffer.tobytes()
