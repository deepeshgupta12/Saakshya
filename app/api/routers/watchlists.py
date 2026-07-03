"""Watchlist endpoints — CRUD + hydrated item list (docs/10 §8, docs/04 §M7).

Polyglot (D-059): watchlist/item documents live in MongoDB (user-private); item
hydration (last_close / change_pct / scanner_tags) and symbol validation read the
analytics core from TimescaleDB. All routes require JWT auth (AuthUserDep).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel
from pymongo.database import Database

from app.api.deps import AsOfDep, AuthUserDep, DbDep, MongoDep
from app.api.envelope import ok

router = APIRouter(prefix="/api/watchlists", tags=["watchlists"])


# ── Request models ─────────────────────────────────────────────────────────

class CreateWatchlistBody(BaseModel):
    name: str


class RenameWatchlistBody(BaseModel):
    name: str


class AddItemBody(BaseModel):
    symbol: str


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


# ── Helpers ────────────────────────────────────────────────────────────────

def _assert_owns(mongo: Database, watchlist_id: str, user_id: str) -> None:
    doc = mongo.watchlists.find_one({"watchlist_id": watchlist_id}, {"user_id": 1})
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found.")
    if doc["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your watchlist.")


def _hydrate_items(conn: Any, symbols: list[str], as_of: Any) -> list[dict[str, Any]]:
    """Attach last_close / change_pct / scanner_tags from TimescaleDB (analytics core).

    daily_ohlc uses stock_id FK (no symbol column) and close_adj — join via stock_master.
    """
    if not symbols:
        return []
    placeholders = ", ".join(["%s"] * len(symbols))
    date_args    = [as_of] if as_of else []
    date_clause  = "AND ohlc.session_date = %s" if as_of else "AND ohlc.session_date = (SELECT max(session_date) FROM daily_ohlc)"
    rows = conn.execute(
        f"""
        SELECT
            sm.primary_symbol,
            sm.name           AS company_name,
            sec.name          AS sector,
            ohlc.close_adj    AS last_close,
            ROUND(CAST(100.0 * (ohlc.close_adj - lag_close) / NULLIF(lag_close, 0) AS numeric), 2) AS change_pct
        FROM stock_master sm
        LEFT JOIN sector_master sec ON sec.sector_id = sm.sector_id
        LEFT JOIN (
            SELECT
                stock_id,
                session_date,
                close_adj,
                LAG(close_adj) OVER (PARTITION BY stock_id ORDER BY session_date) AS lag_close
            FROM daily_ohlc
        ) ohlc ON ohlc.stock_id = sm.stock_id
            {date_clause}
        WHERE sm.primary_symbol IN ({placeholders})
        """,
        date_args + symbols,
    ).fetchall()
    tag_rows = conn.execute(
        f"""
        SELECT sm.primary_symbol, sr.scanner, sr.composite_score
        FROM scanner_results sr
        JOIN stock_master sm ON sm.stock_id = sr.stock_id
        WHERE sm.primary_symbol IN ({placeholders})
          AND sr.session_date = (SELECT max(session_date) FROM scanner_results)
        ORDER BY sr.composite_score DESC
        """,
        symbols,
    ).fetchall()
    tags_by_symbol: dict[str, list[str]] = {}
    for sym, scanner, _score in tag_rows:
        tags_by_symbol.setdefault(sym, []).append(scanner)

    result = []
    for row in rows:
        sym, name, sector, last_close, change_pct = row
        result.append({
            "symbol":       sym,
            "company_name": name,
            "sector":       sector,
            "last_close":   float(last_close) if last_close is not None else None,
            "change_pct":   float(change_pct) if change_pct is not None else None,
            "scanner_tags": tags_by_symbol.get(sym, []),
        })
    found_syms = {r["symbol"] for r in result}
    for sym in symbols:
        if sym not in found_syms:
            result.append({
                "symbol": sym, "company_name": None, "sector": None,
                "last_close": None, "change_pct": None, "scanner_tags": [],
            })
    return result


# ── Routes ─────────────────────────────────────────────────────────────────

@router.get("")
def list_watchlists(user: AuthUserDep, mongo: MongoDep) -> dict[str, Any]:
    docs = mongo.watchlists.find({"user_id": user.user_id}).sort("created_at", 1)
    watchlists = [
        {"watchlist_id": d["watchlist_id"], "name": d["name"], "created_at": str(d["created_at"])}
        for d in docs
    ]
    return ok(watchlists)


@router.post("", status_code=201)
def create_watchlist(body: CreateWatchlistBody, user: AuthUserDep, mongo: MongoDep) -> dict[str, Any]:
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="Watchlist name cannot be empty.")
    watchlist_id = str(uuid.uuid4())
    now = _now()
    mongo.watchlists.insert_one({
        "watchlist_id": watchlist_id, "user_id": user.user_id,
        "name": body.name.strip(), "created_at": now, "updated_at": now,
    })
    return ok({"watchlist_id": watchlist_id, "name": body.name.strip()})


@router.get("/{watchlist_id}")
def get_watchlist(
    watchlist_id: str,
    user: AuthUserDep,
    conn: DbDep,
    mongo: MongoDep,
    as_of: AsOfDep,
) -> dict[str, Any]:
    _assert_owns(mongo, watchlist_id, user.user_id)
    meta = mongo.watchlists.find_one({"watchlist_id": watchlist_id})
    item_docs = list(mongo.watchlist_items.find({"watchlist_id": watchlist_id}).sort("added_at", 1))
    symbols = [d["symbol"] for d in item_docs]
    hydrated = _hydrate_items(conn, symbols, as_of)
    hydrated_map = {h["symbol"]: h for h in hydrated}
    items = [
        {
            "item_id":  d["item_id"],
            "added_at": str(d["added_at"]),
            **hydrated_map.get(d["symbol"], {"symbol": d["symbol"]}),
        }
        for d in item_docs
    ]
    return ok({
        "watchlist_id": watchlist_id,
        "name":         meta["name"],
        "created_at":   str(meta["created_at"]),
        "items":        items,
    })


@router.patch("/{watchlist_id}")
def rename_watchlist(
    watchlist_id: str,
    body: RenameWatchlistBody,
    user: AuthUserDep,
    mongo: MongoDep,
) -> dict[str, Any]:
    _assert_owns(mongo, watchlist_id, user.user_id)
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="Watchlist name cannot be empty.")
    mongo.watchlists.update_one(
        {"watchlist_id": watchlist_id},
        {"$set": {"name": body.name.strip(), "updated_at": _now()}},
    )
    return ok({"watchlist_id": watchlist_id, "name": body.name.strip()})


@router.delete("/{watchlist_id}", status_code=204)
def delete_watchlist(watchlist_id: str, user: AuthUserDep, mongo: MongoDep) -> Response:
    _assert_owns(mongo, watchlist_id, user.user_id)
    mongo.watchlist_items.delete_many({"watchlist_id": watchlist_id})
    mongo.watchlists.delete_one({"watchlist_id": watchlist_id})
    return Response(status_code=204)


@router.post("/{watchlist_id}/items", status_code=201)
def add_item(
    watchlist_id: str,
    body: AddItemBody,
    user: AuthUserDep,
    conn: DbDep,
    mongo: MongoDep,
) -> dict[str, Any]:
    _assert_owns(mongo, watchlist_id, user.user_id)
    symbol = body.symbol.upper().strip()
    # Validate symbol against the analytics universe (TimescaleDB).
    row = conn.execute(
        "SELECT primary_symbol FROM stock_master WHERE primary_symbol = %s", [symbol]
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol!r} not found in universe.")
    existing = mongo.watchlist_items.find_one(
        {"watchlist_id": watchlist_id, "symbol": symbol}, {"item_id": 1}
    )
    if existing:
        return ok({"item_id": existing["item_id"], "symbol": symbol, "already_present": True})
    item_id = str(uuid.uuid4())
    mongo.watchlist_items.insert_one({
        "item_id": item_id, "watchlist_id": watchlist_id,
        "user_id": user.user_id, "symbol": symbol, "added_at": _now(),
    })
    return ok({"item_id": item_id, "symbol": symbol, "already_present": False})


@router.delete("/{watchlist_id}/items/{item_id}", status_code=204)
def remove_item(watchlist_id: str, item_id: str, user: AuthUserDep, mongo: MongoDep) -> Response:
    _assert_owns(mongo, watchlist_id, user.user_id)
    mongo.watchlist_items.delete_one({"item_id": item_id, "watchlist_id": watchlist_id})
    return Response(status_code=204)
