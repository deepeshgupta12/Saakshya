"""One-command local pipeline (SPEC §12). M0 runs the ingest stage.

    python scripts/run_pipeline.py                # full universe, full history
    python scripts/run_pipeline.py --limit 5 --period 1y   # quick smoke run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as a plain script (`python scripts/run_pipeline.py`).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pipeline.ingest import run_ingest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Saakshya local pipeline (M0: ingest).")
    parser.add_argument("--limit", type=int, default=None, help="cap number of universe symbols")
    parser.add_argument(
        "--period", type=str, default=None, help="yfinance history period (e.g. max, 5y, 1y)"
    )
    args = parser.parse_args()

    summary = run_ingest(limit=args.limit, period=args.period)
    print(
        f"[ingest] source={summary.source} symbols={summary.symbols} "
        f"with_data={summary.symbols_with_data} bars_in_db={summary.bars}"
    )
    if summary.empty_symbols:
        print(f"[ingest] no data (quarantined): {summary.empty_symbols}")
    if summary.unmapped:
        print(f"[ingest] unmapped tickers: {summary.unmapped}")
    print("[compute] indicators: pending milestone M2 (02-indicators-and-scanners)")
    print("[scan]    scanners:   pending milestone M3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
