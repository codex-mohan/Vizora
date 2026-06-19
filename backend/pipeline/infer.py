"""Image-first inference orchestrator."""

from __future__ import annotations

from uuid import uuid4

from core.camera_state import CameraStateRegistry
from core.config import BACKEND_ROOT, Settings
from core.model_registry import ModelProfile
from pipeline.anpr.pipeline import AnprPipeline, build_anpr_pipeline
from pipeline.classify.classifiers import (
    BinaryClassifierAdapter,
    build_helmet_classifier,
    build_seatbelt_classifier,
)
from pipeline.contracts import InferenceResult, MediaInput, ReviewReason
from pipeline.detect.detector import DetectorAdapter, build_detector
from pipeline.evidence.packet import EvidencePacketBuilder
from pipeline.pose.pose_estimator import PoseEstimatorAdapter, build_pose_estimator
from pipeline.preprocess.service import PreprocessingService
from pipeline.scene import load_scene_config
from pipeline.track.tracker import TrackerAdapter, build_tracker
from pipeline.violation.engine import ViolationEngine
from pipeline.vlm.describer import VlmDescriber, build_vlm_describer


class InferencePipeline:
    def __init__(self, settings: Settings, profile: ModelProfile) -> None:
        self.settings = settings
        self.profile = profile
        self.camera_states = CameraStateRegistry(settings)
        self.preprocessor = PreprocessingService(settings, self.camera_states)
        self.detector: DetectorAdapter = build_detector(profile.detector)
        self.tracker: TrackerAdapter = build_tracker(profile.tracker)
        self.pose_estimator: PoseEstimatorAdapter = build_pose_estimator(profile.pose)
        self.helmet_classifier: BinaryClassifierAdapter = build_helmet_classifier(profile.helmet_classifier)
        self.seatbelt_classifier: BinaryClassifierAdapter = build_seatbelt_classifier(profile.seatbelt_classifier)
        self.anpr: AnprPipeline = build_anpr_pipeline(profile.plate_detector, profile.ocr)
        self.vlm: VlmDescriber = build_vlm_describer(profile.vlm)
        self.violation_engine = ViolationEngine()
        self.evidence_builder = EvidencePacketBuilder()

    def process(self, media: MediaInput) -> InferenceResult:
        scene = load_scene_config(BACKEND_ROOT / self.settings.camera_scenes_path, media.camera_id)
        preprocessed = self.preprocessor.run(media, self.profile)

        review_reasons: list[ReviewReason] = []
        if preprocessed.quality.review_required:
            review_reasons.append(ReviewReason.POOR_IMAGE_QUALITY)
        if not self.detector.ready:
            review_reasons.append(ReviewReason.MODEL_NOT_READY)

        detections = self.detector.detect(preprocessed)
        tracks = self.tracker.update(detections, media.mode, image_bytes=media.data)
        poses = self.pose_estimator.estimate(preprocessed, detections)
        helmet_scores = self.helmet_classifier.classify(preprocessed, detections)
        seatbelt_scores = self.seatbelt_classifier.classify(preprocessed, detections)
        plates = self.anpr.recognize(preprocessed, detections=detections)
        if any(plate.review_required for plate in plates):
            review_reasons.append(ReviewReason.LOW_CONFIDENCE)
        violations = self.violation_engine.evaluate(
            mode=media.mode,
            scene=scene,
            detections=detections,
            tracks=tracks,
            poses=poses,
            plates=plates,
            helmet_scores=helmet_scores,
            seatbelt_scores=seatbelt_scores,
        )

        for violation in violations:
            for reason in violation.review_reasons:
                if reason not in review_reasons:
                    review_reasons.append(reason)

        result = InferenceResult(
            request_id=f"req-{uuid4().hex}",
            camera_id=media.camera_id,
            timestamp=media.timestamp,
            mode=media.mode,
            quality=preprocessed.quality,
            detections=detections,
            tracks=tracks,
            poses=poses,
            plates=plates,
            violations=violations,
            evidence_packet_id="pending",
            model_profile=self.profile.name.value,
            review_required=bool(review_reasons) or any(v.review_required for v in violations),
            review_reasons=review_reasons,
        )
        evidence = self.evidence_builder.attach(media, result)
        result = result.model_copy(update={"evidence_packet_id": evidence.id})

        description = self.vlm.describe(result)
        if description:
            result = result.model_copy(update={"description": description})

        try:
            from pipeline.evidence.annotator import annotate_evidence

            annotated_bytes = annotate_evidence(
                media.data,
                result,
                face_blur=self.settings.face_blur,
                plate_redact=self.settings.plate_redact_public,
            )
            evidence.annotated_image_bytes = annotated_bytes
        except Exception:
            pass

        return result
