from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/profile")
async def active_model_profile(request: Request) -> dict:
    profile = request.app.state.model_profile
    return profile.model_dump(mode="json")
