"""Pre-load all pipeline models into GPU on startup."""

from __future__ import annotations

import logging
import time

import torch

from core.model_registry import ModelProfile
from pipeline.device import get_device

logger = logging.getLogger(__name__)


def _gpu_mem() -> str:
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / (1024**2)
        reserved = torch.cuda.memory_reserved() / (1024**2)
        return f"GPU mem: {allocated:.0f}MB allocated, {reserved:.0f}MB reserved"
    return "CPU only"


def warmup_models(profile: ModelProfile) -> None:
    """Load all models and run a dummy inference to warm GPU kernels."""
    from pipeline.detect.detector import build_detector
    from pipeline.pose.pose_estimator import build_pose_estimator
    from pipeline.classify.classifiers import build_helmet_classifier, build_seatbelt_classifier
    from pipeline.anpr.pipeline import build_anpr_pipeline
    from pipeline.contracts import MediaInput, PreprocessedImage, ImageQuality
    from datetime import datetime, timezone
    from PIL import Image
    import numpy as np

    device = get_device()
    logger.info("=== Model warmup starting on %s ===", device)
    logger.info("  %s", _gpu_mem())
    t_total = time.perf_counter()

    dummy_img = Image.new("RGB", (640, 640), color=(128, 128, 128))
    dummy_bytes = dummy_img.tobytes()
    dummy_media = MediaInput(
        filename="warmup.png",
        data=dummy_bytes,
        camera_id="warmup",
        timestamp=datetime.now(timezone.utc),
        mode="still_image",
        content_type="image/png",
    )
    dummy_quality = ImageQuality(brightness=128, blur=1000, haze=0, noise=50, score=0.8, review_required=False)
    dummy_preprocessed = PreprocessedImage(
        media=dummy_media,
        quality=dummy_quality,
        applied_steps=["warmup"],
        camera_mode="CLEAN",
    )
    dummy_array = np.asarray(dummy_img)

    # Detector
    t0 = time.perf_counter()
    try:
        detector = build_detector(profile.detector)
        detector.detect(dummy_preprocessed, img_array=dummy_array)
        logger.info("  [detector] %s loaded — %.1fs — %s", profile.detector.choice.value, time.perf_counter() - t0, _gpu_mem())
    except Exception as e:
        logger.warning("  [detector] warmup failed: %s (%.1fs)", e, time.perf_counter() - t0)

    # Pose
    t0 = time.perf_counter()
    try:
        pose = build_pose_estimator(profile.pose)
        if pose.ready:
            pose.estimate(dummy_preprocessed, [], img_array=dummy_array)
            logger.info("  [pose] %s loaded — %.1fs — %s", profile.pose.choice.value, time.perf_counter() - t0, _gpu_mem())
        else:
            logger.info("  [pose] skipped (disabled)")
    except Exception as e:
        logger.warning("  [pose] warmup failed: %s (%.1fs)", e, time.perf_counter() - t0)

    # Helmet classifier
    t0 = time.perf_counter()
    try:
        helmet = build_helmet_classifier(profile.helmet_classifier)
        if helmet.ready:
            helmet.classify(dummy_preprocessed, [], img_array=dummy_array)
            logger.info("  [helmet] %s loaded — %.1fs — %s", profile.helmet_classifier.choice.value, time.perf_counter() - t0, _gpu_mem())
        else:
            logger.info("  [helmet] skipped (disabled)")
    except Exception as e:
        logger.warning("  [helmet] warmup failed: %s (%.1fs)", e, time.perf_counter() - t0)

    # Seatbelt classifier
    t0 = time.perf_counter()
    try:
        seatbelt = build_seatbelt_classifier(profile.seatbelt_classifier)
        if seatbelt.ready:
            seatbelt.classify(dummy_preprocessed, [], img_array=dummy_array)
            logger.info("  [seatbelt] %s loaded — %.1fs — %s", profile.seatbelt_classifier.choice.value, time.perf_counter() - t0, _gpu_mem())
        else:
            logger.info("  [seatbelt] skipped (disabled)")
    except Exception as e:
        logger.warning("  [seatbelt] warmup failed: %s (%.1fs)", e, time.perf_counter() - t0)

    # PaddleOCR (pre-init to avoid first-request latency)
    t0 = time.perf_counter()
    try:
        anpr = build_anpr_pipeline(profile.plate_detector, profile.ocr)
        anpr.preload()
        logger.info("  [anpr] PaddleOCR loaded — %.1fs", time.perf_counter() - t0)
    except Exception as e:
        logger.warning("  [anpr] warmup failed: %s (%.1fs)", e, time.perf_counter() - t0)

    t_total = time.perf_counter() - t_total
    logger.info("=== Warmup complete in %.1fs — %s ===", t_total, _gpu_mem())
