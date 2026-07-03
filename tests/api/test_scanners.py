"""API contract tests for GET /v1/scanners and /v1/scanners/{scanner}."""

from __future__ import annotations

import json
from datetime import date

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_with_data(pg):
    from app.api import deps
    from app.main import app
    from app.storage.repository import OhlcBar, Repository, StockMaster

    repo = Repository(pg)
    sid = repo.upsert_stock(StockMaster(primary_symbol="INFY", name="Infosys"))
    repo.upsert_ohlc([OhlcBar(
        stock_id=sid, session_date=date(2024, 1, 2),
        open_raw=1500, high_raw=1550, low_raw=1490, close_raw=1520,
        open_adj=1500, high_adj=1550, low_adj=1490, close_adj=1520,
        volume=2_000_000, as_of_version=1, source="test",
    )])
    repo.upsert_scanner_result(
        scanner="rsi", stock_id=sid, session_date=date(2024, 1, 2),
        composite_score=65.0,
        sub_scores_json=json.dumps({"rsi_band": 65.0}),
        facts_json=json.dumps({"rsi_14": 68.0}),
        signal_tags_json=json.dumps(["RSI_BULLISH"]),
        risk_flags_json=json.dumps([]),
        data_confidence="HIGH", weights_version="1.0",
        validation_status="VALIDATED", as_of_version=1, engine_version="1.0",
    )

    def _db_override():
        yield pg
    app.dependency_overrides[deps.get_db] = _db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_list_scanners_returns_all(client_with_data) -> None:
    resp = client_with_data.get("/v1/scanners")
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    scanners = body["data"]
    labels = [s["label"] for s in scanners]
    assert "Momentum" in labels
    assert "RSI Conditions" in labels


def test_get_scanner_results_shape(client_with_data) -> None:
    resp = client_with_data.get("/v1/scanners/rsi?date=2024-01-02")
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    assert body["meta"]["page"]["total"] == 1
    row = body["data"][0]
    assert row["symbol"] == "INFY"
    assert row["composite_score"] == 65.0
    assert "RSI_BULLISH" in row["signal_tags"]


def test_get_scanner_unknown_returns_404(client_with_data) -> None:
    resp = client_with_data.get("/v1/scanners/nonexistent?date=2024-01-02")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_get_scanner_min_score_filter(client_with_data) -> None:
    resp = client_with_data.get("/v1/scanners/rsi?date=2024-01-02&min_score=80")
    assert resp.status_code == 200
    body = resp.json()
    # Score is 65.0 so it should be filtered out.
    assert body["meta"]["page"]["total"] == 0
    assert body["data"] == []


def test_envelope_structure_on_scanner(client_with_data) -> None:
    resp = client_with_data.get("/v1/scanners/rsi?date=2024-01-02")
    body = resp.json()
    assert "data" in body
    assert "meta" in body
    assert "error" in body
    assert body["meta"]["as_of"] == "2024-01-02"
