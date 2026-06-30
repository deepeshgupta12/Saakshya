"""DuckDB connection factory + schema bootstrap (local-first storage, SPEC §12)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb

from app.config import get_settings

SCHEMA_PATH: Path = Path(__file__).with_name("schema.sql")

# M2 migration: add indicator columns to technical_indicators (idempotent via IF NOT EXISTS).
# Run after schema.sql so the base table exists before columns are added.
_M2_MIGRATIONS: list[str] = [
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS rsi_14 DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS sma_20 DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS sma_50 DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS sma_200 DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS ema_21 DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS atr_14 DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS macd_line DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS macd_signal DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS bb_upper DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS bb_mid DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS bb_lower DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS adx_14 DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS stoch_rsi_k DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS stoch_rsi_d DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS pivot DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS pivot_r1 DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS pivot_r2 DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS pivot_s1 DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS pivot_s2 DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS vwap DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS ret_5d DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS ret_21d DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS ret_63d DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS ret_126d DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS volume_ratio_20 DOUBLE",
    "ALTER TABLE technical_indicators ADD COLUMN IF NOT EXISTS rel_strength_63d DOUBLE",
]


def connect(path: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Open (creating the parent dir if needed) a DuckDB connection to ``path``.

    Defaults to ``settings.duckdb_path``. Pass ``:memory:`` via a Path for tests.
    """
    db_path = path or get_settings().duckdb_path
    if str(db_path) != ":memory:":
        db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Apply ``schema.sql`` then M2 column migrations (all idempotent).

    Line comments are stripped before splitting on ``;`` so a semicolon inside a
    ``--`` comment is not mistaken for a statement separator.
    """
    raw = SCHEMA_PATH.read_text(encoding="utf-8")
    lines: list[str] = []
    for line in raw.splitlines():
        comment_at = line.find("--")
        lines.append(line[:comment_at] if comment_at != -1 else line)
    script = "\n".join(lines)
    for statement in script.split(";"):
        if statement.strip():
            conn.execute(statement)
    for migration in _M2_MIGRATIONS:
        conn.execute(migration)


@contextmanager
def get_connection(path: Path | None = None) -> Iterator[duckdb.DuckDBPyConnection]:
    """Context-managed connection with the schema ensured."""
    conn = connect(path)
    try:
        init_schema(conn)
        yield conn
    finally:
        conn.close()
