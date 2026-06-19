"""Tests for evidence image annotator."""

from __future__ import annotations

from datetime import datetime, timezone

import cv2
import numpy as np
import pytest

from pipeline.contracts import (
    BBox,
    DetectedObject,
    ImageQuality,
    InferenceResult,
    ObjectClass,
    ProcessingMode,
    ViolationClass,
    ViolationPrediction,
)
from pipeline.evidence.annotator import EvidenceAnnotator, annotate_evidence


def _make_test_image(width: int = 640, height: int = 480) -> np.ndarray:
    rng = np.random.RandomState(42)
    return rng.randint(0, 255, (height, width, 3), dtype=np.uint8)


def _make_result(
    detections: list[DetectedObject] | None = None,
    violations: list[ViolationPrediction] | None = None,
) -> InferenceResult:
    return InferenceResult(
        request_id="test-001",
        camera_id="test-cam",
        timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        mode=ProcessingMode.STILL_IMAGE,
        quality=ImageQuality(brightness=128, blur=100, haze=0.1, noise=5, score=0.8),
        detections=detections or [],
        tracks=[],
        poses=[],
        plates=[],
        violations=violations or [],
        evidence_packet_id="ev-001",
        model_profile="mvp",
        review_required=False,
        review_reasons=[],
    )


class TestAnnotator:
    def test_returns_same_size(self) -> None:
        img = _make_test_image()
        result = _make_result()
        annotated = EvidenceAnnotator(face_blur=False, plate_redact=False).annotate(img, result)
        assert annotated.shape == img.shape

    def test_face_blur_reduces_variance(self) -> None:
        img = _make_test_image()
        det = DetectedObject(
            id="rider-1",
            label=ObjectClass.RIDER,
            bbox=BBox(x1=100, y1=100, x2=200, y2=200),
            confidence=0.9,
        )
        result = _make_result(detections=[det])

        annotator = EvidenceAnnotator(face_blur=True, plate_redact=False)
        annotated = annotator.annotate(img, result)

        face_region = annotated[100:133, 100:200]
        orig_region = img[100:133, 100:200]
        assert face_region.var() < orig_region.var()

    def test_plate_redaction_blacks_out_region(self) -> None:
        img = _make_test_image()
        det = DetectedObject(
            id="plate-1",
            label=ObjectClass.PLATE,
            bbox=BBox(x1=300, y1=300, x2=400, y2=350),
            confidence=0.95,
        )
        result = _make_result(detections=[det])

        annotator = EvidenceAnnotator(face_blur=False, plate_redact=True)
        annotated = annotator.annotate(img, result)

        roi = annotated[300:350, 300:400]
        assert roi.mean() < 10

    def test_watermark_added(self) -> None:
        img = _make_test_image()
        result = _make_result()
        annotator = EvidenceAnnotator(face_blur=False, plate_redact=False)
        annotated = annotator.annotate(img, result)
        top_left = annotated[0:30, 0:30]
        assert not np.array_equal(top_left, img[0:30, 0:30])

    def test_summary_bar_added_when_violations_exist(self) -> None:
        img = _make_test_image()
        viol = ViolationPrediction(
            violation_type=ViolationClass.HELMET,
            confidence=0.9,
            object_ids=["rider-1"],
            bbox=BBox(x1=100, y1=100, x2=200, y2=200),
        )
        result = _make_result(violations=[viol])
        annotator = EvidenceAnnotator(face_blur=False, plate_redact=False)
        annotated = annotator.annotate(img, result)
        assert annotated.shape[0] == img.shape[0] + 30

    def test_no_crash_with_empty_detections_and_violations(self) -> None:
        img = _make_test_image()
        result = _make_result()
        annotator = EvidenceAnnotator(face_blur=True, plate_redact=True)
        annotated = annotator.annotate(img, result)
        assert annotated.shape == img.shape


class TestAnnotateEvidence:
    def test_convenience_function_returns_bytes(self) -> None:
        img = _make_test_image()
        _, buf = cv2.imencode(".png", img)
        image_bytes = buf.tobytes()
        result = _make_result()
        output = annotate_evidence(image_bytes, result)
        assert isinstance(output, bytes)
        assert len(output) > 0

    def test_output_is_valid_png(self) -> None:
        img = _make_test_image()
        _, buf = cv2.imencode(".png", img)
        image_bytes = buf.tobytes()
        result = _make_result()
        output = annotate_evidence(image_bytes, result)
        decoded = cv2.imdecode(np.frombuffer(output, np.uint8), cv2.IMREAD_COLOR)
        assert decoded is not None
