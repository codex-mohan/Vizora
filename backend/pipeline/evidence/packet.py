"""Evidence packet generation."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from pipeline.contracts import InferenceResult, MediaInput
from pipeline.evidence.hashchain import chain_hash, sha256_bytes, sha256_json


class EvidencePacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"ev-{uuid4().hex}")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    media_hash: str
    metadata_hash: str
    chain_hash: str
    public_redacted: bool = True


class EvidencePacketBuilder:
    def build(self, media: MediaInput, result_without_packet: dict) -> EvidencePacket:
        media_hash = sha256_bytes(media.data)
        metadata_hash = sha256_json(result_without_packet)
        return EvidencePacket(
            media_hash=media_hash,
            metadata_hash=metadata_hash,
            chain_hash=chain_hash(media_hash, metadata_hash),
        )

    def attach(self, media: MediaInput, result: InferenceResult) -> EvidencePacket:
        payload = result.model_dump(mode="json")
        payload.pop("evidence_packet_id", None)
        return self.build(media, payload)
