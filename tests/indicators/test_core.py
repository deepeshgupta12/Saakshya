"""Golden-series tests for indicators/core.py (docs/02 §Tests, docs/25 critical-logic).

All expected values are hand-computed from the documented formulas so this suite
is independent of any external library.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from app.indicators.core import (
    adx_14,
    atr,
    bollinger,
    compute_rsi,
    ema,
    macd,
    pivots,
    sma,
    stoch_rsi,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _series(vals: list[float]) -> pd.Series:
    idx = pd.date_range("2024-01-01", periods=len(vals), freq="B")
    return pd.Series(vals, index=idx)


def _isnan(v: object) -> bool:
    try:
        return math.isnan(float(v))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# RSI
# ---------------------------------------------------------------------------

def test_rsi_warmup_is_nan() -> None:
    """First period-1 bars must be NaN, not 0 (docs/02 §1)."""
    closes = _series([100.0] * 20)
    rsi = compute_rsi(closes, period=14)
    for i in range(13):
        assert _isnan(rsi.iloc[i]), f"bar {i} should be NaN"


def test_rsi_golden_ewm() -> None:
    """RSI = 100/14 ≈ 7.143 for 13 consecutive drops then 1 rise (EWM initialization).

    Series: 100 dropping by 1 for 13 bars, then rising by 1 (15 bars total).
    EWM(alpha=1/14) of gains at bar 14: y_14 = (1/14)*1 = 1/14 (previous all-zero).
    EWM(alpha=1/14) of losses at bar 14: y_14 = (13/14)*1 = 13/14 (previous all-one then zero).
    RS = (1/14) / (13/14) = 1/13.
    RSI = 100 - 100/(1 + 1/13) = 100*(1/14) = 100/14.
    """
    closes = _series([float(100 - i) for i in range(14)] + [88.0])
    rsi = compute_rsi(closes, period=14)
    assert not _isnan(rsi.iloc[14]), "bar 14 should be valid"
    assert rsi.iloc[14] == pytest.approx(100.0 / 14.0, rel=1e-6)


def test_rsi_constant_series_is_nan_or_100() -> None:
    """Constant price → all gains = all losses = 0 → avg_loss = 0 → RSI = 100."""
    closes = _series([100.0] * 20)
    rsi = compute_rsi(closes, period=14)
    valid = rsi.dropna()
    assert all(v == pytest.approx(100.0) for v in valid.tolist())


def test_rsi_bounded() -> None:
    """RSI is always in [0, 100] for valid (non-NaN) bars."""
    rng = np.random.default_rng(42)
    closes = _series(list(rng.uniform(50, 200, 100)))
    rsi = compute_rsi(closes)
    valid = rsi.dropna()
    assert (valid >= 0.0).all() and (valid <= 100.0).all()


# ---------------------------------------------------------------------------
# SMA
# ---------------------------------------------------------------------------

def test_sma_warmup() -> None:
    """First n-1 bars are NaN."""
    s = sma(_series([1.0] * 10), 5)
    for i in range(4):
        assert _isnan(s.iloc[i])


def test_sma_correct_value() -> None:
    """SMA(3) at bar 2 = mean of first 3 values."""
    s = sma(_series([1.0, 2.0, 3.0, 4.0, 5.0]), 3)
    assert s.iloc[2] == pytest.approx(2.0)
    assert s.iloc[3] == pytest.approx(3.0)
    assert s.iloc[4] == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# EMA
# ---------------------------------------------------------------------------

def test_ema_warmup() -> None:
    """EMA(n) produces NaN until n bars are available."""
    s = ema(_series([5.0] * 10), n=5)
    for i in range(4):
        assert _isnan(s.iloc[i])


def test_ema_constant_series() -> None:
    """EMA of a constant series converges to that constant."""
    s = ema(_series([7.0] * 30), n=5)
    valid = s.dropna()
    assert all(v == pytest.approx(7.0) for v in valid.tolist())


# ---------------------------------------------------------------------------
# ATR
# ---------------------------------------------------------------------------

def test_atr_warmup() -> None:
    """ATR(14) is NaN for first 13 bars."""
    h = _series([110.0] * 20)
    lo = _series([90.0] * 20)
    c = _series([100.0] * 20)
    result = atr(h, lo, c, period=14)
    for i in range(13):
        assert _isnan(result.iloc[i])


def test_atr_positive() -> None:
    """ATR is always positive for any OHLC where H > L."""
    rng = np.random.default_rng(99)
    lo = _series(list(rng.uniform(80, 100, 50)))
    h = lo + _series(list(rng.uniform(1, 20, 50)))
    c = lo + (h - lo) * 0.5
    result = atr(h, lo, c)
    valid = result.dropna()
    assert (valid > 0.0).all()


def test_atr_constant_range() -> None:
    """ATR converges to TR when H-L is constant."""
    h = _series([110.0] * 30)
    lo = _series([90.0] * 30)
    c = _series([100.0] * 30)
    result = atr(h, lo, c, period=14)
    valid = result.dropna()
    assert all(v == pytest.approx(20.0) for v in valid.tolist())


# ---------------------------------------------------------------------------
# MACD
# ---------------------------------------------------------------------------

def test_macd_warmup() -> None:
    """MACD signal is NaN until bar 33 (0-indexed).

    EMA(26) first valid at bar 25; signal EMA(9) needs 9 MACD values → bar 25+8=33.
    Bars 0–32 (33 bars) are NaN; bar 33 is the first valid signal.
    """
    closes = _series([100.0] * 40)
    _, signal = macd(closes)
    assert all(_isnan(signal.iloc[i]) for i in range(33))  # bars 0-32 are NaN
    assert not _isnan(signal.iloc[33]), "bar 33 should be the first valid signal"


def test_macd_constant_series_zero() -> None:
    """MACD line = 0 for constant series (all EMAs equal the constant)."""
    closes = _series([100.0] * 60)
    m_line, _ = macd(closes)
    valid = m_line.dropna()
    assert all(v == pytest.approx(0.0) for v in valid.tolist())


# ---------------------------------------------------------------------------
# Bollinger Bands
# ---------------------------------------------------------------------------

def test_bollinger_warmup() -> None:
    """Bollinger bands are NaN for first n-1 bars."""
    closes = _series([100.0] * 25)
    upper, mid, lower = bollinger(closes, n=20)
    for i in range(19):
        assert _isnan(upper.iloc[i])


def test_bollinger_ordering() -> None:
    """upper ≥ mid ≥ lower for all valid (non-NaN) bars."""
    rng = np.random.default_rng(7)
    closes = _series(list(rng.uniform(100, 200, 50)))
    upper, mid, lower = bollinger(closes, n=20)
    for i in range(len(closes)):
        if not (_isnan(upper.iloc[i]) or _isnan(lower.iloc[i])):
            assert upper.iloc[i] >= mid.iloc[i] >= lower.iloc[i]


def test_bollinger_constant_std_zero() -> None:
    """Constant series → std = 0 → upper = mid = lower."""
    closes = _series([50.0] * 25)
    upper, mid, lower = bollinger(closes, n=20)
    valid_u = upper.dropna()
    valid_l = lower.dropna()
    assert all(v == pytest.approx(50.0) for v in valid_u.tolist())
    assert all(v == pytest.approx(50.0) for v in valid_l.tolist())


# ---------------------------------------------------------------------------
# ADX
# ---------------------------------------------------------------------------

def test_adx_warmup_nan_not_zero() -> None:
    """ADX(14) is NaN (never 0) during warm-up (~28 bars)."""
    h = _series([110.0] * 50)
    lo = _series([90.0] * 50)
    c = _series([100.0] * 50)
    result = adx_14(h, lo, c)
    for i in range(13):
        # During warm-up, should be NaN
        assert _isnan(result.iloc[i]), f"bar {i}: expected NaN, got {result.iloc[i]}"


def test_adx_range() -> None:
    """ADX is in [0, 100] for valid bars."""
    rng = np.random.default_rng(17)
    lo = pd.Series(list(rng.uniform(80, 100, 80)),
                   index=pd.date_range("2024-01-01", periods=80, freq="B"))
    h = lo + pd.Series(list(rng.uniform(1, 20, 80)), index=lo.index)
    c = lo + (h - lo) * 0.5
    result = adx_14(h, lo, c)
    valid = result.dropna()
    assert (valid >= 0.0).all() and (valid <= 100.0).all()


def test_adx_trending_market() -> None:
    """Monotonically rising prices → ADX should eventually be > 20 (strong trend)."""
    closes = _series([float(i) for i in range(1, 81)])
    h = closes * 1.01
    lo = closes * 0.99
    result = adx_14(h, lo, closes)
    # Take last 20 valid values
    valid = result.dropna().tail(20)
    assert (valid > 20.0).any(), "Trending market should show ADX > 20"


# ---------------------------------------------------------------------------
# Stochastic RSI
# ---------------------------------------------------------------------------

def test_stoch_rsi_warmup() -> None:
    """Stochastic RSI is NaN during warm-up (rsi_period + stoch_period + smoothing)."""
    closes = _series([100.0] * 50)
    k, d = stoch_rsi(closes)
    # At minimum the first rsi_period bars of RSI are NaN, so stoch_rsi_k starts later
    for i in range(14):
        assert _isnan(k.iloc[i])


def test_stoch_rsi_range() -> None:
    """Stochastic RSI %K and %D are in [0, 100] when valid."""
    rng = np.random.default_rng(33)
    closes = _series(list(rng.uniform(100, 200, 100)))
    k, d = stoch_rsi(closes)
    valid_k = k.dropna()
    valid_d = d.dropna()
    assert (valid_k >= 0.0).all() and (valid_k <= 100.0).all()
    assert (valid_d >= 0.0).all() and (valid_d <= 100.0).all()


def test_stoch_rsi_flat_window_nan() -> None:
    """Flat RSI window (max==min) → NaN, not divide-by-zero."""
    closes = _series([100.0] * 50)
    k, _ = stoch_rsi(closes)
    # Constant series → RSI = 100 always → stoch range = 0 → NaN
    valid = k.dropna()
    assert len(valid) == 0 or (valid.isna().all())


# ---------------------------------------------------------------------------
# Pivot Points
# ---------------------------------------------------------------------------

def test_pivots_use_prior_session() -> None:
    """Pivot is computed from previous session's H/L/C, so first row is NaN."""
    h = _series([110.0, 115.0, 120.0])
    lo = _series([90.0, 95.0, 100.0])
    c = _series([100.0, 105.0, 110.0])
    p = pivots(h, lo, c)
    assert _isnan(p["pivot"].iloc[0])


