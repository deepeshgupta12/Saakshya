"""API + SQL regression tests for /v1/sectors (D-059 polyglot).

Guards the TimescaleDB port: the sector aggregation used ``ROUND(<double>, 2)`` which
Postgres rejects (unlike DuckDB). Runs against the live `pg` fixture.
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.storage.repository import OhlcBar, Repository, StockMaster


def _bar(sid: int, d: date, close: float) -> OhlcBar:
    return OhlcBar(
        stock_id=sid, session_date=d,
        open_raw=close, high_raw=close, low_raw=close, close_raw=close,
        open_adj=close, high_adj=close, low_adj=close, close_adj=close,
        volume=1000, as_of_version=1, source="test",
    )


@pytest.fixture
def seeded(pg):
    """Two sectors, two sessions: IT (INFY +10%, TCS -5%) and Financials (SBIN +10%)."""
    d1, d2 = date(2026, 6, 29), date(2026, 6, 30)
    repo = Repository(pg)
    it = repo.upsert_sector("Information Technology")
    fin = repo.upsert_sector("Financials")
    infy = repo.upsert_stock(StockMaster(primary_symbol="INFY", name="Infosys", sector_id=it))
    tcs = repo.upsert_stock(StockMaster(primary_symbol="TCS", name="TCS", sector_id=it))
    sbi = repo.upsert_stock(StockMaster(primary_symbol="SBIN", name="State Bank", sector_id=fin))
    repo.upsert_ohlc([
        _bar(infy, d1, 100.0), _bar(infy, d2, 110.0),
        _bar(tcs, d1, 200.0), _bar(tcs, d2, 190.0),
        _bar(sbi, d1, 50.0), _bar(sbi, d2, 55.0),
    ])
    return pg, d2


def test_sector_rows_compute_change_pct_on_postgres(seeded):
    """_sector_rows must run (no ROUND(double) error) and compute correct averages."""
    from app.api.routers.sectors import _sector_rows

    pg, d2 = seeded
    rows = {r["name"]: r for r in _sector_rows(pg, d2)}
    assert rows["Financials"]["change_pct"] == 10.0        # SBIN +10%
    assert rows["Information Technology"]["change_pct"] == 2.5  # avg(+10%, -5%)
    # ranked by avg change, descending
    assert rows["Financials"]["rank"] < rows["Information Technology"]["rank"]


def test_sectors_endpoint_returns_200_with_data(seeded):
    from app.api import deps
    from app.main import app

    pg, _ = seeded

    def _db_override():
        yield pg

    app.dependency_overrides[deps.get_db] = _db_override
    try:
        with TestClient(app) as client:
            resp = client.get("/v1/sectors")
            assert resp.status_code == 200
            names = [s["name"] for s in resp.json()["data"]]
            assert "Financials" in names and "Information Technology" in names
    finally:
        app.dependency_overrides.clear()
