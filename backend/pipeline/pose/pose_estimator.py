"""Pose estimation using YOLO-Pose from Ultralytics."""

from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image
from ultralytics import YOLO

from core.model_registry import PoseChoice, PoseConfig
from pipeline.contracts import BBox, DetectedObject, Point, PoseResult, PreprocessedImage

YOLO_POSE_MODELS = {
    PoseChoice.RTMO_M: "yolo11n-pose.pt",
}

KEYPOINT_NAMES = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
]


class PoseEstimatorAdapter:
    def __init__(self, config: PoseConfig) -> None:
        self.config = config
        self._model = None

    @property
    def ready(self) -> bool:
        return self.config.choice != PoseChoice.DISABLED

    def estimate(self, image: PreprocessedImage, detections: list[DetectedObject]) -> list[PoseResult]:
        if not self.ready:
            return []
        model = self._load_model()
        pil_image = Image.open(BytesIO(image.media.data)).convert("RGB")
        results = model.predict(np.asarray(pil_image), conf=self.config.confidence_threshold, verbose=False)
        if not results or not results[0].keypoints:
            return []

        poses: list[PoseResult] = []
        kpts = results[0].keypoints
        for i, kpt in enumerate(kpts):
            if kpt.xy is None or kpt.conf is None:
                continue
            xy = kpt.xy[0].cpu().numpy()
            conf = kpt.conf[0].cpu().numpy()
            keypoints: dict[str, Point] = {}
            min_conf = 1.0
            for j, name in enumerate(KEYPOINT_NAMES):
                if j < len(xy) and j < len(conf):
                    keypoints[name] = Point(x=float(xy[j][0]), y=float(xy[j][1]))
                    min_conf = min(min_conf, float(conf[j]))
            poses.append(PoseResult(
                object_id=f"pose-{i}",
                keypoints=keypoints,
                confidence=max(0.0, min_conf),
            ))
        return poses

    def _load_model(self):
        if self._model is not None:
            return self._model
        model_name = YOLO_POSE_MODELS.get(self.config.choice, "yolo11n-pose.pt")
        self._model = YOLO(model_name)
        return self._model


def build_pose_estimator(config: PoseConfig) -> PoseEstimatorAdapter:
    return PoseEstimatorAdapter(config)
