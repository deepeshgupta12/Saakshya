"""Point-in-time validation dataset builder for M3b (docs/steps/03, SPEC §6.5).

For each eligible stock at each historical date t:
  - Computes the momentum sub-score using ONLY data available at t (no look-ahead).
  - Computes realized forward relative strength vs Nifty over 21d and 63d (label).
  - Classifies the market regime at t (BULL / BEAR / SIDEWAYS).

The output is a panel DataFrame written to data/validation/ for reproducibility.

No-look-ahead guarantee: indicator time series are computed as rolling windows that
end at each bar date. Extracting indicator_ts.loc[t] uses only data up to and
including t. Labels use only candles in (t, t+horizon].
"""

from __future__ import annotations

import math
from datetime import date

import pandas as pd

from app.indicators.returns import relative_strength, total_return
from app.scanners.normalize import NEUTRAL, is_neutral, pct_rank

_NAN = float("nan")

# Minimum history (bars) before a stock is eligible at date t.
_MIN_HISTORY_DEFAULT = 200


def build_validation_dataset(
    prices: dict[str, pd.Series],
    nifty: pd.Series,
    start_date: date,
    end_date: date,
    horizons: tuple[int, ...] = (21, 63),
    sectors: dict[str, str] | None = None,
    min_history: int = _MIN_HISTORY_DEFAULT,
) -> pd.DataFrame:
    """Build a point-in-time, leak-free score↔forward-RS panel.

    Args:
        prices:     {symbol: adjusted-close Series with DatetimeIndex}.
        nifty:      Nifty 50 adjusted close with DatetimeIndex.
        start_date: First date to include in the panel (must be after min_history bars).
        end_date:   Last date to include in the panel.
        horizons:   Forward-RS measurement windows (trading days).
        sectors:    Optional {symbol: sector} mapping.
        min_history: Bars of history a stock must have before it is scored at t.

    Returns:
        DataFrame with columns:
            symbol, score_date, momentum_raw,
            forward_rs_{h}d (for each h in horizons),
            regime, sector.
        Only rows with a valid momentum_raw are included.
        Rows where the forward label cannot be computed (insufficient future data)
        have NaN labels — they are included so the universe coverage is visible.
    """
    ts_start = pd.Timestamp(start_date)
    ts_end   = pd.Timestamp(end_date)

    # Precompute rolling indicator series for each symbol (all point-in-time).
    indicator_ts: dict[str, pd.DataFrame] = {}
    for symbol, close in prices.items():
        indicator_ts[symbol] = _precompute_indicators(close, nifty)

    # Build a sorted list of scoring dates within [start_date, end_date].
    all_dates: set[pd.Timestamp] = set()
    for df in indicator_ts.values():
        all_dates.update(df.index[(df.index >= ts_start) & (df.index <= ts_end)])
    scoring_dates = sorted(all_dates)

    nifty_aligned_cache: dict[str, pd.Series] = {}

    rows: list[dict[str, object]] = []
    for t in scoring_dates:
        # Snapshot: indicator values at t for every eligible stock.
        universe_panel: dict[str, dict[str, float]] = {}
        for symbol, close in prices.items():
            ind_df = indicator_ts[symbol]
            if t not in ind_df.index:
                continue
            bars_up_to_t = (close.index <= t).sum()
            if bars_up_to_t < min_history:
                continue
            row = ind_df.loc[t]
            universe_panel[symbol] = {
                "ret_21d":          float(row["ret_21d"]),
                "ret_63d":          float(row["ret_63d"]),
                "ret_126d":         float(row["ret_126d"]),
                "rel_strength_63d": float(row["rel_strength_63d"]),
            }

        # Cross-sectional momentum_raw scores at t (mirrors momentum.py logic).
        scores_at_t = _score_universe_at(universe_panel)
        regime = _regime_at(nifty, t)

        for symbol, raw_score in scores_at_t.items():
            if is_neutral(raw_score):
                continue
            close = prices[symbol]
            if symbol not in nifty_aligned_cache:
                nifty_aligned_cache[symbol] = nifty.reindex(close.index, method="ffill")
            nifty_aligned = nifty_aligned_cache[symbol]

            record: dict[str, object] = {
                "symbol":       symbol,
                "score_date":   t.date(),
                "momentum_raw": raw_score,
                "regime":       regime,
                "sector":       (sectors or {}).get(symbol),
            }
            for h in horizons:
                record[f"forward_rs_{h}d"] = _forward_rs(close, nifty_aligned, t, h)

            rows.append(record)

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _precompute_indicators(close: pd.Series, nifty: pd.Series) -> pd.DataFrame:
    """Compute rolling return indicators for a stock. All values are point-in-time."""
    nifty_aligned = nifty.reindex(close.index, method="ffill")
    ret_21  = total_return(close, 21)
    ret_63  = total_return(close, 63)
    ret_126 = total_return(close, 126)
    rs_63   = relative_strength(close, nifty_aligned, 63)
    return pd.DataFrame(
        {
            "ret_21d":          ret_21,
            "ret_63d":          ret_63,
            "ret_126d":         ret_126,
            "rel_strength_63d": rs_63,
        },
        index=close.index,
    )


