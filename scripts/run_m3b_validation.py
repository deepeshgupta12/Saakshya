"""M3b validation run script (docs/steps/03, SPEC §6.5).

Orchestrates: fetch historical prices → build point-in-time dataset →
run IC + decile analysis → apply decision gate → write report to data/validation/.

Usage:
    python scripts/run_m3b_validation.py [--period 5y] [--config-version v1]

Outputs (data/validation/):
    m3b_dataset.parquet      — raw score/label panel (reproducible)
    m3b_metrics.json         — full ValidationMetrics as JSON
    m3b_verdict.json         — gate verdict + per-criterion pass/fail

Framing: all output is historical measurement, never a return promise (SPEC §3.3).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.validation.analysis import ValidationMetrics, analyze, metrics_to_dict  # noqa: E402
from app.validation.config import load_gate_config  # noqa: E402
from app.validation.dataset import build_validation_dataset  # noqa: E402
from app.validation.gate import GateVerdict, apply_verdict_to_db, evaluate_gate  # noqa: E402

_OUT_DIR = PROJECT_ROOT / "data" / "validation"
_UNIVERSE_CSV = PROJECT_ROOT / "data" / "universe.csv"
_NIFTY_SYMBOL = "^NSEI"
_HORIZONS = (21, 63)


def _fetch_prices(symbols: list[str], period: str = "5y") -> dict[str, pd.Series]:
    """Fetch adjusted-close series via yfinance. Suffix .NS for NSE equities."""
    import yfinance as yf

    tickers_yf = [f"{s}.NS" for s in symbols] + [_NIFTY_SYMBOL]
    raw = yf.download(
        tickers=tickers_yf,
        period=period,
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    close = raw.get("Close", raw)
    prices: dict[str, pd.Series] = {}
    for sym in symbols:
        col = f"{sym}.NS"
        if col in close.columns:
            s = close[col].dropna()
            if len(s) >= 200:
                prices[sym] = s
    return prices


def _fetch_nifty(period: str = "5y") -> pd.Series:
    import yfinance as yf

    raw = yf.download(_NIFTY_SYMBOL, period=period, auto_adjust=True, progress=False)
    close = raw.get("Close", raw)
    if hasattr(close, "squeeze"):
        close = close.squeeze()
    return close.dropna()


def main(period: str = "5y", config_version: str = "v1") -> None:
    _OUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- universe ---
    universe_df = pd.read_csv(_UNIVERSE_CSV)
    symbols  = universe_df["symbol"].tolist()
    default_sectors = [""] * len(universe_df)
    sectors  = dict(
        zip(universe_df["symbol"], universe_df.get("sector", default_sectors), strict=False)
    )
    print(f"Universe: {len(symbols)} symbols")

    # --- fetch ---
    print("Fetching price history via yfinance…")
    prices = _fetch_prices(symbols, period=period)
    nifty  = _fetch_nifty(period=period)
    print(f"Fetched: {len(prices)} stocks with ≥200 bars, Nifty {len(nifty)} bars")

    if not prices:
        print("ERROR: no price data fetched — check network / yfinance")
        sys.exit(1)

    # --- date range ---
    all_idx = pd.DatetimeIndex(
        sorted({d for s in prices.values() for d in s.index})
    )
    start_date = (all_idx[200]).date()
    end_date   = (all_idx[-_HORIZONS[-1] - 1]).date()   # leave room for labels
    print(f"Validation window: {start_date} → {end_date}")

    # --- build dataset ---
    print("Building point-in-time dataset (this may take a few minutes)…")
    df = build_validation_dataset(
        prices=prices,
        nifty=nifty,
        start_date=start_date,
        end_date=end_date,
        horizons=_HORIZONS,
        sectors=sectors,
        min_history=200,
    )
    print(f"Dataset: {len(df):,} rows, {df['symbol'].nunique()} symbols, "
          f"{df['score_date'].nunique()} dates")

    dataset_path = _OUT_DIR / "m3b_dataset.parquet"
    df.to_parquet(dataset_path, index=False)
    print(f"Dataset saved → {dataset_path}")

    # --- analysis ---
    print("Running IC + decile analysis…")
    metrics = analyze(df, horizons=_HORIZONS)

    metrics_path = _OUT_DIR / "m3b_metrics.json"
    with metrics_path.open("w") as f:
        json.dump(metrics_to_dict(metrics), f, indent=2, default=str)
    print(f"Metrics saved → {metrics_path}")

    _print_metrics(metrics)

    # --- gate ---
    config  = load_gate_config(config_version)
    verdict = evaluate_gate(metrics, config)

    verdict_dict = {
        "status":                 verdict.status,
        "config_version":         verdict.config_version,
        "decile_spearman_pass":   {str(k): v for k, v in verdict.decile_spearman_pass.items()},
        "top_bottom_spread_pass": {str(k): v for k, v in verdict.top_bottom_spread_pass.items()},
        "ic_mean_pass":           {str(k): v for k, v in verdict.ic_mean_pass.items()},
        "ic_tstat_pass":          {str(k): v for k, v in verdict.ic_tstat_pass.items()},
        "regime_pass":            {str(k): v for k, v in verdict.regime_pass.items()},
        "details":                {str(k): v for k, v in verdict.details.items()},
    }
    verdict_path = _OUT_DIR / "m3b_verdict.json"
    with verdict_path.open("w") as f:
        json.dump(verdict_dict, f, indent=2, default=str)
    print(f"Verdict saved → {verdict_path}")

    print("\n" + "=" * 60)
    print(f"M3b VERDICT: {verdict.status}")
    print("=" * 60)

    if verdict.status == "VALIDATED":
        print("Score carries signal. Composite may now drive UI.")
        _apply_to_db(verdict)
    else:
        print("Score does not pass validation. Redesign scoring before building UI.")
        print("Failing criteria:")
        for h in metrics.horizons:
            if not verdict.decile_spearman_pass.get(h, False):
                rho = metrics.decile_spearman.get(h, 0.0)
                print(f"  [{h}d] decile Spearman ρ = {rho:.3f} "
                      f"(min {config.decile_spearman_min})")
            if not verdict.top_bottom_spread_pass.get(h, False):
                sp = metrics.top_bottom_spread.get(h, 0.0)
                print(f"  [{h}d] top-bottom spread = {sp:.4f} "
                      f"(must be > {config.top_bottom_spread_min})")
            if not verdict.ic_tstat_pass.get(h, False):
                ts = metrics.ic_tstat.get(h, 0.0)
                print(f"  [{h}d] IC t-stat = {ts:.2f} (min {config.ic_tstat_min})")
            if not verdict.regime_pass.get(h, True):
                print(f"  [{h}d] regime inversion detected")


def _print_metrics(m: ValidationMetrics) -> None:
    print(f"\n  Observations: {m.n_observations:,}  "
          f"Dates: {m.n_dates}  Symbols: {m.n_symbols}")
    for h in m.horizons:
        print(f"\n  --- {h}-day horizon ---")
        print(f"  Decile Spearman ρ : {m.decile_spearman.get(h, float('nan')):.3f}")
        print(f"  Top-bottom spread : {m.top_bottom_spread.get(h, float('nan')):.4f}")
        print(f"  Mean IC           : {m.ic_mean.get(h, float('nan')):.4f}")
        print(f"  IC t-stat         : {m.ic_tstat.get(h, float('nan')):.2f}")
        print(f"  IC hit-rate       : {m.ic_hit_rate.get(h, float('nan')):.2%}")
        for regime, spread in m.regime_spread.get(h, {}).items():
            print(f"  [{regime}] top-bottom : {spread:.4f}")


def _apply_to_db(verdict: GateVerdict) -> None:
    try:
        from app.storage.duckdb import get_connection
        with get_connection() as conn:
            apply_verdict_to_db(verdict, conn)
        print("DB updated: scanner_definitions.validated = TRUE")
    except Exception as exc:  # noqa: BLE001
        print(f"DB update skipped (no local DB): {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run M3b score validation")
    parser.add_argument("--period", default="5y", help="yfinance period (default: 5y)")
    parser.add_argument("--config-version", default="v1", help="Gate config version (default: v1)")
    args = parser.parse_args()
    main(period=args.period, config_version=args.config_version)
