"""Image-first inference orchestrator."""

from __future__ import annotations

import logging
import time
from io import BytesIO
from uuid import uuid4

import numpy as np
import torch
from PIL import Image

from core.camera_state import CameraStateRegistry
from core.config import BACKEND_ROOT, Settings
from core.model_registry import ModelProfile
from pipeline.anpr.pipeline import AnprPipeline, build_anpr_pipeline
from pipeline.classify.classifiers import (
    YoloClassifierAdapter,
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

logger = logging.getLogger(__name__)


class InferencePipeline:
    def __init__(self, settings: Settings, profile: ModelProfile) -> None:
        self.settings = settings
        self.profile = profile
        self.camera_states = CameraStateRegistry(settings)
        self.preprocessor = PreprocessingService(settings, self.camera_states)
        self.detector: DetectorAdapter = build_detector(profile.detector)
        self.tracker: TrackerAdapter = build_tracker(profile.tracker)
        self.pose_estimator: PoseEstimatorAdapter = build_pose_estimator(profile.pose)
        self.helmet_classifier: YoloClassifierAdapter = build_helmet_classifier(profile.helmet_classifier)
        self.seatbelt_classifier: YoloClassifierAdapter = build_seatbelt_classifier(profile.seatbelt_classifier)
        self.anpr: AnprPipeline = build_anpr_pipeline(profile.plate_detector, profile.ocr)
        self.vlm: VlmDescriber = build_vlm_describer(profile.vlm)
        self.violation_engine = ViolationEngine()
        self.evidence_builder = EvidencePacketBuilder()

    def process(self, media: MediaInput, img_array: np.ndarray | None = None) -> InferenceResult:
        t_total = time.perf_counter()
        scene = load_scene_config(BACKEND_ROOT / self.settings.camera_scenes_path, media.camera_id)

        t0 = time.perf_counter()
        if media.realtime_preview:
            preprocessed = self.preprocessor.quick(media)
        else:
            preprocessed = self.preprocessor.run(media, self.profile)
        t_preprocess = time.perf_counter() - t0

        t0 = time.perf_counter()
        if img_array is None:
            img_array = np.asarray(Image.open(BytesIO(media.data)).convert("RGB"))
        t_decode = time.perf_counter() - t0

        review_reasons: list[ReviewReason] = []
        if preprocessed.quality.review_required:
            review_reasons.append(ReviewReason.POOR_IMAGE_QUALITY)
        if not self.detector.ready:
            review_reasons.append(ReviewReason.MODEL_NOT_READY)

        with torch.inference_mode():
            t0 = time.perf_counter()
            detections = self.detector.detect(preprocessed, img_array=img_array)
            t_detect = time.perf_counter() - t0

            if media.realtime_preview:
                tracks = []
                poses = []
                helmet_scores = {}
                seatbelt_scores = {}
                t_track = 0.0
                t_pose = 0.0
                t_helmet = 0.0
                t_seatbelt = 0.0
                t_anpr = 0.0
                t_violation = 0.0
                plates = []
                violations = []
            else:
                t0 = time.perf_counter()
                tracks = self.tracker.update(detections, media.mode, image_bytes=media.data)
                t_track = time.perf_counter() - t0

                t0 = time.perf_counter()
                poses = self.pose_estimator.estimate(preprocessed, detections, img_array=img_array)
                t_pose = time.perf_counter() - t0

                t0 = time.perf_counter()
                helmet_scores = self.helmet_classifier.classify(preprocessed, detections, img_array=img_array)
                t_helmet = time.perf_counter() - t0

                t0 = time.perf_counter()
                seatbelt_scores = self.seatbelt_classifier.classify(preprocessed, detections, img_array=img_array)
                t_seatbelt = time.perf_counter() - t0

                t_anpr = 0.0
                plates = []
                t0 = time.perf_counter()
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
                t_violation = time.perf_counter() - t0

                if violations:
                    t0 = time.perf_counter()
                    plates = self.anpr.recognize(preprocessed, detections=detections, img_array=img_array)
                    t_anpr = time.perf_counter() - t0
                    if any(plate.review_required for plate in plates):
                        review_reasons.append(ReviewReason.LOW_CONFIDENCE)

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
        t_vlm = 0.0
        t_annotate = 0.0
        if media.generate_artifacts:
            evidence = self.evidence_builder.attach(media, result)
            result = result.model_copy(update={"evidence_packet_id": evidence.id})

            t0 = time.perf_counter()
            description = self.vlm.describe(result)
            t_vlm = time.perf_counter() - t0
            if description:
                result = result.model_copy(update={"description": description})

            t0 = time.perf_counter()
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
            t_annotate = time.perf_counter() - t0
        else:
            result = result.model_copy(update={"evidence_packet_id": f"live-{uuid4().hex}"})

        t_total = time.perf_counter() - t_total
        logger.info(
            "Pipeline [%s] total=%.0fms | decode=%.0fms preprocess=%.0fms detect=%.0fms track=%.0fms "
            "pose=%.0fms helmet=%.0fms seatbelt=%.0fms anpr=%.0fms violations=%.0fms vlm=%.0fms annotate=%.0fms | "
            "dets=%d plates=%d violations=%d",
            media.camera_id, t_total * 1000,
            t_decode * 1000, t_preprocess * 1000, t_detect * 1000, t_track * 1000,
            t_pose * 1000, t_helmet * 1000, t_seatbelt * 1000, t_anpr * 1000,
            t_violation * 1000, t_vlm * 1000, t_annotate * 1000,
            len(detections), len(plates), len(violations),
        )

        return result
