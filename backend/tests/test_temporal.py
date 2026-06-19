"""Tests for temporal violation geometry and cooldown helpers."""

from __future__ import annotations

import time

import pytest

from pipeline.contracts import BBox, ObjectClass, Point, Track, ViolationClass
from pipeline.violation.temporal import (
    ViolationCooldown,
    bbox_center,
    bbox_intersects_polygon,
    is_stationary,
    point_in_polygon,
)


# ---------------------------------------------------------------------------
# point_in_polygon
# ---------------------------------------------------------------------------

class TestPointInPolygon:
    def test_inside_square(self) -> None:
        square = [
            Point(x=0, y=0),
            Point(x=10, y=0),
            Point(x=10, y=10),
            Point(x=0, y=10),
        ]
        assert point_in_polygon(Point(x=5, y=5), square) is True

    def test_outside_square(self) -> None:
        square = [
            Point(x=0, y=0),
            Point(x=10, y=0),
            Point(x=10, y=10),
            Point(x=0, y=10),
        ]
        assert point_in_polygon(Point(x=15, y=5), square) is False

    def test_on_edge_returns_true(self) -> None:
        square = [
            Point(x=0, y=0),
            Point(x=10, y=0),
            Point(x=10, y=10),
            Point(x=0, y=10),
        ]
        # Point exactly on the left edge (x=0)
        assert point_in_polygon(Point(x=0, y=5), square) is True

    def test_triangle_inside(self) -> None:
        triangle = [
            Point(x=0, y=0),
            Point(x=10, y=0),
            Point(x=5, y=10),
        ]
        assert point_in_polygon(Point(x=5, y=3), triangle) is True

    def test_triangle_outside(self) -> None:
        triangle = [
            Point(x=0, y=0),
            Point(x=10, y=0),
            Point(x=5, y=10),
        ]
        assert point_in_polygon(Point(x=9, y=9), triangle) is False

    def test_degenerate_polygon(self) -> None:
        assert point_in_polygon(Point(x=1, y=1), [Point(x=0, y=0), Point(x=1, y=1)]) is False


# ---------------------------------------------------------------------------
# bbox_intersects_polygon
# ---------------------------------------------------------------------------

class TestBboxIntersectsPolygon:
    def _square_polygon(self) -> list[Point]:
        return [
            Point(x=0, y=0),
            Point(x=100, y=0),
            Point(x=100, y=100),
            Point(x=0, y=100),
        ]

    def test_fully_inside(self) -> None:
        bbox = BBox(x1=10, y1=10, x2=20, y2=20)
        assert bbox_intersects_polygon(bbox, self._square_polygon()) is True

    def test_partial_overlap(self) -> None:
        bbox = BBox(x1=90, y1=90, x2=110, y2=110)
        assert bbox_intersects_polygon(bbox, self._square_polygon()) is True

    def test_completely_outside(self) -> None:
        bbox = BBox(x1=200, y1=200, x2=300, y2=300)
        assert bbox_intersects_polygon(bbox, self._square_polygon()) is False


# ---------------------------------------------------------------------------
# bbox_center
# ---------------------------------------------------------------------------

class TestBboxCenter:
    def test_standard_bbox(self) -> None:
        bbox = BBox(x1=10, y1=20, x2=30, y2=40)
        center = bbox_center(bbox)
        assert center.x == pytest.approx(20.0)
        assert center.y == pytest.approx(30.0)

    def test_zero_area_bbox(self) -> None:
        bbox = BBox(x1=5, y1=5, x2=5, y2=5)
        center = bbox_center(bbox)
        assert center.x == pytest.approx(5.0)
        assert center.y == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# is_stationary
# ---------------------------------------------------------------------------

class TestIsStationary:
    def _make_track(self, points: list[Point]) -> Track:
        return Track(
            track_id="t1",
            object_id="obj1",
            label=ObjectClass.CAR,
            bbox=BBox(x1=0, y1=0, x2=10, y2=10),
            confidence=0.9,
            trajectory=points,
        )

    def test_all_same_points(self) -> None:
        pts = [Point(x=50, y=50)] * 5
        assert is_stationary(self._make_track(pts)) is True

    def test_moving_track(self) -> None:
        pts = [Point(x=float(i * 20), y=50.0) for i in range(5)]
        assert is_stationary(self._make_track(pts)) is False

    def test_small_movement_below_threshold(self) -> None:
        pts = [Point(x=50.0, y=50.0), Point(x=52.0, y=51.0)]
        assert is_stationary(self._make_track(pts), threshold=5.0) is True

    def test_single_point_track(self) -> None:
        pts = [Point(x=50, y=50)]
        assert is_stationary(self._make_track(pts)) is True


# ---------------------------------------------------------------------------
# ViolationCooldown
# ---------------------------------------------------------------------------

class TestViolationCooldown:
    def test_first_call_returns_true(self) -> None:
        cd = ViolationCooldown()
        assert cd.check_and_record("cam1:veh1", ViolationClass.HELMET, cooldown_s=60) is True

    def test_immediate_second_call_returns_false(self) -> None:
        cd = ViolationCooldown()
        cd.check_and_record("cam1:veh1", ViolationClass.HELMET, cooldown_s=60)
        assert cd.check_and_record("cam1:veh1", ViolationClass.HELMET, cooldown_s=60) is False

    def test_after_cooldown_expires(self) -> None:
        cd = ViolationCooldown()
        cd.check_and_record("cam1:veh1", ViolationClass.HELMET, cooldown_s=1)
        time.sleep(1.1)
        assert cd.check_and_record("cam1:veh1", ViolationClass.HELMET, cooldown_s=1) is True

    def test_different_keys_dont_interfere(self) -> None:
        cd = ViolationCooldown()
        assert cd.check_and_record("cam1:veh1", ViolationClass.HELMET, cooldown_s=60) is True
        assert cd.check_and_record("cam1:veh2", ViolationClass.HELMET, cooldown_s=60) is True

    def test_different_violation_types_dont_interfere(self) -> None:
        cd = ViolationCooldown()
        assert cd.check_and_record("cam1:veh1", ViolationClass.HELMET, cooldown_s=60) is True
        assert cd.check_and_record("cam1:veh1", ViolationClass.SEATBELT, cooldown_s=60) is True
