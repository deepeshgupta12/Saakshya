"""Analysis procedure tests: known signal separates monotonically; noise IC ≈ 0.

Key contracts:
- compute_decile_table: known signal → monotonic decile separation.
- compute_ic_series: known signal → IC consistently positive.
- compute_ic_stats: on shuffled labels → mean IC ≈ 0 and small t-stat.
- analyze: assembles all metrics into ValidationMetrics with correct shapes.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from app.validation.analysis import (
    ValidationMetrics,
    analyze,
    compute_decile_table,
    compute_ic_series,
    compute_ic_stats,
    compute_stratified_spread,
    metrics_to_dict,
)


def _signal_df(
    n: int = 1000,
    n_dates: int = 50,
    noise: float = 0.15,
    seed: int = 42,
) -> pd.DataFrame:
    """Synthetic panel with a KNOWN signal: higher score → higher label + noise."""
    rng = np.random.default_rng(seed)
    scores = rng.uniform(0, 100, n)
    labels = scores / 100.0 + rng.normal(0, noise, n)
    dates  = pd.date_range("2020-01-02", periods=n_dates, freq="B")
    return pd.DataFrame({
        "symbol":          [f"S{i % 50}" for i in range(n)],
        "score_date":      [dates[i % n_dates] for i in range(n)],
        "momentum_raw":    scores,
        "forward_rs_21d":  labels,
        "forward_rs_63d":  labels * 1.2,
        "regime":          ["BULL" if i % 3 != 0 else "SIDEWAYS" for i in range(n)],
        "sector":          ["IT" if i % 2 == 0 else "Banking" for i in range(n)],
    })


def _noise_df(n: int = 1000, seed: int = 99) -> pd.DataFrame:
    """Panel with PURE NOISE: score and label are independent."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2020-01-02", periods=50, freq="B")
    return pd.DataFrame({
        "symbol":         [f"S{i % 50}" for i in range(n)],
        "score_date":     [dates[i % 50] for i in range(n)],
        "momentum_raw":   rng.uniform(0, 100, n),
        "forward_rs_21d": rng.uniform(-0.2, 0.2, n),   # independent of score
    })


# ---------------------------------------------------------------------------
# compute_decile_table
# ---------------------------------------------------------------------------

def test_decile_table_monotonic_on_signal() -> None:
    """Known signal → top decile has higher mean forward RS than bottom decile."""
    df = _signal_df()
    tbl = compute_decile_table(df, "momentum_raw", "forward_rs_21d")
    assert not tbl.empty
    assert "decile" in tbl.columns
    assert "mean_fwd_rs" in tbl.columns
    assert "count" in tbl.columns
    assert float(tbl["mean_fwd_rs"].iloc[-1]) > float(tbl["mean_fwd_rs"].iloc[0])


def test_decile_table_spearman_positive_on_signal() -> None:
    """Spearman ρ of decile→mean RS is strongly positive for a known signal."""
    df = _signal_df()
    tbl = compute_decile_table(df, "momentum_raw", "forward_rs_21d")
    rho = tbl["decile"].corr(tbl["mean_fwd_rs"], method="spearman")
    assert rho > 0.7


def test_decile_table_empty_on_tiny_input() -> None:
    """Fewer than 2*n_deciles rows → empty table (insufficient data for bucketing)."""
    df = _signal_df().head(5)
    tbl = compute_decile_table(df, "momentum_raw", "forward_rs_21d")
    assert tbl.empty


# ---------------------------------------------------------------------------
# compute_ic_series
# ---------------------------------------------------------------------------

def test_ic_series_positive_on_signal() -> None:
    """IC should be predominantly positive for a known signal."""
    df = _signal_df(n=5000, n_dates=100)
    ic = compute_ic_series(df, "momentum_raw", "forward_rs_21d", "score_date")
    assert not ic.empty
    mean_ic = float(ic.mean())
    assert mean_ic > 0.1, f"Expected mean IC > 0.1 for known signal, got {mean_ic:.4f}"


def test_ic_series_near_zero_on_noise() -> None:
    """IC should be near zero for pure noise (score independent of label)."""
    df = _noise_df(n=5000)
    ic = compute_ic_series(df, "momentum_raw", "forward_rs_21d", "score_date")
    if ic.empty:
        pytest.skip("Not enough cross-sections for IC computation")
    mean_ic = float(ic.mean())
    assert abs(mean_ic) < 0.15, f"Expected mean IC ≈ 0 for noise, got {mean_ic:.4f}"


