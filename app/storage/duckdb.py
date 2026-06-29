"""DuckDB connection factory + schema bootstrap (local-first storage, SPEC §12)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb

from app.config import get_settings

SCHEMA_PATH: Path = Path(__file__).with_name("schema.sql")


def connect(path: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Open (creating the parent dir if needed) a DuckDB connection to ``path``.

    Defaults to ``settings.duckdb_path``. Pass ``:memory:`` via a Path for tests.
    """
    db_path = path or get_settings().duckdb_path
    if str(db_path) != ":memory:":
        db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Apply ``schema.sql`` (idempotent — every object uses IF NOT EXISTS).

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


@contextmanager
def get_connection(path: Path | None = None) -> Iterator[duckdb.DuckDBPyConnection]:
    """Context-managed connection with the schema ensured."""
    conn = connect(path)
    try:
        init_schema(conn)
        yield conn
    finally:
        conn.close()
