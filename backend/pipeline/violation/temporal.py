"""Temporal violation helpers: geometry, trajectory analysis, cooldown."""

from __future__ import annotations

import time

from pipeline.contracts import BBox, Point, Track, ViolationClass
from pipeline.scene import LaneDirection


def point_in_polygon(point: Point, polygon: list[Point]) -> bool:
    n = len(polygon)
    if n < 3:
        return False
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i].x, polygon[i].y
        xj, yj = polygon[j].x, polygon[j].y
        if ((yi > point.y) != (yj > point.y)) and (
            point.x < (xj - xi) * (point.y - yi) / (yj - yi + 1e-12) + xi
        ):
            inside = not inside
        j = i
    return inside


def bbox_intersects_polygon(bbox: BBox, polygon: list[Point]) -> bool:
    corners = [
        Point(x=bbox.x1, y=bbox.y1),
        Point(x=bbox.x2, y=bbox.y1),
        Point(x=bbox.x2, y=bbox.y2),
        Point(x=bbox.x1, y=bbox.y2),
    ]
    return any(point_in_polygon(c, polygon) for c in corners)


def bbox_center(bbox: BBox) -> Point:
    return Point(x=(bbox.x1 + bbox.x2) / 2.0, y=(bbox.y1 + bbox.y2) / 2.0)


def line_segment_intersects_polygon(p1: Point, p2: Point, polygon: list[Point]) -> bool:
    n = len(polygon)
    if n < 3:
        return False
    if point_in_polygon(p1, polygon) or point_in_polygon(p2, polygon):
        return True
    for i in range(n):
        a = polygon[i]
        b = polygon[(i + 1) % n]
        if _segments_intersect(p1, p2, a, b):
            return True
    return False


def _segments_intersect(p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
    def cross(ax: float, ay: float, bx: float, by: float) -> float:
        return ax * by - ay * bx

    dx1, dy1 = p2.x - p1.x, p2.y - p1.y
    dx2, dy2 = p4.x - p3.x, p4.y - p3.y
    denom = cross(dx1, dy1, dx2, dy2)
    if abs(denom) < 1e-12:
        return False
    t = cross(p3.x - p1.x, p3.y - p1.y, dx2, dy2) / denom
    u = cross(p3.x - p1.x, p3.y - p1.y, dx1, dy1) / denom
    return 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0


def compute_trajectory_direction(track: Track) -> Point | None:
    pts = track.trajectory
    if len(pts) < 2:
        return None
    tail = pts[-min(5, len(pts)):]
    dx = tail[-1].x - tail[0].x
    dy = tail[-1].y - tail[0].y
    length = (dx * dx + dy * dy) ** 0.5
    if length < 1e-6:
        return None
    return Point(x=dx / length, y=dy / length)


def is_moving_against_lane(track: Track, lane: LaneDirection) -> bool:
    direction = compute_trajectory_direction(track)
    if direction is None:
        return False
    lane_dx = lane.end.x - lane.start.x
    lane_dy = lane.end.y - lane.start.y
    lane_len = (lane_dx * lane_dx + lane_dy * lane_dy) ** 0.5
    if lane_len < 1e-6:
        return False
    lane_dx /= lane_len
    lane_dy /= lane_len
    dot = direction.x * lane_dx + direction.y * lane_dy
    return dot < -0.3


def is_stationary(track: Track, threshold: float = 5.0) -> bool:
    pts = track.trajectory
    if len(pts) < 2:
        return True
    dx = pts[-1].x - pts[0].x
    dy = pts[-1].y - pts[0].y
    return (dx * dx + dy * dy) ** 0.5 < threshold


class ViolationCooldown:
    def __init__(self) -> None:
        self._seen: dict[str, float] = {}

    def check_and_record(
        self,
        key: str,
        violation_type: ViolationClass,
        cooldown_s: int = 60,
    ) -> bool:
        full_key = f"{key}:{violation_type.value}"
        now = time.monotonic()
        last = self._seen.get(full_key)
        if last is not None and (now - last) < cooldown_s:
            return False
        self._seen[full_key] = now
        return True
