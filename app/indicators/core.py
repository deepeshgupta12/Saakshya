"""Vectorized price indicators — pure functions on pd.Series (SPEC §9, docs/27 §7.3).

All functions:
- Operate on the **adjusted** series (adjusted close/high/low for ATR/ADX).
- Return pd.Series aligned to the input index.
- Use NaN for warm-up periods — never fabricate a value before sufficient history.
- Use no TA-Lib; all computations are vectorized pandas/NumPy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI on adjusted close. Returns NaN for first period-1 bars.

    avg_loss == 0 (all gains) → 100.0; avg_gain == 0 (all losses) → 0.0.
    Result bounded [0, 100].
    """
    delta = closes.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi = rsi.where(avg_loss != 0.0, other=100.0)
    return rsi.rename("rsi_14")


def sma(series: pd.Series, n: int) -> pd.Series:
    """Simple moving average. NaN until n periods are available."""
    return series.rolling(n, min_periods=n).mean()


def ema(series: pd.Series, n: int = 21) -> pd.Series:
    """Exponential moving average (span=n). NaN until n periods are available."""
    return series.ewm(span=n, min_periods=n, adjust=False).mean()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder ATR(period) on adjusted H/L/C. TR = max(H-L, |H-Cp|, |L-Cp|)."""
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(com=period - 1, min_periods=period, adjust=False).mean().rename("atr_14")


def macd(
    closes: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series]:
    """MACD line (EMA_fast - EMA_slow) and signal line (EMA of MACD).

    Both series carry NaN during their respective warm-ups.
    """
    ema_fast = closes.ewm(span=fast, min_periods=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, min_periods=slow, adjust=False).mean()
    macd_line = (ema_fast - ema_slow).rename("macd_line")
    signal_line = (
        macd_line.ewm(span=signal, min_periods=signal, adjust=False).mean()
        .rename("macd_signal")
    )
    return macd_line, signal_line


def bollinger(
    closes: pd.Series,
    n: int = 20,
    k: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands (SMA ± k × rolling std). NaN for first n-1 bars."""
    mid = closes.rolling(n, min_periods=n).mean().rename("bb_mid")
    std = closes.rolling(n, min_periods=n).std(ddof=1)
    upper = (mid + k * std).rename("bb_upper")
    lower = (mid - k * std).rename("bb_lower")
    return upper, mid, lower


def adx_14(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Wilder ADX(period): trend-strength 0–100, direction-agnostic.

    Warm-up is ~2×period bars; NaN until then, never 0 during warm-up.
    """
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=high.index,
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=high.index,
    )
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)

    plus_dm_s = plus_dm.ewm(com=period - 1, min_periods=period, adjust=False).mean()
    minus_dm_s = minus_dm.ewm(com=period - 1, min_periods=period, adjust=False).mean()
    tr_s = tr.ewm(com=period - 1, min_periods=period, adjust=False).mean()

    plus_di = 100.0 * plus_dm_s / tr_s.replace(0.0, np.nan)
    minus_di = 100.0 * minus_dm_s / tr_s.replace(0.0, np.nan)
    di_sum = plus_di + minus_di
    dx = 100.0 * (plus_di - minus_di).abs() / di_sum.replace(0.0, np.nan)
    return dx.ewm(com=period - 1, min_periods=period, adjust=False).mean().rename("adx_14")


def stoch_rsi(
    closes: pd.Series,
    rsi_period: int = 14,
    stoch_period: int = 14,
    k_smooth: int = 3,
    d_smooth: int = 3,
) -> tuple[pd.Series, pd.Series]:
    """Stochastic RSI: stochastic transform of RSI(14) → %K / %D, range 0–100.

    Flat-window guard: when max(rsi, period) == min(rsi, period) → NaN; never div-by-zero.
    """
    rsi = compute_rsi(closes, rsi_period)
    rsi_min = rsi.rolling(stoch_period, min_periods=stoch_period).min()
    rsi_max = rsi.rolling(stoch_period, min_periods=stoch_period).max()
    rsi_range = rsi_max - rsi_min
    stoch_raw = (rsi - rsi_min) / rsi_range.replace(0.0, np.nan) * 100.0
    k = stoch_raw.rolling(k_smooth, min_periods=k_smooth).mean().rename("stoch_rsi_k")
    d = k.rolling(d_smooth, min_periods=d_smooth).mean().rename("stoch_rsi_d")
    return k, d


def pivots(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
) -> dict[str, pd.Series]:
    """Classic floor-trader pivot points from the **previous session's** H/L/C.

    First row is NaN (no prior session). Descriptive support/resistance only —
    no entry/target semantics (docs/13 §3.5, SPEC §5).
    """
    ph = high.shift(1)
    pl = low.shift(1)
    pc = close.shift(1)
    p = (ph + pl + pc) / 3.0
    r1 = (2.0 * p - pl).rename("pivot_r1")
    r2 = (p + (ph - pl)).rename("pivot_r2")
    s1 = (2.0 * p - ph).rename("pivot_s1")
    s2 = (p - (ph - pl)).rename("pivot_s2")
    return {
        "pivot": p.rename("pivot"),
        "pivot_r1": r1,
        "pivot_r2": r2,
        "pivot_s1": s1,
        "pivot_s2": s2,
    }
