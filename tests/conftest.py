"""Shared test fixtures for the polyglot stack (D-059).

Tests run against the live Dockerized TimescaleDB + MongoDB (`docker compose up -d`).
Each fixture hands back a clean database (TimescaleDB tables TRUNCATEd, Mongo
collections emptied) so tests are isolated. If the containers aren't reachable the
DB-dependent test is skipped with a clear message rather than erroring.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.storage.mongo_setup import COLLECTIONS
from tests.dbutil import (
    mongo_reachable,
    open_fresh_pg,
    pg_reachable,
    truncate,
)


@pytest.fixture
def pg() -> Iterator[object]:
    """A TimescaleDB connection with all analytics tables truncated (clean slate)."""
    if not pg_reachable():
        pytest.skip("TimescaleDB not reachable — run `docker compose up -d`")
    conn = open_fresh_pg()
    try:
        yield conn
    finally:
        conn.close()  # type: ignore[attr-defined]


@pytest.fixture
def mongo() -> Iterator[object]:
    """The Mongo database with all user/app collections emptied (clean slate)."""
    if not mongo_reachable():
        pytest.skip("MongoDB not reachable — run `docker compose up -d`")
    from app.storage import mongodb  # noqa: PLC0415

    db = mongodb.get_db()
    for c in COLLECTIONS:
        db[c].delete_many({})
    yield db
    for c in COLLECTIONS:
        db[c].delete_many({})


def override_app_dbs(app: object, pg_conn: object | None = None, mongo_db: object | None = None) -> None:
    """Wire a FastAPI app's DB deps to the given test connections.

    get_db is a generator dependency, so its override must be a generator function.
    """
    from app.api import deps  # noqa: PLC0415

    if pg_conn is not None:
        def _db_override():
            yield pg_conn
        app.dependency_overrides[deps.get_db] = _db_override  # type: ignore[attr-defined]
    if mongo_db is not None:
        app.dependency_overrides[deps.get_mongo] = lambda: mongo_db  # type: ignore[attr-defined]
