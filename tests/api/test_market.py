"""API contract tests for GET /v1/market/summary."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.storage.repository import OhlcBar, Repository, StockMaster


def _seed_db(conn):
    """Seed a minimal in-memory DB with one stock, one OHLC bar, one scanner result."""
    repo = Repository(conn)
    sid = repo.upsert_stock(StockMaster(primary_symbol="RELIANCE", name="Reliance"))
    bar = OhlcBar(
        stock_id=sid, session_date=date(2024, 1, 2),
        open_raw=2400, high_raw=2450, low_raw=2380, close_raw=2420,
        open_adj=2400, high_adj=2450, low_adj=2380, close_adj=2420,
        volume=1_000_000, as_of_version=1, source="test",
    )
    repo.upsert_ohlc([bar])
    import json
    repo.upsert_scanner_result(
        scanner="momentum", stock_id=sid, session_date=date(2024, 1, 2),
        composite_score=75.0,
        sub_scores_json=json.dumps({"ret_21d": 70.0}),
        facts_json=json.dumps({"ret_21d": 0.05}),
        signal_tags_json=json.dumps(["MOMENTUM_STRONG"]),
        risk_flags_json=json.dumps([]),
        data_confidence="HIGH", weights_version="1.0",
        validation_status="VALIDATED", as_of_version=1, engine_version="1.0",
    )
    return conn


@pytest.fixture
def client():
    import duckdb
    conn = duckdb.connect(":memory:")
    # Apply schema.
    from app.storage.duckdb import init_schema
    init_schema(conn)
    _seed_db(conn)

    from app.api import deps
    from app.main import app

    # Override DB dependency to use the seeded in-memory connection.
    def _override_db():
        yield conn

    app.dependency_overrides[deps.get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    conn.close()


def test_market_summary_shape(client) -> None:
    resp = client.get("/v1/market/summary?date=2024-01-02")
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    assert body["data"]["session_date"] == "2024-01-02"
    # API returns scanner_counts (not scanners) — see D-037
    assert "scanner_counts" in body["data"]
    assert "momentum" in body["data"]["scanner_counts"]
    assert body["data"]["scanner_counts"]["momentum"]["count"] == 1


def test_market_summary_no_data_returns_422(client) -> None:
    resp = client.get("/v1/market/summary?date=1990-01-01")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "DATA_SUPPRESSED"


def test_health_endpoint(client) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
