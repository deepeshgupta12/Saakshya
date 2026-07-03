"""API contract tests for GET /v1/stocks/{symbol}/* endpoints."""

from __future__ import annotations

import json
from datetime import date

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_with_stock(pg):
    from app.api import deps
    from app.main import app
    from app.storage.repository import OhlcBar, Repository, StockMaster

    conn = pg
    repo = Repository(conn)
    sid = repo.upsert_stock(StockMaster(primary_symbol="TCS", name="Tata Consultancy"))
    repo.upsert_ohlc([OhlcBar(
        stock_id=sid, session_date=date(2024, 1, 2),
        open_raw=3800, high_raw=3850, low_raw=3780, close_raw=3820,
        open_adj=3800, high_adj=3850, low_adj=3780, close_adj=3820,
        volume=500_000, delivery_pct=45.0, as_of_version=1, source="test",
    )])
    # Minimal indicator row.
    conn.execute(
        "INSERT INTO technical_indicators "
        "(stock_id, session_date, as_of_version, indicator_version, rsi_14, sma_50) "
        "VALUES (%s, %s, 1, 1, 62.5, 3700.0)",
        [sid, date(2024, 1, 2)],
    )
    repo.upsert_scanner_result(
        scanner="momentum", stock_id=sid, session_date=date(2024, 1, 2),
        composite_score=72.0,
        sub_scores_json=json.dumps({}),
        facts_json=json.dumps({}),
        signal_tags_json=json.dumps(["MOMENTUM_MODERATE"]),
        risk_flags_json=json.dumps([]),
        data_confidence="HIGH", weights_version="1.0",
        validation_status="VALIDATED", as_of_version=1, engine_version="1.0",
    )

    def _override_db():
        yield conn

    app.dependency_overrides[deps.get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    conn.close()


def test_stock_overview_shape(client_with_stock) -> None:
    resp = client_with_stock.get("/v1/stocks/TCS/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    d = body["data"]
    assert d["symbol"] == "TCS"
    assert d["close"] == 3820.0
    assert "momentum" in d["scanner_memberships"]
    assert "disclaimer" in d


def test_stock_overview_unknown_symbol_404(client_with_stock) -> None:
    resp = client_with_stock.get("/v1/stocks/UNKNOWNSYM/overview")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_stock_technicals_shape(client_with_stock) -> None:
    resp = client_with_stock.get("/v1/stocks/TCS/technicals?date=2024-01-02")
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    assert body["data"]["rsi_14"] == 62.5


def test_stock_technicals_no_data_422(client_with_stock) -> None:
    resp = client_with_stock.get("/v1/stocks/TCS/technicals?date=1990-01-01")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "DATA_SUPPRESSED"


def test_stock_technicals_unknown_symbol_422(client_with_stock) -> None:
    resp = client_with_stock.get("/v1/stocks/GHOSTCO/technicals?date=2024-01-02")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "DATA_SUPPRESSED"
