"""Portfolio AI summary — grounded, Mode-A-safe, audit-logged (docs/14, docs/16 §5).

Pipeline:
  is_suppressed? → return safe fallback
  budget ceiling? → return templated fallback (no model call)
  generate:
    provider.complete() →
    verify_portfolio_grounding() →
    guardrail_check() →
    pass → audit + return PortfolioSummary
    fail → regenerate up to ai_max_regen →
    exhausted → suppress + audit
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field

import psycopg

from app.ai.audit import AuditRecord, write_audit
from app.ai.budget import allow_call, increment_calls
from app.ai.guardrail import GuardrailReport
from app.ai.guardrail import check as guardrail_check
from app.ai.provider import LLMProvider, LLMResult, get_default_provider
from app.ai.registry import get_prompt
from app.ai.verify import GroundingReport, extract_facts

_ABS_TOL      = 0.05
_REL_TOL      = 0.005
_SAFE_NUMERICS = frozenset({0.0, 1.0, 2.0, 100.0})
_YEAR_MIN, _YEAR_MAX = 1990.0, 2100.0
from app.config import get_settings

log = logging.getLogger(__name__)

_SUPPRESSED = (
    "Portfolio summary unavailable — data confidence is too low or "
    "positions are missing. Not investment advice."
)
_DEGRADED = "Portfolio summary temporarily unavailable. Not investment advice."


# ---------------------------------------------------------------------------
# Portfolio payload DTO
# ---------------------------------------------------------------------------

@dataclass
class PortfolioPayload:
    """Structured, serialisable payload sent to the model.

    All numbers in `aggregate`, `health.score`, and allocation weights are the
    only numbers the model is permitted to reference. Grounding verification
    checks the generated text against `all_numerics()`.
    """
    portfolio_id:   str
    as_of_date:     str
    aggregate:      dict                    # total_value, total_pnl, total_pnl_pct, …
    health:         dict                    # score, band, drivers
    top_allocations: list[dict]             # [{symbol, weight_pct, sector}]
    sector_allocation: list[dict]           # [{sector, weight_pct}]
    events:         list[str]               # factual event strings
    data_confidence: str = "HIGH"           # HIGH / MEDIUM / LOW

    def all_numerics(self) -> list[float]:
        """Return every numeric value in the payload for grounding verification."""
        nums: list[float] = []

        def _walk(v: object) -> None:
            if isinstance(v, (int, float)):
                nums.append(float(v))
            elif isinstance(v, dict):
                for vv in v.values():
                    _walk(vv)
            elif isinstance(v, list):
                for item in v:
                    _walk(item)

        _walk(self.aggregate)
        _walk(self.health)
        _walk(self.top_allocations)
        _walk(self.sector_allocation)
        return nums

    def to_json(self) -> str:
        return json.dumps({
            "portfolio_id":     self.portfolio_id,
            "as_of_date":       self.as_of_date,
            "aggregate":        self.aggregate,
            "health":           self.health,
            "top_allocations":  self.top_allocations,
            "sector_allocation": self.sector_allocation,
            "events":           self.events,
            "data_confidence":  self.data_confidence,
        }, default=str)

    def hash(self) -> str:
        return hashlib.sha256(self.to_json().encode()).hexdigest()[:16]


def is_suppressed(payload: PortfolioPayload) -> bool:
    """Suppress when data confidence is LOW or no aggregate data provided."""
    if payload.data_confidence == "LOW":
        return True
    if not payload.aggregate:
        return True
    if payload.aggregate.get("total_value", 0.0) == 0.0:
        return True
    return False


# ---------------------------------------------------------------------------
# Portfolio-specific grounding verifier
# ---------------------------------------------------------------------------

def _matches_any(value: float, candidates: list[float]) -> bool:
    for c in candidates:
        if abs(value - c) <= _ABS_TOL:
            return True
        if abs(c) > 0 and abs(value - c) / abs(c) <= _REL_TOL:
            return True
    return False


def verify_portfolio_grounding(text: str, payload: PortfolioPayload) -> GroundingReport:
    """Check that every numeric in the generated text traces to payload.all_numerics().

    Symbol/tag checks not applied here since portfolio summaries mention sector
    names (strings) rather than NSE tickers or scanner tags.
    """
    extracted    = extract_facts(text)
    payload_nums = payload.all_numerics()

    matched_items:   list[str] = []
    unmatched_items: list[str] = []

    for num in extracted.numerics:
        if num == int(num) and int(num) in extracted.window_nums:
            continue
        if _YEAR_MIN <= num <= _YEAR_MAX and num == int(num):
            continue
        if num in _SAFE_NUMERICS:
            continue
        if _matches_any(num, payload_nums):
            matched_items.append(f"num:{num}")
        else:
            unmatched_items.append(f"num:{num}")

    return GroundingReport(
        matched=not unmatched_items,
        matched_items=matched_items,
        unmatched_items=unmatched_items,
    )


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

@dataclass
class PortfolioSummary:
    summary:          str
    audit_id:         str                  = ""
    suppressed:       bool                 = False
    degraded:         bool                 = False
    grounding_report: GroundingReport | None = None


def summarize_portfolio(
    payload:   PortfolioPayload,
    *,
    provider:  LLMProvider | None = None,
    conn:      psycopg.Connection | None = None,
) -> PortfolioSummary:
    """Generate a grounded portfolio summary (Mode-A safe).

    Short-circuits to a suppressed PortfolioSummary (zero model calls) when
    is_suppressed(payload) is True.
    """
    if provider is None:
        provider = get_default_provider()

    if is_suppressed(payload):
        audit_id = _audit_suppressed(payload, conn)
        return PortfolioSummary(summary=_SUPPRESSED, suppressed=True, audit_id=audit_id)

    if conn is not None and not allow_call(conn):
        templated = _templated_fallback(payload)
        audit_id  = _audit_degraded(payload, templated, conn)
        return PortfolioSummary(summary=templated, degraded=True, audit_id=audit_id)

    return _generate(payload, provider, conn)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _generate(
    payload:  PortfolioPayload,
    provider: LLMProvider,
    conn:     psycopg.Connection | None,
) -> PortfolioSummary:
    cfg = get_settings()
    system_text, prompt_version, model_tier = get_prompt("portfolio_summary")
    payload_json = payload.to_json()

    last_result:    LLMResult | None       = None
    last_grounding: GroundingReport | None = None
    last_guardrail: GuardrailReport | None = None

    for attempt in range(cfg.ai_max_regen + 1):
        try:
            result = provider.complete(
                prompt_id="portfolio_summary",
                prompt_version=prompt_version,
                system=system_text,
                payload_json=payload_json,
                model_tier=model_tier,
            )
        except Exception:
            log.exception("Provider error on attempt %d/%d", attempt, cfg.ai_max_regen)
            break

        last_result = result
        grounding   = verify_portfolio_grounding(result.text, payload)
        guardrail   = guardrail_check(result.text)
        last_grounding = grounding
        last_guardrail = guardrail

        if grounding.matched and guardrail.clean:
            if conn is not None:
                increment_calls(conn)

            audit_id = _write_audit(
                payload, result, grounding, guardrail,
                result.text, suppressed=False, conn=conn,
            )
            return PortfolioSummary(
                summary=result.text,
                audit_id=audit_id,
                suppressed=False,
                grounding_report=grounding,
            )

        log.warning(
            "Portfolio summary attempt %d: grounding=%s guardrail=%s — regenerating",
            attempt, grounding.matched, guardrail.clean,
        )

    # All attempts exhausted → suppress.
    audit_id = _write_audit(
        payload, last_result, last_grounding, last_guardrail,
        _SUPPRESSED, suppressed=True, conn=conn,
    )
    return PortfolioSummary(
        summary=_SUPPRESSED,
        suppressed=True,
        audit_id=audit_id,
        grounding_report=last_grounding,
    )


def _templated_fallback(payload: PortfolioPayload) -> str:
    agg = payload.aggregate
    parts: list[str] = []

    total_pnl     = agg.get("total_pnl")
    total_pnl_pct = agg.get("total_pnl_pct")
    if total_pnl is not None:
        sign = "+" if total_pnl >= 0 else ""
        parts.append(
            f"Portfolio total P&L is {sign}₹{total_pnl:.2f} "
            f"({sign}{total_pnl_pct:.2f}%)."
        )

    health = payload.health
    if health.get("score") is not None:
        parts.append(
            f"Portfolio health score: {health['score']}/100 ({health.get('band', '')})."
        )

    parts.append("These are observations, not recommendations. (Not investment advice.)")
    return " ".join(parts) if len(parts) > 1 else _DEGRADED


def _write_audit(
    payload:   PortfolioPayload,
    result:    LLMResult | None,
    grounding: GroundingReport | None,
    guardrail: GuardrailReport | None,
    user_visible: str,
    *,
    suppressed: bool,
    conn: psycopg.Connection | None,
) -> str:
    if conn is None:
        return ""
    record = AuditRecord(
        intent="portfolio_summary",
        agent="summarize_portfolio",
        prompt_id="portfolio_summary",
        prompt_version=grounding and "v1" or "n/a",
        model_tier=result.model_id if result else "unknown",
        model_id=result.model_id if result else "unknown",
        payload_hash=payload.hash(),
        payload_json=payload.to_json(),
        raw_output=result.text if result else None,
        grounding_report_json=json.dumps(grounding.to_dict()) if grounding else None,
        guardrail_report_json=json.dumps(guardrail.to_dict()) if guardrail else None,
        compliance_decision="SUPPRESS" if suppressed else "PASS",
        user_visible_output=user_visible,
        suppressed=suppressed,
        as_of_version=payload.as_of_date,
        tokens_in=result.tokens_in if result else 0,
        tokens_out=result.tokens_out if result else 0,
        cost_usd=result.cost_usd if result else 0.0,
    )
    return write_audit(record, conn)


def _audit_suppressed(
    payload: PortfolioPayload,
    conn: psycopg.Connection | None,
) -> str:
    return _write_audit(payload, None, None, None, _SUPPRESSED, suppressed=True, conn=conn)


def _audit_degraded(
    payload: PortfolioPayload,
    summary: str,
    conn: psycopg.Connection | None,
) -> str:
    if conn is None:
        return ""
    record = AuditRecord(
        intent="portfolio_summary",
        agent="summarize_portfolio",
        prompt_id="templated",
        prompt_version="v1",
        model_tier="none",
        model_id="templated",
        payload_hash=payload.hash(),
        payload_json=payload.to_json(),
        user_visible_output=summary,
        suppressed=False,
        degraded=True,
        as_of_version=payload.as_of_date,
    )
    return write_audit(record, conn)
