"""Market-level endpoints (docs/10 §1).

GET /v1/market/summary   — breadth snapshot for the last (or a given) session date.

Mode-A compliant — no entry/target/SL, no candidate labels, no directive language.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.deps import AsOfDep, DbDep, UserDep
from app.api.envelope import ok
from app.api.errors import DataSuppressedError, NotFoundError
from app.api.ratelimit import read_rate_limit_dep

router = APIRouter(prefix="/v1/market", tags=["market"])


@router.get("/summary")
def get_market_summary(
    request:  Request,
    conn:     DbDep,
    as_of:    AsOfDep,
    _user:    UserDep,
    _rl:      None = Depends(read_rate_limit_dep),
) -> dict[str, Any]:
    if as_of is None:
        raise NotFoundError("No session data available yet. Run the pipeline first.")

    # Aggregate scanner counts and breadth stats from scanner_results.
    rows = conn.execute(
        "SELECT scanner, count(*) as cnt, avg(composite_score) as avg_score "
        "FROM scanner_results WHERE session_date = %s AND as_of_version = 1 "
        "GROUP BY scanner ORDER BY scanner",
        [as_of],
    ).fetchall()

    if not rows:
        raise DataSuppressedError(
            f"No scanner data for {as_of}. Run the pipeline first."
        )

    _LABELS = {
        "momentum":        "Momentum",
        "volume_breakout": "Volume Breakout",
        "rsi":             "RSI Conditions",
        "moving_average":  "Moving Average",
    }
    scanner_counts: dict[str, dict[str, object]] = {
        str(r[0]): {"count": int(r[1]), "label": _LABELS.get(str(r[0]), str(r[0]))}
        for r in rows
    }
    total_members: int = sum(int(r[1]) for r in rows)

    advance_count, decline_count = _ohlc_advance_decline(conn, as_of)

    data = {
        "session_date":   str(as_of),
        "total_members":  total_members,
        "advance_count":  advance_count,
        "decline_count":  decline_count,
        "scanner_counts": scanner_counts,
        "disclaimer":     "Not investment advice. Evidence-based analytics only.",
    }
    return ok(
        data,
        as_of=str(as_of),
        source="scanner_results",
    )


def _f(v: object) -> float | None:
    try:
        return round(float(v), 2)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _ohlc_advance_decline(conn: Any, session_date: Any) -> tuple[int, int]:
    """Compute advance/decline counts by comparing session_date vs previous session OHLC."""
    row = conn.execute(
        """
        WITH prev AS (
            SELECT stock_id, close_adj AS prev_close
            FROM daily_ohlc
            WHERE session_date = (
                SELECT MAX(session_date) FROM daily_ohlc
                WHERE session_date < %s AND as_of_version = 1
            ) AND as_of_version = 1
        )
        SELECT
            SUM(CASE WHEN o.close_adj > p.prev_close THEN 1 ELSE 0 END),
            SUM(CASE WHEN o.close_adj < p.prev_close THEN 1 ELSE 0 END)
        FROM daily_ohlc o
        JOIN prev p ON p.stock_id = o.stock_id
        WHERE o.session_date = %s AND o.as_of_version = 1
        """,
        [session_date, session_date],
    ).fetchone()
    if row is None or row[0] is None:
        return 0, 0
    return int(row[0]), int(row[1])
