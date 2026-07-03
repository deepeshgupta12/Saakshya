"""AI explanation layer: generate grounded, Mode-A-safe descriptive summaries.

Pipeline per call:
  is_suppressed? → return safe fallback (no model call)
  cache hit?     → return cached summary
  ceiling hit?   → return templated (non-AI) fallback + audit degraded=True
  generate:
    provider.complete() →
    verify (grounding harness) →
    guardrail (blocked-phrase check) →
    pass → cache + audit + return Explanation
    fail → regenerate up to ai_max_regen →
    exhausted → suppress + audit suppressed=True

Every terminal path writes one audit row (docs/14 §7).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import psycopg

from app.ai.audit import AuditRecord, write_audit
from app.ai.budget import allow_call, increment_calls
from app.ai.cache import get_cached, put_cached, signal_category
from app.ai.guardrail import GuardrailReport
from app.ai.guardrail import check as guardrail_check
from app.ai.payload import Payload, is_suppressed
from app.ai.provider import LLMProvider, LLMResult, get_default_provider
from app.ai.registry import get_prompt
from app.ai.verify import GroundingReport
from app.ai.verify import verify as verify_grounding
from app.config import get_settings

log = logging.getLogger(__name__)

_SUPPRESSED_SUMMARY = (
    "Summary unavailable — required inputs are missing or data confidence is too low. "
    "Not investment advice."
)
_DEGRADED_SUMMARY = "Summary temporarily unavailable. Not investment advice."


@dataclass
class Explanation:
    summary:          str
    cited_facts:      list[str]           = field(default_factory=list)
    risk_notes:       list[str]           = field(default_factory=list)
    model_version:    str                 = ""
    audit_id:         str                 = ""
    suppressed:       bool                = False
    degraded:         bool                = False
    grounding_report: GroundingReport | None = None


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

def explain_stock(
    payload:   Payload,
    *,
    provider:  LLMProvider | None = None,
    conn:      psycopg.Connection | None = None,
    use_cache: bool = True,
) -> Explanation:
    """Generate a grounded stock scanner summary (Mode-A safe).

    Short-circuits to a suppressed Explanation with zero provider calls when
    is_suppressed(payload) is True.
    """
    if provider is None:
        provider = get_default_provider()

    if is_suppressed(payload):
        audit_id = _audit_suppressed(payload, "explain_stock", conn)
        return Explanation(summary=_SUPPRESSED_SUMMARY, suppressed=True, audit_id=audit_id)

    if use_cache and conn is not None and payload.subject.symbol:
        category = signal_category(payload)
        cached   = get_cached(payload.subject.symbol, category, conn)
        if cached is not None:
            return Explanation(summary=cached, model_version="cached")

    if conn is not None and not allow_call(conn):
        templated = _templated_fallback(payload)
        audit_id  = _audit_degraded(payload, "explain_stock", templated, conn)
        return Explanation(summary=templated, degraded=True, audit_id=audit_id)

    return _generate(payload, "stock_summary", "explain_stock", provider, conn, use_cache)


def explain_market(
    payload:   Payload,
    *,
    provider:  LLMProvider | None = None,
    conn:      psycopg.Connection | None = None,
    use_cache: bool = True,
) -> Explanation:
    """Generate a grounded market brief (Mode-A safe)."""
    if provider is None:
        provider = get_default_provider()

    if is_suppressed(payload):
        audit_id = _audit_suppressed(payload, "explain_market", conn)
        return Explanation(summary=_SUPPRESSED_SUMMARY, suppressed=True, audit_id=audit_id)

    if conn is not None and not allow_call(conn):
        templated = _templated_fallback(payload)
        audit_id  = _audit_degraded(payload, "explain_market", templated, conn)
        return Explanation(summary=templated, degraded=True, audit_id=audit_id)

    return _generate(payload, "market_brief", "explain_market", provider, conn, use_cache)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _generate(
    payload:   Payload,
    prompt_id: str,
    agent:     str,
    provider:  LLMProvider,
    conn:      psycopg.Connection | None,
    use_cache: bool,
) -> Explanation:
    cfg = get_settings()
    system_text, prompt_version, model_tier = get_prompt(prompt_id)
    payload_json = payload.to_model_json()

    last_result:    LLMResult | None       = None
    last_grounding: GroundingReport | None = None
    last_guardrail: GuardrailReport | None = None

    for attempt in range(cfg.ai_max_regen + 1):
        try:
            result = provider.complete(
                prompt_id=prompt_id,
                prompt_version=prompt_version,
                system=system_text,
                payload_json=payload_json,
                model_tier=model_tier,
            )
        except Exception:
            log.exception("Provider error on attempt %d/%d", attempt, cfg.ai_max_regen)
            break

        last_result = result
        grounding   = verify_grounding(result.text, payload)
        guardrail   = guardrail_check(result.text)
        last_grounding = grounding
        last_guardrail = guardrail

        if grounding.matched and guardrail.clean:
            if conn is not None:
                increment_calls(conn)

            audit_id = _write_audit(
                payload, agent, prompt_id, prompt_version, result,
                grounding, guardrail, result.text, suppressed=False, conn=conn,
            )

            if use_cache and conn is not None and payload.subject.symbol:
                put_cached(
                    payload.subject.symbol,
                    signal_category(payload),
                    result.text,
                    audit_id,
                    payload.as_of_date,
                    result.model_id,
                    conn,
                )

            return Explanation(
                summary=result.text,
                cited_facts=grounding.matched_items,
                risk_notes=list(payload.risk_flags),
                model_version=result.model_id,
                audit_id=audit_id,
                suppressed=False,
                grounding_report=grounding,
            )

        log.warning(
            "Attempt %d: grounding=%s guardrail=%s — regenerating",
            attempt, grounding.matched, guardrail.clean,
        )

    # All attempts exhausted → suppress.
    audit_id = _write_audit(
        payload, agent, prompt_id, prompt_version, last_result,
        last_grounding, last_guardrail,
        _SUPPRESSED_SUMMARY, suppressed=True, conn=conn,
    )
    return Explanation(
        summary=_SUPPRESSED_SUMMARY,
        suppressed=True,
        audit_id=audit_id,
        grounding_report=last_grounding,
    )


def _templated_fallback(payload: Payload) -> str:
    """Non-AI fallback using only payload vocabulary — grounded and Mode-A safe."""
    vocab  = payload.permitted_vocabulary
    parts: list[str] = []

    if payload.subject.symbol:
        parts.append(f"{payload.subject.symbol} appears in the {payload.computed.scanner} scanner.")

    for tag in payload.signal_tags[:3]:
        phrase = vocab.get(tag)
        if phrase:
            parts.append(f"The stock is {phrase}.")

    for flag in payload.risk_flags[:2]:
        phrase = vocab.get(flag)
        if phrase:
            parts.append(f"Risk note: {phrase}.")

    parts.append("Not investment advice.")
    return " ".join(parts) if parts else _DEGRADED_SUMMARY


def _write_audit(
    payload:        Payload,
    agent:          str,
    prompt_id:      str,
    prompt_version: str,
    result:         LLMResult | None,
    grounding:      GroundingReport | None,
    guardrail:      GuardrailReport | None,
    user_visible:   str,
    *,
    suppressed: bool,
    conn: psycopg.Connection | None,
) -> str:
    if conn is None:
        return ""
    record = AuditRecord(
        intent=payload.intent,
        agent=agent,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        model_tier=result.model_id if result else "unknown",
        model_id=result.model_id if result else "unknown",
        payload_hash=payload.hash(),
        payload_json=payload.to_model_json(),
        raw_output=result.text if result else None,
        grounding_report_json=json.dumps(grounding.to_dict()) if grounding else None,
        guardrail_report_json=json.dumps(guardrail.to_dict()) if guardrail else None,
        compliance_decision="SUPPRESS" if suppressed else "PASS",
        user_visible_output=user_visible,
        suppressed=suppressed,
        as_of_version=payload.as_of_version,
        tokens_in=result.tokens_in if result else 0,
        tokens_out=result.tokens_out if result else 0,
        cost_usd=result.cost_usd if result else 0.0,
    )
    return write_audit(record, conn)


def _audit_suppressed(
    payload: Payload, agent: str, conn: psycopg.Connection | None
) -> str:
    return _write_audit(
        payload, agent, "n/a", "n/a", None, None, None,
        _SUPPRESSED_SUMMARY, suppressed=True, conn=conn,
    )


def _audit_degraded(
    payload: Payload, agent: str, summary: str, conn: psycopg.Connection | None
) -> str:
    if conn is None:
        return ""
    record = AuditRecord(
        intent=payload.intent,
        agent=agent,
        prompt_id="templated",
        prompt_version="v1",
        model_tier="none",
        model_id="templated",
        payload_hash=payload.hash(),
        payload_json=payload.to_model_json(),
        user_visible_output=summary,
        suppressed=False,
        degraded=True,
        as_of_version=payload.as_of_version,
    )
    return write_audit(record, conn)
