"""Tests for the ViolationEngine rule engine."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pipeline.contracts import (
    BBox,
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
from pipeline.scene import (
    CameraSceneConfig,
    LaneDirection,
    Point,
    PolygonZone,
    SignalConfig,
)
from pipeline.violation.engine import ViolationEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _det(obj_id: str, label: ObjectClass, bbox: BBox | None = None) -> DetectedObject:
    return DetectedObject(
        id=obj_id,
        label=label,
        bbox=bbox or BBox(x1=100, y1=100, x2=200, y2=200),
        confidence=0.9,
    )


def _track(obj_id: str, label: ObjectClass, points: list[Point], bbox: BBox | None = None) -> Track:
    return Track(
        track_id=f"track-{obj_id}",
        object_id=obj_id,
        label=label,
        bbox=bbox or BBox(x1=100, y1=100, x2=200, y2=200),
        confidence=0.9,
        trajectory=points,
    )


def _empty_scene() -> CameraSceneConfig:
    return CameraSceneConfig(camera_id="test-cam", location_name="Test")


def _scene_with_lane() -> CameraSceneConfig:
    return CameraSceneConfig(
        camera_id="test-cam",
        location_name="Test",
        lane_directions=[
            LaneDirection(
                id="lane-1",
                start=Point(x=0, y=500),
                end=Point(x=500, y=500),
            )
        ],
    )


def _scene_with_stop_line() -> CameraSceneConfig:
    return CameraSceneConfig(
        camera_id="test-cam",
        location_name="Test",
        stop_lines=[
            PolygonZone(
                id="sl-1",
                label="stop-line",
                points=[
                    Point(x=100, y=300),
                    Point(x=400, y=300),
                    Point(x=400, y=320),
                    Point(x=100, y=320),
                ],
            )
        ],
    )


def _scene_with_signal_and_stop_line() -> CameraSceneConfig:
    return CameraSceneConfig(
        camera_id="test-cam",
        location_name="Test",
        stop_lines=[
            PolygonZone(
                id="sl-1",
                label="stop-line",
                points=[
                    Point(x=100, y=300),
                    Point(x=400, y=300),
                    Point(x=400, y=320),
                    Point(x=100, y=320),
                ],
            )
        ],
        signal=SignalConfig(external_signal_source="mqtt://signal-1"),
    )


def _scene_with_no_parking() -> CameraSceneConfig:
    return CameraSceneConfig(
        camera_id="test-cam",
        location_name="Test",
        no_parking_zones=[
            PolygonZone(
                id="np-1",
                label="no-parking",
                points=[
                    Point(x=0, y=0),
                    Point(x=500, y=0),
                    Point(x=500, y=500),
                    Point(x=0, y=500),
                ],
            )
        ],
    )


# ---------------------------------------------------------------------------
# Helmet violations
# ---------------------------------------------------------------------------

class TestHelmetViolations:
    def test_low_helmet_score_produces_violation(self) -> None:
        engine = ViolationEngine()
        det = _det("rider-1", ObjectClass.RIDER)
        violations = engine.evaluate(
            mode=ProcessingMode.STILL_IMAGE,
            scene=_empty_scene(),
            detections=[det],
            tracks=[],
            poses=[],
            plates=[],
            helmet_scores={"rider-1": 0.1},
            seatbelt_scores={},
        )
        assert any(v.violation_type == ViolationClass.HELMET for v in violations)

    def test_high_helmet_score_no_violation(self) -> None:
        engine = ViolationEngine()
        det = _det("rider-1", ObjectClass.RIDER)
        violations = engine.evaluate(
            mode=ProcessingMode.STILL_IMAGE,
            scene=_empty_scene(),
            detections=[det],
            tracks=[],
            poses=[],
            plates=[],
            helmet_scores={"rider-1": 0.95},
            seatbelt_scores={},
        )
        assert not any(v.violation_type == ViolationClass.HELMET for v in violations)

    def test_non_rider_ignored(self) -> None:
        engine = ViolationEngine()
        det = _det("car-1", ObjectClass.CAR)
        violations = engine.evaluate(
            mode=ProcessingMode.STILL_IMAGE,
            scene=_empty_scene(),
            detections=[det],
            tracks=[],
            poses=[],
            plates=[],
            helmet_scores={"car-1": 0.1},
            seatbelt_scores={},
        )
        assert not any(v.violation_type == ViolationClass.HELMET for v in violations)


# ---------------------------------------------------------------------------
# Seatbelt violations
# ---------------------------------------------------------------------------

class TestSeatbeltViolations:
    def test_low_seatbelt_score_produces_violation(self) -> None:
        engine = ViolationEngine()
        det = _det("driver-1", ObjectClass.DRIVER)
        violations = engine.evaluate(
            mode=ProcessingMode.STILL_IMAGE,
            scene=_empty_scene(),
            detections=[det],
            tracks=[],
            poses=[],
            plates=[],
            helmet_scores={},
            seatbelt_scores={"driver-1": 0.1},
        )
        assert any(v.violation_type == ViolationClass.SEATBELT for v in violations)

    def test_high_seatbelt_score_no_violation(self) -> None:
        engine = ViolationEngine()
        det = _det("driver-1", ObjectClass.DRIVER)
        violations = engine.evaluate(
            mode=ProcessingMode.STILL_IMAGE,
            scene=_empty_scene(),
            detections=[det],
            tracks=[],
            poses=[],
            plates=[],
            helmet_scores={},
            seatbelt_scores={"driver-1": 0.95},
        )
        assert not any(v.violation_type == ViolationClass.SEATBELT for v in violations)


# ---------------------------------------------------------------------------
# Triple ride
# ---------------------------------------------------------------------------

class TestTripleRide:
    def test_three_riders_near_motorcycle(self) -> None:
        engine = ViolationEngine()
        moto = _det("moto-1", ObjectClass.MOTORCYCLE, BBox(x1=200, y1=200, x2=300, y2=300))
        riders = [
            _det(f"rider-{i}", ObjectClass.RIDER, BBox(x1=220, y1=220, x2=260, y2=260))
            for i in range(3)
        ]
        violations = engine.evaluate(
            mode=ProcessingMode.TEMPORAL_BURST,
            scene=_empty_scene(),
            detections=[moto, *riders],
            tracks=[],
            poses=[],
            plates=[],
            helmet_scores={},
            seatbelt_scores={},
        )
        triple = [v for v in violations if v.violation_type == ViolationClass.TRIPLE_RIDE]
        assert len(triple) == 1

    def test_two_riders_no_violation(self) -> None:
        engine = ViolationEngine()
        moto = _det("moto-1", ObjectClass.MOTORCYCLE, BBox(x1=200, y1=200, x2=300, y2=300))
        riders = [
            _det(f"rider-{i}", ObjectClass.RIDER, BBox(x1=220, y1=220, x2=260, y2=260))
            for i in range(2)
        ]
        violations = engine.evaluate(
            mode=ProcessingMode.TEMPORAL_BURST,
            scene=_empty_scene(),
            detections=[moto, *riders],
            tracks=[],
            poses=[],
            plates=[],
            helmet_scores={},
            seatbelt_scores={},
        )
        assert not any(v.violation_type == ViolationClass.TRIPLE_RIDE for v in violations)

    def test_still_image_mode_reduces_confidence_and_flags_review(self) -> None:
        engine = ViolationEngine()
        moto = _det("moto-1", ObjectClass.MOTORCYCLE, BBox(x1=200, y1=200, x2=300, y2=300))
        riders = [
            _det(f"rider-{i}", ObjectClass.RIDER, BBox(x1=220, y1=220, x2=260, y2=260))
            for i in range(3)
        ]
        violations = engine.evaluate(
            mode=ProcessingMode.STILL_IMAGE,
            scene=_empty_scene(),
            detections=[moto, *riders],
            tracks=[],
            poses=[],
            plates=[],
            helmet_scores={},
            seatbelt_scores={},
        )
        triple = [v for v in violations if v.violation_type == ViolationClass.TRIPLE_RIDE]
        assert len(triple) == 1
        assert triple[0].confidence <= 0.65
        assert triple[0].review_required is True
        assert ReviewReason.TEMPORAL_REQUIRED in triple[0].review_reasons


# ---------------------------------------------------------------------------
# Wrong side (temporal)
# ---------------------------------------------------------------------------

class TestWrongSide:
    def test_track_against_lane_direction(self) -> None:
        engine = ViolationEngine()
        track = _track(
            "veh-1",
            ObjectClass.CAR,
            [Point(x=400, y=500), Point(x=300, y=500), Point(x=200, y=500)],
        )
        det = _det("veh-1", ObjectClass.CAR, BBox(x1=200, y1=480, x2=300, y2=520))
        violations = engine.evaluate(
            mode=ProcessingMode.TEMPORAL_BURST,
            scene=_scene_with_lane(),
            detections=[det],
            tracks=[track],
            poses=[],
            plates=[],
            helmet_scores={},
            seatbelt_scores={},
        )
        assert any(v.violation_type == ViolationClass.WRONG_SIDE for v in violations)

    def test_track_with_lane_direction_no_violation(self) -> None:
        engine = ViolationEngine()
        track = _track(
            "veh-1",
            ObjectClass.CAR,
            [Point(x=100, y=500), Point(x=200, y=500), Point(x=300, y=500)],
        )
        det = _det("veh-1", ObjectClass.CAR, BBox(x1=200, y1=480, x2=300, y2=520))
        violations = engine.evaluate(
            mode=ProcessingMode.TEMPORAL_BURST,
            scene=_scene_with_lane(),
            detections=[det],
            tracks=[track],
            poses=[],
            plates=[],
            helmet_scores={},
            seatbelt_scores={},
        )
        assert not any(v.violation_type == ViolationClass.WRONG_SIDE for v in violations)

    def test_no_lane_config_skipped(self) -> None:
        engine = ViolationEngine()
        det = _det("veh-1", ObjectClass.CAR)
        violations = engine.evaluate(
            mode=ProcessingMode.TEMPORAL_BURST,
            scene=_empty_scene(),
            detections=[det],
            tracks=[],
            poses=[],
            plates=[],
            helmet_scores={},
            seatbelt_scores={},
        )
        assert not any(v.violation_type == ViolationClass.WRONG_SIDE for v in violations)


# ---------------------------------------------------------------------------
# Stop line
# ---------------------------------------------------------------------------

class TestStopLine:
    def test_vehicle_in_stop_line_zone(self) -> None:
        engine = ViolationEngine()
        track = _track(
            "veh-1",
            ObjectClass.CAR,
            [Point(x=200, y=200), Point(x=250, y=310)],
            bbox=BBox(x1=200, y1=305, x2=300, y2=315),
        )
        det = _det("veh-1", ObjectClass.CAR, BBox(x1=200, y1=305, x2=300, y2=315))
        violations = engine.evaluate(
            mode=ProcessingMode.TEMPORAL_BURST,
            scene=_scene_with_stop_line(),
            detections=[det],
            tracks=[track],
            poses=[],
            plates=[],
            helmet_scores={},
            seatbelt_scores={},
        )
        assert any(v.violation_type == ViolationClass.STOP_LINE for v in violations)

    def test_vehicle_outside_zone_no_violation(self) -> None:
        engine = ViolationEngine()
        track = _track(
            "veh-1",
            ObjectClass.CAR,
            [Point(x=200, y=100), Point(x=250, y=150)],
            bbox=BBox(x1=180, y1=100, x2=280, y2=200),
        )
        det = _det("veh-1", ObjectClass.CAR, BBox(x1=180, y1=100, x2=280, y2=200))
        violations = engine.evaluate(
            mode=ProcessingMode.TEMPORAL_BURST,
            scene=_scene_with_stop_line(),
            detections=[det],
            tracks=[track],
            poses=[],
            plates=[],
            helmet_scores={},
            seatbelt_scores={},
        )
        assert not any(v.violation_type == ViolationClass.STOP_LINE for v in violations)

    def test_no_stop_line_config_skipped(self) -> None:
        engine = ViolationEngine()
        det = _det("veh-1", ObjectClass.CAR)
        violations = engine.evaluate(
            mode=ProcessingMode.TEMPORAL_BURST,
            scene=_empty_scene(),
            detections=[det],
            tracks=[],
            poses=[],
            plates=[],
            helmet_scores={},
            seatbelt_scores={},
        )
        assert not any(v.violation_type == ViolationClass.STOP_LINE for v in violations)


# ---------------------------------------------------------------------------
# Illegal parking (temporal)
# ---------------------------------------------------------------------------

class TestIllegalParking:
    def test_stationary_track_in_no_parking_zone(self) -> None:
        engine = ViolationEngine()
        pts = [Point(x=250, y=250)] * 5
        track = _track("veh-1", ObjectClass.CAR, pts, bbox=BBox(x1=230, y1=230, x2=270, y2=270))
        det = _det("veh-1", ObjectClass.CAR, BBox(x1=230, y1=230, x2=270, y2=270))
        violations = engine.evaluate(
            mode=ProcessingMode.TEMPORAL_BURST,
            scene=_scene_with_no_parking(),
            detections=[det],
            tracks=[track],
            poses=[],
            plates=[],
            helmet_scores={},
            seatbelt_scores={},
        )
        assert any(v.violation_type == ViolationClass.ILLEGAL_PARKING for v in violations)

    def test_moving_track_in_zone_no_violation(self) -> None:
        engine = ViolationEngine()
        pts = [Point(x=float(i * 50), y=250.0) for i in range(5)]
        track = _track("veh-1", ObjectClass.CAR, pts, bbox=BBox(x1=0, y1=230, x2=250, y2=270))
        det = _det("veh-1", ObjectClass.CAR, BBox(x1=0, y1=230, x2=250, y2=270))
        violations = engine.evaluate(
            mode=ProcessingMode.TEMPORAL_BURST,
            scene=_scene_with_no_parking(),
            detections=[det],
            tracks=[track],
            poses=[],
            plates=[],
            helmet_scores={},
            seatbelt_scores={},
        )
        assert not any(v.violation_type == ViolationClass.ILLEGAL_PARKING for v in violations)


# ---------------------------------------------------------------------------
# Cooldown integration
# ---------------------------------------------------------------------------

class TestCooldownIntegration:
    def test_duplicate_violation_filtered(self) -> None:
        engine = ViolationEngine()
        det = _det("rider-1", ObjectClass.RIDER)
        kwargs = dict(
            mode=ProcessingMode.STILL_IMAGE,
            scene=_empty_scene(),
            detections=[det],
            tracks=[],
            poses=[],
            plates=[],
            helmet_scores={"rider-1": 0.05},
            seatbelt_scores={},
        )
        first = engine.evaluate(**kwargs)
        second = engine.evaluate(**kwargs)
        assert len(first) == 1
        assert len(second) == 0
