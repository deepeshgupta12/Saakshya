"""Auth endpoints — POST /api/auth/{register|login|refresh|logout} (docs/10 §1, docs/23 §1).

Local-first: HS256 JWT, Argon2id passwords, DuckDB token store.
Mode-A compliant: no financial data, no PII beyond email + display_name.
Rate limits: 5/min register (IP), 10/min login (IP).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from app.api.deps import AuthUserDep, DbDep
from app.api.envelope import ok
from app.api.ratelimit import auth_rate_limit_dep
from app.auth.passwords import hash_password, verify_password, MIN_LENGTH
from app.auth.tokens import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    make_token_id,
    make_family_id,
    refresh_expiry,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Request / Response models ──────────────────────────────────────────────

class RegisterBody(BaseModel):
    email: EmailStr
    password: str
    display_name: str = ""
    consent_not_advice: bool = False
    consent_ai_use: bool = False


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


# ── Helpers ────────────────────────────────────────────────────────────────

def _issue_token_pair(conn: Any, user_id: str, plan: str) -> dict[str, Any]:
    """Create access + refresh tokens, persist refresh to DB, return the pair."""
    access = create_access_token(user_id, plan)
    raw_refresh, refresh_hash = create_refresh_token()
    token_id  = make_token_id()
    family_id = make_family_id()
    expires   = refresh_expiry()
    conn.execute(
        "INSERT INTO refresh_tokens (token_id, family_id, user_id, token_hash, expires_at) "
        "VALUES (?, ?, ?, ?, ?)",
        [token_id, family_id, user_id, refresh_hash, expires],
    )
    return {
        "access_token":  access,
        "refresh_token": raw_refresh,
        "expires_in":    900,
        "plan":          plan,
    }


# ── Routes ─────────────────────────────────────────────────────────────────

@router.post("/register", status_code=201)
def register(
    body:    RegisterBody,
    request: Request,
    conn:    DbDep,
    _rl:     None = Depends(auth_rate_limit_dep),
) -> dict[str, Any]:
    # Compliance gate: consent required before account creation (SPEC §6.7).
    if not body.consent_not_advice or not body.consent_ai_use:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must acknowledge the not-advice and AI-use notices to register.",
        )
    if len(body.password) < MIN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Password must be at least {MIN_LENGTH} characters.",
        )
    # Duplicate email check (email is UNIQUE in users table).
    existing = conn.execute(
        "SELECT user_id FROM users WHERE email = ?", [str(body.email)]
    ).fetchone()
    if existing:
        # Non-leaking error — don't distinguish existing vs new account.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    user_id   = str(uuid.uuid4())
    pw_hash   = hash_password(body.password)
    plan      = "free"
    conn.execute(
        "INSERT INTO users (user_id, email, password_hash, display_name, plan) "
        "VALUES (?, ?, ?, ?, ?)",
        [user_id, str(body.email), pw_hash, body.display_name or str(body.email).split("@")[0], plan],
    )
    # Record consents (SPEC §6.7, docs/23 §1).
    for ctype in ("not_advice", "ai_use"):
        conn.execute(
            "INSERT INTO consents (consent_id, user_id, consent_type) VALUES (?, ?, ?)",
            [str(uuid.uuid4()), user_id, ctype],
        )
    tokens = _issue_token_pair(conn, user_id, plan)
    return ok({"user_id": user_id, "email": str(body.email), **tokens})


@router.post("/login")
def login(
    body:    LoginBody,
    request: Request,
    conn:    DbDep,
    _rl:     None = Depends(auth_rate_limit_dep),
) -> dict[str, Any]:
    row = conn.execute(
        "SELECT user_id, password_hash, plan FROM users WHERE email = ?",
        [str(body.email)],
    ).fetchone()
    # Constant-time response — same error whether email or password is wrong.
    _GENERIC_ERROR = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
    )
    if row is None:
        raise _GENERIC_ERROR
    user_id, pw_hash, plan = row
    if not verify_password(body.password, pw_hash):
        raise _GENERIC_ERROR
    tokens = _issue_token_pair(conn, user_id, plan)
    return ok(tokens)


@router.post("/refresh")
def refresh_token(
    body: RefreshBody,
    conn: DbDep,
) -> dict[str, Any]:
    incoming_hash = hash_refresh_token(body.refresh_token)
    row = conn.execute(
        "SELECT token_id, family_id, user_id, revoked, expires_at "
        "FROM refresh_tokens WHERE token_hash = ?",
        [incoming_hash],
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
    token_id, family_id, user_id, revoked, expires_at = row
    if revoked:
        # Replay detected — revoke entire family (docs/23 §1 reuse detection).
        conn.execute(
            "UPDATE refresh_tokens SET revoked = TRUE WHERE family_id = ?", [family_id]
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token replayed; session revoked.")
    now = datetime.now(timezone.utc)
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if now > expires_at:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired.")
    # Rotate: revoke old token, issue new pair in same family.
    conn.execute("UPDATE refresh_tokens SET revoked = TRUE WHERE token_id = ?", [token_id])
    user_row = conn.execute("SELECT plan FROM users WHERE user_id = ?", [user_id]).fetchone()
    plan = user_row[0] if user_row else "free"
    access = create_access_token(user_id, plan)
    raw_refresh, refresh_hash = create_refresh_token()
    new_token_id = make_token_id()
    expires = refresh_expiry()
    conn.execute(
        "INSERT INTO refresh_tokens (token_id, family_id, user_id, token_hash, expires_at) "
        "VALUES (?, ?, ?, ?, ?)",
        [new_token_id, family_id, user_id, refresh_hash, expires],
    )
    return ok({"access_token": access, "refresh_token": raw_refresh, "expires_in": 900, "plan": plan})


@router.post("/logout")
def logout(
    body: RefreshBody,
    conn: DbDep,
    _user: AuthUserDep,
) -> dict[str, Any]:
    incoming_hash = hash_refresh_token(body.refresh_token)
    conn.execute(
        "UPDATE refresh_tokens SET revoked = TRUE WHERE token_hash = ? AND user_id = ?",
        [incoming_hash, _user.user_id],
    )
    return ok({"ok": True})
