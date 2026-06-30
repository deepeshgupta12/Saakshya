"""Tests for indicators/returns.py (docs/02 §Tests)."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from app.indicators.returns import relative_strength, total_return, volume_ratio_20


def _s(vals: list[float]) -> pd.Series:
    return pd.Series(vals, index=pd.date_range("2024-01-01", periods=len(vals), freq="B"))


def _nan(v: object) -> bool:
    try:
        return math.isnan(float(v))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# total_return
# ---------------------------------------------------------------------------

def test_total_return_warmup() -> None:
    """First `window` rows are NaN."""
    s = total_return(_s([100.0] * 10), 5)
    for i in range(5):
        assert _nan(s.iloc[i])


def test_total_return_simple() -> None:
    """Return over 1 period: (close_t / close_(t-1)) - 1."""
    s = total_return(_s([100.0, 110.0, 121.0]), 1)
    assert s.iloc[1] == pytest.approx(0.10)
    assert s.iloc[2] == pytest.approx(0.10)


def test_total_return_multi_period() -> None:
    """Return over 2 periods: (121 / 100) - 1 = 0.21."""
    s = total_return(_s([100.0, 110.0, 121.0]), 2)
    assert _nan(s.iloc[0]) and _nan(s.iloc[1])
    assert s.iloc[2] == pytest.approx(0.21)


# ---------------------------------------------------------------------------
# volume_ratio_20
# ---------------------------------------------------------------------------

def test_volume_ratio_warmup() -> None:
    """First 20 bars are NaN (rolling(20) needs 20 bars, then shift(1) adds one more)."""
    v = volume_ratio_20(_s([1000.0] * 25))
    for i in range(20):
        assert _nan(v.iloc[i])


def test_volume_ratio_constant() -> None:
    """Constant volume → ratio = 1.0 always."""
    v = volume_ratio_20(_s([500.0] * 25))
    valid = v.dropna()
    assert all(x == pytest.approx(1.0) for x in valid.tolist())


def test_volume_ratio_double() -> None:
    """When current volume = 2× average → ratio = 2.0."""
    vals = [1000.0] * 20 + [2000.0]
    v = volume_ratio_20(_s(vals))
    assert v.iloc[20] == pytest.approx(2.0)


def test_volume_ratio_zero_denominator_nan() -> None:
    """Zero average volume → NaN (never divide by zero)."""
    v = volume_ratio_20(_s([0.0] * 25))
    valid = v.dropna()
    assert all(_nan(x) for x in valid.tolist())


# ---------------------------------------------------------------------------
# relative_strength
# ---------------------------------------------------------------------------

def test_relative_strength_zero_outperformance() -> None:
    """Stock return == bench return → RS = 0."""
    stock = _s([100.0, 110.0])
    bench = _s([100.0, 110.0])
    rs = relative_strength(stock, bench, 1)
    assert rs.iloc[1] == pytest.approx(0.0)


def test_relative_strength_positive() -> None:
    """Stock +20%, bench +10% over 1 period → RS = 0.10 (in decimal)."""
    stock = _s([100.0, 120.0])
    bench = _s([100.0, 110.0])
    rs = relative_strength(stock, bench, 1)
    assert rs.iloc[1] == pytest.approx(0.10)


def test_relative_strength_negative() -> None:
    """Stock underperforms → RS < 0."""
    stock = _s([100.0, 105.0])
    bench = _s([100.0, 115.0])
    rs = relative_strength(stock, bench, 1)
    assert rs.iloc[1] < 0.0
