"""Shared DB test helpers for the polyglot stack (D-059).

Importable by test modules (`from tests.dbutil import open_fresh_pg, pg_cm, fresh_mongo`).
All helpers target the live Dockerized TimescaleDB + MongoDB (`docker compose up -d`).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from app.storage import mongodb, postgres
from app.storage.mongo_setup import COLLECTIONS

PG_TABLES = [
    "daily_ohlc", "index_ohlc", "technical_indicators", "scanner_results",
    "scanner_definitions", "corporate_actions", "data_quality_logs",
    "ai_audit_log", "ai_summary_cache", "ai_daily_calls", "market_brief_cache",
    "news_stock_links", "news_items", "news_sources",
    "exchange_symbols", "stock_master", "sector_master", "industry_master",
]


def pg_reachable() -> bool:
    try:
        with postgres.get_connection() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def mongo_reachable() -> bool:
    try:
        mongodb.get_client().admin.command("ping")
        return True
    except Exception:
        return False


def truncate(conn: object) -> None:
    conn.execute("TRUNCATE " + ", ".join(PG_TABLES) + " RESTART IDENTITY CASCADE")  # type: ignore[attr-defined]


def open_fresh_pg() -> object:
    """An open, truncated TimescaleDB connection (caller-managed lifecycle).

    Drop-in for the old ``_db()`` helpers that returned a bare in-memory DuckDB conn.
    """
    conn = postgres.connect()
    postgres.init_schema(conn)
    truncate(conn)
    return conn


@contextmanager
def pg_cm(*_args: object, **_kwargs: object) -> Iterator[object]:
    """Context-manager drop-in for the old ``get_connection(MEMORY)`` usage."""
    postgres.reset_schema_flag()
    with postgres.get_connection() as conn:
        truncate(conn)
        yield conn


def fresh_mongo() -> object:
    """The Mongo db with all user/app collections emptied."""
    db = mongodb.get_db()
    for c in COLLECTIONS:
        db[c].delete_many({})
    return db
