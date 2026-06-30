"""EOD ingest + compute pipeline: universe → source → DuckDB → indicators → scanners.

Pipeline stages (docs/12 §1):
  M0  1. Seed the universe (stock_master + exchange_symbols)
      2. Fetch full-history OHLCV from the active DataSource
      3. Normalize to stock_id-keyed OhlcBar (raw + source adj)
      4. Upsert into daily_ohlc

  M1  5. Fetch corporate actions from yfinance (splits + dividends)
      6. Ingest into the corporate_actions master (compute single-event factors)
      7. Back-adjust full history: compute cumulative adj_factor per date,
         write *_adj columns, set is_adjusted=True
      8. Reconcile our adj_close vs yfinance adj_close (2nd-source cross-check);
         flag mismatches to data_quality_logs
      9. Check for abnormal price jumps not explained by a corp action → quarantine

  M2 10. Compute all vectorized indicators per stock (RSI/SMA/EMA/ATR/MACD/Bollinger/
         ADX/Stoch RSI/Pivots/returns/volume_ratio/relative_strength) and persist to
         technical_indicators (SPEC §12 M2)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.config import get_settings
from app.data.base import OHLCRow, get_source
from app.data.corp_action_adjuster import AdjustSummary, adjust_all
from app.data.corp_actions import ingest_corp_actions
from app.data.normalize import to_bars
from app.data.universe import load_universe, seed_universe
from app.indicators.compute import ComputeSummary, compute_all
from app.storage.duckdb import get_connection
from app.storage.repository import DataQualityLog, Repository

_AS_OF_VERSION = 1
_JOB_ID_INGEST = "m0_ingest"
_JOB_ID_ADJUST = "m1_adjust"

# Corp actions are fetched going back to this date (covers all modern NSE listings).
_CORP_ACTION_SINCE = date(2000, 1, 1)


@dataclass
class IngestSummary:
    source: str
    symbols: int
    bars: int
    symbols_with_data: int
    corp_actions_ingested: int = 0
    adjust: AdjustSummary | None = None
    compute: ComputeSummary | None = None
    unmapped: list[str] = field(default_factory=list)
    empty_symbols: list[str] = field(default_factory=list)


def run_ingest(limit: int | None = None, period: str | None = None) -> IngestSummary:
    settings = get_settings()
    window = period or settings.history_period
    entries = load_universe()
    if limit is not None:
        entries = entries[:limit]

    with get_connection() as conn:
        repo = Repository(conn)
        ticker_to_stock_id = seed_universe(repo, entries)

        source = get_source()
        tickers = list(ticker_to_stock_id.keys())

        # ── M0: fetch history and land raw bars ──────────────────────────
        rows: list[OHLCRow] = source.fetch_history(tickers, window)
        bars, unmapped = to_bars(rows, ticker_to_stock_id, as_of_version=_AS_OF_VERSION)
        repo.upsert_ohlc(bars)

        landed = {bar.stock_id for bar in bars}
        empty: list[str] = []
        for entry in entries:
            stock_id = ticker_to_stock_id[entry.yf_ticker]
            if stock_id not in landed:
                empty.append(entry.symbol)
                repo.write_quality_log(DataQualityLog(
                    job_id=_JOB_ID_INGEST,
                    source=source.name,
                    check_type="missing_candle",
                    severity="warn",
                    status="quarantined",
                    stock_id=stock_id,
                    detail=f"no bars returned for {entry.symbol}",
                ))

        # ── M1: corp-action master ────────────────────────────────────────
        # Always use yfinance as the corp-action source for now; the NSE corporate-
        # action API adapter is a future iteration (docs/steps/01 §corp-actions).
        from app.data.yfinance_source import YFinanceSource

        yf_source = YFinanceSource()
        ca_rows = yf_source.fetch_corporate_actions(tickers, since=_CORP_ACTION_SINCE)
        ca_count = ingest_corp_actions(
            repo, ticker_to_stock_id, ca_rows, as_of_version=_AS_OF_VERSION
        )

        # ── M1: build yfinance adj_close map for reconciliation ───────────
        # rows already contains yfinance's own adj_close (from the M0 fetch above).
        # Build {ticker → {session_date → yf_adj_close}} before the adjuster
        # overwrites *_adj columns with our computed values.
        yf_adj_map = _build_yf_adj_map(rows)

        # ── M1: back-adjust + reconcile ───────────────────────────────────
        adj_summary = adjust_all(
            repo=repo,
            ticker_to_stock_id=ticker_to_stock_id,
            yf_adj_close=yf_adj_map,
            as_of_version=_AS_OF_VERSION,
            job_id=_JOB_ID_ADJUST,
        )

        # ── M2: compute indicators for all stocks ─────────────────────────
        compute_summary = compute_all(repo, as_of_version=_AS_OF_VERSION)

        return IngestSummary(
            source=source.name,
            symbols=len(entries),
            bars=repo.count_ohlc(),
            symbols_with_data=len(landed),
            corp_actions_ingested=ca_count,
            adjust=adj_summary,
            compute=compute_summary,
            unmapped=unmapped,
            empty_symbols=empty,
        )


def _build_yf_adj_map(rows: list[OHLCRow]) -> dict[str, dict[date, float]]:
    """Group yfinance OHLCRows into {ticker → {date → adj_close}}."""
    result: dict[str, dict[date, float]] = {}
    for r in rows:
        if r.close_adj and r.close_adj > 0:
            result.setdefault(r.symbol, {})[r.session_date] = r.close_adj
    return result
