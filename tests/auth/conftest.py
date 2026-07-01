"""Shared fixtures for auth + IDOR test suite (docs/23 §1–§2, M7)."""

from __future__ import annotations

import uuid
import pytest
import duckdb
from fastapi.testclient import TestClient

from app.storage.duckdb import init_schema
from app.auth.passwords import hash_password
from app.auth.tokens import create_access_token, create_refresh_token, hash_refresh_token, refresh_expiry
from app.api import deps
from app.main import app


def _make_user(conn, email: str, plan: str = "free") -> tuple[str, str]:
    """Insert a test user and return (user_id, access_token)."""
    uid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO users (user_id, email, password_hash, display_name, plan) VALUES (?,?,?,?,?)",
        [uid, email, hash_password("Passw0rd!secure1"), "Test", plan],
    )
    token = create_access_token(uid, plan)
    return uid, token


def _make_refresh(conn, user_id: str) -> tuple[str, str]:
    """Insert a refresh token and return (raw_token, family_id)."""
    raw, hashed = create_refresh_token()
    tid = str(uuid.uuid4())
    fid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO refresh_tokens (token_id, family_id, user_id, token_hash, expires_at) VALUES (?,?,?,?,?)",
        [tid, fid, user_id, hash_refresh_token(raw), refresh_expiry()],
    )
    return raw, fid


@pytest.fixture
def mem_db():
    conn = duckdb.connect(":memory:")
    init_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def client(mem_db):
    def _override_db():
        yield mem_db

    app.dependency_overrides[deps.get_db] = _override_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def two_users(mem_db):
    """Return ((uid_a, token_a), (uid_b, token_b)) for IDOR tests."""
    a = _make_user(mem_db, "alice@test.com")
    b = _make_user(mem_db, "bob@test.com")
    return a, b
