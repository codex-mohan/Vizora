"""FastAPI application entry point."""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import analytics, auth, cameras, evidence, health, models, process, violations
from core.config import BACKEND_ROOT, settings
from core.database import init_db
from core.model_registry import load_model_profiles
from pipeline.infer import InferencePipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
    force=True,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    profiles = load_model_profiles(BACKEND_ROOT / settings.model_profiles_path)
    app.state.model_profiles = profiles
    app.state.model_profile = profiles.active()

    pipeline = InferencePipeline(settings, profiles.active())
    app.state.inference_pipeline = pipeline

    from pipeline.warmup import warmup_models
    warmup_models(profiles.active())

    from sqlalchemy import select
    from core.models.camera import Camera
    from core.database import async_session_factory
    from pipeline.ingest.worker import ingestion_manager

    async with async_session_factory() as db:
        result = await db.execute(
            select(Camera).where(Camera.enabled == True, Camera.source_url.isnot(None))
        )
        cameras = result.scalars().all()
        for cam in cameras:
            try:
                await ingestion_manager.start_camera(
                    camera_id=str(cam.id),
                    camera_name=cam.name,
                    source_type=cam.source_type or "http_snapshot",
                    source_url=cam.source_url,
                    pipeline=pipeline,
                    org_id=str(cam.org_id),
                )
            except Exception as e:
                logger.warning("Failed to start ingestion for camera %s: %s", cam.name, e)

    logger.info("Pipeline ready — %d cameras with active ingestion", len(ingestion_manager.active_cameras()))
    yield

    await ingestion_manager.stop_all()

app = FastAPI(
    title="Traffic Violation Detection System",
    description="Automated photo identification and classification of traffic violations",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(violations.router, prefix="/api/violations", tags=["violations"])
app.include_router(evidence.router, prefix="/api/evidence", tags=["evidence"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(cameras.router, prefix="/api/cameras", tags=["cameras"])
app.include_router(models.router, prefix="/api/models", tags=["models"])
app.include_router(process.router, prefix="/api/process", tags=["process"])
