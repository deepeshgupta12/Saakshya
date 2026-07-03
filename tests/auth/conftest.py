"""Shared fixtures for auth + IDOR test suite (docs/23 §1–§2, M7).

Auth data lives in MongoDB (D-059); user-scoped routes that hydrate from the analytics
core also get a TimescaleDB connection. Runs against the live Dockerized DBs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.auth.passwords import hash_password
from app.auth.tokens import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    refresh_expiry,
)
from app.main import app
from tests.dbutil import fresh_mongo, open_fresh_pg


def _make_user(db, email: str, plan: str = "free") -> tuple[str, str]:
    """Insert a test user (Mongo) and return (user_id, access_token)."""
    uid = str(uuid.uuid4())
    now = datetime.now(tz=timezone.utc)
    db.users.insert_one({
        "user_id": uid, "email": email,
        "password_hash": hash_password("Passw0rd!secure1"),
        "display_name": "Test", "plan": plan, "created_at": now, "updated_at": now,
    })
    return uid, create_access_token(uid, plan)


def _make_refresh(db, user_id: str) -> tuple[str, str]:
    """Insert a refresh token (Mongo) and return (raw_token, family_id)."""
    raw, _hashed = create_refresh_token()
    fid = str(uuid.uuid4())
    db.refresh_tokens.insert_one({
        "token_id": str(uuid.uuid4()), "family_id": fid, "user_id": user_id,
        "token_hash": hash_refresh_token(raw), "revoked": False,
        "issued_at": datetime.now(tz=timezone.utc), "expires_at": refresh_expiry(),
    })
    return raw, fid


@pytest.fixture
def mem_db():
    """The Mongo db (cleared) — the auth/user document store."""
    yield fresh_mongo()


@pytest.fixture
def pg_conn():
    """A fresh TimescaleDB connection for routes that hydrate the analytics core."""
    conn = open_fresh_pg()
    yield conn
    conn.close()


@pytest.fixture
def client(mem_db, pg_conn):
    def _db_override():
        yield pg_conn

    app.dependency_overrides[deps.get_db] = _db_override
    app.dependency_overrides[deps.get_mongo] = lambda: mem_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def two_users(mem_db):
    """Return ((uid_a, token_a), (uid_b, token_b)) for IDOR tests."""
    a = _make_user(mem_db, "alice@test.com")
    b = _make_user(mem_db, "bob@test.com")
    return a, b
