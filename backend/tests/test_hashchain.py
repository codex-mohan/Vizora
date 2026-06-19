"""Tests for evidence hash chain."""

from __future__ import annotations

import pytest

from pipeline.evidence.hashchain import chain_hash, sha256_bytes, sha256_json


class TestSha256Bytes:
    def test_deterministic(self) -> None:
        data = b"hello world"
        assert sha256_bytes(data) == sha256_bytes(data)

    def test_different_inputs_different_hashes(self) -> None:
        assert sha256_bytes(b"hello") != sha256_bytes(b"world")

    def test_returns_hex_string(self) -> None:
        h = sha256_bytes(b"test")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestSha256Json:
    def test_deterministic(self) -> None:
        payload = {"b": 2, "a": 1}
        assert sha256_json(payload) == sha256_json(payload)

    def test_key_order_invariant(self) -> None:
        assert sha256_json({"a": 1, "b": 2}) == sha256_json({"b": 2, "a": 1})

    def test_different_payloads_different_hashes(self) -> None:
        assert sha256_json({"a": 1}) != sha256_json({"a": 2})


class TestChainHash:
    def test_deterministic(self) -> None:
        h = chain_hash("prev", "payload")
        assert h == chain_hash("prev", "payload")

    def test_different_previous_hash_changes_result(self) -> None:
        assert chain_hash("prev1", "payload") != chain_hash("prev2", "payload")

    def test_different_payload_hash_changes_result(self) -> None:
        assert chain_hash("prev", "payload1") != chain_hash("prev", "payload2")

    def test_chain_linkage(self) -> None:
        h0 = sha256_bytes(b"genesis")
        h1 = chain_hash(h0, sha256_json({"frame": 1}))
        h2 = chain_hash(h1, sha256_json({"frame": 2}))
        assert h1 != h2
        assert len(h1) == 64
        assert len(h2) == 64
