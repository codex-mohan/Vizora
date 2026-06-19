from fastapi import APIRouter

router = APIRouter()


@router.get("/{packet_id}")
async def get_evidence(packet_id: str) -> dict:
    return {"packet_id": packet_id, "frames": [], "metadata": {}, "description": None}
