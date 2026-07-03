"""Regression: compute_all persists indicators against TimescaleDB (D-059).

app/indicators/compute.py had DuckDB-only `?` placeholders and `conn.executemany`
(psycopg's Connection has neither) — so the indicator engine never ran on Postgres.
Tests seeded technical_indicators directly, so this was uncaught. Runs on `pg`.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.indicators.compute import compute_all
from app.storage.repository import OhlcBar, Repository, StockMaster


def _sessions(n: int, end: date) -> list[date]:
    out: list[date] = []
    d = end
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return list(reversed(out))


def test_compute_all_writes_indicators(pg):
    repo = Repository(pg)
    sec = repo.upsert_sector("Information Technology")
    sid = repo.upsert_stock(StockMaster(primary_symbol="INFY", name="Infosys", sector_id=sec))
    sessions = _sessions(60, date(2026, 6, 30))
    price = 1000.0
    bars = []
    for i, d in enumerate(sessions):
        price *= 1.004 if i % 2 == 0 else 0.997
        c = round(price, 2)
        bars.append(OhlcBar(
            stock_id=sid, session_date=d,
            open_raw=c, high_raw=c * 1.01, low_raw=c * 0.99, close_raw=c,
            open_adj=c, high_adj=c * 1.01, low_adj=c * 0.99, close_adj=c,
            volume=1_000_000, as_of_version=1, source="test",
        ))
    repo.upsert_ohlc(bars)

    summary = compute_all(repo, as_of_version=1)
    assert summary.stocks_processed == 1
    assert summary.rows_written > 0
    assert not summary.errors

    # A real indicator row exists for the latest session with computed values.
    ind = repo.get_latest_indicators_for_symbol("INFY", sessions[-1], 1)
    assert ind is not None
    assert ind["rsi_14"] is not None and ind["sma_20"] is not None
