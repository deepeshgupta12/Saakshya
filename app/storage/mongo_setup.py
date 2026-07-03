"""MongoDB collection + index setup for the user/app documents (D-059).

Mirrors the UNIQUE/index constraints from the retired DuckDB schema so document
integrity is preserved. Idempotent: ``create_index`` is a no-op if the index exists.

Collections (all under the ``saakshya`` db):
  users, refresh_tokens, consents, user_preferences, oauth_identities,
  watchlists, watchlist_items, portfolios, transactions,
  alert_definitions, alert_events, strategy_definitions, screener_library
"""

from __future__ import annotations

from pymongo import ASCENDING, MongoClient
from pymongo.database import Database

# Names are referenced by the Mongo repositories; keep them centralised here.
COLLECTIONS: tuple[str, ...] = (
    "users",
    "refresh_tokens",
    "consents",
    "user_preferences",
    "oauth_identities",
    "watchlists",
    "watchlist_items",
    "portfolios",
    "transactions",
    "alert_definitions",
    "alert_events",
    "strategy_definitions",
    "screener_library",
)

_ensured_dbs: set[str] = set()


def ensure_indexes(db: Database) -> None:
    """Create the required indexes (idempotent; runs once per (process, db))."""
    if db.name in _ensured_dbs:
        return

    db.users.create_index([("email", ASCENDING)], unique=True, name="uq_user_email")
    db.oauth_identities.create_index(
        [("provider", ASCENDING), ("subject", ASCENDING)],
        unique=True, name="uq_oauth_provider_subject",
    )
    db.refresh_tokens.create_index([("family_id", ASCENDING)], name="ix_refresh_family")
    db.refresh_tokens.create_index([("user_id", ASCENDING)], name="ix_refresh_user")
    db.watchlist_items.create_index([("watchlist_id", ASCENDING)], name="ix_wl_items")
    db.transactions.create_index(
        [("portfolio_id", ASCENDING), ("trade_date", ASCENDING)], name="ix_txn_portfolio_date"
    )
    db.transactions.create_index(
        [("portfolio_id", ASCENDING), ("symbol", ASCENDING)], name="ix_txn_portfolio_symbol"
    )
    db.alert_definitions.create_index(
        [("user_id", ASCENDING), ("enabled", ASCENDING)], name="ix_alertdef_user"
    )
    db.alert_events.create_index(
        [("dedup_key", ASCENDING), ("as_of_date", ASCENDING)],
        unique=True, name="uq_alert_dedup_date",
    )
    db.strategy_definitions.create_index(
        [("owner_user_id", ASCENDING)], name="ix_strategy_owner"
    )
    db.screener_library.create_index([("category", ASCENDING)], name="ix_screener_category")

    _ensured_dbs.add(db.name)


def init_mongo(url: str, db_name: str) -> Database:
    """Standalone setup entry point (used by scripts): connect + ensure indexes."""
    db = MongoClient(url, tz_aware=True)[db_name]
    ensure_indexes(db)
    return db
