"""Schema applies cleanly; raw+adjusted + as-of versioning present (docs/steps/01)."""

from __future__ import annotations

from pathlib import Path

from app.storage.duckdb import get_connection

MEMORY = Path(":memory:")
REQUIRED_TABLES = [
    "sector_master",
    "industry_master",
    "stock_master",
    "exchange_symbols",
    "daily_ohlc",
    "index_ohlc",
    "technical_indicators",
    "corporate_actions",
    "data_quality_logs",
]


def _columns(conn, table: str) -> set[str]:
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = ?", [table]
    ).fetchall()
    return {r[0] for r in rows}


def test_all_tables_created() -> None:
    with get_connection(MEMORY) as conn:
        tables = {
            r[0]
            for r in conn.execute("SELECT table_name FROM information_schema.tables").fetchall()
        }
        for table in REQUIRED_TABLES:
            assert table in tables, f"missing table {table}"


def test_daily_ohlc_has_raw_and_adjusted() -> None:
    with get_connection(MEMORY) as conn:
        cols = _columns(conn, "daily_ohlc")
        for col in ("open_raw", "close_raw", "open_adj", "close_adj", "is_adjusted", "adj_factor"):
            assert col in cols


def test_time_series_tables_carry_as_of_version() -> None:
    with get_connection(MEMORY) as conn:
        for table in ("daily_ohlc", "index_ohlc", "technical_indicators", "corporate_actions"):
            assert "as_of_version" in _columns(conn, table)
