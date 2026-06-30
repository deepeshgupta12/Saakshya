"""FastAPI shared dependencies (docs/09 §6, docs/10 §0 local-first note).

Local-first stubs:
  - Auth/plan: no-op (single-user dev); wired so production can swap in JWT validation.
  - as_of resolver: returns latest session date from DB when not specified.
  - DuckDB session: context-managed connection per request.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
from typing import Annotated

import duckdb
from fastapi import Depends, Query

from app.storage.duckdb import get_connection

# ---------------------------------------------------------------------------
# DuckDB session
# ---------------------------------------------------------------------------

def get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Yield an open DuckDB connection; closes on request teardown."""
    with get_connection() as conn:
        yield conn


DbDep = Annotated[duckdb.DuckDBPyConnection, Depends(get_db)]


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
# Stubbed auth / plan (local-first; production: replace with JWT validation)
# ---------------------------------------------------------------------------

class _StubUser:
    user_id: str = "local"
    plan:    str = "pro"      # all features open in local-first mode
    scopes:  list[str] = []


def get_current_user() -> _StubUser:
    """Stubbed auth — always returns a local super-user. Swap for JWT in production."""
    return _StubUser()


UserDep = Annotated[_StubUser, Depends(get_current_user)]
