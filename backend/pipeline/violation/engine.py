"""Rule engine for image-first and temporal traffic violations."""

from __future__ import annotations

from core.config import settings
from pipeline.contracts import (
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
from pipeline.scene import CameraSceneConfig
from pipeline.violation.temporal import (
    ViolationCooldown,
    bbox_center,
    bbox_intersects_polygon,
    is_moving_against_lane,
    is_stationary,
)


class ViolationEngine:
    def __init__(self) -> None:
        self.cooldown = ViolationCooldown()

    def evaluate(
        self,
        *,
        mode: ProcessingMode,
        scene: CameraSceneConfig,
        detections: list[DetectedObject],
        tracks: list[Track],
        poses: list[PoseResult],
        plates: list[PlateResult],
        helmet_scores: dict[str, float],
        seatbelt_scores: dict[str, float],
    ) -> list[ViolationPrediction]:
        raw: list[ViolationPrediction] = []
        raw.extend(self._helmet_violations(detections, helmet_scores))
        raw.extend(self._seatbelt_violations(detections, seatbelt_scores))
        raw.extend(self._triple_ride(mode, detections))
        raw.extend(self._wrong_side(mode, scene, detections, tracks))
        raw.extend(self._stop_line(mode, scene, detections, tracks))
        raw.extend(self._red_light(mode, scene, detections, tracks))
        raw.extend(self._illegal_parking(mode, scene, detections, tracks))

        cooldown_s = settings.violation_cooldown_s
        filtered: list[ViolationPrediction] = []
        for v in raw:
            key = v.object_ids[0] if v.object_ids else "unknown"
            if self.cooldown.check_and_record(key, v.violation_type, cooldown_s):
                filtered.append(v)
        return filtered

    def _helmet_violations(
        self,
        detections: list[DetectedObject],
        helmet_scores: dict[str, float],
    ) -> list[ViolationPrediction]:
        violations: list[ViolationPrediction] = []
        for det in detections:
            if det.label != ObjectClass.RIDER:
                continue
            score = helmet_scores.get(det.id)
            if score is None:
                continue
            no_helmet = 1.0 - score
            if no_helmet >= 0.55:
                violations.append(
                    ViolationPrediction(
                        violation_type=ViolationClass.HELMET,
                        confidence=no_helmet,
                        object_ids=[det.id],
                        bbox=det.bbox,
                    )
                )
        return violations

    def _seatbelt_violations(
        self,
        detections: list[DetectedObject],
        seatbelt_scores: dict[str, float],
    ) -> list[ViolationPrediction]:
        violations: list[ViolationPrediction] = []
        for det in detections:
            if det.label != ObjectClass.DRIVER:
                continue
            score = seatbelt_scores.get(det.id)
            if score is None:
                continue
            no_belt = 1.0 - score
            if no_belt >= 0.6:
                violations.append(
                    ViolationPrediction(
                        violation_type=ViolationClass.SEATBELT,
                        confidence=no_belt,
                        object_ids=[det.id],
                        bbox=det.bbox,
                    )
                )
        return violations

    def _triple_ride(
        self,
        mode: ProcessingMode,
        detections: list[DetectedObject],
    ) -> list[ViolationPrediction]:
        motorcycles = [d for d in detections if d.label == ObjectClass.MOTORCYCLE]
        riders = [d for d in detections if d.label == ObjectClass.RIDER]
        if not motorcycles or len(riders) < 3:
            return []

        violations: list[ViolationPrediction] = []
        for moto in motorcycles:
            mc = bbox_center(moto.bbox)
            associated: list[DetectedObject] = []
            for r in riders:
                rc = bbox_center(r.bbox)
                dx = rc.x - mc.x
                dy = rc.y - mc.y
                if (dx * dx + dy * dy) ** 0.5 < 50.0:
                    associated.append(r)
            if len(associated) < 3:
                continue

            rider_ids = [r.id for r in associated]
            count = len(associated)
            if count == 3:
                confidence = 0.7
            else:
                confidence = min(0.9, 0.7 + 0.05 * (count - 3))

            reasons: list[ReviewReason] = []
            if mode == ProcessingMode.STILL_IMAGE:
                confidence = min(confidence, 0.65)
                reasons.append(ReviewReason.TEMPORAL_REQUIRED)

            violations.append(
                ViolationPrediction(
                    violation_type=ViolationClass.TRIPLE_RIDE,
                    confidence=confidence,
                    object_ids=[moto.id, *rider_ids[:4]],
                    bbox=moto.bbox,
                    review_required=bool(reasons),
                    review_reasons=reasons,
                )
            )
        return violations

    def _wrong_side(
        self,
        mode: ProcessingMode,
        scene: CameraSceneConfig,
        detections: list[DetectedObject],
        tracks: list[Track],
    ) -> list[ViolationPrediction]:
        if not scene.lane_directions:
            return []

        vehicles = [d for d in detections if d.label in (
            ObjectClass.CAR, ObjectClass.MOTORCYCLE, ObjectClass.AUTO,
            ObjectClass.BUS, ObjectClass.TRUCK, ObjectClass.BICYCLE,
        )]
        if not vehicles:
            return []

        if mode == ProcessingMode.TEMPORAL_BURST:
            return self._wrong_side_temporal(scene, tracks)
        return self._wrong_side_still(scene, vehicles)

    def _wrong_side_temporal(
        self,
        scene: CameraSceneConfig,
        tracks: list[Track],
    ) -> list[ViolationPrediction]:
        violations: list[ViolationPrediction] = []
        vehicle_tracks = [t for t in tracks if t.label in (
            ObjectClass.CAR, ObjectClass.MOTORCYCLE, ObjectClass.AUTO,
            ObjectClass.BUS, ObjectClass.TRUCK, ObjectClass.BICYCLE,
        )]
        for track in vehicle_tracks:
            for lane in scene.lane_directions:
                if is_moving_against_lane(track, lane):
                    violations.append(
                        ViolationPrediction(
                            violation_type=ViolationClass.WRONG_SIDE,
                            confidence=0.85,
                            object_ids=[track.object_id],
                            bbox=track.bbox,
                            evidence={"lane_id": lane.id, "lane_label": lane.id},
                        )
                    )
                    break
        return violations

    def _wrong_side_still(
        self,
        scene: CameraSceneConfig,
        vehicles: list[DetectedObject],
    ) -> list[ViolationPrediction]:
        violations: list[ViolationPrediction] = []
        for v in vehicles:
            direction_hint = v.metadata.get("direction")
            if not direction_hint:
                continue
            for lane in scene.lane_directions:
                lane_vec = (lane.end.x - lane.start.x, lane.end.y - lane.start.y)
                dot = direction_hint[0] * lane_vec[0] + direction_hint[1] * lane_vec[1]
                if dot < 0:
                    violations.append(
                        ViolationPrediction(
                            violation_type=ViolationClass.WRONG_SIDE,
                            confidence=0.45,
                            object_ids=[v.id],
                            bbox=v.bbox,
                            review_required=True,
                            review_reasons=[ReviewReason.TEMPORAL_REQUIRED],
                            evidence={"lane_id": lane.id, "mode": "still_image_heuristic"},
                        )
                    )
                    break
        return violations

    def _stop_line(
        self,
        mode: ProcessingMode,
        scene: CameraSceneConfig,
        detections: list[DetectedObject],
        tracks: list[Track],
    ) -> list[ViolationPrediction]:
        if not scene.stop_lines:
            return []

        if mode == ProcessingMode.TEMPORAL_BURST:
            return self._stop_line_temporal(scene, tracks)
        return self._stop_line_still(scene, detections)

    def _stop_line_temporal(
        self,
        scene: CameraSceneConfig,
        tracks: list[Track],
    ) -> list[ViolationPrediction]:
        violations: list[ViolationPrediction] = []
        vehicle_tracks = [t for t in tracks if t.label in (
            ObjectClass.CAR, ObjectClass.MOTORCYCLE, ObjectClass.AUTO,
            ObjectClass.BUS, ObjectClass.TRUCK, ObjectClass.BICYCLE,
        )]
        for track in vehicle_tracks:
            if len(track.trajectory) < 2:
                continue
            for sl in scene.stop_lines:
                if bbox_intersects_polygon(track.bbox, sl.points):
                    violations.append(
                        ViolationPrediction(
                            violation_type=ViolationClass.STOP_LINE,
                            confidence=0.8,
                            object_ids=[track.object_id],
                            bbox=track.bbox,
                            evidence={"stop_line_id": sl.id},
                        )
                    )
                    break
        return violations

    def _stop_line_still(
        self,
        scene: CameraSceneConfig,
        detections: list[DetectedObject],
    ) -> list[ViolationPrediction]:
        if not scene.has_signal_context:
            return []
        vehicles = [d for d in detections if d.label in (
            ObjectClass.CAR, ObjectClass.MOTORCYCLE, ObjectClass.AUTO,
            ObjectClass.BUS, ObjectClass.TRUCK, ObjectClass.BICYCLE,
        )]
        violations: list[ViolationPrediction] = []
        for v in vehicles:
            for sl in scene.stop_lines:
                if bbox_intersects_polygon(v.bbox, sl.points):
                    violations.append(
                        ViolationPrediction(
                            violation_type=ViolationClass.STOP_LINE,
                            confidence=0.55,
                            object_ids=[v.id],
                            bbox=v.bbox,
                            review_required=True,
                            review_reasons=[ReviewReason.TEMPORAL_REQUIRED],
                            evidence={"stop_line_id": sl.id, "mode": "still_image_heuristic"},
                        )
                    )
                    break
        return violations

    def _red_light(
        self,
        mode: ProcessingMode,
        scene: CameraSceneConfig,
        detections: list[DetectedObject],
        tracks: list[Track],
    ) -> list[ViolationPrediction]:
        if not scene.has_signal_context:
            return []

        if mode == ProcessingMode.TEMPORAL_BURST:
            return self._red_light_temporal(scene, tracks)
        return self._red_light_still(scene, detections)

    def _red_light_temporal(
        self,
        scene: CameraSceneConfig,
        tracks: list[Track],
    ) -> list[ViolationPrediction]:
        violations: list[ViolationPrediction] = []
        vehicle_tracks = [t for t in tracks if t.label in (
            ObjectClass.CAR, ObjectClass.MOTORCYCLE, ObjectClass.AUTO,
            ObjectClass.BUS, ObjectClass.TRUCK, ObjectClass.BICYCLE,
        )]
        for track in vehicle_tracks:
            if len(track.trajectory) < 2:
                continue
            for sl in scene.stop_lines:
                if bbox_intersects_polygon(track.bbox, sl.points):
                    violations.append(
                        ViolationPrediction(
                            violation_type=ViolationClass.RED_LIGHT,
                            confidence=0.85,
                            object_ids=[track.object_id],
                            bbox=track.bbox,
                            evidence={"stop_line_id": sl.id},
                        )
                    )
                    break
        return violations

    def _red_light_still(
        self,
        scene: CameraSceneConfig,
        detections: list[DetectedObject],
    ) -> list[ViolationPrediction]:
        violations: list[ViolationPrediction] = []
        for v in detections:
            if v.label not in (
                ObjectClass.CAR, ObjectClass.MOTORCYCLE, ObjectClass.AUTO,
                ObjectClass.BUS, ObjectClass.TRUCK, ObjectClass.BICYCLE,
            ):
                continue
            violations.append(
                ViolationPrediction(
                    violation_type=ViolationClass.RED_LIGHT,
                    confidence=0.35,
                    object_ids=[v.id],
                    bbox=v.bbox,
                    review_required=True,
                    review_reasons=[ReviewReason.TEMPORAL_REQUIRED],
                    evidence={"mode": "still_image_no_signal_state"},
                )
            )
        return violations

    def _illegal_parking(
        self,
        mode: ProcessingMode,
        scene: CameraSceneConfig,
        detections: list[DetectedObject],
        tracks: list[Track],
    ) -> list[ViolationPrediction]:
        if not scene.no_parking_zones:
            return []

        if mode == ProcessingMode.TEMPORAL_BURST:
            return self._illegal_parking_temporal(scene, tracks)
        return self._illegal_parking_still(scene, detections)

    def _illegal_parking_temporal(
        self,
        scene: CameraSceneConfig,
        tracks: list[Track],
    ) -> list[ViolationPrediction]:
        violations: list[ViolationPrediction] = []
        vehicle_tracks = [t for t in tracks if t.label in (
            ObjectClass.CAR, ObjectClass.MOTORCYCLE, ObjectClass.AUTO,
            ObjectClass.BUS, ObjectClass.TRUCK,
        )]
        for track in vehicle_tracks:
            if not is_stationary(track, threshold=10.0):
                continue
            for zone in scene.no_parking_zones:
                if bbox_intersects_polygon(track.bbox, zone.points):
                    violations.append(
                        ViolationPrediction(
                            violation_type=ViolationClass.ILLEGAL_PARKING,
                            confidence=0.8,
                            object_ids=[track.object_id],
                            bbox=track.bbox,
                            evidence={"zone_id": zone.id},
                        )
                    )
                    break
        return violations

    def _illegal_parking_still(
        self,
        scene: CameraSceneConfig,
        detections: list[DetectedObject],
    ) -> list[ViolationPrediction]:
        vehicles = [d for d in detections if d.label in (
            ObjectClass.CAR, ObjectClass.MOTORCYCLE, ObjectClass.AUTO,
            ObjectClass.BUS, ObjectClass.TRUCK,
        )]
        violations: list[ViolationPrediction] = []
        for v in vehicles:
            for zone in scene.no_parking_zones:
                if bbox_intersects_polygon(v.bbox, zone.points):
                    violations.append(
                        ViolationPrediction(
                            violation_type=ViolationClass.ILLEGAL_PARKING,
                            confidence=0.5,
                            object_ids=[v.id],
                            bbox=v.bbox,
                            review_required=True,
                            review_reasons=[ReviewReason.TEMPORAL_REQUIRED],
                            evidence={"zone_id": zone.id, "mode": "still_image_heuristic"},
                        )
                    )
                    break
        return violations
