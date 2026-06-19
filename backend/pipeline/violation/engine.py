"""Rule engine for image-first and temporal traffic violations."""

from __future__ import annotations

from pipeline.contracts import (
    DetectedObject,
    ObjectClass,
    PlateResult,
    PoseResult,
    ProcessingMode,
    ReviewReason,
    Track,
    ViolationClass,
    ViolationPrediction,
)
from pipeline.scene import CameraSceneConfig


class ViolationEngine:
    def evaluate(
        self,
        *,
        mode: ProcessingMode,
        scene: CameraSceneConfig,
        detections: list[DetectedObject],
        tracks: list[Track],
        poses: list[PoseResult],
        plates: list[PlateResult],
        helmet_scores: dict[str, float],
        seatbelt_scores: dict[str, float],
    ) -> list[ViolationPrediction]:
        violations: list[ViolationPrediction] = []
        violations.extend(self._helmet_violations(detections, helmet_scores))
        violations.extend(self._seatbelt_violations(detections, seatbelt_scores))
        violations.extend(self._triple_ride(mode, detections, tracks))
        violations.extend(self._temporal_placeholders(mode, scene))
        return violations

    def _helmet_violations(
        self,
        detections: list[DetectedObject],
        helmet_scores: dict[str, float],
    ) -> list[ViolationPrediction]:
        violations: list[ViolationPrediction] = []
        for detection in detections:
            if detection.label != ObjectClass.RIDER:
                continue
            score = helmet_scores.get(detection.id)
            if score is None:
                continue
            no_helmet_confidence = 1.0 - score
            if no_helmet_confidence >= 0.55:
                violations.append(
                    ViolationPrediction(
                        violation_type=ViolationClass.HELMET,
                        confidence=no_helmet_confidence,
                        object_ids=[detection.id],
                        bbox=detection.bbox,
                    )
                )
        return violations

    def _seatbelt_violations(
        self,
        detections: list[DetectedObject],
        seatbelt_scores: dict[str, float],
    ) -> list[ViolationPrediction]:
        violations: list[ViolationPrediction] = []
        for detection in detections:
            if detection.label != ObjectClass.DRIVER:
                continue
            score = seatbelt_scores.get(detection.id)
            if score is None:
                continue
            no_seatbelt_confidence = 1.0 - score
            if no_seatbelt_confidence >= 0.6:
                violations.append(
                    ViolationPrediction(
                        violation_type=ViolationClass.SEATBELT,
                        confidence=no_seatbelt_confidence,
                        object_ids=[detection.id],
                        bbox=detection.bbox,
                    )
                )
        return violations

    def _triple_ride(
        self,
        mode: ProcessingMode,
        detections: list[DetectedObject],
        tracks: list[Track],
    ) -> list[ViolationPrediction]:
        motorcycles = [d for d in detections if d.label == ObjectClass.MOTORCYCLE]
        riders = [d for d in detections if d.label == ObjectClass.RIDER]
        if not motorcycles or len(riders) < 3:
            return []

        confidence = min(0.9, 0.55 + 0.1 * len(riders))
        reasons: list[ReviewReason] = []
        if mode == ProcessingMode.STILL_IMAGE:
            confidence = min(confidence, 0.68)
            reasons.append(ReviewReason.TEMPORAL_REQUIRED)

        return [
            ViolationPrediction(
                violation_type=ViolationClass.TRIPLE_RIDE,
                confidence=confidence,
                object_ids=[motorcycles[0].id, *[r.id for r in riders[:3]]],
                bbox=motorcycles[0].bbox,
                review_required=bool(reasons),
                review_reasons=reasons,
            )
        ]

    def _temporal_placeholders(
        self,
        mode: ProcessingMode,
        scene: CameraSceneConfig,
    ) -> list[ViolationPrediction]:
        if mode == ProcessingMode.TEMPORAL_BURST and scene.has_temporal_violation_context:
            return []

        if mode == ProcessingMode.STILL_IMAGE:
            return []

        return [
            ViolationPrediction(
                violation_type=ViolationClass.WRONG_SIDE,
                confidence=0.0,
                review_required=True,
                review_reasons=[ReviewReason.MISSING_SCENE_CONFIG],
                evidence={"message": "Temporal violation logic requires camera scene config."},
            )
        ]
