"""Evidence routes with real DB queries."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUser, get_current_user
from core.database import get_db
from core.models.camera import Camera
from core.models.violation import EvidencePacket, Violation
from core.storage import get_storage

router = APIRouter()


def _to_api_path(key: str | None) -> str | None:
    """Convert an S3 key to a backend API path (frontend prepends its base URL)."""
    if not key:
        return None
    if key.startswith("http://") or key.startswith("https://"):
        return key
    return f"/api/evidence/file?key={key}"


def _to_api_path_list(keys: list[str]) -> list[str]:
    return [url for key in keys if (url := _to_api_path(key))]


@router.get("/file")
async def serve_evidence_file(
    key: str = Query(..., description="S3 object key"),
):
    """Proxy an evidence file from MinIO through the backend."""
    import io
    storage = get_storage()
    try:
        data = storage.download(key)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found in storage")
    content_type = "image/png"
    if key.endswith(".jpg") or key.endswith(".jpeg"):
        content_type = "image/jpeg"
    elif key.endswith(".mp4"):
        content_type = "video/mp4"
    return StreamingResponse(io.BytesIO(data), media_type=content_type)


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

    camera_name = None
    if v.camera_id:
        cam_result = await db.execute(select(Camera.name).where(Camera.id == v.camera_id))
        camera_name = cam_result.scalar_one_or_none()

    metadata = dict(ep.metadata_json or {})
    metadata["violation_metadata"] = v.metadata_json or {}

    return {
        "packet_id": str(ep.id),
        "violation_id": str(ep.violation_id),
        "frame_urls": _to_api_path_list(ep.frame_urls or []),
        "plate_crop_url": _to_api_path(ep.plate_crop_url),
        "annotated_frame_url": _to_api_path(ep.annotated_frame_url),
        "vlm_description": ep.vlm_description,
        "hash_chain": ep.hash_chain,
        "metadata": metadata,
        "created_at": ep.created_at.isoformat(),
        "violation": {
            "id": str(v.id),
            "violation_type": v.violation_type,
            "confidence": v.confidence,
            "camera_id": str(v.camera_id) if v.camera_id else "",
            "location": camera_name or v.location_name or "",
            "timestamp": v.created_at.isoformat(),
            "status": v.status,
            "vehicle_class": v.vehicle_class,
            "plate": v.plate_text,
            "plate_hash": v.plate_hash,
            "description": ep.vlm_description,
            "evidence_packet_id": str(ep.id),
            "review_required": v.review_required,
            "review_reasons": v.review_reasons or [],
            "location_name": v.location_name,
            "latitude": v.latitude,
            "longitude": v.longitude,
            "created_at": v.created_at.isoformat(),
        },
    }
