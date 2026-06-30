"""Tests for app/ai/verify.py — runtime grounding harness."""

from __future__ import annotations

from app.ai.payload import ComputedBlock, DataConfidence, Payload, Subject
from app.ai.verify import extract_facts, verify


def _make_payload(
    facts: dict | None = None,
    tags: list[str] | None = None,
    composite: float = 87.4,
) -> Payload:
    return Payload(
        intent="explain_scanner_result",
        as_of_date="2026-06-26",
        as_of_version="v1",
        subject=Subject(type="stock", symbol="TATAMOTORS.NS"),
        computed=ComputedBlock(
            scanner="momentum",
            composite_score=composite,
            sub_scores={"priceMomentum": 92.1},
            facts=facts or {
                "ret_3m_pct": 21.4,
                "close": 980.0,
                "sma50": 882.0,
                "vol_ratio": 2.4,
                "atr_pct": 3.4,
            },
        ),
        signal_tags=tags or ["MOMENTUM_STRONG", "ABOVE_50DMA"],
        risk_flags=["ELEVATED_VOLATILITY"],
        data_confidence=DataConfidence.HIGH,
        permitted_vocabulary={
            "MOMENTUM_STRONG": "appears in the momentum scanner",
            "ABOVE_50DMA": "trading above its 50-day moving average",
            "ELEVATED_VOLATILITY": "short-term volatility is elevated",
        },
    )


SPEC_WORKED_EXAMPLE = (
    "TATAMOTORS.NS has risen 21.4% over the past three months and trades above its "
    "50-day moving average. Volume has expanded roughly 2.4 times its 20-day average. "
    "Short-term volatility is elevated, with ATR at 3.4% of price. Not investment advice."
)


class TestGroundedText:
    def test_spec_example_passes(self) -> None:
        report = verify(SPEC_WORKED_EXAMPLE, _make_payload())
        assert report.matched, f"Unmatched: {report.unmatched_items}"

    def test_empty_text_passes(self) -> None:
        report = verify("", _make_payload())
        assert report.matched

    def test_safe_text_no_numbers_passes(self) -> None:
        report = verify(
            "The stock appears in the momentum scanner. Not investment advice.",
            _make_payload(),
        )
        assert report.matched


class TestFabricatedNumbers:
    def test_injected_number_fails(self) -> None:
        # Payload has ret_3m_pct=21.4; output claims 35.0.
        report = verify(
            "The stock has risen 35.0% over the past three months.",
            _make_payload(),
        )
        assert not report.matched
        assert any("num:35.0" in u for u in report.unmatched_items)

    def test_fabricated_price_fails(self) -> None:
        report = verify(
            "The target price is 1200. Not investment advice.",
            _make_payload(),
        )
        assert not report.matched

    def test_close_number_matches(self) -> None:
        # 980.0 is in payload.computed.facts.close
        report = verify(
            "The stock closed at 980.0 yesterday. Not investment advice.",
            _make_payload(),
        )
        assert report.matched


class TestWindowLabels:
    def test_50dma_label_not_flagged(self) -> None:
        report = verify(
            "The stock trades above its 50-day moving average. Not investment advice.",
            _make_payload(),
        )
        assert report.matched, f"Unmatched: {report.unmatched_items}"

    def test_200dma_label_not_flagged(self) -> None:
        payload = _make_payload(facts={"close": 500.0, "sma200": 450.0})
        report = verify(
            "Trading above its 200-day moving average. Not investment advice.",
            payload,
        )
        assert report.matched

    def test_20day_avg_label_not_flagged(self) -> None:
        report = verify(
            "Volume expanded 2.4 times its 20-day average. Not investment advice.",
            _make_payload(),
        )
        assert report.matched


class TestUnknownTags:
    def test_unknown_scanner_tag_fails(self) -> None:
        # UNKNOWN_TAG is not in payload.signal_tags or permitted_vocabulary.
        report = verify(
            "The stock shows UNKNOWN_TAG momentum. Not investment advice.",
            _make_payload(),
        )
        assert not report.matched
        assert any("tag:UNKNOWN_TAG" in u for u in report.unmatched_items)

    def test_valid_tag_passes(self) -> None:
        report = verify(
            "The stock shows MOMENTUM_STRONG signals. Not investment advice.",
            _make_payload(),
        )
        assert report.matched


class TestExtractFacts:
    def test_numeric_extraction(self) -> None:
        facts = extract_facts("The stock rose 21.4% and closed at ₹980.0.")
        assert 21.4 in facts.numerics
        assert 980.0 in facts.numerics

    def test_window_label_extraction(self) -> None:
        facts = extract_facts("Trading above its 50-DMA and 200-day moving average.")
        assert 50 in facts.window_nums
        assert 200 in facts.window_nums
        # The window numbers themselves should not appear in free numerics
        assert 50.0 not in facts.numerics
        assert 200.0 not in facts.numerics

    def test_tag_extraction(self) -> None:
        facts = extract_facts("Shows MOMENTUM_STRONG and ABOVE_50DMA signals.")
        assert "MOMENTUM_STRONG" in facts.tags
        assert "ABOVE_50DMA" in facts.tags

    def test_symbol_extraction(self) -> None:
        facts = extract_facts("TATAMOTORS.NS traded at 980.0 today.")
        assert "TATAMOTORS" in facts.symbols or "TATAMOTORS.NS" in facts.symbols
