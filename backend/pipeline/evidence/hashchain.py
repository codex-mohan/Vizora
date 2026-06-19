"""Tamper-evident hash-chain helpers for evidence packets."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(encoded)


def chain_hash(previous_hash: str, payload_hash: str) -> str:
    return sha256_bytes(f"{previous_hash}:{payload_hash}".encode("utf-8"))
