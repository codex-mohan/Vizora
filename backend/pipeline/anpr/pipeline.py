"""ANPR pipeline: vehicle crop + PaddleOCR."""

from __future__ import annotations

import re
from io import BytesIO

import numpy as np
from PIL import Image

from core.model_registry import OcrChoice, OcrConfig, PlateDetectorConfig
from pipeline.contracts import BBox, DetectedObject, ObjectClass, PlateResult, PreprocessedImage

PLATE_CANDIDATE_RE = re.compile(r"[A-Z0-9]{4,12}")
VEHICLE_CLASSES = {ObjectClass.CAR, ObjectClass.MOTORCYCLE, ObjectClass.BUS, ObjectClass.TRUCK, ObjectClass.AUTO}


class AnprPipeline:
    def __init__(self, plate_detector: PlateDetectorConfig, ocr: OcrConfig) -> None:
        self.plate_detector = plate_detector
        self.ocr = ocr
        self._ocr_model = None

    @property
    def ready(self) -> bool:
        return self.ocr.primary == OcrChoice.PADDLEOCR_PP_OCRV5

    def recognize(self, image: PreprocessedImage, detections: list[DetectedObject] | None = None) -> list[PlateResult]:
        if not self.ready:
            return []
        try:
            ocr_model = self._load_ocr()
            pil_image = Image.open(BytesIO(image.media.data)).convert("RGB")
            img_w, img_h = pil_image.size

            crops: list[tuple[BBox, Image.Image]] = []
            vehicles = [d for d in (detections or []) if d.label in VEHICLE_CLASSES]
            if vehicles:
                for veh in vehicles:
                    plate_box = self._estimate_plate_region(veh.bbox, img_w, img_h)
                    crop = pil_image.crop((int(plate_box.x1), int(plate_box.y1), int(plate_box.x2), int(plate_box.y2)))
                    if crop.size[0] > 20 and crop.size[1] > 10:
                        crops.append((plate_box, crop))
            else:
                crops.append((BBox(x1=0, y1=0, x2=float(img_w), y2=float(img_h)), pil_image))

            candidates: list[PlateResult] = []
            for crop_box, crop_img in crops:
                raw = ocr_model.predict(np.asarray(crop_img))
                if not raw:
                    continue
                page = raw[0]
                for text, score, box in zip(page.get("rec_texts", []), page.get("rec_scores", []), page.get("rec_boxes", [])):
                    normalized = self._normalize_text(str(text))
                    if not normalized:
                        continue
                    bbox = self._offset_ocr_box(box, crop_box)
                    candidates.append(
                        PlateResult(
                            plate_text=normalized,
                            confidence=float(score),
                            bbox=bbox,
                            review_required=float(score) < self.ocr.accept_threshold,
                        )
                    )
            return sorted(candidates, key=lambda x: x.confidence, reverse=True)[:5]
        except Exception:
            return []

    def _estimate_plate_region(self, vehicle: BBox, img_w: int, img_h: int) -> BBox:
        v_w = vehicle.x2 - vehicle.x1
        v_h = vehicle.y2 - vehicle.y1
        plate_w = v_w * 0.7
        plate_h = v_h * 0.15
        cx = (vehicle.x1 + vehicle.x2) / 2
        cy = vehicle.y2 - v_h * 0.12
        return BBox(
            x1=max(0.0, cx - plate_w / 2),
            y1=max(0.0, cy - plate_h / 2),
            x2=min(float(img_w), cx + plate_w / 2),
            y2=min(float(img_h), cy + plate_h / 2),
        )

    def _offset_ocr_box(self, box, offset: BBox) -> BBox | None:
        arr = np.asarray(box, dtype=float).reshape(-1)
        if arr.size < 4:
            return None
        if arr.size == 4:
            x1, y1, x2, y2 = arr.tolist()
            return BBox(x1=x1 + offset.x1, y1=y1 + offset.y1, x2=x2 + offset.x1, y2=y2 + offset.y1)
        xs = arr[0::2] + offset.x1
        ys = arr[1::2] + offset.y1
        return BBox(x1=float(xs.min()), y1=float(ys.min()), x2=float(xs.max()), y2=float(ys.max()))

    def _load_ocr(self):
        if self._ocr_model is not None:
            return self._ocr_model
        from paddleocr import PaddleOCR
        self._ocr_model = PaddleOCR(lang="en", ocr_version="PP-OCRv5", use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)
        return self._ocr_model

    def _normalize_text(self, text: str) -> str | None:
        compact = re.sub(r"[^A-Za-z0-9]", "", text).upper()
        match = PLATE_CANDIDATE_RE.search(compact)
        return match.group(0) if match else None


def build_anpr_pipeline(plate_detector: PlateDetectorConfig, ocr: OcrConfig) -> AnprPipeline:
    return AnprPipeline(plate_detector, ocr)
