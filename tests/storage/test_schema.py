"""Schema applies cleanly; raw+adjusted + as-of versioning present (docs/steps/01).

Runs against the live TimescaleDB (D-059) via the shared `pg` fixture.
"""

from __future__ import annotations

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
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s", [table]
    ).fetchall()
    return {r[0] for r in rows}


def test_all_tables_created(pg) -> None:
    tables = {
        r[0]
        for r in pg.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        ).fetchall()
    }
    for table in REQUIRED_TABLES:
        assert table in tables, f"missing table {table}"


def test_daily_ohlc_has_raw_and_adjusted(pg) -> None:
    cols = _columns(pg, "daily_ohlc")
    for col in ("open_raw", "close_raw", "open_adj", "close_adj", "is_adjusted", "adj_factor"):
        assert col in cols


def test_time_series_tables_carry_as_of_version(pg) -> None:
    for table in ("daily_ohlc", "index_ohlc", "technical_indicators", "corporate_actions"):
        assert "as_of_version" in _columns(pg, table)
