"""Stock-level endpoints (docs/10 §3).

GET /v1/stocks/{symbol}/overview      — latest OHLCV + scanner memberships
GET /v1/stocks/{symbol}/technicals    — computed indicators for a date
GET /v1/stocks/{symbol}/ai-summary    — AI-generated explanation (cache-aware)

Mode-A compliant: no entry/target/SL, no candidate/buy-lean labels, no directive language.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.api.deps import AsOfDep, DbDep, UserDep
from app.api.envelope import ok
from app.api.errors import DataSuppressedError, NotFoundError
from app.api.ratelimit import ai_rate_limit_dep, read_rate_limit_dep
from app.storage.repository import Repository

router = APIRouter(prefix="/v1/stocks", tags=["stocks"])


@router.get("/{symbol}/overview")
def get_stock_overview(
    symbol:  str,
    request: Request,
    conn:    DbDep,
    as_of:   AsOfDep,
    _user:   UserDep,
    _rl:     None = Depends(read_rate_limit_dep),
) -> dict[str, Any]:
    sym = symbol.upper()
    repo = Repository(conn)

    # Latest OHLC bar (close_adj, open, high, low, volume).
    bar = repo.get_latest_ohlc_for_symbol(sym)
    if bar is None:
        raise NotFoundError(f"No OHLC data found for symbol '{sym}'.")

    session_date = as_of or bar.session_date
    memberships = repo.get_scanner_memberships(sym, session_date, 1)

    data = {
        "symbol":       sym,
        "session_date": str(bar.session_date),
        "open":         _f(bar.open_adj),
        "high":         _f(bar.high_adj),
        "low":          _f(bar.low_adj),
        "close":        _f(bar.close_adj),
        "volume":       bar.volume,
        "delivery_pct": _f(bar.delivery_pct),
        "scanner_memberships": memberships,
        "disclaimer":   "Not investment advice. Evidence-based analytics only.",
    }
    return ok(data, as_of=str(bar.session_date), source="daily_ohlc")


@router.get("/{symbol}/technicals")
def get_stock_technicals(
    symbol:  str,
    request: Request,
    conn:    DbDep,
    as_of:   AsOfDep,
    _user:   UserDep,
    _rl:     None = Depends(read_rate_limit_dep),
) -> dict[str, Any]:
    sym = symbol.upper()
    repo = Repository(conn)
    ind = repo.get_latest_indicators_for_symbol(sym, as_of, 1)
    if ind is None:
        raise DataSuppressedError(
            f"Indicator data for '{sym}' is not available for {as_of}. "
            "Run the pipeline to compute indicators."
        )

    data = {k: (_f(v) if isinstance(v, float) else v) for k, v in ind.items()}
    return ok(data, as_of=str(as_of) if as_of else None, source="technical_indicators")


@router.get("/{symbol}/ai-summary")
def get_stock_ai_summary(
    symbol:  str,
    request: Request,
    conn:    DbDep,
    as_of:   AsOfDep,
    _user:   UserDep,
    _rl:     None = Depends(ai_rate_limit_dep),
) -> dict[str, Any]:
    sym = symbol.upper()
    repo = Repository(conn)

    session_date = as_of
    if session_date is None:
        bar = repo.get_latest_ohlc_for_symbol(sym)
        if bar is None:
            raise NotFoundError(f"No data found for '{sym}'.")
        session_date = bar.session_date

    ind = repo.get_latest_indicators_for_symbol(sym, session_date, 1)
    if ind is None:
        raise DataSuppressedError(
            f"Indicator data for '{sym}' unavailable — cannot generate AI summary."
        )

    # Load most relevant scanner result for this symbol.
    scanner_rows = conn.execute(
        "SELECT sr.scanner, sr.composite_score, sr.sub_scores, sr.facts, "
        "sr.signal_tags, sr.risk_flags, sr.data_confidence "
        "FROM scanner_results sr "
        "JOIN stock_master sm ON sm.stock_id = sr.stock_id "
        "WHERE sm.primary_symbol = ? AND sr.session_date = ? AND sr.as_of_version = 1 "
        "ORDER BY sr.composite_score DESC NULLS LAST LIMIT 1",
        [sym, session_date],
    ).fetchone()

    scanner_info: dict[str, Any] = {}
    if scanner_rows:
        scanner_info = {
            "scanner":         scanner_rows[0],
            "composite_score": scanner_rows[1],
            "sub_scores":      _j(scanner_rows[2]),
            "facts":           _j(scanner_rows[3]),
            "signal_tags":     _j(scanner_rows[4]) or [],
            "risk_flags":      _j(scanner_rows[5]) or [],
            "data_confidence": str(scanner_rows[6]) if scanner_rows[6] else "MEDIUM",
        }

    bar = repo.get_latest_ohlc_for_symbol(sym)
    raw_ind: dict[str, object] = dict(ind)
    if bar:
        raw_ind["close"] = bar.close_adj
        raw_ind["volume"] = float(bar.volume)
    # Narrow to float|bool as required by build_stock_payload.
    indicators: dict[str, float | bool] = {
        k: v
        for k, v in raw_ind.items()
        if isinstance(v, int | float | bool) and not isinstance(v, type(None))
    }

    from app.ai.explainer import explain_stock
    from app.ai.payload import build_stock_payload

    try:
        payload = build_stock_payload(
            sym,
            indicators,
            scanner_info,
            scanner_info.get("risk_flags", []),
            as_of=str(session_date),
            as_of_version=f"ds-{session_date}",
        )
    except Exception as exc:
        raise DataSuppressedError(
            f"Could not build AI payload for '{sym}': {exc}"
        ) from exc

    try:
        expl = explain_stock(payload, conn=conn, use_cache=True)
    except Exception as exc:
        raise DataSuppressedError(
            f"AI explanation failed for '{sym}': {exc}"
        ) from exc

    if expl.suppressed:
        raise DataSuppressedError(
            "AI summary suppressed due to insufficient evidence. "
            "Check technicals endpoint for available data."
        )

    data = {
        "symbol":        sym,
        "session_date":  str(session_date),
        "summary":       expl.summary,
        "cited_facts":   expl.cited_facts,
        "risk_notes":    expl.risk_notes,
        "model_version": expl.model_version,
        "disclaimer":    "AI-generated description of data evidence. Not investment advice.",
    }
    cache_hit = "hit" if expl.model_version == "cached" else "miss"
    return ok(
        data,
        as_of=str(session_date),
        source="ai_explanation",
        data_confidence=scanner_info.get("data_confidence", "MEDIUM"),
        cache=cache_hit,
    )


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
