"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import analytics, auth, cameras, evidence, health, models, process, violations
from core.config import BACKEND_ROOT, settings
from core.database import init_db
from core.model_registry import load_model_profiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    profiles = load_model_profiles(BACKEND_ROOT / settings.model_profiles_path)
    app.state.model_profiles = profiles
    app.state.model_profile = profiles.active()
    yield

app = FastAPI(
    title="Traffic Violation Detection System",
    description="Automated photo identification and classification of traffic violations",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
