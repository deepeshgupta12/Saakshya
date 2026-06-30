"""Multi-window return, volume-ratio, and relative-strength computations.

All functions operate on **adjusted** series (docs/13 §4.1, docs/02 §2).
"""

from __future__ import annotations

import pandas as pd


def total_return(closes: pd.Series, window: int) -> pd.Series:
    """Total return over `window` periods: (close_t / close_(t-window)) - 1.

    Returns NaN for the first `window` bars.
    """
    return closes.pct_change(periods=window)


def volume_ratio_20(volume: pd.Series) -> pd.Series:
    """Current volume / prior 20-period SMA(volume). NaN for first 20 bars.

    Uses shift(1) so today's spike does not inflate the denominator.
    Denominator 0 → NaN (never divides by zero).
    """
    avg = volume.rolling(20, min_periods=20).mean().shift(1)
    return (volume / avg.replace(0.0, float("nan"))).rename("volume_ratio_20")


def relative_strength(
    stock_closes: pd.Series,
    bench_closes: pd.Series,
    window: int,
) -> pd.Series:
    """RS = total_return(stock, window) − total_return(bench, window).

    Used for 3-month RS vs Nifty 50 (window=63) in the momentum scanner.
    """
    return (total_return(stock_closes, window) - total_return(bench_closes, window)).rename(
        f"rel_strength_{window}d"
    )
