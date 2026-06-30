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
        "FROM scanner_results WHERE session_date = ? AND as_of_version = 1 "
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

    advance_count = _momentum_count(conn, as_of, min_score=60.0)
    decline_count = _momentum_count(conn, as_of, max_score=40.0)

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


def _momentum_count(conn: Any, session_date: Any, *, min_score: float | None = None,
                    max_score: float | None = None) -> int:
    where = "scanner='momentum' AND session_date=? AND as_of_version=1"
    params: list[object] = [session_date]
    if min_score is not None:
        where += " AND composite_score >= ?"
        params.append(min_score)
    if max_score is not None:
        where += " AND composite_score <= ?"
        params.append(max_score)
    row = conn.execute(
        f"SELECT count(*) FROM scanner_results WHERE {where}", params
    ).fetchone()
    return int(row[0]) if row else 0
