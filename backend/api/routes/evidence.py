"""Evidence routes with real DB queries."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUser, get_current_user
from core.database import get_db
from core.models.violation import EvidencePacket, Violation

router = APIRouter()


@router.get("/{packet_id}")
async def get_evidence(
    packet_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(EvidencePacket).where(EvidencePacket.id == packet_id)
    )
    ep = result.scalar_one_or_none()
    if ep is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence packet not found")

    v_result = await db.execute(
        select(Violation).where(
            Violation.id == ep.violation_id,
            Violation.org_id == current_user.org_id,
        )
    )
    v = v_result.scalar_one_or_none()
    if v is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Violation not found")

    return {
        "packet_id": str(ep.id),
        "violation_id": str(ep.violation_id),
        "frame_urls": ep.frame_urls,
        "plate_crop_url": ep.plate_crop_url,
        "annotated_frame_url": ep.annotated_frame_url,
        "vlm_description": ep.vlm_description,
        "hash_chain": ep.hash_chain,
        "metadata": ep.metadata_json,
        "created_at": ep.created_at.isoformat(),
        "violation": {
            "id": str(v.id),
            "violation_type": v.violation_type,
            "confidence": v.confidence,
            "status": v.status,
            "vehicle_class": v.vehicle_class,
            "plate": v.plate_text,
            "plate_hash": v.plate_hash,
            "location_name": v.location_name,
            "latitude": v.latitude,
            "longitude": v.longitude,
            "created_at": v.created_at.isoformat(),
        },
    }
