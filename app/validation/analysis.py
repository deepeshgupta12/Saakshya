"""Quantile / IC analysis for M3b score validation (docs/15 §4, docs/13 §7.1).

Framing: all outputs are historical characterizations of score-to-label separation.
Never reword separation evidence as expected return or performance promise (SPEC §3.3).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats


@dataclass
class ValidationMetrics:
    """Summary statistics from the M3b IC + decile analysis."""

    horizons: tuple[int, ...]
    n_observations: int
    n_dates: int
    n_symbols: int

    # Per horizon: Spearman ρ of decile rank → mean forward RS.
    decile_spearman: dict[int, float] = field(default_factory=dict)

    # Per horizon: (top-decile mean RS) − (bottom-decile mean RS).
    top_bottom_spread: dict[int, float] = field(default_factory=dict)

    # Per horizon: mean IC, std IC, IC t-stat, fraction of dates with IC > 0.
    ic_mean:     dict[int, float] = field(default_factory=dict)
    ic_std:      dict[int, float] = field(default_factory=dict)
    ic_tstat:    dict[int, float] = field(default_factory=dict)
    ic_hit_rate: dict[int, float] = field(default_factory=dict)

    # Per horizon, per regime: top-bottom spread (regime stability check).
    regime_spread: dict[int, dict[str, float]] = field(default_factory=dict)

    # Per horizon, per sector: top-bottom spread (sector stability check).
    sector_spread: dict[int, dict[str, float]] = field(default_factory=dict)


def analyze(
    df: pd.DataFrame,
    horizons: tuple[int, ...] = (21, 63),
    n_deciles: int = 10,
) -> ValidationMetrics:
    """Run the full decile / IC / stratified analysis on the validation dataset.

    Args:
        df: Output of dataset.build_validation_dataset. Must have columns:
            symbol, score_date, momentum_raw, forward_rs_{h}d (for each h),
            regime (optional), sector (optional).
        horizons: Forward-RS horizons (trading days) to analyse.
        n_deciles: Number of deciles for bucketing (default 10).

    Returns:
        ValidationMetrics with all measurements. Regime/sector spread use
        "N/A" when the strat column is absent or has insufficient coverage.
    """
    score_col = "momentum_raw"
    n_obs = len(df)
    n_dates = df["score_date"].nunique() if "score_date" in df.columns else 0
    n_syms  = df["symbol"].nunique() if "symbol" in df.columns else 0

    metrics = ValidationMetrics(
        horizons=horizons,
        n_observations=n_obs,
        n_dates=n_dates,
        n_symbols=n_syms,
    )

    for h in horizons:
        label_col = f"forward_rs_{h}d"
        if label_col not in df.columns:
            continue

        sub = df[[score_col, label_col, "score_date"]].dropna()
        if sub.empty:
            continue

        # Decile analysis
        decile_tbl = compute_decile_table(sub, score_col, label_col, n_deciles)
        if not decile_tbl.empty:
            rho = decile_tbl["decile"].corr(decile_tbl["mean_fwd_rs"], method="spearman")
            metrics.decile_spearman[h] = float(rho) if not math.isnan(rho) else 0.0
            top_mean = float(decile_tbl["mean_fwd_rs"].iloc[-1])
            bot_mean = float(decile_tbl["mean_fwd_rs"].iloc[0])
            metrics.top_bottom_spread[h] = top_mean - bot_mean

        # IC analysis
        ic_series = compute_ic_series(sub, score_col, label_col, "score_date")
        ic_stats  = compute_ic_stats(ic_series)
        metrics.ic_mean[h]     = ic_stats["ic_mean"]
        metrics.ic_std[h]      = ic_stats["ic_std"]
        metrics.ic_tstat[h]    = ic_stats["ic_tstat"]
        metrics.ic_hit_rate[h] = ic_stats["ic_hit_rate"]

        # Stratified: regime
        if "regime" in df.columns:
            strat_sub = df[[score_col, label_col, "regime"]].dropna()
            metrics.regime_spread[h] = compute_stratified_spread(
                strat_sub, score_col, label_col, "regime", n_deciles
            )

        # Stratified: sector
        if "sector" in df.columns:
            strat_sub = df[[score_col, label_col, "sector"]].dropna()
            metrics.sector_spread[h] = compute_stratified_spread(
                strat_sub, score_col, label_col, "sector", n_deciles
            )

    return metrics


def compute_decile_table(
    df: pd.DataFrame,
    score_col: str,
    label_col: str,
    n_deciles: int = 10,
) -> pd.DataFrame:
    """Bucket observations into score deciles; compute mean/median forward RS per decile.

    Returns a DataFrame with columns: decile (1=lowest), mean_fwd_rs, median_fwd_rs, count.
    """
    sub = df[[score_col, label_col]].dropna()
    if len(sub) < n_deciles * 2:
        return pd.DataFrame()

    sub = sub.copy()
    sub["decile"] = pd.qcut(sub[score_col], q=n_deciles, labels=False, duplicates="drop")
    sub["decile"] = sub["decile"] + 1  # 1-indexed

    table = (
        sub.groupby("decile")[label_col]
        .agg(mean_fwd_rs="mean", median_fwd_rs="median", count="count")
        .reset_index()
    )
    return table


def compute_ic_series(
    df: pd.DataFrame,
    score_col: str,
    label_col: str,
    date_col: str,
) -> pd.Series:
    """Compute cross-sectional Spearman rank IC per date.

    IC = Spearman rank correlation of score vs forward RS within each date.
    Returns a pd.Series indexed by date.
    """
    ic_records: dict[object, float] = {}
    for date_val, group in df.groupby(date_col):
        sub = group[[score_col, label_col]].dropna()
        if len(sub) < 5:
            continue
        rho, _ = scipy_stats.spearmanr(sub[score_col], sub[label_col])
        if not math.isnan(rho):
            ic_records[date_val] = float(rho)

    return pd.Series(ic_records, name="ic")


def compute_ic_stats(ic_series: pd.Series) -> dict[str, float]:
    """Aggregate IC time series into summary statistics."""
    if ic_series.empty:
        return {"ic_mean": 0.0, "ic_std": 0.0, "ic_tstat": 0.0, "ic_hit_rate": 0.0}

    ic_arr = ic_series.dropna().values
    n = len(ic_arr)
    if n == 0:
        return {"ic_mean": 0.0, "ic_std": 0.0, "ic_tstat": 0.0, "ic_hit_rate": 0.0}

    ic_mean     = float(np.mean(ic_arr))
    ic_std      = float(np.std(ic_arr, ddof=1)) if n > 1 else 0.0
    ic_tstat    = (ic_mean / ic_std * math.sqrt(n)) if ic_std > 0.0 else 0.0
    ic_hit_rate = float(np.mean(ic_arr > 0.0))

    return {
        "ic_mean":     ic_mean,
        "ic_std":      ic_std,
        "ic_tstat":    ic_tstat,
        "ic_hit_rate": ic_hit_rate,
    }


def compute_stratified_spread(
    df: pd.DataFrame,
    score_col: str,
    label_col: str,
    strat_col: str,
    n_deciles: int = 10,
) -> dict[str, float]:
    """Top-minus-bottom decile spread per stratum (regime, sector)."""
    spreads: dict[str, float] = {}
    for stratum, group in df.groupby(strat_col):
        sub = group[[score_col, label_col]].dropna()
        tbl = compute_decile_table(sub, score_col, label_col, n_deciles)
        if tbl.empty or len(tbl) < 2:
            spreads[str(stratum)] = float("nan")
            continue
        top  = float(tbl["mean_fwd_rs"].iloc[-1])
        bot  = float(tbl["mean_fwd_rs"].iloc[0])
        spreads[str(stratum)] = top - bot
    return spreads


def metrics_to_dict(m: ValidationMetrics) -> dict[str, object]:
    """Serialize ValidationMetrics to a plain dict for JSON / decision log."""
    return {
        "horizons":          list(m.horizons),
        "n_observations":    m.n_observations,
        "n_dates":           m.n_dates,
        "n_symbols":         m.n_symbols,
        "decile_spearman":   m.decile_spearman,
        "top_bottom_spread": m.top_bottom_spread,
        "ic_mean":           m.ic_mean,
        "ic_std":            m.ic_std,
        "ic_tstat":          m.ic_tstat,
        "ic_hit_rate":       m.ic_hit_rate,
        "regime_spread":     m.regime_spread,
        "sector_spread":     m.sector_spread,
    }
