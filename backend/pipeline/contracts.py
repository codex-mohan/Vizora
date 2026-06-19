"""Shared pipeline data contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProcessingMode(str, Enum):
    STILL_IMAGE = "still_image"
    TEMPORAL_BURST = "temporal_burst"


class ObjectClass(str, Enum):
    CAR = "car"
    MOTORCYCLE = "motorcycle"
    AUTO = "auto"
    BUS = "bus"
    TRUCK = "truck"
    BICYCLE = "bicycle"
    RIDER = "rider"
    DRIVER = "driver"
    PEDESTRIAN = "pedestrian"
    PLATE = "plate"
    HELMET = "helmet"
    NO_HELMET = "no_helmet"
    TURBAN_PAGDI = "turban_pagdi"
    HAT_CAP = "hat_cap"
    SKULL_CAP = "skull_cap"
    HOOD_SCARF = "hood_scarf"
    CONSTRUCTION_HARDHAT = "construction_hardhat"
    UNCLEAR_HEAD = "unclear_head"
    SEATBELT = "seatbelt"
    NO_SEATBELT = "no_seatbelt"
    SEATBELT_VISIBLE = "seatbelt_visible"
    STRAP_LIKE_FALSE_POSITIVE = "strap_like_false_positive"
    OCCLUDED_REFLECTION = "occluded_reflection"
    UNCLEAR = "unclear"
    UNKNOWN = "unknown"


class ViolationClass(str, Enum):
    HELMET = "HELMET"
    SEATBELT = "SEATBELT"
    TRIPLE_RIDE = "TRIPLE_RIDE"
    WRONG_SIDE = "WRONG_SIDE"
    STOP_LINE = "STOP_LINE"
    RED_LIGHT = "RED_LIGHT"
    ILLEGAL_PARKING = "ILLEGAL_PARKING"


class ReviewReason(str, Enum):
    LOW_CONFIDENCE = "low_confidence"
    TEMPORAL_REQUIRED = "temporal_required"
    MISSING_SCENE_CONFIG = "missing_scene_config"
    POOR_IMAGE_QUALITY = "poor_image_quality"
    MODEL_NOT_READY = "model_not_ready"


class Point(BaseModel):
    x: float
    y: float


class BBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

    @field_validator("x2")
    @classmethod
    def x2_after_x1(cls, value: float, info) -> float:
        x1 = info.data.get("x1")
        if x1 is not None and value < x1:
            raise ValueError("x2 must be >= x1")
        return value

    @field_validator("y2")
    @classmethod
    def y2_after_y1(cls, value: float, info) -> float:
        y1 = info.data.get("y1")
        if y1 is not None and value < y1:
            raise ValueError("y2 must be >= y1")
        return value

    @property
    def area(self) -> float:
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)


class MediaInput(BaseModel):
    filename: str
    content_type: str | None = None
    data: bytes = Field(repr=False)
    camera_id: str = "demo-camera"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    mode: ProcessingMode = ProcessingMode.STILL_IMAGE


class ImageQuality(BaseModel):
    brightness: float = Field(ge=0.0, le=255.0)
    blur: float = Field(ge=0.0)
    haze: float = Field(ge=0.0, le=1.0)
    noise: float = Field(ge=0.0)
    score: float = Field(ge=0.0, le=1.0)
    review_required: bool = False


class PreprocessedImage(BaseModel):
    media: MediaInput
    quality: ImageQuality
    applied_steps: list[str]
    camera_mode: str


class DetectedObject(BaseModel):
    id: str
    label: ObjectClass
    bbox: BBox
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Track(BaseModel):
    track_id: str
    object_id: str
    label: ObjectClass
    bbox: BBox
    confidence: float = Field(ge=0.0, le=1.0)
    trajectory: list[Point] = Field(default_factory=list)


class PoseResult(BaseModel):
    object_id: str
    keypoints: dict[str, Point]
    confidence: float = Field(ge=0.0, le=1.0)


class PlateResult(BaseModel):
    plate_text: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    bbox: BBox | None = None
    review_required: bool = True


class ViolationPrediction(BaseModel):
    violation_type: ViolationClass
    confidence: float = Field(ge=0.0, le=1.0)
    object_ids: list[str] = Field(default_factory=list)
    bbox: BBox | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    review_required: bool = False
    review_reasons: list[ReviewReason] = Field(default_factory=list)


class InferenceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    camera_id: str
    timestamp: datetime
    mode: ProcessingMode
    quality: ImageQuality
    detections: list[DetectedObject]
    tracks: list[Track]
    poses: list[PoseResult]
    plates: list[PlateResult]
    violations: list[ViolationPrediction]
    evidence_packet_id: str
    model_profile: str
    review_required: bool
    review_reasons: list[ReviewReason]
    description: str | None = None
