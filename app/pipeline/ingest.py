"""M0 ingest stage: universe → yfinance → DuckDB (adjusted OHLCV lands).

Orchestrates: seed the universe, fetch full-history bars from the active DataSource,
normalize to stock_id-keyed bars, upsert into ``daily_ohlc`` (raw + adjusted, as-of v1),
and log a data-quality warning for any symbol that returned no bars (fail-loud, SPEC §6.2).
Compute (M2) and scan (M3) stages are wired in later milestones.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import get_settings
from app.data.base import get_source
from app.data.normalize import to_bars
from app.data.universe import load_universe, seed_universe
from app.storage.duckdb import get_connection
from app.storage.repository import DataQualityLog, Repository

_AS_OF_VERSION = 1
_JOB_ID = "m0_ingest"


@dataclass
class IngestSummary:
    source: str
    symbols: int
    bars: int
    symbols_with_data: int
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
        rows = source.fetch_history(tickers, window)
        bars, unmapped = to_bars(rows, ticker_to_stock_id, as_of_version=_AS_OF_VERSION)
        repo.upsert_ohlc(bars)

        landed = {bar.stock_id for bar in bars}
        empty: list[str] = []
        for entry in entries:
            stock_id = ticker_to_stock_id[entry.yf_ticker]
            if stock_id not in landed:
                empty.append(entry.symbol)
                repo.write_quality_log(
                    DataQualityLog(
                        job_id=_JOB_ID,
                        source=source.name,
                        check_type="missing_candle",
                        severity="warn",
                        status="quarantined",
                        stock_id=stock_id,
                        detail=f"no bars returned for {entry.symbol}",
                    )
                )

        return IngestSummary(
            source=source.name,
            symbols=len(entries),
            bars=repo.count_ohlc(),
            symbols_with_data=len(landed),
            unmapped=unmapped,
            empty_symbols=empty,
        )
