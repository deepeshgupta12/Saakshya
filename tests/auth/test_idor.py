"""IDOR test suite — user A cannot read/write user B's resources (docs/23 §2).

Exit gate from step 07: user A cannot read/write any of user B's watchlists/
preferences (must return 403 or 404, never user B's data).

Tests:
- List watchlists: only own watchlists returned, never cross-user
- Get watchlist by ID: 403 if owned by another user
- Rename watchlist: 403 if owned by another user
- Delete watchlist: 403 if owned by another user
- Add item: 403 if watchlist owned by another user
- Remove item: 403 if watchlist owned by another user
"""

from __future__ import annotations

import uuid
import pytest

from tests.auth.conftest import _make_user


def _create_watchlist(client, token: str, name: str = "My List") -> str:
    resp = client.post(
        "/api/watchlists",
        json={"name": name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["watchlist_id"]


# ── List isolation ─────────────────────────────────────────────────────────────

def test_list_watchlists_only_own(client, two_users):
    (uid_a, tok_a), (uid_b, tok_b) = two_users
    _create_watchlist(client, tok_a, "A-List")
    _create_watchlist(client, tok_b, "B-List")

    resp = client.get("/api/watchlists", headers={"Authorization": f"Bearer {tok_a}"})
    assert resp.status_code == 200
    names = [w["name"] for w in resp.json()["data"]]
    assert "A-List" in names
    assert "B-List" not in names, "User A must never see User B's watchlists"


# ── Read isolation ─────────────────────────────────────────────────────────────

def test_get_watchlist_cross_user_forbidden(client, two_users):
    (uid_a, tok_a), (uid_b, tok_b) = two_users
    wid_b = _create_watchlist(client, tok_b, "B-Secret")

    resp = client.get(f"/api/watchlists/{wid_b}", headers={"Authorization": f"Bearer {tok_a}"})
    assert resp.status_code in (403, 404), f"Expected 403/404, got {resp.status_code}: {resp.text}"


def test_get_own_watchlist_succeeds(client, two_users):
    (uid_a, tok_a), _ = two_users
    wid_a = _create_watchlist(client, tok_a, "A-Own")
    resp = client.get(f"/api/watchlists/{wid_a}", headers={"Authorization": f"Bearer {tok_a}"})
    assert resp.status_code == 200
    assert resp.json()["data"]["watchlist_id"] == wid_a


# ── Mutation isolation ─────────────────────────────────────────────────────────

def test_rename_cross_user_forbidden(client, two_users):
    (uid_a, tok_a), (uid_b, tok_b) = two_users
    wid_b = _create_watchlist(client, tok_b, "B-Original")

    resp = client.patch(
        f"/api/watchlists/{wid_b}",
        json={"name": "Hijacked"},
        headers={"Authorization": f"Bearer {tok_a}"},
    )
    assert resp.status_code in (403, 404)

    # Verify B's list is unchanged
    resp_b = client.get(f"/api/watchlists/{wid_b}", headers={"Authorization": f"Bearer {tok_b}"})
    assert resp_b.json()["data"]["name"] == "B-Original"


def test_delete_cross_user_forbidden(client, two_users):
    (uid_a, tok_a), (uid_b, tok_b) = two_users
    wid_b = _create_watchlist(client, tok_b, "B-Delete-Target")

    resp = client.delete(f"/api/watchlists/{wid_b}", headers={"Authorization": f"Bearer {tok_a}"})
    assert resp.status_code in (403, 404)

    # Verify B's list still exists
    resp_b = client.get(f"/api/watchlists/{wid_b}", headers={"Authorization": f"Bearer {tok_b}"})
    assert resp_b.status_code == 200


def test_add_item_cross_user_forbidden(client, two_users, mem_db):
    (uid_a, tok_a), (uid_b, tok_b) = two_users
    wid_b = _create_watchlist(client, tok_b, "B-Items")

    # Seed a valid symbol so the symbol-exists check passes
    mem_db.execute(
        "INSERT OR IGNORE INTO stock_master (primary_symbol, name) VALUES (?, ?)",
        ["RELIANCE", "Reliance Industries"],
    )

    resp = client.post(
        f"/api/watchlists/{wid_b}/items",
        json={"symbol": "RELIANCE"},
        headers={"Authorization": f"Bearer {tok_a}"},
    )
    assert resp.status_code in (403, 404)


def test_remove_item_cross_user_forbidden(client, two_users, mem_db):
    (uid_a, tok_a), (uid_b, tok_b) = two_users
    # Seed symbol
    mem_db.execute(
        "INSERT OR IGNORE INTO stock_master (primary_symbol, name) VALUES (?, ?)",
        ["INFY", "Infosys"],
    )
    wid_b = _create_watchlist(client, tok_b, "B-WithItem")
    # Add item as B
    add_resp = client.post(
        f"/api/watchlists/{wid_b}/items",
        json={"symbol": "INFY"},
        headers={"Authorization": f"Bearer {tok_b}"},
    )
    assert add_resp.status_code == 201
    item_id = add_resp.json()["data"]["item_id"]

    # Try removing as A → must be forbidden
    resp = client.delete(
        f"/api/watchlists/{wid_b}/items/{item_id}",
        headers={"Authorization": f"Bearer {tok_a}"},
    )
    assert resp.status_code in (403, 404)

    # Verify item still exists for B
    detail = client.get(f"/api/watchlists/{wid_b}", headers={"Authorization": f"Bearer {tok_b}"})
    symbols = [i["symbol"] for i in detail.json()["data"]["items"]]
    assert "INFY" in symbols


# ── No-auth fallback ──────────────────────────────────────────────────────────

def test_watchlists_require_auth(client):
    resp = client.get("/api/watchlists")
    assert resp.status_code == 401

    resp = client.post("/api/watchlists", json={"name": "Anon"})
    assert resp.status_code == 401
