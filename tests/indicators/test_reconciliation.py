"""M2 gate: indicator reconciliation vs a 2nd source (SPEC §12 M2, docs/02 §Tests).

Verifies our indicator implementations match hand-computed expected values derived
independently from the documented formulas — the "2nd source" for this golden series.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from app.indicators.core import bollinger, compute_rsi, macd, pivots, sma
from app.indicators.returns import total_return, volume_ratio_20


def _s(vals: list[float]) -> pd.Series:
    return pd.Series(vals, index=pd.date_range("2024-01-01", periods=len(vals), freq="B"))


# ---------------------------------------------------------------------------
# RSI — Wilder's method, cross-checked against formula
# ---------------------------------------------------------------------------

def test_rsi_reconcile_ewm_formula() -> None:
    """Verify RSI at bar 14 from independent EWM formula calculation.

    Series: 100, 99, 98, ..., 87 (13 drops), 88 (1 rise).
    EWM(alpha=1/14, adjust=False) applied to gains and losses:
      gains  at bars 1-13 = 0, at bar 14 = 1 → EWM[14] = (1/14)*1 + (13/14)*0 = 1/14
      losses at bars 1-13 = 1, at bar 14 = 0 → EWM[14] = (1/14)*0 + (13/14)*1 = 13/14
    RS = (1/14)/(13/14) = 1/13
    RSI = 100 - 100/(1 + 1/13) = 100*(1 - 13/14) = 100/14 ≈ 7.143
    """
    closes = _s([float(100 - i) for i in range(14)] + [88.0])
    rsi = compute_rsi(closes, 14)
    assert rsi.iloc[14] == pytest.approx(100.0 / 14.0, rel=1e-6)


# ---------------------------------------------------------------------------
# SMA — cross-checked against rolling mean
# ---------------------------------------------------------------------------

def test_sma_reconcile_rolling_mean() -> None:
    """SMA(5) at bar 9 == mean of bars 5–9 == 8.0 for [1…10]."""
    closes = _s(list(range(1, 11)))  # [1,2,3,4,5,6,7,8,9,10]
    result = sma(closes, 5)
    # bar 4: mean([1,2,3,4,5]) = 3.0
    assert result.iloc[4] == pytest.approx(3.0)
    # bar 9: mean([6,7,8,9,10]) = 8.0
    assert result.iloc[9] == pytest.approx(8.0)


# ---------------------------------------------------------------------------
# Bollinger — cross-checked against numpy std
# ---------------------------------------------------------------------------

def test_bollinger_reconcile_std() -> None:
    """Bollinger upper = SMA(20) + 2×std(20) — verify against numpy."""
    import numpy as np
    vals = list(range(1, 31))   # [1..30], 30 bars
    closes = _s([float(v) for v in vals])
    upper, mid, lower = bollinger(closes, n=20, k=2.0)

    # At bar 19: window is [1..20]
    window = [float(v) for v in range(1, 21)]
    expected_mid = sum(window) / 20
    # ddof=1 sample std
    expected_std = float(np.std(window, ddof=1))
    assert mid.iloc[19] == pytest.approx(expected_mid, rel=1e-10)
    assert upper.iloc[19] == pytest.approx(expected_mid + 2 * expected_std, rel=1e-10)
    assert lower.iloc[19] == pytest.approx(expected_mid - 2 * expected_std, rel=1e-10)


# ---------------------------------------------------------------------------
# MACD — cross-checked against formula
# ---------------------------------------------------------------------------

def test_macd_line_equals_ema_diff() -> None:
    """MACD line == EMA(12) - EMA(26) at each bar."""
    from app.indicators.core import ema
    rng_vals = [float(100 + i % 7 - 3) for i in range(60)]
    closes = _s(rng_vals)
    macd_line, _ = macd(closes)
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    expected = ema12 - ema26
    for i in range(26, 60):
        if not math.isnan(macd_line.iloc[i]):
            assert macd_line.iloc[i] == pytest.approx(expected.iloc[i], rel=1e-10)


# ---------------------------------------------------------------------------
# Pivots — cross-checked against floor-trader formula
# ---------------------------------------------------------------------------

def test_pivots_reconcile_formula() -> None:
    """Pivot levels at bar 1 match (H+L+C)/3 floor-trader formula for prior bar."""
    h = _s([120.0, 130.0, 140.0])
    lo = _s([100.0, 110.0, 120.0])
    c = _s([115.0, 125.0, 135.0])
    p = pivots(h, lo, c)

    # At bar 2, prior session = bar 1: H=130, L=110, C=125
    ph, pl, pc = 130.0, 110.0, 125.0
    piv = (ph + pl + pc) / 3.0
    assert p["pivot"].iloc[2]    == pytest.approx(piv, rel=1e-10)
    assert p["pivot_r1"].iloc[2] == pytest.approx(2 * piv - pl, rel=1e-10)
    assert p["pivot_r2"].iloc[2] == pytest.approx(piv + (ph - pl), rel=1e-10)
    assert p["pivot_s1"].iloc[2] == pytest.approx(2 * piv - ph, rel=1e-10)
    assert p["pivot_s2"].iloc[2] == pytest.approx(piv - (ph - pl), rel=1e-10)


# ---------------------------------------------------------------------------
# total_return — cross-checked
# ---------------------------------------------------------------------------

def test_total_return_reconcile() -> None:
    """(close_t / close_(t-n)) - 1 matches pandas pct_change."""
    closes = _s([100.0, 105.0, 110.25, 115.76, 121.55])
    result = total_return(closes, 2)
    # Bar 2: (110.25/100) - 1 = 0.1025
    assert result.iloc[2] == pytest.approx(0.1025, rel=1e-5)
    # Bar 4: (121.55/110.25) - 1
    assert result.iloc[4] == pytest.approx(121.55 / 110.25 - 1, rel=1e-5)


# ---------------------------------------------------------------------------
# volume_ratio_20 — cross-checked
# ---------------------------------------------------------------------------

def test_volume_ratio_reconcile() -> None:
    """volume / sma(volume, 20) — cross-check at bar 20."""
    base = [1000.0] * 20
    closes = _s(base + [3000.0])
    result = volume_ratio_20(closes)
    # sma20 at bar 19 = 1000.0 (all equal); bar 20: volume=3000, avg=1000 → ratio=3.0
    assert result.iloc[20] == pytest.approx(3.0, rel=1e-10)
