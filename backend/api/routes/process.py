from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, CurrentUser
from core.config import BACKEND_ROOT, settings
from core.database import async_session_factory, get_db
from core.models.camera import Camera
from core.models.violation import EvidencePacket, Plate, Violation
from core.realtime import realtime_bus
from pipeline.contracts import MediaInput, ProcessingMode
from pipeline.evidence.hashchain import chain_hash, sha256_bytes, sha256_json
from pipeline.infer import InferencePipeline
from pipeline.scene import load_scene_config

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_pipeline(request: Request) -> InferencePipeline:
    return request.app.state.inference_pipeline


def _bbox_payload(bbox) -> dict | None:
    return bbox.model_dump() if bbox else None


def _detection_payload(detection) -> dict:
    return {
        "id": detection.id,
        "label": detection.label.value,
        "bbox": _bbox_payload(detection.bbox),
        "confidence": detection.confidence,
        "metadata": detection.metadata,
    }


def _plate_payload(plate, plate_hash: str | None = None) -> dict:
    return {
        "plate_text": plate.plate_text,
        "plate_hash": plate_hash,
        "confidence": plate.confidence,
        "bbox": _bbox_payload(plate.bbox),
        "review_required": plate.review_required,
    }


def _best_plate(result) -> Any | None:
    if not result.plates:
        return None
    return max(result.plates, key=lambda p: p.confidence)


def _related_detections(result, object_ids: list[str]) -> list[dict]:
    wanted = set(object_ids)
    if not wanted:
        return []
    return [
        _detection_payload(detection)
        for detection in result.detections
        if detection.id in wanted
    ]


def _privacy_metadata() -> dict:
    return {
        "identity_policy": "vehicle_plate_and_event_context_only",
        "face_recognition_used": False,
        "face_embeddings_stored": False,
        "person_reidentification_used": False,
        "face_blur_enabled": settings.face_blur,
        "public_plate_redaction_enabled": settings.plate_redact_public,
    }


def _scene_road_segments(scene) -> list[dict]:
    return [
        {
            "id": segment.id,
            "label": segment.label,
            "coordinates": [
                [coordinate.longitude, coordinate.latitude]
                for coordinate in segment.coordinates
            ],
        }
        for segment in scene.road_segments
    ]


