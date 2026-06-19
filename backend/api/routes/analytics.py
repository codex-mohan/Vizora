from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/summary")
async def summary() -> dict:
    return {"total_violations": 0, "by_type": {}, "by_hour": {}, "trend": []}


@router.get("/hotspots")
async def hotspots(
    limit: int = Query(10, ge=1, le=100),
) -> list[dict]:
    return []
