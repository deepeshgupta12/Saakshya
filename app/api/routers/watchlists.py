"""Watchlist endpoints — CRUD + hydrated item list (docs/10 §8, docs/04 §M7).

All routes require JWT auth (AuthUserDep). Watchlist data is user-private.
Item hydration surfaces last_close/change_pct/scanner_tags from daily_ohlc +
technical_indicators — no forward-looking signals, evidence-led (SPEC §2).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from app.api.deps import AuthUserDep, AsOfDep, DbDep
from app.api.envelope import ok

router = APIRouter(prefix="/api/watchlists", tags=["watchlists"])


# ── Request models ─────────────────────────────────────────────────────────

class CreateWatchlistBody(BaseModel):
    name: str


class RenameWatchlistBody(BaseModel):
    name: str


class AddItemBody(BaseModel):
    symbol: str


# ── Helpers ────────────────────────────────────────────────────────────────

def _assert_owns(conn: Any, watchlist_id: str, user_id: str) -> None:
    row = conn.execute(
        "SELECT user_id FROM watchlists WHERE watchlist_id = ?", [watchlist_id]
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found.")
    if row[0] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your watchlist.")


def _hydrate_items(conn: Any, symbols: list[str], as_of: Any) -> list[dict[str, Any]]:
    """Attach last_close / change_pct / scanner_tags from daily_ohlc + scanner_results."""
    if not symbols:
        return []
    placeholders = ", ".join("?" * len(symbols))
    # Latest price data.
    date_filter = "AND o.session_date = ?" if as_of else ""
    date_args   = [as_of] if as_of else []
    rows = conn.execute(
        f"""
        SELECT
            sm.primary_symbol,
            sm.company_name,
            sm.sector,
            o.close AS last_close,
            ROUND(100.0 * (o.close - lag_close) / NULLIF(lag_close, 0), 2) AS change_pct
        FROM stock_master sm
        LEFT JOIN (
            SELECT
                symbol,
                session_date,
                close,
                LAG(close) OVER (PARTITION BY symbol ORDER BY session_date) AS lag_close
            FROM daily_ohlc
        ) o ON o.symbol = sm.primary_symbol
            {'AND o.session_date = ?' if as_of else 'AND o.session_date = (SELECT max(session_date) FROM daily_ohlc)'}
        WHERE sm.primary_symbol IN ({placeholders})
        """,
        date_args + symbols,
    ).fetchall()
    # Scanner tags (most recent session).
    tag_rows = conn.execute(
        f"""
        SELECT symbol, scanner, rank
        FROM scanner_results
        WHERE symbol IN ({placeholders})
          AND session_date = (SELECT max(session_date) FROM scanner_results)
        ORDER BY rank ASC
        """,
        symbols,
    ).fetchall()
    tags_by_symbol: dict[str, list[str]] = {}
    for sym, scanner, _rank in tag_rows:
        tags_by_symbol.setdefault(sym, []).append(scanner)

    result = []
    for row in rows:
        sym, name, sector, last_close, change_pct = row
        result.append({
            "symbol":       sym,
            "company_name": name,
            "sector":       sector,
            "last_close":   last_close,
            "change_pct":   change_pct,
            "scanner_tags": tags_by_symbol.get(sym, []),
        })
    # Symbols with no OHLC data still appear (with nulls).
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
def list_watchlists(user: AuthUserDep, conn: DbDep) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT watchlist_id, name, created_at FROM watchlists WHERE user_id = ? ORDER BY created_at ASC",
        [user.user_id],
    ).fetchall()
    watchlists = [{"watchlist_id": r[0], "name": r[1], "created_at": str(r[2])} for r in rows]
    return ok(watchlists)


@router.post("", status_code=201)
def create_watchlist(body: CreateWatchlistBody, user: AuthUserDep, conn: DbDep) -> dict[str, Any]:
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="Watchlist name cannot be empty.")
    watchlist_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO watchlists (watchlist_id, user_id, name) VALUES (?, ?, ?)",
        [watchlist_id, user.user_id, body.name.strip()],
    )
    return ok({"watchlist_id": watchlist_id, "name": body.name.strip()})


@router.get("/{watchlist_id}")
def get_watchlist(
    watchlist_id: str,
    user: AuthUserDep,
    conn: DbDep,
    as_of: AsOfDep,
) -> dict[str, Any]:
    _assert_owns(conn, watchlist_id, user.user_id)
    meta_row = conn.execute(
        "SELECT name, created_at FROM watchlists WHERE watchlist_id = ?", [watchlist_id]
    ).fetchone()
    item_rows = conn.execute(
        "SELECT item_id, symbol, added_at FROM watchlist_items WHERE watchlist_id = ? ORDER BY added_at ASC",
        [watchlist_id],
    ).fetchall()
    symbols = [r[1] for r in item_rows]
    hydrated = _hydrate_items(conn, symbols, as_of)
    hydrated_map = {h["symbol"]: h for h in hydrated}
    items = [
        {
            "item_id":  r[0],
            "added_at": str(r[2]),
            **hydrated_map.get(r[1], {"symbol": r[1]}),
        }
        for r in item_rows
    ]
    return ok({
        "watchlist_id": watchlist_id,
        "name":         meta_row[0],
        "created_at":   str(meta_row[1]),
        "items":        items,
    })


@router.patch("/{watchlist_id}")
def rename_watchlist(
    watchlist_id: str,
    body: RenameWatchlistBody,
    user: AuthUserDep,
    conn: DbDep,
) -> dict[str, Any]:
    _assert_owns(conn, watchlist_id, user.user_id)
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="Watchlist name cannot be empty.")
    conn.execute(
        "UPDATE watchlists SET name = ?, updated_at = now() WHERE watchlist_id = ?",
        [body.name.strip(), watchlist_id],
    )
    return ok({"watchlist_id": watchlist_id, "name": body.name.strip()})


@router.delete("/{watchlist_id}", status_code=204)
def delete_watchlist(watchlist_id: str, user: AuthUserDep, conn: DbDep) -> Response:
    _assert_owns(conn, watchlist_id, user.user_id)
    conn.execute("DELETE FROM watchlist_items WHERE watchlist_id = ?", [watchlist_id])
    conn.execute("DELETE FROM watchlists WHERE watchlist_id = ?", [watchlist_id])
    return Response(status_code=204)


@router.post("/{watchlist_id}/items", status_code=201)
def add_item(
    watchlist_id: str,
    body: AddItemBody,
    user: AuthUserDep,
    conn: DbDep,
) -> dict[str, Any]:
    _assert_owns(conn, watchlist_id, user.user_id)
    symbol = body.symbol.upper().strip()
    # Validate symbol exists in stock_master.
    row = conn.execute(
        "SELECT primary_symbol FROM stock_master WHERE primary_symbol = ?", [symbol]
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol!r} not found in universe.")
    # Idempotent — skip if already in the watchlist.
    exists = conn.execute(
        "SELECT item_id FROM watchlist_items WHERE watchlist_id = ? AND symbol = ?",
        [watchlist_id, symbol],
    ).fetchone()
    if exists:
        return ok({"item_id": exists[0], "symbol": symbol, "already_present": True})
    item_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO watchlist_items (item_id, watchlist_id, user_id, symbol) VALUES (?, ?, ?, ?)",
        [item_id, watchlist_id, user.user_id, symbol],
    )
    return ok({"item_id": item_id, "symbol": symbol, "already_present": False})


@router.delete("/{watchlist_id}/items/{item_id}", status_code=204)
def remove_item(watchlist_id: str, item_id: str, user: AuthUserDep, conn: DbDep) -> Response:
    _assert_owns(conn, watchlist_id, user.user_id)
    conn.execute(
        "DELETE FROM watchlist_items WHERE item_id = ? AND watchlist_id = ?",
        [item_id, watchlist_id],
    )
    return Response(status_code=204)
