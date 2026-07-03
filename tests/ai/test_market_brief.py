"""Regression test for the AI market-brief payload builder (D-059 polyglot).

`_build_brief_payload` previously joined `daily_ohlc` on a non-existent `symbol`
column and used DuckDB-only `ROUND(double, n)` / alias-in-`ORDER BY`; the numeric
`ROUND` result also had to be JSON-serializable. Runs against the live `pg` fixture.
"""

from __future__ import annotations

import json
from datetime import date

import pytest
from fastapi.testclient import TestClient  # noqa: F401  (kept parallel with other API tests)

from app.storage.repository import OhlcBar, Repository, StockMaster


def _bar(sid: int, d: date, close: float) -> OhlcBar:
    return OhlcBar(
        stock_id=sid, session_date=d,
        open_raw=close, high_raw=close, low_raw=close, close_raw=close,
        open_adj=close, high_adj=close, low_adj=close, close_adj=close,
        volume=1000, as_of_version=1, source="test",
    )


def test_build_brief_payload_runs_and_is_json_serializable(pg):
    from app.ai.market_brief import _build_brief_payload

    d1, d2 = date(2026, 6, 29), date(2026, 6, 30)
    repo = Repository(pg)
    it = repo.upsert_sector("Information Technology")
    fin = repo.upsert_sector("Financials")
    infy = repo.upsert_stock(StockMaster(primary_symbol="INFY", name="Infosys", sector_id=it))
    tcs = repo.upsert_stock(StockMaster(primary_symbol="TCS", name="TCS", sector_id=it))
    sbi = repo.upsert_stock(StockMaster(primary_symbol="SBIN", name="State Bank", sector_id=fin))
    repo.upsert_ohlc([
        _bar(infy, d1, 100.0), _bar(infy, d2, 110.0),  # +10%
        _bar(tcs, d1, 200.0), _bar(tcs, d2, 190.0),     # -5%
        _bar(sbi, d1, 50.0), _bar(sbi, d2, 55.0),        # +10%
    ])

    payload = _build_brief_payload(pg, d2)
    assert payload is not None
    assert payload["advance_count"] == 2
    assert payload["decline_count"] == 1
    # Top mover is the largest absolute move.
    assert payload["top_movers"][0]["symbol"] in {"INFY", "SBIN"}
    assert payload["top_movers"][0]["change_pct"] == 10.0
    # Must be JSON-serializable (market_brief json.dumps() its own payload → no Decimal).
    json.dumps(payload, ensure_ascii=False)


def test_build_brief_payload_none_when_no_data(pg):
    from app.ai.market_brief import _build_brief_payload

    assert _build_brief_payload(pg, date(2026, 6, 30)) is None
