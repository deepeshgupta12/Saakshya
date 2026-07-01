"""Auth endpoint tests — register, login, refresh, logout, token expiry (docs/23 §1).

Tests:
- POST /api/auth/register: happy path, duplicate email, missing consent
- POST /api/auth/login: correct creds, wrong password, nonexistent email
  → indistinguishable responses
- POST /api/auth/refresh: rotation, replay detection → family revoke
- POST /api/auth/logout: revokes token; replayed token → 401
- Unsigned/expired JWT → 401 on protected endpoints
"""

from __future__ import annotations

import uuid
import time
import pytest
from jose import jwt

from tests.auth.conftest import _make_user, _make_refresh


# ── Registration ──────────────────────────────────────────────────────────────

def test_register_happy_path(client, mem_db):
    resp = client.post("/api/auth/register", json={
        "email": "new@test.com",
        "password": "Str0ngPassw0rd!",
        "consent_not_advice": True,
        "consent_ai_use": True,
    })
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["plan"] == "free"
    # Consent rows recorded
    rows = mem_db.execute(
        "SELECT consent_type FROM consents WHERE user_id = ? ORDER BY consent_type", [data["user_id"]]
    ).fetchall()
    assert [r[0] for r in rows] == ["ai_use", "not_advice"]


def test_register_missing_consent_blocked(client):
    resp = client.post("/api/auth/register", json={
        "email": "a@test.com",
        "password": "Str0ngPassw0rd!",
        "consent_not_advice": False,
        "consent_ai_use": True,
    })
    assert resp.status_code == 422


def test_register_weak_password_blocked(client):
    resp = client.post("/api/auth/register", json={
        "email": "a@test.com",
        "password": "short",
        "consent_not_advice": True,
        "consent_ai_use": True,
    })
    assert resp.status_code == 422


def test_register_duplicate_email_returns_409(client):
    body = {"email": "dup@test.com", "password": "Str0ngPassw0rd!", "consent_not_advice": True, "consent_ai_use": True}
    client.post("/api/auth/register", json=body)
    resp = client.post("/api/auth/register", json=body)
    assert resp.status_code == 409


# ── Login ─────────────────────────────────────────────────────────────────────

def test_login_correct_credentials(client, mem_db):
    _make_user(mem_db, "login@test.com")
    resp = client.post("/api/auth/login", json={"email": "login@test.com", "password": "Passw0rd!secure1"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_wrong_password_same_as_nonexistent(client, mem_db):
    """Wrong password and nonexistent email must return indistinguishable 401 (docs/23 §1)."""
    _make_user(mem_db, "exists@test.com")
    resp_wrong = client.post("/api/auth/login", json={"email": "exists@test.com", "password": "WrongPassword!!"})
    resp_ghost = client.post("/api/auth/login", json={"email": "ghost@test.com",  "password": "AnyPassword123!"})
    assert resp_wrong.status_code == 401
    assert resp_ghost.status_code == 401
    # Same error message — no account-existence leakage (envelope format)
    assert resp_wrong.json()["error"]["message"] == resp_ghost.json()["error"]["message"]  # type: ignore[index]


# ── Refresh / rotation ────────────────────────────────────────────────────────

def test_refresh_rotates_token(client, mem_db):
    uid, _ = _make_user(mem_db, "ref@test.com")
    raw, _ = _make_refresh(mem_db, uid)
    resp = client.post("/api/auth/refresh", json={"refresh_token": raw})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "access_token" in data
    new_raw = data["refresh_token"]
    assert new_raw != raw  # rotated


def test_refresh_replay_revokes_family(client, mem_db):
    """Replaying an already-used refresh token must revoke the entire family (docs/23 §1)."""
    uid, _ = _make_user(mem_db, "replay@test.com")
    raw, fid = _make_refresh(mem_db, uid)

    # First use — should succeed and rotate
    r1 = client.post("/api/auth/refresh", json={"refresh_token": raw})
    assert r1.status_code == 200

    # Replay the same (now revoked) token → should revoke the whole family
    r2 = client.post("/api/auth/refresh", json={"refresh_token": raw})
    assert r2.status_code == 401

    # The new token issued in r1 should also be revoked (family revocation)
    new_raw = r1.json()["data"]["refresh_token"]
    r3 = client.post("/api/auth/refresh", json={"refresh_token": new_raw})
    assert r3.status_code == 401


def test_refresh_invalid_token_rejected(client):
    resp = client.post("/api/auth/refresh", json={"refresh_token": "not-a-valid-token"})
    assert resp.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

def test_logout_revokes_refresh_token(client, mem_db):
    uid, access = _make_user(mem_db, "logout@test.com")
    raw, _ = _make_refresh(mem_db, uid)
    resp = client.post(
        "/api/auth/logout",
        json={"refresh_token": raw},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 200
    # Refresh is now revoked — cannot be replayed
    r2 = client.post("/api/auth/refresh", json={"refresh_token": raw})
    assert r2.status_code == 401


# ── JWT guards ────────────────────────────────────────────────────────────────

def test_protected_endpoint_no_token_returns_401(client):
    resp = client.get("/api/watchlists")
    assert resp.status_code == 401


def test_protected_endpoint_unsigned_token_returns_401(client):
    forged = jwt.encode({"sub": "hacker", "plan": "pro", "type": "access"}, "wrong-secret", algorithm="HS256")
    resp = client.get("/api/watchlists", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 401


def test_protected_endpoint_wrong_token_type_returns_401(client, mem_db):
    """A refresh-shaped JWT (type='refresh') must not grant access."""
    from app.config import get_settings
    forged = jwt.encode(
        {"sub": "uid", "plan": "free", "type": "refresh"},
        get_settings().secret_key, algorithm="HS256",
    )
    resp = client.get("/api/watchlists", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 401