async def _persist_violations(
    result,
    media: MediaInput,
    db: AsyncSession,
    org_id: uuid.UUID,
) -> None:
    """Persist inference results to database and MinIO."""
    from core.storage import get_storage

    storage = get_storage()
    scene = load_scene_config(BACKEND_ROOT / settings.camera_scenes_path, media.camera_id)
    camera_record: Camera | None = None
    try:
        candidate_id = uuid.UUID(media.camera_id)
    except ValueError:
        candidate_id = None

    if candidate_id is not None:
        camera_result = await db.execute(
            select(Camera).where(Camera.id == candidate_id, Camera.org_id == org_id)
        )
        camera_record = camera_result.scalar_one_or_none()

    location_name = (
        camera_record.location_name
        if camera_record and camera_record.location_name
        else scene.location_name or media.camera_id
    )
    latitude = (
        camera_record.latitude
        if camera_record and camera_record.latitude is not None
        else scene.latitude
    )
    longitude = (
        camera_record.longitude
        if camera_record and camera_record.longitude is not None
        else scene.longitude
    )
    road_segments = _scene_road_segments(scene)
    primary_road_segment = road_segments[0] if len(road_segments) == 1 else None
    media_hash = sha256_bytes(media.data)

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

    # Persist each violation
    packet_base_id = uuid.UUID(result.evidence_packet_id.replace("ev-", "").replace("pending", uuid.uuid4().hex[:12]))
    for violation in result.violations:
        plate_text = None
        plate_hash = None
        best_plate = _best_plate(result)
        if best_plate and best_plate.plate_text:
            plate_text = best_plate.plate_text
            plate_hash = hashlib.sha256(plate_text.encode()).hexdigest()

        review_reasons = {
            *(r.value for r in result.review_reasons),
            *(r.value for r in violation.review_reasons),
        }

        plate_evidence = _plate_payload(best_plate, plate_hash) if best_plate else None
        related_detections = _related_detections(result, violation.object_ids)
        metadata_json = {
            "evidence_version": "1.0",
            "object_ids": violation.object_ids,
            "related_detections": related_detections,
            "evidence": violation.evidence,
            "bbox": _bbox_payload(violation.bbox),
            "plate": plate_evidence,
            "quality": result.quality.model_dump(mode="json"),
            "model_profile": result.model_profile,
            "review": {
                "required": result.review_required or violation.review_required,
                "reasons": sorted(review_reasons),
            },
            "location": {
                "camera_id": str(camera_record.id) if camera_record else media.camera_id,
                "location_name": location_name,
                "latitude": latitude,
                "longitude": longitude,
            },
            "privacy": _privacy_metadata(),
            "subject": {
                "primary_identifier": "plate_hash" if plate_hash else "camera_time_event",
                "plate_hash": plate_hash,
                "biometric_identifier_used": False,
                "track_scope": "single_event_or_clip_only",
            },
        }
        if road_segments:
            metadata_json["road_segments"] = road_segments
        if primary_road_segment:
            metadata_json["road_segment_id"] = primary_road_segment["id"]
            metadata_json["road_segment_label"] = primary_road_segment["label"]
            metadata_json["road_segment_coordinates"] = primary_road_segment["coordinates"]

        integrity_source = {
            "request_id": result.request_id,
            "camera_id": result.camera_id,
            "timestamp": result.timestamp.isoformat(),
            "violation_type": violation.violation_type.value,
            "confidence": violation.confidence,
            "metadata": metadata_json,
        }
        metadata_hash = sha256_json(integrity_source)
        packet_chain_hash = chain_hash(media_hash, metadata_hash)
        metadata_json["integrity"] = {
            "media_hash": media_hash,
            "metadata_hash": metadata_hash,
            "chain_hash": packet_chain_hash,
            "algorithm": "sha256",
        }

        db_violation = Violation(
            org_id=org_id,
            camera_id=camera_record.id if camera_record else None,
            violation_type=violation.violation_type.value,
            confidence=violation.confidence,
            status="pending",
            review_required=result.review_required or violation.review_required,
            review_reasons=sorted(review_reasons) or None,
            vehicle_class=None,
            plate_text=plate_text,
            plate_hash=plate_hash,
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            metadata_json=metadata_json,
        )
        db.add(db_violation)
        await db.flush()

        packet_id = (
            packet_base_id
            if len(result.violations) == 1
            else uuid.uuid5(uuid.NAMESPACE_URL, f"{result.evidence_packet_id}:{db_violation.id}")
        )
        evidence_packet = EvidencePacket(
            id=packet_id,
            violation_id=db_violation.id,
            frame_urls=[raw_key],
            annotated_frame_url=annotated_key,
            plate_crop_url=None,
            vlm_description=result.description,
            hash_chain=packet_chain_hash,
            metadata_json={
                "evidence_version": "1.0",
                "request_id": result.request_id,
                "camera_id": result.camera_id,
                "location_name": location_name,
                "latitude": latitude,
                "longitude": longitude,
                "model_profile": result.model_profile,
                "quality_score": result.quality.score,
                "detection_count": len(result.detections),
                "violation_type": violation.violation_type.value,
                "violation_confidence": violation.confidence,
                "violation_bbox": _bbox_payload(violation.bbox),
                "object_ids": violation.object_ids,
                "related_detections": related_detections,
                "plate": plate_evidence,
                "review": metadata_json["review"],
                "privacy": metadata_json["privacy"],
                "subject": metadata_json["subject"],
                "integrity": metadata_json["integrity"],
                "scan_review_required": result.review_required,
            },
        )
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
    current_user: CurrentUser = Depends(get_current_user),
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
            await _persist_violations(result, media, db, current_user.org_id)
    except Exception:
        logger.exception("Failed to persist inference result %s", result.request_id)

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