def _score_universe_at(
    panel: dict[str, dict[str, float]],
) -> dict[str, float]:
    """Compute momentum_raw for every stock in a cross-sectional snapshot.

    Mirrors app/scanners/momentum.py without the _ENTER_RAW entrance threshold
    so validation covers the full distribution, not just top-scoring names.
    """
    blended_rets: list[float] = []
    rs3m_vals:    list[float] = []

    for ind in panel.values():
        r1  = _f(ind.get("ret_21d"))
        r3  = _f(ind.get("ret_63d"))
        r6  = _f(ind.get("ret_126d"))
        rs3 = _f(ind.get("rel_strength_63d"))
        if not any(is_neutral(v) for v in [r1, r3, r6, rs3]):
            bl = 0.5 * r3 + 0.3 * r6 + 0.2 * r1
            blended_rets.append(bl)
            rs3m_vals.append(rs3)

    scores: dict[str, float] = {}
    for symbol, ind in panel.items():
        r1  = _f(ind.get("ret_21d"))
        r3  = _f(ind.get("ret_63d"))
        r6  = _f(ind.get("ret_126d"))
        rs3 = _f(ind.get("rel_strength_63d"))
        if any(is_neutral(v) for v in [r1, r3, r6, rs3]):
            scores[symbol] = NEUTRAL
            continue
        bl = 0.5 * r3 + 0.3 * r6 + 0.2 * r1
        scores[symbol] = (
            0.6 * pct_rank(bl,  blended_rets)
            + 0.4 * pct_rank(rs3, rs3m_vals)
        )

    return scores


def _forward_rs(
    close: pd.Series,
    nifty_aligned: pd.Series,
    t: pd.Timestamp,
    horizon: int,
) -> float:
    """Realized forward relative strength of stock vs Nifty from t over horizon bars.

    Uses only candles STRICTLY AFTER t — enforcing the label/score partition.
    Returns NaN when there are not enough future bars.
    """
    future_close  = close.loc[close.index > t]
    future_nifty  = nifty_aligned.loc[nifty_aligned.index > t]

    if len(future_close) < horizon or len(future_nifty) < horizon:
        return _NAN

    if t not in close.index or t not in nifty_aligned.index:
        return _NAN

    p0 = float(close.loc[t])
    n0 = float(nifty_aligned.loc[t])
    ph = float(future_close.iloc[horizon - 1])
    nh = float(future_nifty.iloc[horizon - 1])

    if any(math.isnan(v) or v == 0.0 for v in [p0, n0, ph, nh]):
        return _NAN

    stock_ret = ph / p0 - 1.0
    nifty_ret = nh / n0 - 1.0
    return stock_ret - nifty_ret


def _regime_at(nifty: pd.Series, t: pd.Timestamp) -> str:
    """BULL / BEAR / SIDEWAYS based on Nifty trailing 252-bar return at t."""
    past = nifty.loc[nifty.index <= t]
    if len(past) < 252:
        return "UNKNOWN"
    ret_12m = float(past.iloc[-1]) / float(past.iloc[-252]) - 1.0
    if math.isnan(ret_12m):
        return "UNKNOWN"
    if ret_12m > 0.10:
        return "BULL"
    if ret_12m < -0.10:
        return "BEAR"
    return "SIDEWAYS"


def _f(v: object) -> float:
    """Coerce to float; return NEUTRAL on failure."""
    if v is None:
        return NEUTRAL
    try:
        fv = float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return NEUTRAL
    return fv
