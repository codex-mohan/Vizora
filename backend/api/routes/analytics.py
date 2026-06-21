"""Analytics routes with real DB aggregation queries."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUser, get_current_user
from core.database import get_db
from core.models.camera import Camera
from core.models.violation import Plate, Violation

router = APIRouter()


def _feature_collection(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": features}


def _valid_lat_lng(latitude: float | None, longitude: float | None) -> bool:
    if latitude is None or longitude is None:
        return False
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


def _metadata_float(metadata: dict[str, Any] | None, key: str) -> float | None:
    if not isinstance(metadata, dict):
        return None
    value = metadata.get(key)
    if value is None:
        evidence = metadata.get("evidence")
        value = evidence.get(key) if isinstance(evidence, dict) else None
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _normalise_coordinates(raw: Any) -> list[list[float]]:
    coordinates = raw.get("coordinates") if isinstance(raw, dict) else raw
    if not isinstance(coordinates, list):
        return []

    normalised: list[list[float]] = []
    for point in coordinates:
        if isinstance(point, dict):
            lng = point.get("lng", point.get("longitude"))
            lat = point.get("lat", point.get("latitude"))
        elif isinstance(point, (list, tuple)) and len(point) >= 2:
            lng, lat = point[0], point[1]
        else:
            continue
        try:
            lng_float = float(lng)
            lat_float = float(lat)
        except (TypeError, ValueError):
            continue
        if _valid_lat_lng(lat_float, lng_float):
            normalised.append([round(lng_float, 6), round(lat_float, 6)])
    return normalised


def _road_segments_from_scene_config(scene_config: dict[str, Any] | None) -> list[dict]:
    if not isinstance(scene_config, dict):
        return []
    raw_segments = scene_config.get("road_segments") or scene_config.get("routes") or []
    if not isinstance(raw_segments, list):
        return []

    segments: list[dict] = []
    for index, segment in enumerate(raw_segments):
        if not isinstance(segment, dict):
            continue
        coordinates = _normalise_coordinates(
            segment.get("coordinates")
            or segment.get("geometry")
            or segment.get("line")
        )
        if len(coordinates) < 2:
            continue
        segments.append(
            {
                "id": str(segment.get("id") or f"segment-{index + 1}"),
                "label": str(segment.get("label") or segment.get("name") or "Road segment"),
                "coordinates": coordinates,
            }
        )
    return segments


def _road_segment_from_metadata(metadata: dict[str, Any] | None) -> dict | None:
    if not isinstance(metadata, dict):
        return None

    containers = [metadata]
    evidence = metadata.get("evidence")
    if isinstance(evidence, dict):
        containers.append(evidence)

    for container in containers:
        segment_id = (
            container.get("road_segment_id")
            or container.get("route_segment_id")
            or container.get("road_id")
        )
        raw_coordinates = (
            container.get("road_segment_coordinates")
            or container.get("route_coordinates")
            or container.get("road_geometry")
        )
        coordinates = _normalise_coordinates(raw_coordinates)
        if segment_id and len(coordinates) >= 2:
            return {
                "id": str(segment_id),
                "label": str(
                    container.get("road_segment_label")
                    or container.get("route_segment_label")
                    or segment_id
                ),
                "coordinates": coordinates,
            }
    return None


def _dominant_violation(violation_types: dict[str, int]) -> str | None:
    if not violation_types:
        return None
    return max(violation_types.items(), key=lambda item: item[1])[0]


def _finalise_point_features(point_buckets: dict[str, dict]) -> list[dict]:
    features: list[dict] = []
    for bucket in point_buckets.values():
        count = bucket["count"]
        latitude = bucket["latitude_sum"] / count
        longitude = bucket["longitude_sum"] / count
        violation_types = dict(sorted(bucket["violation_types"].items()))
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(longitude, 6), round(latitude, 6)],
                },
                "properties": {
                    "location_name": bucket["location_name"],
                    "camera_id": bucket["camera_id"],
                    "violation_count": count,
                    "avg_confidence": round(bucket["confidence_sum"] / count, 4),
                    "dominant_violation": _dominant_violation(violation_types),
                    "violation_types": violation_types,
                    "weight": count,
                },
            }
        )
    return sorted(
        features,
        key=lambda feature: feature["properties"]["violation_count"],
        reverse=True,
    )


def _finalise_road_features(road_buckets: dict[str, dict]) -> list[dict]:
    features: list[dict] = []
    for bucket in road_buckets.values():
        count = bucket["count"]
        violation_types = dict(sorted(bucket["violation_types"].items()))
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": bucket["coordinates"],
                },
                "properties": {
                    "segment_id": bucket["segment_id"],
                    "label": bucket["label"],
                    "camera_id": bucket["camera_id"],
                    "location_name": bucket["location_name"],
                    "violation_count": count,
                    "avg_confidence": round(bucket["confidence_sum"] / count, 4),
                    "dominant_violation": _dominant_violation(violation_types),
                    "violation_types": violation_types,
                    "weight": count,
                },
            }
        )
    return sorted(
        features,
        key=lambda feature: feature["properties"]["violation_count"],
        reverse=True,
    )


def _build_hotspot_map_payload(rows: list[tuple[Violation, Camera | None]]) -> dict:
    point_buckets: dict[str, dict] = {}
    road_buckets: dict[str, dict] = {}

    for violation, camera in rows:
        metadata = violation.metadata_json if isinstance(violation.metadata_json, dict) else {}
        latitude = violation.latitude
        longitude = violation.longitude
        if not _valid_lat_lng(latitude, longitude):
            latitude = camera.latitude if camera else None
            longitude = camera.longitude if camera else None
        if not _valid_lat_lng(latitude, longitude):
            latitude = _metadata_float(metadata, "latitude")
            longitude = _metadata_float(metadata, "longitude")
        if not _valid_lat_lng(latitude, longitude):
            continue

        camera_id = str(violation.camera_id) if violation.camera_id else (
            str(camera.id) if camera else None
        )
        location_name = (
            violation.location_name
            or (camera.location_name if camera else None)
            or (camera.name if camera else None)
            or "Unknown location"
        )
        point_key = camera_id or f"{location_name}:{round(latitude, 5)}:{round(longitude, 5)}"
        if point_key not in point_buckets:
            point_buckets[point_key] = {
                "camera_id": camera_id,
                "location_name": location_name,
                "latitude_sum": 0.0,
                "longitude_sum": 0.0,
                "confidence_sum": 0.0,
                "count": 0,
                "violation_types": defaultdict(int),
            }
        point_bucket = point_buckets[point_key]
        point_bucket["latitude_sum"] += latitude
        point_bucket["longitude_sum"] += longitude
        point_bucket["confidence_sum"] += violation.confidence
        point_bucket["count"] += 1
        point_bucket["violation_types"][violation.violation_type] += 1

        segment = _road_segment_from_metadata(metadata)
        camera_segments = _road_segments_from_scene_config(camera.scene_config if camera else None)
        if segment is None and len(camera_segments) == 1:
            segment = camera_segments[0]
        if segment is None:
            continue

        road_key = f"{camera_id or location_name}:{segment['id']}"
        if road_key not in road_buckets:
            road_buckets[road_key] = {
                "segment_id": segment["id"],
                "label": segment["label"],
                "camera_id": camera_id,
                "location_name": location_name,
                "coordinates": segment["coordinates"],
                "confidence_sum": 0.0,
                "count": 0,
                "violation_types": defaultdict(int),
            }
        road_bucket = road_buckets[road_key]
        road_bucket["confidence_sum"] += violation.confidence
        road_bucket["count"] += 1
        road_bucket["violation_types"][violation.violation_type] += 1

    point_features = _finalise_point_features(point_buckets)
    road_features = _finalise_road_features(road_buckets)
    all_point_coordinates = [
        feature["geometry"]["coordinates"]
        for feature in point_features
    ]
    if all_point_coordinates:
        center = {
            "longitude": round(
                sum(coordinates[0] for coordinates in all_point_coordinates)
                / len(all_point_coordinates),
                6,
            ),
            "latitude": round(
                sum(coordinates[1] for coordinates in all_point_coordinates)
                / len(all_point_coordinates),
                6,
            ),
        }
    else:
        center = None

    max_count = max(
        [feature["properties"]["violation_count"] for feature in point_features] or [0]
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "center": center,
        "points": _feature_collection(point_features),
        "road_segments": _feature_collection(road_features),
        "totals": {
            "point_count": len(point_features),
            "road_segment_count": len(road_features),
            "max_count": max_count,
        },
    }


@router.get("/summary")
async def summary(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    camera_id: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    filters = [Violation.org_id == current_user.org_id]
    if date_from:
        filters.append(Violation.created_at >= date_from)
    if date_to:
        filters.append(Violation.created_at <= date_to)
    if camera_id:
        try:
            filters.append(Violation.camera_id == uuid.UUID(camera_id))
        except ValueError:
            pass

    total_result = await db.execute(
        select(func.count()).select_from(Violation).where(*filters)
    )
    total_violations = total_result.scalar_one()

    type_result = await db.execute(
        select(Violation.violation_type, func.count())
        .where(*filters)
        .group_by(Violation.violation_type)
    )
    by_type = {row[0]: row[1] for row in type_result.all()}

    hour_result = await db.execute(
        select(extract("hour", Violation.created_at).label("hour"), func.count())
        .where(*filters)
        .group_by("hour")
        .order_by("hour")
    )
    by_hour = {int(row[0]): row[1] for row in hour_result.all()}

    trend_result = await db.execute(
        select(
            func.date_trunc("day", Violation.created_at).label("day"),
            func.count(),
        )
        .where(*filters)
        .group_by("day")
        .order_by("day")
    )
    trend = [{"date": row[0].isoformat(), "count": row[1]} for row in trend_result.all()]

    avg_conf_result = await db.execute(
        select(func.avg(Violation.confidence)).where(*filters)
    )
    avg_confidence = round(avg_conf_result.scalar_one() or 0.0, 4)

    review_result = await db.execute(
        select(func.count())
        .select_from(Violation)
        .where(*filters, Violation.status == "pending", Violation.review_required == True)
    )
    review_queue_depth = review_result.scalar_one()

    active_cam_result = await db.execute(
        select(func.count())
        .select_from(Camera)
        .where(Camera.org_id == current_user.org_id, Camera.status == "online")
    )
    active_cameras_count = active_cam_result.scalar_one()

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(func.count())
        .select_from(Violation)
        .where(*filters, Violation.created_at >= today_start)
    )
    violations_today = today_result.scalar_one()

    return {
        "total_violations": total_violations,
        "by_type": by_type,
        "by_hour": by_hour,
        "trend": trend,
        "avg_confidence": avg_confidence,
        "review_queue_depth": review_queue_depth,
        "active_cameras": active_cameras_count,
        "active_cameras_count": active_cameras_count,
        "violations_today": violations_today,
    }


@router.get("/hotspots")
async def hotspots(
    limit: int = Query(10, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(
            Violation.location_name,
            func.avg(Violation.latitude).label("latitude"),
            func.avg(Violation.longitude).label("longitude"),
            func.count().label("violation_count"),
        )
        .where(
            Violation.org_id == current_user.org_id,
            Violation.location_name.isnot(None),
        )
        .group_by(Violation.location_name)
        .order_by(func.count().desc())
        .limit(limit)
    )
    return [
        {
            "location_name": row[0],
            "latitude": round(row[1], 6) if row[1] else None,
            "longitude": round(row[2], 6) if row[2] else None,
            "violation_count": row[3],
        }
        for row in result.all()
    ]


@router.get("/repeat-offenders")
async def repeat_offenders(
    limit: int = Query(10, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(Plate)
        .where(Plate.org_id == current_user.org_id)
        .order_by(Plate.violation_count.desc())
        .limit(limit)
    )
    plates = result.scalars().all()

    offenders = []
    for plate in plates:
        vtypes_result = await db.execute(
            select(Violation.violation_type, func.count())
            .where(
                Violation.plate_hash == plate.plate_hash,
                Violation.org_id == current_user.org_id,
            )
            .group_by(Violation.violation_type)
        )
        violation_types = {row[0]: row[1] for row in vtypes_result.all()}

        offenders.append({
            "plate_text": plate.plate_text,
            "plate_hash": plate.plate_hash,
            "violation_count": plate.violation_count,
            "last_seen_at": plate.last_seen_at.isoformat(),
            "violation_types": violation_types,
        })

    return offenders


@router.get("/day-hour-heatmap")
async def day_hour_heatmap(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(
            extract("dow", Violation.created_at).label("day"),
            extract("hour", Violation.created_at).label("hour"),
            func.count().label("count"),
        )
        .where(Violation.org_id == current_user.org_id)
        .group_by("day", "hour")
        .order_by("day", "hour")
    )
    return [
        {"day": int(row[0]), "hour": int(row[1]), "count": row[2]}
        for row in result.all()
    ]


@router.get("/hotspot-map")
async def hotspot_map(
    limit: int = Query(5000, ge=1, le=50000),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    camera_id: str | None = None,
    violation_type: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    filters = [Violation.org_id == current_user.org_id]
    if date_from:
        filters.append(Violation.created_at >= date_from)
    if date_to:
        filters.append(Violation.created_at <= date_to)
    if camera_id:
        try:
            filters.append(Violation.camera_id == uuid.UUID(camera_id))
        except ValueError:
            filters.append(Violation.location_name == camera_id)
    if violation_type:
        filters.append(Violation.violation_type == violation_type)

    result = await db.execute(
        select(Violation, Camera)
        .outerjoin(Camera, Violation.camera_id == Camera.id)
        .where(*filters)
        .order_by(Violation.created_at.desc())
        .limit(limit)
    )
    return _build_hotspot_map_payload(result.all())
