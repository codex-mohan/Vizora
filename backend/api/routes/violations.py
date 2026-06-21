"""Violation routes with real DB queries."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUser, get_current_user, require_role
from api.schemas.violation import Violation as ViolationSchema
from api.schemas.violation import ViolationList, ViolationType
from core.database import get_db
from core.models.camera import Camera
from core.models.violation import EvidencePacket, Violation
from core.storage import get_storage

router = APIRouter()


def _to_api_path(key: str | None) -> str | None:
    if not key:
        return None
    if key.startswith("http://") or key.startswith("https://"):
        return key
    return f"/api/evidence/file?key={key}"


def _to_api_path_list(keys: list[str]) -> list[str]:
    return [url for key in keys if (url := _to_api_path(key))]


class ViolationStatusUpdate(BaseModel):
    status: str | None = None
    action: str | None = None


def _to_violation_schema(
    v: Violation,
    camera_name: str | None,
    evidence_packet_id: str | None,
    vlm_description: str | None,
) -> ViolationSchema:
    return ViolationSchema(
        id=str(v.id),
        violation_type=ViolationType(v.violation_type),
        confidence=v.confidence,
        camera_id=str(v.camera_id) if v.camera_id else "",
        location=camera_name or v.location_name or "",
        timestamp=v.created_at,
        vehicle_class=v.vehicle_class,
        plate=v.plate_text,
        plate_hash=v.plate_hash,
        description=vlm_description,
        evidence_packet_id=evidence_packet_id,
        review_required=v.review_required,
        review_reasons=v.review_reasons or [],
        status=v.status,
    )


@router.get("", response_model=ViolationList)
async def list_violations(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    violation_type: ViolationType | None = None,
    camera_id: str | None = None,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    plate_search: str | None = None,
    review_required: bool | None = None,
    status_filter: str | None = Query(None, alias="status"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ViolationList:
    filters = [Violation.org_id == current_user.org_id]

    if violation_type is not None:
        filters.append(Violation.violation_type == violation_type.value)
    if camera_id is not None:
        try:
            filters.append(Violation.camera_id == uuid.UUID(camera_id))
        except ValueError:
            filters.append(Violation.camera_id == None)
    if min_confidence > 0.0:
        filters.append(Violation.confidence >= min_confidence)
    if date_from is not None:
        filters.append(Violation.created_at >= date_from)
    if date_to is not None:
        filters.append(Violation.created_at <= date_to)
    if plate_search is not None:
        filters.append(Violation.plate_text.ilike(f"%{plate_search}%"))
    if review_required is not None:
        filters.append(Violation.review_required == review_required)
    if status_filter is not None:
        filters.append(Violation.status == status_filter)

    count_stmt = select(func.count()).select_from(Violation).where(*filters)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    offset = (page - 1) * size
    stmt = (
        select(Violation)
        .where(*filters)
        .order_by(Violation.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    result = await db.execute(stmt)
    violations = result.scalars().all()

    violation_ids = [v.id for v in violations]
    camera_ids = {v.camera_id for v in violations if v.camera_id is not None}

    camera_names: dict[uuid.UUID, str] = {}
    if camera_ids:
        cam_result = await db.execute(
            select(Camera.id, Camera.name).where(Camera.id.in_(camera_ids))
        )
        camera_names = {row[0]: row[1] for row in cam_result.all()}

    evidence_map: dict[uuid.UUID, tuple[str, str | None]] = {}
    if violation_ids:
        ep_result = await db.execute(
            select(EvidencePacket.violation_id, EvidencePacket.id, EvidencePacket.vlm_description).where(
                EvidencePacket.violation_id.in_(violation_ids)
            )
        )
        for row in ep_result.all():
            evidence_map[row[0]] = (str(row[1]), row[2])

    items = []
    for v in violations:
        ep_id, vlm_desc = evidence_map.get(v.id, (None, None))
        items.append(
            _to_violation_schema(
                v, camera_names.get(v.camera_id), ep_id, vlm_desc
            )
        )

    return ViolationList(items=items, total=total, page=page, size=size)


@router.get("/{violation_id}")
async def get_violation(
    violation_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Violation).where(
            Violation.id == violation_id,
            Violation.org_id == current_user.org_id,
        )
    )
    v = result.scalar_one_or_none()
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Violation not found")

    camera_name = None
    if v.camera_id:
        cam_result = await db.execute(select(Camera.name).where(Camera.id == v.camera_id))
        camera_name = cam_result.scalar_one_or_none()

    ep_result = await db.execute(
        select(EvidencePacket).where(EvidencePacket.violation_id == v.id)
    )
    ep = ep_result.scalar_one_or_none()

    return {
        "id": str(v.id),
        "violation_type": v.violation_type,
        "confidence": v.confidence,
        "camera_id": str(v.camera_id) if v.camera_id else None,
        "location": camera_name or v.location_name,
        "timestamp": v.created_at.isoformat(),
        "vehicle_class": v.vehicle_class,
        "plate": v.plate_text,
        "plate_hash": v.plate_hash,
        "status": v.status,
        "review_required": v.review_required,
        "review_reasons": v.review_reasons,
        "latitude": v.latitude,
        "longitude": v.longitude,
        "metadata": v.metadata_json,
        "reviewed_at": v.reviewed_at.isoformat() if v.reviewed_at else None,
        "reviewed_by": str(v.reviewed_by) if v.reviewed_by else None,
        "evidence_packet": {
            "id": str(ep.id),
            "frame_urls": _to_api_path_list(ep.frame_urls or []),
            "plate_crop_url": _to_api_path(ep.plate_crop_url),
            "annotated_frame_url": _to_api_path(ep.annotated_frame_url),
            "vlm_description": ep.vlm_description,
            "hash_chain": ep.hash_chain,
            "metadata": ep.metadata_json,
            "created_at": ep.created_at.isoformat(),
        } if ep else None,
    }


@router.patch("/{violation_id}/status")
async def update_violation_status(
    violation_id: uuid.UUID,
    body: ViolationStatusUpdate | None = None,
    new_status: str | None = Query(None, alias="action"),
    current_user: CurrentUser = Depends(require_role("admin", "reviewer")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    requested_status = new_status or (body.action if body else None) or (body.status if body else None)
    status_map = {
        "approve": "approved",
        "approved": "approved",
        "reject": "rejected",
        "rejected": "rejected",
        "escalate": "escalated",
        "escalated": "escalated",
    }
    canonical_status = status_map.get(requested_status or "")
    if canonical_status is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be approve/approved, reject/rejected, or escalate/escalated.",
        )

    result = await db.execute(
        select(Violation).where(
            Violation.id == violation_id,
            Violation.org_id == current_user.org_id,
        )
    )
    v = result.scalar_one_or_none()
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Violation not found")

    v.status = canonical_status
    v.reviewed_at = datetime.now(timezone.utc)
    v.reviewed_by = current_user.user_id
    await db.commit()
    await db.refresh(v)

    return {
        "id": str(v.id),
        "status": v.status,
        "reviewed_at": v.reviewed_at.isoformat(),
        "reviewed_by": str(v.reviewed_by),
    }
