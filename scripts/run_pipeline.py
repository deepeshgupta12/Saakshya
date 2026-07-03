"""One-command local pipeline (SPEC §12, docs/steps/05).

Runs ingest → scan → explain over the local universe and prints a stage summary.

    python scripts/run_pipeline.py                       # full pipeline
    python scripts/run_pipeline.py --stages ingest scan  # skip explain
    python scripts/run_pipeline.py --limit 5 --period 1y # quick smoke run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.pipeline.orchestrator import run  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Saakshya local pipeline (M5).")
    parser.add_argument("--limit", type=int, default=None,
                        help="cap number of universe symbols")
    parser.add_argument("--period", type=str, default=None,
                        help="EOD history window (e.g. max, 5y, 1y)")
    parser.add_argument("--stages", nargs="+",
                        choices=["ingest", "scan", "explain"],
                        default=None,
                        help="stages to run (default: all)")
    args = parser.parse_args()

    result = run(limit=args.limit, period=args.period, stages=args.stages)

    print(f"\n[pipeline] run_id={result.run_id}  "
          f"session_date={result.session_date}  "
          f"total={result.total_duration_s:.1f}s")

    for s in result.stages:
        print(f"  [{s.stage:<8}] rows_in={s.rows_in:<5} rows_out={s.rows_out:<5} "
              f"{s.duration_s:.1f}s  {s.notes}")

    if result.ai_calls or result.ai_cache_hits or result.ai_suppressed:
        print(f"\n  [explain]  ai_calls={result.ai_calls}  "
              f"cache_hits={result.ai_cache_hits}  "
              f"suppressed={result.ai_suppressed}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
