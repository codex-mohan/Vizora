from fastapi import APIRouter

from core.camera_state import CameraStateRegistry
from core.config import settings

router = APIRouter()
_registry = CameraStateRegistry(settings)


@router.get("")
async def list_cameras() -> dict:
    return {"cameras": []}


@router.get("/{camera_id}/mode")
async def camera_mode(camera_id: str) -> dict:
    state = _registry.get(camera_id)
    return {"camera_id": camera_id, "mode": state.mode.value}