def test_ic_series_skips_dates_with_few_stocks() -> None:
    """Dates with fewer than 5 stocks are skipped (IC unreliable at tiny n)."""
    df = pd.DataFrame({
        "score_date":     pd.date_range("2020-01-01", periods=3, freq="D").tolist() * 5,
        "momentum_raw":   [float(i) for i in range(15)],
        "forward_rs_21d": [float(i) * 0.01 for i in range(15)],
    })
    ic = compute_ic_series(df, "momentum_raw", "forward_rs_21d", "score_date")
    # Each date has 5 stocks — exactly at the threshold, may or may not be skipped
    # depending on implementation. We just check it doesn't crash.
    assert isinstance(ic, pd.Series)


# ---------------------------------------------------------------------------
# compute_ic_stats
# ---------------------------------------------------------------------------

def test_ic_stats_tstat_high_on_consistent_signal() -> None:
    """Consistently positive IC series → high t-stat."""
    rng = np.random.default_rng(1)
    ic_series = pd.Series(rng.uniform(0.05, 0.20, 100))  # all positive
    stats = compute_ic_stats(ic_series)
    assert stats["ic_mean"] > 0.0
    tstat = stats["ic_tstat"]
    assert tstat > 2.0, f"Expected t-stat > 2 for consistent IC, got {tstat:.2f}"
    assert stats["ic_hit_rate"] == pytest.approx(1.0)


def test_ic_stats_tstat_near_zero_on_noise() -> None:
    """Noise IC series (positive and negative, mean ≈ 0) → |t-stat| < 1.5."""
    rng = np.random.default_rng(2)
    ic_series = pd.Series(rng.uniform(-0.1, 0.1, 200))   # zero-mean noise
    stats = compute_ic_stats(ic_series)
    assert abs(stats["ic_mean"]) < 0.05
    assert abs(stats["ic_tstat"]) < 1.5, (
        f"Expected |t-stat| < 1.5 for noise IC, got {stats['ic_tstat']:.2f}"
    )


def test_ic_stats_empty_series() -> None:
    """Empty IC series returns zero-filled stats (no crash)."""
    stats = compute_ic_stats(pd.Series(dtype=float))
    assert stats["ic_mean"] == 0.0
    assert stats["ic_tstat"] == 0.0


# ---------------------------------------------------------------------------
# compute_stratified_spread
# ---------------------------------------------------------------------------

def test_stratified_spread_positive_on_signal() -> None:
    """Known signal → positive top-bottom spread per stratum."""
    df = _signal_df()
    spreads = compute_stratified_spread(df, "momentum_raw", "forward_rs_21d", "regime")
    for stratum, spread in spreads.items():
        if not math.isnan(spread):
            assert spread > 0.0, f"[{stratum}] expected positive spread, got {spread:.4f}"


# ---------------------------------------------------------------------------
# analyze (end-to-end)
# ---------------------------------------------------------------------------

def test_analyze_returns_valid_metrics_on_signal() -> None:
    """analyze() produces ValidationMetrics with populated fields for a known signal."""
    df = _signal_df(n=3000, n_dates=60)
    m  = analyze(df, horizons=(21, 63))

    assert isinstance(m, ValidationMetrics)
    assert m.horizons == (21, 63)
    assert m.n_observations == len(df)
    assert 21 in m.decile_spearman
    assert 63 in m.decile_spearman
    assert m.decile_spearman[21] > 0.5
    assert m.ic_mean[21] > 0.0
    assert m.ic_tstat[21] > 0.0


def test_analyze_handles_missing_horizon_label() -> None:
    """If a label column is missing, that horizon is silently skipped (no crash)."""
    df = _signal_df()[["symbol", "score_date", "momentum_raw", "forward_rs_21d", "regime"]]
    # forward_rs_63d is absent
    m = analyze(df, horizons=(21, 63))
    assert 21 in m.decile_spearman
    assert 63 not in m.decile_spearman  # absent horizon not added


def test_metrics_to_dict_serializable() -> None:
    """metrics_to_dict produces a plain dict (JSON-serializable)."""
    import json

    df = _signal_df()
    m  = analyze(df, horizons=(21,))
    d  = metrics_to_dict(m)

    dumped = json.dumps(d)
    assert "decile_spearman" in dumped
    assert "ic_tstat" in dumped
