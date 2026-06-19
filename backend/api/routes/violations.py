from fastapi import APIRouter, Query

from api.schemas.violation import ViolationList, ViolationType

router = APIRouter()


@router.get("", response_model=ViolationList)
async def list_violations(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    violation_type: ViolationType | None = None,
    camera_id: str | None = None,
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
) -> ViolationList:
    return ViolationList(items=[], total=0, page=page, size=size)
