from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ViolationType(str, Enum):
    HELMET = "HELMET"
    SEATBELT = "SEATBELT"
    TRIPLE_RIDE = "TRIPLE_RIDE"
    WRONG_SIDE = "WRONG_SIDE"
    STOP_LINE = "STOP_LINE"
    RED_LIGHT = "RED_LIGHT"
    ILLEGAL_PARKING = "ILLEGAL_PARKING"


class Violation(BaseModel):
    id: str
    violation_type: ViolationType
    confidence: float = Field(ge=0.0, le=1.0)
    camera_id: str
    location: str
    timestamp: datetime
    vehicle_class: str | None = None
    plate: str | None = None
    plate_hash: str | None = None
    description: str | None = None
    evidence_packet_id: str | None = None
    review_required: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    status: str = "pending"


class ViolationList(BaseModel):
    items: list[Violation]
    total: int
    page: int
    size: int
