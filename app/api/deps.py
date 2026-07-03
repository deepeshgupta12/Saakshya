"""FastAPI shared dependencies (docs/09 §6, docs/10 §0 local-first note).

Auth tiers (M7):
  - UserDep        — public stub for V1 read-only routes (no token required).
  - AuthUserDep    — real JWT validation; 401 if missing/expired (V2 gated routes).
  - OptionalAuthDep — JWT if present, None if absent (hydrates user context when logged in).
  - as_of resolver: returns latest session date from DB when not specified.
  - TimescaleDB session (analytics) + MongoDB (docs): context-managed per request.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
from typing import TYPE_CHECKING, Annotated

import psycopg
from fastapi import Depends, Header, HTTPException, Query, status
from jose import JWTError

from app.auth.tokens import decode_access_token
from app.storage.postgres import get_connection

if TYPE_CHECKING:
    from pymongo.database import Database

# ---------------------------------------------------------------------------
# Database sessions (polyglot, D-059): TimescaleDB analytics + MongoDB documents
# ---------------------------------------------------------------------------

def get_db() -> Generator[psycopg.Connection, None, None]:
    """Yield an open TimescaleDB connection (analytics routers); closes on teardown."""
    with get_connection() as conn:
        yield conn


DbDep = Annotated[psycopg.Connection, Depends(get_db)]


def get_mongo() -> "Database":
    """Return the MongoDB database (user/app routers: portfolios, alerts, strategies…)."""
    from app.storage.mongodb import get_db as _mongo_db  # noqa: PLC0415

    return _mongo_db()


MongoDep = Annotated["Database", Depends(get_mongo)]


# ---------------------------------------------------------------------------
# as_of resolver
# ---------------------------------------------------------------------------

def resolve_as_of(
    conn: DbDep,
    date_param: str | None = Query(default=None, alias="date"),
) -> date | None:
    """Resolve the ?date= param to a session_date.

    Returns the requested date if provided, otherwise the latest available
    session_date in daily_ohlc (None if no data at all).
    """
    if date_param:
        try:
            return date.fromisoformat(date_param)
        except ValueError:
            return None
    row = conn.execute("SELECT max(session_date) FROM daily_ohlc").fetchone()
    return row[0] if row and row[0] is not None else None


AsOfDep = Annotated[date | None, Depends(resolve_as_of)]


# ---------------------------------------------------------------------------
# Auth — stub (V1 public routes) + real JWT (V2 gated routes)
# ---------------------------------------------------------------------------

class AuthUser:
    """Authenticated user extracted from a validated JWT."""
    def __init__(self, user_id: str, plan: str) -> None:
        self.user_id = user_id
        self.plan    = plan
        self.scopes: list[str] = []

    @property
    def is_premium(self) -> bool:
        return self.plan in ("premium", "pro", "enterprise")


class _StubUser(AuthUser):
    """Local-first stub — all V1 public read routes work without any token."""
    def __init__(self) -> None:
        super().__init__(user_id="local", plan="pro")


def get_current_user() -> _StubUser:
    """Public stub for V1 read-only routes — no token required."""
    return _StubUser()


def _bearer_token(authorization: str | None = Header(default=None)) -> str | None:
    """Extract raw Bearer token from Authorization header, or None."""
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:]
    return None


def _require_auth(token: str | None = Depends(_bearer_token)) -> AuthUser:
    """JWT validation dep — raises 401 if token is missing, expired, or invalid."""
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return AuthUser(user_id=payload["sub"], plan=payload.get("plan", "free"))


def _optional_auth(token: str | None = Depends(_bearer_token)) -> AuthUser | None:
    """Optional JWT — returns AuthUser if valid token present, None otherwise."""
    if token is None:
        return None
    try:
        payload = decode_access_token(token)
        return AuthUser(user_id=payload["sub"], plan=payload.get("plan", "free"))
    except JWTError:
        return None


# Type aliases for route signatures
UserDep        = Annotated[_StubUser, Depends(get_current_user)]   # V1 public (unchanged)
AuthUserDep    = Annotated[AuthUser,  Depends(_require_auth)]       # V2 JWT-required
OptionalAuthDep = Annotated[AuthUser | None, Depends(_optional_auth)]  # V2 optional
