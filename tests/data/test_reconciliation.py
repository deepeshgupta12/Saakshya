"""Reconciliation tests (SPEC §6.1, docs/steps/01 — reconcile vs 2nd source).

Uses an in-memory DuckDB database so tests run without network or file I/O.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from app.data.reconcile import ReconcileResult, check_abnormal_jumps, reconcile_stock
from tests.dbutil import pg_cm as get_connection
from app.storage.repository import CorpActionRecord, OhlcBar, Repository, StockMaster

MEMORY = Path(":memory:")


def _bar(stock_id: int, d: date, close_raw: float, close_adj: float) -> OhlcBar:
    return OhlcBar(
        stock_id=stock_id,
        session_date=d,
        open_raw=close_raw, high_raw=close_raw, low_raw=close_raw, close_raw=close_raw,
        open_adj=close_adj, high_adj=close_adj, low_adj=close_adj, close_adj=close_adj,
        volume=1000, is_adjusted=True, adj_factor=close_adj / close_raw if close_raw else 1.0,
        source="test", as_of_version=1, reconciled=False,
    )


# ---------------------------------------------------------------------------
# reconcile_stock
# ---------------------------------------------------------------------------

def test_matching_2nd_source_sets_reconciled() -> None:
    """Our adj_close within 1% of yfinance adj_close → reconciled_count increments."""
    with get_connection(MEMORY) as conn:
        repo = Repository(conn)
        sid = repo.upsert_stock(StockMaster(primary_symbol="RC1", name="RC Co 1"))

        bars = [
            _bar(sid, date(2024, 1, 2), close_raw=1000.0, close_adj=500.0),  # after split
            _bar(sid, date(2024, 1, 3), close_raw=502.0,  close_adj=502.0),
        ]
        # yfinance adj_close matches ours within tolerance.
        yf_adj = {date(2024, 1, 2): 500.5, date(2024, 1, 3): 502.0}

        result = reconcile_stock(sid, bars, yf_adj, repo, job_id="test")

    assert isinstance(result, ReconcileResult)
    assert result.reconciled == 2
    assert result.mismatches == 0
    assert result.no_reference == 0


def test_mismatch_writes_dq_log() -> None:
    """Our adj_close differs >1% from yfinance → mismatch logged, reconciled=False."""
    with get_connection(MEMORY) as conn:
        repo = Repository(conn)
        sid = repo.upsert_stock(StockMaster(primary_symbol="RC2", name="RC Co 2"))

        bars = [
            _bar(sid, date(2024, 1, 2), close_raw=1000.0, close_adj=500.0),
        ]
        # yfinance says 600 — we computed 500; diff = 16.7%, well above 1% tol.
        yf_adj = {date(2024, 1, 2): 600.0}

        result = reconcile_stock(sid, bars, yf_adj, repo, job_id="test_mismatch")

        # Confirm DQ log was written.
        dq_rows = conn.execute(
            "SELECT check_type, status FROM data_quality_logs WHERE stock_id=%s", [sid]
        ).fetchall()

    assert result.mismatches == 1
    assert result.reconciled == 0
    assert len(dq_rows) == 1
    assert dq_rows[0][0] == "reconcile_mismatch"
    assert dq_rows[0][1] == "quarantined"


def test_no_yf_reference_marks_no_reference() -> None:
    """Missing yfinance reference → no_reference count; no DQ log written."""
    with get_connection(MEMORY) as conn:
        repo = Repository(conn)
        sid = repo.upsert_stock(StockMaster(primary_symbol="RC3", name="RC Co 3"))

        bars = [_bar(sid, date(2024, 1, 2), close_raw=1000.0, close_adj=500.0)]
        result = reconcile_stock(sid, bars, {}, repo, job_id="test_no_ref")

        dq_count = conn.execute(
            "SELECT count(*) FROM data_quality_logs WHERE stock_id=%s", [sid]
        ).fetchone()[0]

    assert result.no_reference == 1
    assert result.reconciled == 0
    assert result.mismatches == 0
    assert dq_count == 0


def test_reconcile_tolerance_boundary() -> None:
    """Exactly 1% difference is within tolerance; > 1% is a mismatch."""
    with get_connection(MEMORY) as conn:
        repo = Repository(conn)
        sid = repo.upsert_stock(StockMaster(primary_symbol="RC4", name="RC Co 4"))

        bars = [
            _bar(sid, date(2024, 1, 2), close_raw=100.0, close_adj=100.0),
            _bar(sid, date(2024, 1, 3), close_raw=100.0, close_adj=100.0),
        ]
        # 1.0% diff = at tolerance boundary (tol=0.01 uses <=)
        # 1.1% diff = beyond tolerance
        yf_adj = {date(2024, 1, 2): 101.0, date(2024, 1, 3): 101.1}

        result = reconcile_stock(sid, bars, yf_adj, repo, job_id="test_tol", tol=0.01)

    assert result.reconciled == 1  # 2024-01-02: diff=1.0% → reconciled
    assert result.mismatches == 1  # 2024-01-03: diff=1.1% → mismatch


# ---------------------------------------------------------------------------
# check_abnormal_jumps
# ---------------------------------------------------------------------------

def test_abnormal_jump_no_corp_action_quarantined() -> None:
    """A 20% move with no corp action → quarantined."""
    with get_connection(MEMORY) as conn:
        repo = Repository(conn)
        sid = repo.upsert_stock(StockMaster(primary_symbol="AJ1", name="AJ Co 1"))

        bars = [
            _bar(sid, date(2024, 1, 2), close_raw=100.0, close_adj=100.0),
            _bar(sid, date(2024, 1, 3), close_raw=125.0, close_adj=125.0),  # +25%
        ]
        count = check_abnormal_jumps(sid, bars, [], repo, "test_jump", threshold=0.15)

        dq_rows = conn.execute(
            "SELECT check_type FROM data_quality_logs WHERE stock_id=%s", [sid]
        ).fetchall()

    assert count == 1
    assert dq_rows[0][0] == "abnormal_jump"


def test_abnormal_jump_explained_by_corp_action_ignored() -> None:
    """A 50% drop on a split ex_date is NOT quarantined — it's explained."""
    with get_connection(MEMORY) as conn:
        repo = Repository(conn)
        sid = repo.upsert_stock(StockMaster(primary_symbol="AJ2", name="AJ Co 2"))

        bars = [
            _bar(sid, date(2024, 1, 2), close_raw=100.0, close_adj=100.0),
            _bar(sid, date(2024, 1, 3), close_raw=50.0,  close_adj=50.0),  # −50% (split)
        ]
        split_action = CorpActionRecord(
            stock_id=sid, action_type="split",
            ex_date=date(2024, 1, 3), ratio_from=1.0, ratio_to=2.0,
            factor=0.5, source="test",
        )
        count = check_abnormal_jumps(sid, bars, [split_action], repo, "test_jump2",
                                     threshold=0.15)

    assert count == 0
