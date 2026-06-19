"""Pydantic-validated model registry.

All model choices live here so pipeline modules can switch models by profile
without hardcoding model names inside detection, OCR, or VLM adapters.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProfileName(str, Enum):
    MVP = "mvp"
    ACCURACY = "accuracy"
    EDGE = "edge"
    REVIEW = "review"


class Runtime(str, Enum):
    DISABLED = "disabled"
    PYTORCH = "pytorch"
    ONNX = "onnx"
    TENSORRT = "tensorrt"
    HUGGINGFACE = "huggingface"
    VLLM = "vllm"
    EXTERNAL_API = "external_api"


class Precision(str, Enum):
    FP32 = "fp32"
    FP16 = "fp16"
    INT8 = "int8"


class DetectorChoice(str, Enum):
    YOLO11N = "yolo11n"
    YOLO11S = "yolo11s"
    YOLO11M = "yolo11m"
    YOLO11X = "yolo11x"
    DFINE_L = "dfine_l"


class TrackerChoice(str, Enum):
    DISABLED = "disabled"
    BYTE_TRACK_V2 = "byte_track_v2"


class PoseChoice(str, Enum):
    DISABLED = "disabled"
    RTMO_M = "rtmo_m"


class ClassifierChoice(str, Enum):
    DISABLED = "disabled"
    EFFICIENTNETV2_S = "efficientnetv2_s"
    CONVNEXTV2_BASE = "convnextv2_base"


class PlateDetectorChoice(str, Enum):
    YOLO11_PLATE = "yolo11_plate"


class OcrChoice(str, Enum):
    PADDLEOCR_PP_OCRV5 = "paddleocr_pp_ocrv5"
    PARSEQ = "parseq"


class VlmChoice(str, Enum):
    DISABLED = "disabled"
    QWEN3_5_VL = "qwen3_5_vl"
    QWEN2_5_VL_3B = "qwen2_5_vl_3b"
    QWEN2_5_VL_7B = "qwen2_5_vl_7b"
    FLORENCE2_LARGE = "florence2_large"
    FLORENCE2_BASE = "florence2_base"


class EnhancementChoice(str, Enum):
    DISABLED = "disabled"
    ZERO_DCE_PLUS_PLUS = "zero_dce_plus_plus"
    AOD_NET = "aod_net"
    DERAIN_NET = "derain_net"
    NAFNET_SMALL = "nafnet_small"
    REAL_ESRGAN = "real_esrgan"


class ComponentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    runtime: Runtime = Runtime.PYTORCH
    weights: str | None = None
    device: str = "auto"
    precision: Precision = Precision.FP16
    batch_size: int = Field(default=1, ge=1, le=128)
    options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def disabled_components_do_not_require_runtime(self) -> ComponentConfig:
        if not self.enabled:
            self.runtime = Runtime.DISABLED
        return self


class DetectorConfig(ComponentConfig):
    choice: DetectorChoice = DetectorChoice.YOLO11N
    confidence_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.6, ge=0.0, le=1.0)


class TrackerConfig(ComponentConfig):
    choice: TrackerChoice = TrackerChoice.BYTE_TRACK_V2
    runtime: Runtime = Runtime.PYTORCH
    max_lost_frames: int = Field(default=30, ge=0)
    association_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class PoseConfig(ComponentConfig):
    choice: PoseChoice = PoseChoice.RTMO_M
    confidence_threshold: float = Field(default=0.4, ge=0.0, le=1.0)


class ClassifierConfig(ComponentConfig):
    choice: ClassifierChoice = ClassifierChoice.EFFICIENTNETV2_S
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class PlateDetectorConfig(ComponentConfig):
    choice: PlateDetectorChoice = PlateDetectorChoice.YOLO11_PLATE
    confidence_threshold: float = Field(default=0.35, ge=0.0, le=1.0)


class OcrConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: OcrChoice = OcrChoice.PADDLEOCR_PP_OCRV5
    fallback: OcrChoice = OcrChoice.PARSEQ
    accept_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    review_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    primary_runtime: Runtime = Runtime.PYTORCH
    fallback_runtime: Runtime = Runtime.PYTORCH

    @model_validator(mode="after")
    def review_threshold_must_not_exceed_accept(self) -> OcrConfig:
        if self.review_threshold > self.accept_threshold:
            raise ValueError("review_threshold must be <= accept_threshold")
        return self


class VlmConfig(ComponentConfig):
    choice: VlmChoice = VlmChoice.QWEN2_5_VL_3B
    runtime: Runtime = Runtime.HUGGINGFACE
    max_tokens: int = Field(default=512, ge=32, le=4096)
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    endpoint_url: str | None = None

    @model_validator(mode="after")
    def validate_external_api_endpoint(self) -> VlmConfig:
        if self.enabled and self.runtime == Runtime.EXTERNAL_API and not self.endpoint_url:
            raise ValueError("endpoint_url is required when VLM runtime is external_api")
        return self


class PreprocessingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    budget_ms: int = Field(default=15, ge=1, le=100)
    always_on: list[str] = Field(
        default_factory=lambda: [
            "resize",
            "normalize",
            "clahe",
            "gamma_correction",
            "white_balance",
            "roi_mask",
        ]
    )
    lowlight_model: EnhancementChoice = EnhancementChoice.DISABLED
    haze_model: EnhancementChoice = EnhancementChoice.DISABLED
    rain_model: EnhancementChoice = EnhancementChoice.DISABLED
    crop_super_resolution: EnhancementChoice = EnhancementChoice.REAL_ESRGAN


class ModelProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ProfileName = ProfileName.MVP
    detector: DetectorConfig = Field(default_factory=DetectorConfig)
    tracker: TrackerConfig = Field(default_factory=TrackerConfig)
    pose: PoseConfig = Field(default_factory=PoseConfig)
    helmet_classifier: ClassifierConfig = Field(default_factory=ClassifierConfig)
    seatbelt_classifier: ClassifierConfig = Field(default_factory=ClassifierConfig)
    plate_detector: PlateDetectorConfig = Field(default_factory=PlateDetectorConfig)
    ocr: OcrConfig = Field(default_factory=OcrConfig)
    vlm: VlmConfig = Field(default_factory=VlmConfig)
    preprocessing: PreprocessingConfig = Field(default_factory=PreprocessingConfig)


class ModelProfiles(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_profile: ProfileName = ProfileName.MVP
    profiles: dict[ProfileName, ModelProfile]

    def active(self) -> ModelProfile:
        return self.profiles[self.active_profile]


def load_model_profiles(path: str | Path) -> ModelProfiles:
    with Path(path).open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file)
    return ModelProfiles.model_validate(raw)


DEFAULT_MODEL_PROFILE = ModelProfile()
