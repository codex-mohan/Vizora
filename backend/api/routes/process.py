from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from core.config import settings
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
