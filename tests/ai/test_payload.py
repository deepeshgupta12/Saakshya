"""Tests for app/ai/payload.py — payload contract, suppression, builders."""

from __future__ import annotations

import json

import pytest

from app.ai.payload import (
    ComputedBlock,
    DataConfidence,
    ForbiddenFieldError,
    Payload,
    Subject,
    build_stock_payload,
    is_suppressed,
)


def _make_payload(
    *,
    composite: float | None = 85.0,
    facts: dict | None = None,
    confidence: DataConfidence = DataConfidence.HIGH,
    signal_tags: list[str] | None = None,
) -> Payload:
    return Payload(
        intent="explain_scanner_result",
        as_of_date="2026-06-26",
        as_of_version="v1",
        subject=Subject(type="stock", symbol="RELIANCE.NS"),
        computed=ComputedBlock(
            scanner="momentum",
            composite_score=composite,
            sub_scores={"priceMomentum": 90.0},
            facts=facts or {"close": 2800.0, "ret_3m_pct": 15.0, "sma50": 2600.0},
        ),
        signal_tags=signal_tags or ["MOMENTUM_STRONG"],
        risk_flags=["ELEVATED_VOLATILITY"],
        data_confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Forbidden fields
# ---------------------------------------------------------------------------

class TestForbiddenFields:
    def test_target_raises(self) -> None:
        with pytest.raises(ForbiddenFieldError):
            ComputedBlock(
                scanner="momentum",
                composite_score=80.0,
                facts={"close": 100.0, "target": 120.0},
            )

    def test_stop_loss_raises(self) -> None:
        with pytest.raises(ForbiddenFieldError):
            ComputedBlock(scanner="m", composite_score=1.0, facts={"stop_loss": 90.0})

    def test_price_target_raises(self) -> None:
        with pytest.raises(ForbiddenFieldError):
            ComputedBlock(scanner="m", composite_score=1.0, facts={"price_target": 150.0})

    def test_valid_facts_accepted(self) -> None:
        cb = ComputedBlock(
            scanner="momentum",
            composite_score=80.0,
            facts={"close": 100.0, "ret_3m_pct": 10.0, "sma50": 90.0},
        )
        assert cb.facts["close"] == 100.0


# ---------------------------------------------------------------------------
# Hash stability
# ---------------------------------------------------------------------------

class TestHashStability:
    def test_same_inputs_same_hash(self) -> None:
        p1 = _make_payload()
        p2 = _make_payload()
        assert p1.hash() == p2.hash()

    def test_reordered_facts_same_hash(self) -> None:
        p1 = _make_payload(facts={"a": 1.0, "b": 2.0})
        p2 = _make_payload(facts={"b": 2.0, "a": 1.0})
        assert p1.hash() == p2.hash()

    def test_different_scores_different_hash(self) -> None:
        p1 = _make_payload(composite=80.0)
        p2 = _make_payload(composite=90.0)
        assert p1.hash() != p2.hash()


# ---------------------------------------------------------------------------
# Suppression
# ---------------------------------------------------------------------------

class TestSuppression:
    def test_low_confidence_is_suppressed(self) -> None:
        p = _make_payload(confidence=DataConfidence.LOW)
        assert is_suppressed(p)

    def test_suppressed_confidence_is_suppressed(self) -> None:
        p = _make_payload(confidence=DataConfidence.SUPPRESSED)
        assert is_suppressed(p)

    def test_none_composite_is_suppressed(self) -> None:
        p = _make_payload(composite=None)
        assert is_suppressed(p)

    def test_missing_close_is_suppressed(self) -> None:
        p = _make_payload(facts={"ret_3m_pct": 10.0, "sma50": 90.0})
        assert is_suppressed(p)

    def test_high_confidence_complete_not_suppressed(self) -> None:
        p = _make_payload()
        assert not is_suppressed(p)


# ---------------------------------------------------------------------------
# to_model_json / to_model_dict
# ---------------------------------------------------------------------------

class TestModelJson:
    def test_json_parses_to_dict(self) -> None:
        p   = _make_payload()
        doc = json.loads(p.to_model_json())
        assert "payload" in doc
        assert doc["payload"]["modeContext"] == "A"

    def test_no_forward_fields_in_output(self) -> None:
        p   = _make_payload()
        txt = p.to_model_json()
        for forbidden in ("target", "stop_loss", "price_target", "entry"):
            assert f'"{forbidden}"' not in txt


# ---------------------------------------------------------------------------
# build_stock_payload
# ---------------------------------------------------------------------------

class TestBuildStockPayload:
    def test_basic_build(self) -> None:
        indicators = {"close": 500.0, "ret_3m_pct": 20.0, "sma50": 450.0}
        scanner    = {
            "composite_score": 78.0, "scanner": "momentum",
            "signal_tags": ["MOMENTUM_STRONG"],
        }
        p = build_stock_payload(
            "INFOSYS.NS", indicators, scanner, [],
            as_of="2026-06-26", as_of_version="v1",
        )
        assert p.subject.symbol == "INFOSYS.NS"
        assert p.computed.composite_score == 78.0
        assert p.data_confidence == DataConfidence.HIGH

    def test_missing_two_critical_fields_lowers_confidence(self) -> None:
        indicators = {"vol_ratio": 2.0}  # missing close, ret_3m_pct, sma50
        scanner    = {"composite_score": 60.0, "scanner": "momentum", "signal_tags": []}
        p = build_stock_payload(
            "X.NS", indicators, scanner, [],
            as_of="2026-06-26", as_of_version="v1",
        )
        assert p.data_confidence == DataConfidence.LOW

    def test_forbidden_fields_stripped_from_indicators(self) -> None:
        indicators = {"close": 100.0, "target": 120.0, "stop_loss": 90.0}
        scanner    = {"composite_score": 70.0, "scanner": "momentum", "signal_tags": []}
        p = build_stock_payload(
            "X.NS", indicators, scanner, [],
            as_of="2026-06-26", as_of_version="v1",
        )
        assert "target" not in p.computed.facts
        assert "stop_loss" not in p.computed.facts
        assert "close" in p.computed.facts
