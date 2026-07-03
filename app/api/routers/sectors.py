"""Sector endpoints (docs/10 §3).

GET /v1/sectors          — ranked sector strength list
GET /v1/sectors/{slug}   — single sector detail

Mode-A compliant — descriptive analytics only, no directive language.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.deps import AsOfDep, DbDep, UserDep
from app.api.envelope import ok
from app.api.errors import NotFoundError
from app.api.ratelimit import read_rate_limit_dep

router = APIRouter(prefix="/v1/sectors", tags=["sectors"])


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _sector_rows(conn: Any, as_of: Any) -> list[dict[str, Any]]:
    """Aggregate sector change_pct and constituent count from daily_ohlc."""
    if as_of is None:
        # No pipeline run yet — return static sector list with no metrics.
        rows = conn.execute(
            "SELECT sector_id, name FROM sector_master ORDER BY name"
        ).fetchall()
        return [
            {
                "sector_id": f"SEC_{r[0]}",
                "name":       r[1],
                "slug":       _slug(r[1]),
                "strength_score": None,
                "change_pct":     None,
                "breadth":        None,
                "rank":           None,
            }
            for r in rows
        ]

    # Compute average change_pct per sector from daily_ohlc + previous session.
    sql = """
    WITH prev AS (
        SELECT o.stock_id, o.close_adj AS prev_close
        FROM daily_ohlc o
        WHERE o.session_date = (
            SELECT MAX(session_date)
            FROM daily_ohlc
            WHERE session_date < %s
              AND as_of_version = 1
        )
          AND o.as_of_version = 1
    ),
    cur AS (
        SELECT o.stock_id, o.close_adj
        FROM daily_ohlc o
        WHERE o.session_date = %s AND o.as_of_version = 1
    ),
    stock_chg AS (
        SELECT
            sm.sector_id,
            CASE
                WHEN p.prev_close IS NOT NULL AND p.prev_close <> 0
                THEN (c.close_adj - p.prev_close) / p.prev_close * 100.0
                ELSE NULL
            END AS chg_pct
        FROM cur c
        JOIN stock_master sm ON sm.stock_id = c.stock_id
        LEFT JOIN prev p ON p.stock_id = c.stock_id
    )
    SELECT
        sec.sector_id,
        sec.name,
        ROUND(AVG(sc.chg_pct), 2)                           AS avg_change_pct,
        COUNT(sc.chg_pct)                                   AS member_count,
        ROUND(
            100.0 * SUM(CASE WHEN sc.chg_pct >= 0 THEN 1 ELSE 0 END)
            / NULLIF(COUNT(sc.chg_pct), 0), 1
        )                                                    AS breadth_pct_up
    FROM sector_master sec
    LEFT JOIN stock_chg sc ON sc.sector_id = sec.sector_id
    GROUP BY sec.sector_id, sec.name
    ORDER BY avg_change_pct DESC NULLS LAST
    """
    rows = conn.execute(sql, [as_of, as_of]).fetchall()
    result = []
    for rank, r in enumerate(rows, start=1):
        sector_id, name, chg, members, breadth = r
        result.append({
            "sector_id":      f"SEC_{sector_id}",
            "name":           name,
            "slug":           _slug(name),
            "strength_score": None,
            "change_pct":     float(chg) if chg is not None else None,
            "breadth":        float(breadth) if breadth is not None else None,
            "rank":           rank,
        })
    return result


@router.get("")
def list_sectors(
    request: Request,
    conn:    DbDep,
    as_of:   AsOfDep,
    _user:   UserDep,
    _rl:     None = Depends(read_rate_limit_dep),
) -> dict[str, Any]:
    sectors = _sector_rows(conn, as_of)
    return ok(sectors, as_of=str(as_of) if as_of else None, source="daily_ohlc:sector_master")


@router.get("/{slug}")
def get_sector_detail(
    slug:    str,
    request: Request,
    conn:    DbDep,
    as_of:   AsOfDep,
    _user:   UserDep,
    _rl:     None = Depends(read_rate_limit_dep),
) -> dict[str, Any]:
    sectors = _sector_rows(conn, as_of)
    match = next((s for s in sectors if s["slug"] == slug), None)
    if match is None:
        raise NotFoundError(f"Sector '{slug}' not found.")

    # Add top-5 constituents by change_pct for this session.
    constituents: list[dict[str, Any]] = []
    if as_of is not None:
        # Resolve sector_id (numeric) from slug.
        sec_name = match["name"]
        sec_row = conn.execute(
            "SELECT sector_id FROM sector_master WHERE name = %s", [sec_name]
        ).fetchone()
        if sec_row:
            numeric_id = sec_row[0]
            sql = """
            WITH prev AS (
                SELECT stock_id, close_adj AS prev_close
                FROM daily_ohlc
                WHERE session_date = (
                    SELECT MAX(session_date) FROM daily_ohlc
                    WHERE session_date < %s AND as_of_version = 1
                ) AND as_of_version = 1
            )
            SELECT
                sm.primary_symbol AS symbol,
                sm.name,
                CASE WHEN p.prev_close IS NOT NULL AND p.prev_close <> 0
                     THEN ROUND((o.close_adj - p.prev_close) / p.prev_close * 100.0, 2)
                     ELSE NULL END AS chg_pct
            FROM daily_ohlc o
            JOIN stock_master sm ON sm.stock_id = o.stock_id
            LEFT JOIN prev p ON p.stock_id = o.stock_id
            WHERE o.session_date = %s AND o.as_of_version = 1
              AND sm.sector_id = %s
            ORDER BY chg_pct DESC NULLS LAST
            LIMIT 10
            """
            rows = conn.execute(sql, [as_of, as_of, numeric_id]).fetchall()
            constituents = [
                {"symbol": r[0], "name": r[1], "change_pct": r[2]}
                for r in rows
            ]

    return ok(
        {**match, "constituents": constituents},
        as_of=str(as_of) if as_of else None,
        source="daily_ohlc:sector_master",
    )
