"""MongoDB client for user/app documents (D-059).

Holds the document-shaped, per-user data that is NOT joined to the analytics time-series:
portfolios, transactions, alerts, strategies, watchlists, and auth. The analytics core
(OHLC/indicators/scanners/AI/news) lives in TimescaleDB — see app/storage/postgres.py.

Linked to analytics only by symbol string (never a DB join), so the two stores stay
independent.
"""

from __future__ import annotations

from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database

from app.config import get_settings


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    """Process-wide MongoDB client (pooled)."""
    return MongoClient(get_settings().mongodb_url, tz_aware=True)


def get_db() -> Database:
    """Return the Saakshya Mongo database, ensuring indexes once per process."""
    from app.storage.mongo_setup import ensure_indexes  # noqa: PLC0415 — avoid import cycle

    db = get_client()[get_settings().mongodb_db]
    ensure_indexes(db)
    return db


def reset_client() -> None:
    """Drop the cached client (used by tests pointing at a fresh Mongo)."""
    get_client.cache_clear()
