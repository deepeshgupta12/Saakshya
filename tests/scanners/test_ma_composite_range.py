"""Regression: moving-average composite must stay within the 0–100 contract.

The slope term used `10.0 * scale(...)` (scale returns 0–100), so a neutral slope alone
added 10×50 = 500 — composites reached ~540. Fixed to `0.1 * (...)`. docs/13 §6.5.
"""

from __future__ import annotations

from datetime import date

from app.scanners.moving_average import run_ma_scanner


def test_ma_composite_within_0_100_fully_bullish():
    """A stock above both MAs, stacked, with a strong positive slope stays ≤ 100."""
    universe = {
        1: {"symbol": "BULL", "close_adj": 1300.0, "sma_20": 1250.0,
            "sma_50": 1200.0, "sma_200": 1000.0, "slope_50": 0.08},  # strong slope
    }
    results = run_ma_scanner(universe, date(2024, 1, 31))
    assert results, "expected an MA scanner result"
    score = results[0].composite_score
    assert score is not None
    assert 0.0 <= score <= 100.0, f"composite {score} outside 0–100"


def test_ma_composite_neutral_slope_within_range():
    """Neutral slope must not inflate the composite (the original 10×50=500 bug)."""
    universe = {
        1: {"symbol": "FLAT", "close_adj": 1050.0, "sma_20": 1040.0,
            "sma_50": 1000.0, "sma_200": 950.0, "slope_50": 0.0},  # neutral
    }
    results = run_ma_scanner(universe, date(2024, 1, 31))
    assert results
    assert 0.0 <= results[0].composite_score <= 100.0
