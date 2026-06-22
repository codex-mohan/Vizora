"""Camera scene configuration for rule-based violation reasoning."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from pipeline.contracts import Point


class PolygonZone(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    points: list[Point] = Field(min_length=3)


class LaneDirection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    start: Point
    end: Point


class GeoCoordinate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float
    longitude: float


class RoadSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    coordinates: list[GeoCoordinate] = Field(min_length=2)


class SignalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_roi: PolygonZone | None = None
    external_signal_source: str | None = None


class CameraSceneConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    camera_id: str
    location_name: str = "Unknown"
    latitude: float | None = None
    longitude: float | None = None
    stop_lines: list[PolygonZone] = Field(default_factory=list)
    no_parking_zones: list[PolygonZone] = Field(default_factory=list)
    lane_directions: list[LaneDirection] = Field(default_factory=list)
    road_segments: list[RoadSegment] = Field(default_factory=list)
    signal: SignalConfig = Field(default_factory=SignalConfig)
    homography_points: list[Point] = Field(default_factory=list)

    @property
    def has_temporal_violation_context(self) -> bool:
        return bool(self.stop_lines or self.no_parking_zones or self.lane_directions)

    @property
    def has_signal_context(self) -> bool:
        return self.signal.signal_roi is not None or self.signal.external_signal_source is not None


def default_scene_config(camera_id: str) -> CameraSceneConfig:
    return CameraSceneConfig(camera_id=camera_id, location_name="Demo camera")


_scene_cache: dict[str, CameraSceneConfig] = {}


def load_scene_config(path: str | Path, camera_id: str) -> CameraSceneConfig:
    cache_key = f"{path}:{camera_id}"
    cached = _scene_cache.get(cache_key)
    if cached is not None:
        return cached

    config_path = Path(path)
    if not config_path.exists():
        result = default_scene_config(camera_id)
        _scene_cache[cache_key] = result
        return result

    with config_path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file) or {}

    cameras = raw.get("cameras", {})
    camera_config = cameras.get(camera_id)
    if camera_config is None:
        result = default_scene_config(camera_id)
    else:
        result = CameraSceneConfig.model_validate(camera_config)

    _scene_cache[cache_key] = result
    return result