def test_pivots_golden_values() -> None:
    """Classic formula: pivot=(H+L+C)/3; R1=2P-L; S1=2P-H; R2=P+(H-L); S2=P-(H-L)."""
    h = _series([120.0, 130.0])
    lo = _series([100.0, 110.0])
    c = _series([115.0, 125.0])
    p = pivots(h, lo, c)

    # At index 1: prior session H=120, L=100, C=115
    prev_h, prev_l, prev_c = 120.0, 100.0, 115.0
    expected_pivot = (prev_h + prev_l + prev_c) / 3.0  # 111.667
    expected_r1 = 2.0 * expected_pivot - prev_l         # 123.333
    expected_r2 = expected_pivot + (prev_h - prev_l)    # 131.667
    expected_s1 = 2.0 * expected_pivot - prev_h         # 103.333
    expected_s2 = expected_pivot - (prev_h - prev_l)    # 91.667

    assert p["pivot"].iloc[1]    == pytest.approx(expected_pivot, rel=1e-5)
    assert p["pivot_r1"].iloc[1] == pytest.approx(expected_r1, rel=1e-5)
    assert p["pivot_r2"].iloc[1] == pytest.approx(expected_r2, rel=1e-5)
    assert p["pivot_s1"].iloc[1] == pytest.approx(expected_s1, rel=1e-5)
    assert p["pivot_s2"].iloc[1] == pytest.approx(expected_s2, rel=1e-5)


def test_pivots_keys() -> None:
    """pivots() returns a dict with exactly the expected 5 keys."""
    h = _series([110.0] * 3)
    lo = _series([90.0] * 3)
    c = _series([100.0] * 3)
    p = pivots(h, lo, c)
    assert set(p.keys()) == {"pivot", "pivot_r1", "pivot_r2", "pivot_s1", "pivot_s2"}
