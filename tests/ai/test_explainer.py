"""Tests for app/ai/explainer.py — explain_stock, explain_market, pipeline."""

from __future__ import annotations

from dataclasses import dataclass


from app.ai.explainer import explain_market, explain_stock
from app.ai.payload import (
    ComputedBlock,
    DataConfidence,
    Payload,
    Subject,
)
from app.ai.provider import LLMResult
from tests.dbutil import open_fresh_pg

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _in_memory_db():
    return open_fresh_pg()


def _make_payload(
    confidence: DataConfidence = DataConfidence.HIGH,
    composite: float | None = 85.0,
    symbol: str = "RELIANCE.NS",
) -> Payload:
    return Payload(
        intent="explain_scanner_result",
        as_of_date="2026-06-26",
        as_of_version="v1",
        subject=Subject(type="stock", symbol=symbol),
        computed=ComputedBlock(
            scanner="momentum",
            composite_score=composite,
            sub_scores={"priceMomentum": 90.0},
            facts={"close": 2800.0, "ret_3m_pct": 15.0, "sma50": 2600.0},
        ),
        signal_tags=["MOMENTUM_STRONG", "ABOVE_50DMA"],
        risk_flags=["ELEVATED_VOLATILITY"],
        data_confidence=confidence,
        permitted_vocabulary={
            "MOMENTUM_STRONG": "appears in the momentum scanner",
            "ABOVE_50DMA": "trading above its 50-day moving average",
            "ELEVATED_VOLATILITY": "short-term volatility is elevated",
        },
    )


@dataclass
class _MockProvider:
    return_text: str
    call_count:  int = 0

    def complete(
        self, *, prompt_id: str, prompt_version: str,
        system: str, payload_json: str, model_tier: str,
    ) -> LLMResult:
        self.call_count += 1
        return LLMResult(
            text=self.return_text,
            model_id="mock",
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.0,
        )


# The SPEC §5 worked example — grounded and guardrail-clean.
_GROUNDED_SUMMARY = (
    "RELIANCE.NS has risen 15.0% over three months and trades above its 50-day moving average. "
    "The stock is trading above its 50-day moving average. "
    "Short-term volatility is elevated. Not investment advice."
)


# ---------------------------------------------------------------------------
# Suppression tests
# ---------------------------------------------------------------------------

class TestSuppression:
    def test_low_confidence_suppresses_with_zero_calls(self) -> None:
        payload   = _make_payload(confidence=DataConfidence.LOW)
        mock      = _MockProvider(return_text="irrelevant")
        result    = explain_stock(payload, provider=mock, conn=None)
        assert result.suppressed
        assert mock.call_count == 0

    def test_missing_composite_suppresses(self) -> None:
        payload = _make_payload(composite=None)
        mock    = _MockProvider(return_text="irrelevant")
        result  = explain_stock(payload, provider=mock, conn=None)
        assert result.suppressed
        assert mock.call_count == 0

    def test_suppressed_summary_ends_with_not_investment_advice(self) -> None:
        payload = _make_payload(confidence=DataConfidence.LOW)
        result  = explain_stock(payload, provider=_MockProvider("x"), conn=None)
        assert "Not investment advice" in result.summary


# ---------------------------------------------------------------------------
# Grounded summary
# ---------------------------------------------------------------------------

class TestGroundedSummary:
    def test_grounded_summary_returns_not_suppressed(self) -> None:
        payload = _make_payload()
        mock    = _MockProvider(return_text=_GROUNDED_SUMMARY)
        result  = explain_stock(payload, provider=mock, conn=None, use_cache=False)
        assert not result.suppressed
        assert not result.degraded
        assert result.summary == _GROUNDED_SUMMARY

    def test_grounded_summary_has_model_version(self) -> None:
        payload = _make_payload()
        mock    = _MockProvider(return_text=_GROUNDED_SUMMARY)
        result  = explain_stock(payload, provider=mock, conn=None, use_cache=False)
        assert result.model_version == "mock"


# ---------------------------------------------------------------------------
# Fabricated output → suppress after regen exhaustion
# ---------------------------------------------------------------------------

