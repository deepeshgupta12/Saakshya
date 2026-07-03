"""Daily AI call ceiling with graceful degradation (docs/14 §3, SPEC §6.8).

When the ceiling is reached, explain_* returns a templated (non-AI) fallback
assembled from the payload's permitted vocabulary — still grounded, still Mode-A.
The ceiling resets at midnight UTC (one row per calendar date in ai_daily_calls).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import psycopg

from app.config import get_settings

log = logging.getLogger(__name__)


def _today() -> str:
    return datetime.now(tz=timezone.utc).date().isoformat()


def allow_call(conn: psycopg.Connection) -> bool:
    """Return True when today's call count is below the configured ceiling."""
    ceiling = get_settings().ai_daily_call_ceiling
    today   = _today()
    row = conn.execute(
        "SELECT call_count FROM ai_daily_calls WHERE call_date = %s",
        [today],
    ).fetchone()
    count = row[0] if row else 0
    if count >= ceiling:
        log.warning("AI daily call ceiling (%d) reached for %s", ceiling, today)
        return False
    return True


def increment_calls(conn: psycopg.Connection, n: int = 1) -> None:
    """Increment today's call counter by n (default 1)."""
    today = _today()
    conn.execute(
        """
        INSERT INTO ai_daily_calls (call_date, call_count) VALUES (%s, %s)
        ON CONFLICT (call_date) DO UPDATE SET call_count = ai_daily_calls.call_count + excluded.call_count
        """,
        [today, n],
    )


def current_count(conn: psycopg.Connection) -> int:
    """Return today's call count (for monitoring / admin)."""
    today = _today()
    row = conn.execute(
        "SELECT call_count FROM ai_daily_calls WHERE call_date = %s",
        [today],
    ).fetchone()
    return row[0] if row else 0
