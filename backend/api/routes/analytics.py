"""Analytics routes with real DB aggregation queries."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUser, get_current_user
from core.database import get_db
from core.models.camera import Camera
from core.models.violation import Plate, Violation

router = APIRouter()


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