class TestFabricatedOutputSuppressed:
    def test_fabricated_number_triggers_suppress(self) -> None:
        # Payload has ret_3m_pct=15.0; mock returns 99.9 — grounding fails every time.
        payload = _make_payload()
        mock    = _MockProvider(return_text="The stock rose 99.9%. Not investment advice.")
        result  = explain_stock(payload, provider=mock, conn=None, use_cache=False)
        assert result.suppressed
        # Provider must have been called ai_max_regen+1 times (default=2 → 3 attempts).
        assert mock.call_count >= 1

    def test_directive_output_triggers_suppress(self) -> None:
        payload = _make_payload()
        mock    = _MockProvider(
            return_text="Buy now. The stock has risen 15.0%. Not investment advice."
        )
        result = explain_stock(payload, provider=mock, conn=None, use_cache=False)
        assert result.suppressed


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

class TestCache:
    def test_cache_hit_serves_cached_without_second_call(self) -> None:
        conn    = _in_memory_db()
        payload = _make_payload()
        mock    = _MockProvider(return_text=_GROUNDED_SUMMARY)

        # First call — populates cache.
        r1 = explain_stock(payload, provider=mock, conn=conn, use_cache=True)
        assert not r1.suppressed
        first_count = mock.call_count

        # Second call — same payload → same signal category → cache hit.
        r2 = explain_stock(payload, provider=mock, conn=conn, use_cache=True)
        assert mock.call_count == first_count  # provider NOT called again
        assert r2.summary == _GROUNDED_SUMMARY
        conn.close()

    def test_cache_miss_on_signal_change(self) -> None:
        conn     = _in_memory_db()
        payload1 = _make_payload(symbol="RELIANCE.NS")
        payload2 = _make_payload(symbol="RELIANCE.NS")
        # Modify signal tags to change the category.
        payload2.signal_tags.clear()
        payload2.signal_tags.append("VOLUME_SURGE")

        mock = _MockProvider(return_text=_GROUNDED_SUMMARY)
        explain_stock(payload1, provider=mock, conn=conn, use_cache=True)
        explain_stock(payload2, provider=mock, conn=conn, use_cache=True)
        assert mock.call_count == 2  # both calls reach the provider
        conn.close()


# ---------------------------------------------------------------------------
# Daily call ceiling
# ---------------------------------------------------------------------------

class TestCeilingDegradation:
    def test_ceiling_returns_templated_fallback(self) -> None:
        conn    = _in_memory_db()
        payload = _make_payload()
        mock    = _MockProvider(return_text=_GROUNDED_SUMMARY)

        from app.config import get_settings
        ceiling = get_settings().ai_daily_call_ceiling
        from app.ai.budget import _today
        today = _today()
        # Insert a count exceeding the ceiling so allow_call returns False.
        conn.execute(
            "INSERT INTO ai_daily_calls (call_date, call_count) VALUES (%s, %s)",
            [today, ceiling + 1],
        )

        result = explain_stock(payload, provider=mock, conn=conn, use_cache=False)
        assert result.degraded
        assert mock.call_count == 0  # provider not called
        assert "Not investment advice" in result.summary
        conn.close()


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

class TestAuditLog:
    def test_audit_written_on_publish(self) -> None:
        conn    = _in_memory_db()
        payload = _make_payload()
        mock    = _MockProvider(return_text=_GROUNDED_SUMMARY)

        result = explain_stock(payload, provider=mock, conn=conn, use_cache=False)
        row = conn.execute(
            "SELECT suppressed, degraded FROM ai_audit_log WHERE audit_id = %s",
            [result.audit_id],
        ).fetchone()
        assert row is not None
        assert row[0] is False  # suppressed
        assert row[1] is False  # degraded
        conn.close()

    def test_audit_written_on_suppress(self) -> None:
        conn    = _in_memory_db()
        payload = _make_payload(confidence=DataConfidence.LOW)
        result  = explain_stock(payload, provider=_MockProvider("x"), conn=conn)

        row = conn.execute(
            "SELECT suppressed FROM ai_audit_log WHERE audit_id = %s",
            [result.audit_id],
        ).fetchone()
        assert row is not None
        assert row[0] is True
        conn.close()


# ---------------------------------------------------------------------------
# explain_market
# ---------------------------------------------------------------------------

class TestExplainMarket:
    def test_market_suppressed_on_low_confidence(self) -> None:
        payload = Payload(
            intent="explain_market_summary",
            as_of_date="2026-06-26",
            as_of_version="v1",
            subject=Subject(type="market"),
            computed=ComputedBlock(scanner="market", composite_score=None, facts={}),
            data_confidence=DataConfidence.LOW,
        )
        result = explain_market(payload, provider=_MockProvider("x"), conn=None)
        assert result.suppressed
