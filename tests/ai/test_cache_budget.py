"""Tests for app/ai/cache.py and app/ai/budget.py."""

from __future__ import annotations

import pytest

from app.ai.budget import allow_call, current_count, increment_calls
from app.ai.cache import get_cached, put_cached, signal_category
from app.ai.payload import ComputedBlock, DataConfidence, Payload, Subject
from tests.dbutil import open_fresh_pg


def _db():
    return open_fresh_pg()


def _make_payload(
    tags: list[str] | None = None,
    flags: list[str] | None = None,
    composite: float = 80.0,
) -> Payload:
    return Payload(
        intent="explain_scanner_result",
        as_of_date="2026-06-26",
        as_of_version="v1",
        subject=Subject(type="stock", symbol="INFY.NS"),
        computed=ComputedBlock(
            scanner="momentum",
            composite_score=composite,
            facts={"close": 1500.0, "ret_3m_pct": 10.0, "sma50": 1400.0},
        ),
        signal_tags=tags or ["MOMENTUM_STRONG"],
        risk_flags=flags or [],
        data_confidence=DataConfidence.HIGH,
    )


# ---------------------------------------------------------------------------
# signal_category
# ---------------------------------------------------------------------------

class TestSignalCategory:
    def test_same_payload_same_category(self) -> None:
        p = _make_payload()
        assert signal_category(p) == signal_category(p)

    def test_different_tags_different_category(self) -> None:
        p1 = _make_payload(tags=["MOMENTUM_STRONG"])
        p2 = _make_payload(tags=["VOLUME_SURGE"])
        assert signal_category(p1) != signal_category(p2)

    def test_different_flags_different_category(self) -> None:
        p1 = _make_payload(flags=[])
        p2 = _make_payload(flags=["ELEVATED_VOLATILITY"])
        assert signal_category(p1) != signal_category(p2)

    def test_same_band_score_same_category(self) -> None:
        p1 = _make_payload(composite=80.0)
        p2 = _make_payload(composite=89.9)
        assert signal_category(p1) == signal_category(p2)

    def test_different_band_different_category(self) -> None:
        p1 = _make_payload(composite=79.9)  # band 7
        p2 = _make_payload(composite=80.0)  # band 8
        assert signal_category(p1) != signal_category(p2)


# ---------------------------------------------------------------------------
# Cache put/get
# ---------------------------------------------------------------------------

class TestCache:
    def test_put_then_get_returns_summary(self) -> None:
        conn = _db()
        put_cached("INFY.NS", "cat123", "A summary.", "gen-abc", "2026-06-26", "mock", conn)
        assert get_cached("INFY.NS", "cat123", conn) == "A summary."
        conn.close()

    def test_get_missing_returns_none(self) -> None:
        conn = _db()
        assert get_cached("INFY.NS", "does-not-exist", conn) is None
        conn.close()

    def test_put_twice_upserts(self) -> None:
        conn = _db()
        put_cached("INFY.NS", "cat999", "First.", "id1", "2026-06-26", "m", conn)
        put_cached("INFY.NS", "cat999", "Second.", "id2", "2026-06-26", "m", conn)
        assert get_cached("INFY.NS", "cat999", conn) == "Second."
        conn.close()

    def test_different_symbols_independent(self) -> None:
        conn = _db()
        put_cached("A.NS", "cat", "Alpha.", "id1", "2026-06-26", "m", conn)
        put_cached("B.NS", "cat", "Beta.",  "id2", "2026-06-26", "m", conn)
        assert get_cached("A.NS", "cat", conn) == "Alpha."
        assert get_cached("B.NS", "cat", conn) == "Beta."
        conn.close()


# ---------------------------------------------------------------------------
# Budget (daily call ceiling)
# ---------------------------------------------------------------------------

class TestBudget:
    def test_allow_call_when_empty(self) -> None:
        conn = _db()
        assert allow_call(conn)
        conn.close()

    def test_increment_then_read(self) -> None:
        conn = _db()
        increment_calls(conn)
        increment_calls(conn)
        assert current_count(conn) == 2
        conn.close()

    def test_ceiling_blocks_when_exceeded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app import config as cfg_mod

        conn = _db()
        today = __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).date().isoformat()
        conn.execute(
            "INSERT INTO ai_daily_calls (call_date, call_count) VALUES (%s, 1001)",
            [today],
        )

        # Patch ceiling to 1000.
        monkeypatch.setattr(
            cfg_mod.get_settings(), "ai_daily_call_ceiling", 1000, raising=True
        )
        assert not allow_call(conn)
        conn.close()

    def test_increment_is_idempotent_on_new_day(self) -> None:
        conn = _db()
        for _ in range(3):
            increment_calls(conn)
        assert current_count(conn) == 3
        conn.close()
