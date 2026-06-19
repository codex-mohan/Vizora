from __future__ import annotations

import hashlib
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, CurrentUser
from core.config import settings
from core.database import async_session_factory, get_db
from core.models.violation import EvidencePacket, Plate, Violation
from core.realtime import realtime_bus
from pipeline.contracts import MediaInput, ProcessingMode
from pipeline.infer import InferencePipeline

router = APIRouter()


def _get_pipeline(request: Request) -> InferencePipeline:
    pipeline = getattr(request.app.state, "inference_pipeline", None)
    if pipeline is None:
        profile = request.app.state.model_profile
        pipeline = InferencePipeline(settings, profile)
        request.app.state.inference_pipeline = pipeline
    return pipeline


async def _persist_violations(
    result,
    media: MediaInput,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> None:
    """Persist inference results to database and MinIO."""
    from core.storage import get_storage

    storage = get_storage()

    # Upload raw image to MinIO
    raw_key = storage.upload_image(media.data, content_type=media.content_type or "image/png",
                                   folder=f"evidence/{org_id}")

    # Upload annotated image if available
    annotated_key = None
    evidence_packet = None
    if hasattr(result, "annotated_image_bytes") and result.annotated_image_bytes:
        annotated_key = storage.upload_image(
            result.annotated_image_bytes, content_type="image/png",
            folder=f"annotated/{org_id}"
        )

    # Create evidence packet
    evidence_packet = EvidencePacket(
        id=uuid.UUID(result.evidence_packet_id.replace("ev-", "").replace("pending", uuid.uuid4().hex[:12])),
        violation_id=uuid.uuid4(),  # will update after violation created
        frame_urls=[raw_key],
        annotated_frame_url=annotated_key,
        plate_crop_url=None,
        vlm_description=result.description,
        hash_chain=hashlib.sha256(
            f"{result.request_id}:{result.camera_id}:{result.timestamp}".encode()
        ).hexdigest(),
        metadata_json={
            "request_id": result.request_id,
            "model_profile": result.model_profile,
            "quality_score": result.quality.score,
            "detection_count": len(result.detections),
        },
    )

    # Persist each violation
    for violation in result.violations:
        plate_text = None
        plate_hash = None
        if result.plates:
            best_plate = max(result.plates, key=lambda p: p.confidence)
            if best_plate.plate_text:
                plate_text = best_plate.plate_text
                plate_hash = hashlib.sha256(plate_text.encode()).hexdigest()

        db_violation = Violation(
            org_id=org_id,
            violation_type=violation.violation_type.value,
            confidence=violation.confidence,
            status="pending",
            review_required=violation.review_required,
            review_reasons=[r.value for r in violation.review_reasons] if violation.review_reasons else None,
            vehicle_class=None,
            plate_text=plate_text,
            plate_hash=plate_hash,
            location_name=media.camera_id,
            metadata_json={
                "object_ids": violation.object_ids,
                "evidence": violation.evidence,
                "bbox": violation.bbox.model_dump() if violation.bbox else None,
            },
        )
        db.add(db_violation)
        await db.flush()

        # Update evidence packet with actual violation ID
        evidence_packet.violation_id = db_violation.id
        db.add(evidence_packet)

        # Upsert plate record
        if plate_text and plate_hash:
            from sqlalchemy import select
            existing = await db.execute(
                select(Plate).where(Plate.plate_hash == plate_hash, Plate.org_id == org_id)
            )
            plate_record = existing.scalar_one_or_none()
            if plate_record:
                plate_record.violation_count += 1
                from datetime import datetime, timezone
                plate_record.last_seen_at = datetime.now(timezone.utc)
            else:
                plate_record = Plate(
                    org_id=org_id,
                    plate_text=plate_text,
                    plate_hash=plate_hash,
                    violation_count=1,
                )
                db.add(plate_record)

    await db.commit()


@router.post("")
async def process_media(
    request: Request,
    file: UploadFile = File(...),
    camera_id: str = Form("demo-camera"),
    mode: ProcessingMode = Form(ProcessingMode.STILL_IMAGE),
) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    media = MediaInput(
        filename=file.filename or "upload",
        content_type=file.content_type,
        data=data,
        camera_id=camera_id,
        mode=mode,
    )
    result = _get_pipeline(request).process(media)
    payload = result.model_dump(mode="json")

    # Persist to DB (org_id from auth or default demo org)
    try:
        async with async_session_factory() as db:
            org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")  # demo org
            await _persist_violations(result, media, db, org_id)
    except Exception:
        pass  # don't fail inference if persistence fails

    realtime_bus.publish(
        {
            "type": "inference.completed",
            "request_id": result.request_id,
            "camera_id": result.camera_id,
            "violation_count": len(result.violations),
            "review_required": result.review_required,
            "evidence_packet_id": result.evidence_packet_id,
        }
    )
    return payload


@router.get("/events")
async def process_events() -> StreamingResponse:
    return StreamingResponse(realtime_bus.subscribe(), media_type="text/event-stream")
