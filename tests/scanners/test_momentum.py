"""Golden-series tests for the momentum scanner (docs/02 §Tests, critical-logic)."""

from __future__ import annotations

import math
from datetime import date

import pytest

from app.scanners.momentum import _rsi_health, run_momentum_scanner
from app.scanners.normalize import NEUTRAL


def _ind(
    ret_21d: float = 0.05,
    ret_63d: float = 0.15,
    ret_126d: float = 0.25,
    rel_strength_63d: float = 0.08,
    rsi_14: float = 55.0,
    close_adj: float = 500.0,
    sma_50: float = 450.0,
    atr_14: float = 15.0,
    symbol: str = "TEST",
) -> dict:
    return {
        "symbol": symbol,
        "ret_21d": ret_21d,
        "ret_63d": ret_63d,
        "ret_126d": ret_126d,
        "rel_strength_63d": rel_strength_63d,
        "rsi_14": rsi_14,
        "close_adj": close_adj,
        "sma_50": sma_50,
        "atr_14": atr_14,
    }


# ---------------------------------------------------------------------------
# RSI health sub-score
# ---------------------------------------------------------------------------

def test_rsi_health_oversold_is_zero() -> None:
    assert _rsi_health(20.0) == pytest.approx(0.0)


def test_rsi_health_bullish_band_above_50() -> None:
    h = _rsi_health(55.0)
    assert h > 50.0


def test_rsi_health_overbought_below_50() -> None:
    h = _rsi_health(80.0)
    assert h < 50.0


def test_rsi_health_neutral_nan() -> None:
    assert math.isnan(_rsi_health(NEUTRAL))


# ---------------------------------------------------------------------------
# run_momentum_scanner
# ---------------------------------------------------------------------------

def test_scanner_emits_result_above_threshold() -> None:
    universe = {1: _ind(ret_63d=0.25, rel_strength_63d=0.10)}
    # Pre-populate blended/rs distributions so ranks are 100%
    results = run_momentum_scanner(universe, date(2024, 1, 31))
    assert len(results) == 1
    r = results[0]
    assert r.scanner == "momentum"
    assert r.composite_score is not None
    assert r.as_of_date == date(2024, 1, 31)


def test_scanner_excludes_negative_rs() -> None:
    """rs_3m <= 0 → excluded even if momentum raw is high."""
    universe = {1: _ind(ret_63d=0.30, rel_strength_63d=-0.01)}
    results = run_momentum_scanner(universe, date(2024, 1, 31))
    assert len(results) == 0


def test_scanner_excludes_missing_returns() -> None:
    """NEUTRAL returns → excluded."""
    ind = _ind()
    ind["ret_63d"] = NEUTRAL
    results = run_momentum_scanner({1: ind}, date(2024, 1, 31))
    assert len(results) == 0


def test_scanner_facts_no_forward_fields() -> None:
    """AI payload must not contain entry, target, stop, or return-promise fields."""
    universe = {1: _ind()}
    results = run_momentum_scanner(universe, date(2024, 1, 31))
    if results:
        payload = results[0].ai_payload()
        forbidden = {"entry", "target", "stop_loss", "sl", "return_promise"}
        for key in payload:
            assert key.lower() not in forbidden, f"Forbidden field in payload: {key}"


def test_scanner_tags_from_vocabulary() -> None:
    """All signal_tags are from the canonical SIGNAL_TAGS vocabulary."""
    from app.scanners.vocabulary import SIGNAL_TAGS
    universe = {1: _ind()}
    results = run_momentum_scanner(universe, date(2024, 1, 31))
    for r in results:
        for tag in r.signal_tags:
            assert tag in SIGNAL_TAGS, f"Unknown tag: {tag}"


def test_scanner_flags_from_vocabulary() -> None:
    """All risk_flags are from the canonical RISK_FLAGS vocabulary."""
    from app.scanners.vocabulary import RISK_FLAGS
    universe = {1: _ind(rsi_14=75.0)}  # → RSI_OVERBOUGHT flag
    results = run_momentum_scanner(universe, date(2024, 1, 31))
    for r in results:
        for flag in r.risk_flags:
            assert flag in RISK_FLAGS, f"Unknown flag: {flag}"


def test_scanner_validation_status_pending() -> None:
    """validationStatus must be PENDING_M3B until validated (SPEC §6.5)."""
    universe = {1: _ind()}
    results = run_momentum_scanner(universe, date(2024, 1, 31))
    if results:
        assert results[0].validation_status == "PENDING_M3B"


def test_scanner_facts_pct_values_reasonable() -> None:
    """ret_3m_pct should be in percent form (not fraction)."""
    universe = {1: _ind(ret_63d=0.20)}
    results = run_momentum_scanner(universe, date(2024, 1, 31))
    if results:
        facts = results[0].facts
        if "ret_3m_pct" in facts:
            assert abs(float(facts["ret_3m_pct"])) > 1.0  # 20% not 0.20
