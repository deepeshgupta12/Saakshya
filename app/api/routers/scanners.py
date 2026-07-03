"""Scanner endpoints (docs/10 §2).

GET /v1/scanners                    — list available scanners
GET /v1/scanners/{scanner}          — paginated scanner results for a date

Mode-A compliant: descriptions are descriptive/evidence-led, no directive labels.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import AsOfDep, DbDep, UserDep
from app.api.envelope import PageMeta, ok
from app.api.errors import NotFoundError
from app.api.ratelimit import read_rate_limit_dep
from app.storage.repository import Repository

router = APIRouter(prefix="/v1/scanners", tags=["scanners"])

_SCANNER_META: dict[str, dict[str, str]] = {
    "momentum": {
        "label":       "Momentum",
        "description": "Stocks with sustained price return across 21d / 63d / 126d horizons, "
                       "scored by multi-period return rank and trend confirmation.",
    },
    "volume_breakout": {
        "label":       "Volume Breakout",
        "description": "Stocks where volume has expanded meaningfully above the 20-day average, "
                       "suggesting unusual participation.",
    },
    "rsi": {
        "label":       "RSI Conditions",
        "description": "Stocks in RSI bands associated with momentum, elevated readings, "
                       "or oversold conditions. Evidence-based — not directives.",
    },
    "moving_average": {
        "label":       "Moving Average Structure",
        "description": "Stocks with identifiable price-vs-MA relationships and MA stacking "
                       "patterns. Descriptive of trend structure only.",
    },
}


@router.get("")
def list_scanners(
    request: Request,
    conn:    DbDep,
    as_of:   AsOfDep,
    _user:   UserDep,
    _rl:     None = Depends(read_rate_limit_dep),
) -> dict[str, Any]:
    # Build result counts from DB for the latest session (0 when no pipeline run yet).
    counts: dict[str, int] = {}
    if as_of is not None:
        rows = conn.execute(
            "SELECT scanner, count(*) FROM scanner_results "
            "WHERE session_date = %s AND as_of_version = 1 GROUP BY scanner",
            [as_of],
        ).fetchall()
        counts = {str(r[0]): int(r[1]) for r in rows}

    items = [
        {
            "scanner":      key,
            "label":        meta["label"],
            "description":  meta["description"],
            "result_count": counts.get(key, 0),
        }
        for key, meta in _SCANNER_META.items()
    ]
    return ok(items)


@router.get("/{scanner}")
def get_scanner_results(
    scanner:   str,
    request:   Request,
    conn:      DbDep,
    as_of:     AsOfDep,
    _user:     UserDep,
    min_score: float | None = Query(default=None, ge=0, le=100),
    limit:     int          = Query(default=50, ge=1, le=200),
    offset:    int          = Query(default=0, ge=0),
    sort:      str          = Query(default="composite_score",
                                   pattern="^(composite_score|symbol)$"),
    _rl:       None         = Depends(read_rate_limit_dep),
) -> dict[str, Any]:
    if scanner not in _SCANNER_META:
        raise NotFoundError(f"Scanner '{scanner}' not found. Available: {list(_SCANNER_META)}")

    if as_of is None:
        raise NotFoundError("No session data available yet. Run the pipeline first.")

    repo = Repository(conn)
    total = repo.count_scanner_results_for_date(scanner, as_of, 1, min_score)
    rows = repo.get_scanner_results_for_date(
        scanner, as_of, 1,
        min_score=min_score,
        limit=limit,
        offset=offset,
        sort=sort,
    )

    # Enrich with stock name, sector, and last close/change from daily_ohlc.
    # Join via stock_master.primary_symbol — exchange_symbols has '.NS' suffix
    # which never matches the bare primary_symbol returned by the repository.
    symbols = [r["symbol"] for r in rows] if rows else []
    enrichment: dict[str, dict[str, Any]] = {}
    if symbols:
        placeholders = ", ".join(["%s"] * len(symbols))
        rich_rows = conn.execute(
            f"""
            SELECT
                sm.primary_symbol AS symbol,
                sm.name,
                sec.name          AS sector,
                o.close_adj,
                o2.close_adj      AS prev_close
            FROM stock_master sm
            LEFT JOIN sector_master sec ON sec.sector_id = sm.sector_id
            LEFT JOIN daily_ohlc o  ON o.stock_id  = sm.stock_id
                                   AND o.session_date = %s
                                   AND o.as_of_version = 1
            LEFT JOIN daily_ohlc o2 ON o2.stock_id = sm.stock_id
                                   AND o2.session_date = (
                                       SELECT MAX(session_date)
                                       FROM daily_ohlc
                                       WHERE stock_id = sm.stock_id
                                         AND session_date < %s
                                         AND as_of_version = 1
                                   )
                                   AND o2.as_of_version = 1
            WHERE sm.primary_symbol IN ({placeholders})
            """,
            [as_of, as_of, *symbols],
        ).fetchall()
        for row in rich_rows:
            sym, name, sector, close, prev_close = row
            change_pct = None
            if close is not None and prev_close is not None and prev_close != 0:
                change_pct = round((close - prev_close) / prev_close * 100, 2)
            enrichment[str(sym)] = {
                "name": name or "",
                "sector": sector,
                "close": close,
                "change_pct": change_pct,
            }

    results = [_format_row(r, enrichment.get(r["symbol"], {}), str(as_of)) for r in rows]

    return ok(
        results,
        as_of=str(as_of),
        source=f"scanner_results:{scanner}",
        page=PageMeta(limit=limit, offset=offset, total=total),
    )


def _format_row(r: dict[str, Any], enrich: dict[str, Any], as_of: str) -> dict[str, Any]:
    signal_tags = _j(r.get("signal_tags_json")) or []
    return {
        "symbol":          r["symbol"],
        "name":            enrich.get("name", ""),
        "sector":          enrich.get("sector"),
        "composite_score": _f(r.get("composite_score")),
        "sub_scores":      _j(r.get("sub_scores_json")),
        "facts":           _j(r.get("facts_json")),
        "reasons":         signal_tags,
        "signal_tags":     signal_tags,
        "risk_flags":      _j(r.get("risk_flags_json")) or [],
        "data_confidence": r.get("data_confidence"),
        "last_close":      enrich.get("close"),
        "change_pct":      enrich.get("change_pct"),
        "as_of":           as_of,
    }


def _f(v: object) -> float | None:
    try:
        return round(float(v), 2)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _j(v: object) -> Any:
    if v is None:
        return None
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (json.JSONDecodeError, ValueError):
            return None
    return v
