"""Universe seeding + symbol resolution incl. symbol-change windows (docs/steps/01)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from app.data.universe import load_universe, seed_universe
from app.storage.duckdb import get_connection
from app.storage.repository import Repository, StockMaster

MEMORY = Path(":memory:")


def test_universe_seeds_master_and_resolves() -> None:
    entries = load_universe()
    assert len(entries) >= 50  # ~50-name Nifty universe
    # primary_symbols are unique
    assert len({e.symbol for e in entries}) == len(entries)

    with get_connection(MEMORY) as conn:
        repo = Repository(conn)
        mapping = seed_universe(repo, entries)
        assert len(mapping) == len(entries)

        sid = repo.get_stock_id("RELIANCE")
        assert sid is not None
        assert repo.resolve_ticker("NSE", "RELIANCE.NS") == sid
        assert repo.resolve_ticker("NSE", "DOES.NOT.EXIST") is None


def test_symbol_change_history_resolves_by_date() -> None:
    with get_connection(MEMORY) as conn:
        repo = Repository(conn)
        sid = repo.upsert_stock(StockMaster(primary_symbol="NEWCO", name="New Co"))
        # Old ticker valid until 2023-06-30, new ticker from 2023-07-01 (same stock_id).
        conn.execute(
            "INSERT INTO exchange_symbols (stock_id, exchange, symbol, valid_from, valid_to) "
            "VALUES (?, 'NSE', 'OLDCO.NS', DATE '1990-01-01', DATE '2023-06-30')",
            [sid],
        )
        conn.execute(
            "INSERT INTO exchange_symbols (stock_id, exchange, symbol, valid_from, valid_to) "
            "VALUES (?, 'NSE', 'NEWCO.NS', DATE '2023-07-01', NULL)",
            [sid],
        )
        assert repo.resolve_ticker("NSE", "OLDCO.NS", on=date(2023, 1, 1)) == sid
        assert repo.resolve_ticker("NSE", "NEWCO.NS", on=date(2024, 1, 1)) == sid
        assert repo.resolve_ticker("NSE", "OLDCO.NS", on=date(2024, 1, 1)) is None
