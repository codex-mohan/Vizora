"""Central configuration for the traffic violation detection pipeline."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Final

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT: Final = Path(__file__).resolve().parent.parent
MODELS_DIR: Final = BACKEND_ROOT / "models"
CONFIGS_DIR: Final = BACKEND_ROOT / "configs"
DATA_DIR: Final = BACKEND_ROOT.parent / "data"


class CameraMode(str, Enum):
    CLEAN = "CLEAN"
    LOWLIGHT = "LOWLIGHT"
    HAZE = "HAZE"
    RAIN = "RAIN"
    MULTI = "MULTI"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TVD_", env_file=".env", extra="ignore")

    app_name: str = "Traffic Violation Detection"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql://tvds:tvds@localhost:5432/tvds"
    s3_endpoint: str = "localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "evidence"

    preprocessing_budget_ms: int = 15
    camera_eval_interval_s: int = 5
    degraded_exit_evals: int = 30
    degraded_enter_evals: int = 5

    model_profiles_path: str = "configs/model_profiles.example.yaml"
    active_model_profile: str = "fast"
    camera_scenes_path: str = "configs/camera_scenes.example.yaml"

    detection_model: str = "models/detect/dfine_l.onnx"
    detection_conf_threshold: float = 0.35
    detection_iou_threshold: float = 0.6

    tracker_max_lost: int = 30
    tracker_iou_threshold: float = 0.5

    anpr_confidence_threshold: float = 0.7
    anpr_review_threshold: float = 0.6

    vlm_model: str = "models/vlm/florence2_base"
    vlm_enabled: bool = True

    violation_cooldown_s: int = 60
    evidence_frame_count: int = 5

    face_blur: bool = True
    plate_redact_public: bool = True

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://vizora.localhost",
        "https://frontend.localhost",
        "https://api.localhost",
    ]


settings = Settings()
