"""Pipeline orchestrator: ingest → scan → explain (docs/09 §4, docs/steps/05).

Stages:
  ingest  — fetch OHLCV, corp-action adjust, compute indicators (wraps run_ingest)
  scan    — run all scanners, persist scanner_results
  explain — AI summaries for scanner members (cache-aware, ceiling-aware)

All stages share a single as_of_version (int, DB point-in-time key) and a
human-readable run_id string used in AI audit records.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

import psycopg

from app.pipeline.ingest import run_ingest
from app.scanners.momentum import run_momentum_scanner
from app.scanners.moving_average import run_ma_scanner
from app.scanners.rsi import run_rsi_scanner
from app.scanners.schema import ScannerResult
from app.scanners.volume_breakout import run_volume_breakout_scanner
from app.storage.postgres import get_connection
from app.storage.repository import Repository

log = logging.getLogger(__name__)

_ALL_STAGES = ["ingest", "scan", "explain"]
_AS_OF_VERSION = 1  # bump on restatement; shared with existing ingest code

_SCANNERS = [
    ("momentum",       run_momentum_scanner),
    ("volume_breakout", run_volume_breakout_scanner),
    ("rsi",            run_rsi_scanner),
    ("moving_average", run_ma_scanner),
]


@dataclass
class StageResult:
    stage:      str
    rows_in:    int
    rows_out:   int
    duration_s: float
    notes:      str = ""


@dataclass
class PipelineResult:
    run_id:          str
    as_of_version:   int
    session_date:    date | None
    stages:          list[StageResult] = field(default_factory=list)
    total_duration_s: float = 0.0
    ai_calls:        int = 0
    ai_cache_hits:   int = 0
    ai_suppressed:   int = 0

    def stage(self, name: str) -> StageResult | None:
        return next((s for s in self.stages if s.stage == name), None)


def run(
    *,
    limit: int | None = None,
    period: str | None = None,
    stages: list[str] | None = None,
    as_of_version: int = _AS_OF_VERSION,
    conn: psycopg.Connection | None = None,
) -> PipelineResult:
    """Run the full EOD pipeline or a subset of stages.

    Args:
        limit: cap universe size (useful for quick smoke runs).
        period: EOD history window (e.g. "1y", "max").
        stages: subset of ["ingest", "scan", "explain"]; None = all.
        as_of_version: DB point-in-time key (int); bump on restatement.
        conn: optional open TimescaleDB connection (uses get_connection() otherwise).
    """
    active_stages = stages or _ALL_STAGES
    run_id = f"ds-{datetime.now(tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')}"
    result = PipelineResult(run_id=run_id, as_of_version=as_of_version, session_date=None)
    wall_start = time.monotonic()

    # Use ExitStack so the context manager object is kept alive for the full run.
    # get_connection().__enter__() without storing the manager causes immediate GC-close.
    _stack = ExitStack()
    if conn is None:
        conn = _stack.enter_context(get_connection())

    try:
        repo = Repository(conn)

        # ── Stage 1: ingest (M0+M1+M2) ─────────────────────────────────────
        if "ingest" in active_stages:
            t0 = time.monotonic()
            log.info("[pipeline] stage=ingest starting")
            # Pass the same connection so ingest doesn't open a second write-conn
            # to the same DB (reuse the caller's connection).
            ingest_summary = run_ingest(limit=limit, period=period, conn=conn)
            elapsed = time.monotonic() - t0
            result.stages.append(StageResult(
                stage="ingest",
                rows_in=ingest_summary.symbols,
                rows_out=ingest_summary.bars,
                duration_s=round(elapsed, 2),
                notes=(
                    f"source={ingest_summary.source} "
                    f"with_data={ingest_summary.symbols_with_data} "
                    f"ca={ingest_summary.corp_actions_ingested}"
                ),
            ))
            log.info(
                "[pipeline] stage=ingest done symbols=%d bars=%d %.1fs",
                ingest_summary.symbols, ingest_summary.bars, elapsed,
            )

        # Resolve session_date from DB (latest date with OHLC data).
        result.session_date = repo.get_latest_session_date()
        if result.session_date is None:
            log.warning("[pipeline] no session_date found — skipping scan + explain")
            return result

        session_date = result.session_date

        # ── Stage 2: scan ───────────────────────────────────────────────────
        if "scan" in active_stages:
            t0 = time.monotonic()
            log.info("[pipeline] stage=scan date=%s", session_date)
            universe = repo.get_universe_for_scanner(session_date, as_of_version)
            total_results = 0
            for scanner_name, runner_fn in _SCANNERS:
                scanner_results = runner_fn(universe, session_date, as_of_version)
                _persist_scanner_results(repo, scanner_results)
                total_results += len(scanner_results)
                log.info(
                    "[pipeline] scanner=%s members=%d", scanner_name, len(scanner_results)
                )
            elapsed = time.monotonic() - t0
            result.stages.append(StageResult(
                stage="scan",
                rows_in=len(universe),
                rows_out=total_results,
                duration_s=round(elapsed, 2),
                notes=f"scanners={len(_SCANNERS)} date={session_date}",
            ))
            log.info(
                "[pipeline] stage=scan done total_results=%d %.1fs", total_results, elapsed
            )

        # ── Stage 3: explain ────────────────────────────────────────────────
        if "explain" in active_stages:
            t0 = time.monotonic()
            log.info("[pipeline] stage=explain date=%s", session_date)
            ai_calls, cache_hits, suppressed = _run_explain_stage(
                repo, conn, session_date, as_of_version, run_id
            )
            elapsed = time.monotonic() - t0
            result.ai_calls    = ai_calls
            result.ai_cache_hits = cache_hits
            result.ai_suppressed = suppressed
            result.stages.append(StageResult(
                stage="explain",
                rows_in=ai_calls + cache_hits + suppressed,
                rows_out=ai_calls + cache_hits,
                duration_s=round(elapsed, 2),
                notes=(
                    f"ai_calls={ai_calls} cache_hits={cache_hits} "
                    f"suppressed={suppressed}"
                ),
            ))
            log.info(
                "[pipeline] stage=explain done calls=%d cached=%d suppressed=%d %.1fs",
                ai_calls, cache_hits, suppressed, elapsed,
            )

    finally:
        _stack.close()  # closes the connection only if we opened it

    result.total_duration_s = round(time.monotonic() - wall_start, 2)
    log.info("[pipeline] run_id=%s total=%.1fs", run_id, result.total_duration_s)
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _persist_scanner_results(repo: Repository, results: list[ScannerResult]) -> None:
    for r in results:
        repo.upsert_scanner_result(
            scanner=r.scanner,
            stock_id=r.stock_id,
            session_date=r.as_of_date,
            composite_score=r.composite_score,
            sub_scores_json=json.dumps({
                k: (v if not _is_nan(v) else None)
                for k, v in r.sub_scores.items()
            }),
            facts_json=json.dumps(r.facts),
            signal_tags_json=json.dumps(r.signal_tags),
            risk_flags_json=json.dumps(r.risk_flags),
            data_confidence=r.data_confidence,
            weights_version=r.weights_version,
            validation_status=r.validation_status,
            as_of_version=r.as_of_version,
            engine_version=r.engine_version,
        )


def _run_explain_stage(
    repo: Repository,
    conn: psycopg.Connection,
    session_date: date,
    as_of_version: int,
    run_id: str,
) -> tuple[int, int, int]:
    """Generate AI summaries for all scanner members. Returns (calls, cache_hits, suppressed)."""
    from app.ai.explainer import explain_stock
    from app.ai.payload import build_stock_payload

    ai_calls = cache_hits = suppressed = 0

    # Collect distinct symbols that appear in any scanner for this date.
    all_rows = conn.execute(
        "SELECT DISTINCT sm.primary_symbol, sr.scanner, sr.composite_score, "
        "sr.sub_scores, sr.facts, sr.signal_tags, sr.risk_flags, sr.data_confidence "
        "FROM scanner_results sr "
        "JOIN stock_master sm ON sm.stock_id = sr.stock_id "
        "WHERE sr.session_date = %s AND sr.as_of_version = %s",
        [session_date, as_of_version],
    ).fetchall()

    # De-dup by symbol: pick highest composite_score scanner per symbol.
    by_symbol: dict[str, dict[str, object]] = {}
    for row in all_rows:
        sym = str(row[0])
        score = row[2]
        if sym not in by_symbol or (score and (
            by_symbol[sym]["composite_score"] is None
            or score > by_symbol[sym]["composite_score"]
        )):
            by_symbol[sym] = {
                "symbol": sym,
                "scanner": row[1],
                "composite_score": score,
                "sub_scores": json.loads(row[3]) if row[3] else {},
                "facts": json.loads(row[4]) if row[4] else {},
                "signal_tags": json.loads(row[5]) if row[5] else [],
                "risk_flags": json.loads(row[6]) if row[6] else [],
                "data_confidence": str(row[7]) if row[7] else "MEDIUM",
            }

    for sym, info in by_symbol.items():
        # Look up latest indicators for the close price.
        ind = repo.get_latest_indicators_for_symbol(sym, session_date, as_of_version)
        ohlc = repo.get_latest_ohlc_for_symbol(sym)
        raw_ind: dict[str, object] = dict(ind) if ind else {}
        if ohlc:
            raw_ind["close"] = ohlc.close_adj
            raw_ind["volume"] = float(ohlc.volume)
        # Narrow to float|bool for build_stock_payload.
        indicators: dict[str, float | bool] = {
            k: v
            for k, v in raw_ind.items()
            if isinstance(v, int | float | bool) and not isinstance(v, type(None))
        }
        _rf = info.get("risk_flags")
        risk_flags = [str(f) for f in _rf] if isinstance(_rf, list) else []

        try:
            payload = build_stock_payload(
                sym,
                indicators,
                info,
                risk_flags,
                as_of=session_date.isoformat(),
                as_of_version=run_id,
            )
        except Exception:
            log.exception("[explain] payload build failed for %s — skipping", sym)
            suppressed += 1
            continue

        try:
            expl = explain_stock(payload, conn=conn, use_cache=True)
        except Exception:
            log.exception("[explain] explain_stock failed for %s — skipping", sym)
            suppressed += 1
            continue

        if expl.suppressed:
            suppressed += 1
        elif expl.model_version == "cached":
            cache_hits += 1
        else:
            ai_calls += 1

    return ai_calls, cache_hits, suppressed


def _is_nan(v: object) -> bool:
    try:
        import math
        return math.isnan(float(v))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
