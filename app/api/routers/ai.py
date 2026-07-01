"""AI endpoints — market brief and (future) per-stock summary overrides (docs/10 §9).

GET /api/ai/market-brief  — Mode-A daily market overview, evidence-led.
Rate-limited by the ai_rate_limit_dep (30 req/min).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.ai.market_brief import get_or_generate_brief
from app.api.deps import AsOfDep, DbDep
from app.api.envelope import ok
from app.api.ratelimit import ai_rate_limit_dep

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/market-brief")
def market_brief(
    conn:  DbDep,
    as_of: AsOfDep,
    _rl:   None = Depends(ai_rate_limit_dep),
) -> dict[str, Any]:
    """Return the AI-generated daily market overview for the requested session date."""
    if as_of is None:
        return ok(
            {"brief": "No market data available yet.", "session_date": None},
            data_confidence="low",
        )
    result = get_or_generate_brief(conn, as_of)
    confidence = "low" if result.get("suppressed") or result.get("degraded") else "high"
    return ok(result, as_of=str(as_of), data_confidence=confidence)
