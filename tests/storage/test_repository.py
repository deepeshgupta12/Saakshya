"""Repository round-trip + point-in-time discipline (SPEC §6.2, docs/steps/01)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from app.storage.duckdb import get_connection
from app.storage.repository import OhlcBar, Repository, StockMaster

MEMORY = Path(":memory:")


def _bar(stock_id: int, version: int, close: float) -> OhlcBar:
    return OhlcBar(
        stock_id=stock_id,
        session_date=date(2024, 1, 2),
        open_raw=close, high_raw=close, low_raw=close, close_raw=close,
        open_adj=close, high_adj=close, low_adj=close, close_adj=close,
        volume=100, as_of_version=version, source="test",
    )


def test_restatement_creates_new_version_preserving_history() -> None:
    with get_connection(MEMORY) as conn:
        repo = Repository(conn)
        sid = repo.upsert_stock(StockMaster(primary_symbol="TEST", name="Test Co"))

        repo.upsert_ohlc([_bar(sid, version=1, close=100.0)])
        assert repo.count_ohlc(sid) == 1
        assert repo.max_as_of_version(sid, date(2024, 1, 2)) == 1

        # A restatement is a NEW as_of_version, not an overwrite.
        repo.upsert_ohlc([_bar(sid, version=2, close=111.0)])
        assert repo.count_ohlc(sid) == 2  # history preserved
        assert repo.max_as_of_version(sid, date(2024, 1, 2)) == 2

        latest = repo.latest_bars(sid, limit=5)
        assert len(latest) == 1  # one session, latest version
        assert latest[0].as_of_version == 2
        assert latest[0].close_raw == 111.0


def test_reingest_same_version_is_idempotent_update() -> None:
    with get_connection(MEMORY) as conn:
        repo = Repository(conn)
        sid = repo.upsert_stock(StockMaster(primary_symbol="T2", name="T2 Co"))
        repo.upsert_ohlc([_bar(sid, version=1, close=100.0)])
        repo.upsert_ohlc([_bar(sid, version=1, close=105.0)])  # same version -> update
        assert repo.count_ohlc(sid) == 1
        assert repo.latest_bars(sid)[0].close_raw == 105.0


def test_upsert_stock_is_idempotent_by_symbol() -> None:
    with get_connection(MEMORY) as conn:
        repo = Repository(conn)
        a = repo.upsert_stock(StockMaster(primary_symbol="DUP", name="First"))
        b = repo.upsert_stock(StockMaster(primary_symbol="DUP", name="First Updated"))
        assert a == b
