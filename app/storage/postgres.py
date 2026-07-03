"""TimescaleDB (Postgres) connection factory + schema bootstrap (D-059).

The analytics core lives here (OHLC/indicators/scanners/AI/news). Mirrors the retired
DuckDB module's ``connect`` / ``init_schema`` / ``get_connection`` surface so the
Repository port is mechanical. Connections are ``autocommit=True`` to match DuckDB's
implicit-commit behaviour (each ``execute`` commits) — keeps repository methods simple.

psycopg (v3) uses ``%s`` placeholders (not DuckDB's ``?``); the Repository port swaps them.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psycopg

from app.config import get_settings

SCHEMA_PATH: Path = Path(__file__).with_name("schema_postgres.sql")

# Schema DDL is idempotent (IF NOT EXISTS); run it once per process, not per connection.
_schema_ready: bool = False


def connect(url: str | None = None) -> psycopg.Connection:
    """Open an autocommit connection to TimescaleDB (defaults to settings.timescale_url)."""
    dsn = url or get_settings().timescale_url
    return psycopg.connect(dsn, autocommit=True)


def init_schema(conn: psycopg.Connection) -> None:
    """Apply ``schema_postgres.sql`` (idempotent). Line comments stripped before split."""
    raw = SCHEMA_PATH.read_text(encoding="utf-8")
    lines: list[str] = []
    for line in raw.splitlines():
        comment_at = line.find("--")
        lines.append(line[:comment_at] if comment_at != -1 else line)
    script = "\n".join(lines)
    for statement in script.split(";"):
        if statement.strip():
            conn.execute(statement)


@contextmanager
def get_connection(url: str | None = None) -> Iterator[psycopg.Connection]:
    """Context-managed connection with the schema ensured once per process."""
    global _schema_ready
    conn = connect(url)
    try:
        if not _schema_ready:
            init_schema(conn)
            _schema_ready = True
        yield conn
    finally:
        conn.close()


def reset_schema_flag() -> None:
    """Force the next get_connection() to re-run schema init (used by tests)."""
    global _schema_ready
    _schema_ready = False
