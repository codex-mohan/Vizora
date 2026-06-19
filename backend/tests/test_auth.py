"""Tests for authentication utilities."""

from __future__ import annotations

from uuid import uuid4

import pytest

from core.auth import create_access_token, decode_access_token, hash_password, verify_password


class TestPasswordHashing:
    def test_hash_returns_non_empty_string(self) -> None:
        result = hash_password("mypassword")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_verify_correct_password(self) -> None:
        hashed = hash_password("securepass")
        assert verify_password("securepass", hashed) is True

    def test_verify_wrong_password(self) -> None:
        hashed = hash_password("securepass")
        assert verify_password("wrongpass", hashed) is False

    def test_different_passwords_different_hashes(self) -> None:
        h1 = hash_password("password1")
        h2 = hash_password("password2")
        assert h1 != h2


class TestJWTToken:
    def test_create_returns_non_empty_string(self) -> None:
        token = create_access_token(uuid4(), uuid4(), "reviewer")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_returns_correct_payload(self) -> None:
        user_id = uuid4()
        org_id = uuid4()
        token = create_access_token(user_id, org_id, "admin")
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["org_id"] == str(org_id)
        assert payload["role"] == "admin"

    def test_decode_invalid_token_returns_none(self) -> None:
        assert decode_access_token("not.a.valid.token") is None

    def test_token_contains_expected_claims(self) -> None:
        token = create_access_token(uuid4(), uuid4(), "analyst")
        payload = decode_access_token(token)
        assert payload is not None
        assert "sub" in payload
        assert "org_id" in payload
        assert "role" in payload
        assert "exp" in payload
