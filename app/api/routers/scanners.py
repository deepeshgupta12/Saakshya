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
    _user:   UserDep,
    _rl:     None = Depends(read_rate_limit_dep),
) -> dict[str, Any]:
    return ok(list(_SCANNER_META.values()))


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

    results = [_format_row(r) for r in rows]

    return ok(
        results,
        as_of=str(as_of),
        source=f"scanner_results:{scanner}",
        page=PageMeta(limit=limit, offset=offset, total=total),
    )


def _format_row(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol":          r["symbol"],
        "composite_score": _f(r.get("composite_score")),
        "sub_scores":      _j(r.get("sub_scores_json")),
        "facts":           _j(r.get("facts_json")),
        "signal_tags":     _j(r.get("signal_tags_json")) or [],
        "risk_flags":      _j(r.get("risk_flags_json")) or [],
        "data_confidence": r.get("data_confidence"),
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
