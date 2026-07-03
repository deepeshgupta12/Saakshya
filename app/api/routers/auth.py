"""Auth endpoints — POST /api/auth/{register|login|refresh|logout|oauth/google}.

Local-first: HS256 JWT, Argon2id passwords, MongoDB token store (D-059).
Mode-A compliant: no financial data, no PII beyond email + display_name.
Rate limits: auth_rate_limit_dep on register/login.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from pydantic import BaseModel, EmailStr
from pymongo.database import Database

from app.api.deps import AuthUserDep, MongoDep
from app.api.envelope import ok
from app.api.ratelimit import auth_rate_limit_dep
from app.auth.oauth import get_or_create_google_user, validate_google_id_token
from app.auth.passwords import MIN_LENGTH, hash_password, verify_password
from app.auth.tokens import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    make_family_id,
    make_token_id,
    refresh_expiry,
)
from app.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


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


class GoogleOAuthBody(BaseModel):
    id_token: str


def _issue_token_pair(mongo: Database, user_id: str, plan: str) -> dict[str, object]:
    """Create access + refresh tokens, persist the refresh token to Mongo."""
    access = create_access_token(user_id, plan)
    raw_refresh, refresh_hash = create_refresh_token()
    mongo.refresh_tokens.insert_one({
        "token_id":   make_token_id(),
        "family_id":  make_family_id(),
        "user_id":    user_id,
        "token_hash": refresh_hash,
        "revoked":    False,
        "issued_at":  datetime.now(tz=timezone.utc),
        "expires_at": refresh_expiry(),
    })
    return {"access_token": access, "refresh_token": raw_refresh, "expires_in": 900, "plan": plan}


@router.post("/register", status_code=201)
def register(
    body: RegisterBody,
    request: Request,
    mongo: MongoDep,
    _rl: None = Depends(auth_rate_limit_dep),
) -> dict[str, object]:
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
    if mongo.users.find_one({"email": str(body.email)}, {"user_id": 1}):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    user_id = str(uuid.uuid4())
    now = datetime.now(tz=timezone.utc)
    mongo.users.insert_one({
        "user_id": user_id, "email": str(body.email),
        "password_hash": hash_password(body.password),
        "display_name": body.display_name or str(body.email).split("@")[0],
        "plan": "free", "created_at": now, "updated_at": now,
    })
    mongo.consents.insert_many([
        {"consent_id": str(uuid.uuid4()), "user_id": user_id,
         "consent_type": ctype, "granted_at": now}
        for ctype in ("not_advice", "ai_use")
    ])
    tokens = _issue_token_pair(mongo, user_id, "free")
    return ok({"user_id": user_id, "email": str(body.email), **tokens})


@router.post("/login")
def login(
    body: LoginBody,
    request: Request,
    mongo: MongoDep,
    _rl: None = Depends(auth_rate_limit_dep),
) -> dict[str, object]:
    doc = mongo.users.find_one({"email": str(body.email)})
    generic_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password."
    )
    if doc is None or not verify_password(body.password, doc.get("password_hash") or ""):
        raise generic_error
    return ok(_issue_token_pair(mongo, doc["user_id"], doc.get("plan", "free")))


@router.post("/refresh")
def refresh_token(body: RefreshBody, mongo: MongoDep) -> dict[str, object]:
    incoming_hash = hash_refresh_token(body.refresh_token)
    doc = mongo.refresh_tokens.find_one({"token_hash": incoming_hash})
    if doc is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
    if doc.get("revoked"):
        # Replay detected — revoke the whole family (docs/23 §1 reuse detection).
        mongo.refresh_tokens.update_many(
            {"family_id": doc["family_id"]}, {"$set": {"revoked": True}}
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token replayed; session revoked.")
    now = datetime.now(timezone.utc)
    expires_at = doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if now > expires_at:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired.")
    # Rotate: revoke old, issue new pair in the same family.
    mongo.refresh_tokens.update_one({"token_id": doc["token_id"]}, {"$set": {"revoked": True}})
    user = mongo.users.find_one({"user_id": doc["user_id"]}, {"plan": 1})
    plan = user["plan"] if user else "free"
    access = create_access_token(doc["user_id"], plan)
    raw_refresh, refresh_hash = create_refresh_token()
    mongo.refresh_tokens.insert_one({
        "token_id":   make_token_id(),
        "family_id":  doc["family_id"],
        "user_id":    doc["user_id"],
        "token_hash": refresh_hash,
        "revoked":    False,
        "issued_at":  now,
        "expires_at": refresh_expiry(),
    })
    return ok({"access_token": access, "refresh_token": raw_refresh, "expires_in": 900, "plan": plan})


@router.post("/oauth/google", status_code=200)
def oauth_google(body: GoogleOAuthBody, mongo: MongoDep) -> dict[str, object]:
    """Validate a Google ID token and return our JWT pair (503 if unconfigured)."""
    client_id: str | None = getattr(get_settings(), "google_client_id", None)
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured on this server.",
        )
    try:
        claims = validate_google_id_token(body.id_token, client_id)
    except (ValueError, JWTError, Exception) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google ID token: {exc}",
        ) from exc
    user_id, plan = get_or_create_google_user(mongo, claims)
    tokens = _issue_token_pair(mongo, user_id, plan)
    return ok({"user_id": user_id, "email": claims.get("email", ""), **tokens})


@router.post("/logout")
def logout(body: RefreshBody, mongo: MongoDep, _user: AuthUserDep) -> dict[str, object]:
    incoming_hash = hash_refresh_token(body.refresh_token)
    mongo.refresh_tokens.update_one(
        {"token_hash": incoming_hash, "user_id": _user.user_id},
        {"$set": {"revoked": True}},
    )
    return ok({"ok": True})
