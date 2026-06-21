"""Camera routes with real DB queries."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUser, get_current_user, require_role
from core.database import get_db
from core.models.camera import Camera

router = APIRouter()


class CameraCreate(BaseModel):
    name: str
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    source_type: str | None = None
    source_url: str | None = None
    model_profile: str = "fast"
    enabled: bool = True
    scene_config: dict | None = None


class CameraUpdate(BaseModel):
    name: str | None = None
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    source_type: str | None = None
    source_url: str | None = None
    model_profile: str | None = None
    enabled: bool | None = None
    scene_config: dict | None = None
    status: str | None = None


class ModeUpdate(BaseModel):
    mode: str


def _cam_dict(c: Camera) -> dict:
    return {
        "id": str(c.id),
        "name": c.name,
        "location_name": c.location_name,
        "latitude": c.latitude,
        "longitude": c.longitude,
        "source_type": c.source_type,
        "source_url": c.source_url,
        "model_profile": c.model_profile,
        "enabled": c.enabled,
        "current_mode": c.current_mode,
        "status": c.status,
        "scene_config": c.scene_config,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


@router.get("")
async def list_cameras(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(Camera)
        .where(Camera.org_id == current_user.org_id)
        .order_by(Camera.created_at.desc())
    )
    cameras = result.scalars().all()
    return [_cam_dict(c) for c in cameras]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_camera(
    body: CameraCreate,
    current_user: CurrentUser = Depends(require_role("admin", "reviewer")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    camera = Camera(
        org_id=current_user.org_id,
        name=body.name,
        location_name=body.location_name,
        latitude=body.latitude,
        longitude=body.longitude,
        source_type=body.source_type,
        source_url=body.source_url,
        model_profile=body.model_profile,
        enabled=body.enabled,
        scene_config=body.scene_config,
    )
    db.add(camera)
    await db.flush()
    await db.refresh(camera)
    return _cam_dict(camera)


@router.get("/{camera_id}")
async def get_camera(
    camera_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Camera).where(
            Camera.id == camera_id,
            Camera.org_id == current_user.org_id,
        )
    )
    camera = result.scalar_one_or_none()
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return _cam_dict(camera)


@router.patch("/{camera_id}")
async def update_camera(
    camera_id: uuid.UUID,
    body: CameraUpdate,
    request: Request,
    current_user: CurrentUser = Depends(require_role("admin", "reviewer")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Camera).where(
            Camera.id == camera_id,
            Camera.org_id == current_user.org_id,
        )
    )
    camera = result.scalar_one_or_none()
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(camera, field, value)

    camera.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(camera)

    from pipeline.ingest.worker import ingestion_manager
    pipeline = request.app.state.inference_pipeline
    cam_id = str(camera.id)

    if camera.enabled and camera.source_url:
        await ingestion_manager.start_camera(
            camera_id=cam_id,
            camera_name=camera.name,
            source_type=camera.source_type or "http_snapshot",
            source_url=camera.source_url,
            pipeline=pipeline,
            org_id=str(camera.org_id),
        )
    else:
        await ingestion_manager.stop_camera(cam_id)

    return _cam_dict(camera)


@router.patch("/{camera_id}/mode")
async def update_camera_mode(
    camera_id: uuid.UUID,
    body: ModeUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Camera).where(
            Camera.id == camera_id,
            Camera.org_id == current_user.org_id,
        )
    )
    camera = result.scalar_one_or_none()
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")

    camera.current_mode = body.mode
    camera.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(camera)
    return {"camera_id": str(camera.id), "mode": camera.current_mode}


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_camera(
    camera_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Camera).where(
            Camera.id == camera_id,
            Camera.org_id == current_user.org_id,
        )
    )
    camera = result.scalar_one_or_none()
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")

    camera.status = "maintenance"
    camera.updated_at = datetime.now(timezone.utc)

    from pipeline.ingest.worker import ingestion_manager
    await ingestion_manager.stop_camera(str(camera_id))
