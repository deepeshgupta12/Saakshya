"""JWT access + rotating refresh tokens — docs/23 §1.

HS256 for local-first (single service). Production: swap to RS256 asymmetric keys.
Refresh token rotation: each use issues a new token; a replayed token revokes the family.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.config import get_settings

_ALGORITHM = "HS256"
_ACCESS_EXPIRE_MINUTES = 15
_REFRESH_EXPIRE_DAYS = 30


def _secret() -> str:
    return get_settings().secret_key


def create_access_token(user_id: str, plan: str, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "plan": plan,
        "iat": now,
        "exp": now + timedelta(minutes=_ACCESS_EXPIRE_MINUTES),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, _secret(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token. Raises JWTError on any failure."""
    payload = jwt.decode(token, _secret(), algorithms=[_ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Not an access token")
    return payload


def create_refresh_token() -> tuple[str, str]:
    """Return (raw_token, token_hash). Store only the hash; send the raw token to client."""
    raw = secrets.token_urlsafe(48)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def make_token_id() -> str:
    return str(uuid.uuid4())


def make_family_id() -> str:
    return str(uuid.uuid4())


def refresh_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=_REFRESH_EXPIRE_DAYS)
