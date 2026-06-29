"""2nd-source cross-reconciliation helpers (SPEC §6.1, docs/12 §4, docs/steps/01).

This module provides utilities that are used by the adjuster and the pipeline to
compare our computed adjusted series against an external reference.

reconcile_stock   — compares our adj_close vs a reference dict for one stock;
                    returns (reconciled_count, mismatch_count).
check_abnormal_jumps — flags unexplained price moves (not backed by a corp action).

These are thin wrappers over the logic in corp_action_adjuster._adjust_stock;
exposed here so other pipeline stages (e.g. future intraday reconciler) can reuse
them without depending on the full adjuster.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.storage.repository import CorpActionRecord, OhlcBar, Repository

_DEFAULT_TOL = 0.01


@dataclass
class ReconcileResult:
    stock_id: int
    reconciled: int
    mismatches: int
    no_reference: int  # dates where yf_adj_close had no entry


def reconcile_stock(
    stock_id: int,
    bars: list[OhlcBar],
    yf_adj_close: dict[date, float],
    repo: Repository,
    job_id: str,
    tol: float = _DEFAULT_TOL,
) -> ReconcileResult:
    """Compare bar.close_adj against yf_adj_close; write a DQ log entry on any mismatch.

    This is a *read-only* operation on ``bars`` — it does not update the DB rows.
    The adjuster (corp_action_adjuster.py) is what writes the adj columns; this module
    can be used independently to audit an already-adjusted dataset.
    """
    from app.storage.repository import DataQualityLog

    reconciled = mismatches = no_ref = 0
    for bar in bars:
        yf_c = yf_adj_close.get(bar.session_date)
        if yf_c is None or yf_c <= 0:
            no_ref += 1
            continue
        rel_diff = abs(bar.close_adj - yf_c) / yf_c
        if rel_diff <= tol:
            reconciled += 1
        else:
            mismatches += 1
            repo.write_quality_log(DataQualityLog(
                job_id=job_id,
                source="reconcile",
                check_type="reconcile_mismatch",
                severity="warn",
                status="quarantined",
                stock_id=stock_id,
                session_date=bar.session_date,
                detail=(
                    f"adj_close={bar.close_adj:.4f} yf_adj={yf_c:.4f} "
                    f"diff={rel_diff * 100:.2f}%"
                ),
            ))
    return ReconcileResult(
        stock_id=stock_id,
        reconciled=reconciled,
        mismatches=mismatches,
        no_reference=no_ref,
    )


def check_abnormal_jumps(
    stock_id: int,
    bars: list[OhlcBar],
    corp_actions: list[CorpActionRecord],
    repo: Repository,
    job_id: str,
    threshold: float = 0.15,
) -> int:
    """Quarantine session dates with unexplained raw-price moves exceeding ``threshold``.

    A move is "explained" if there is a corp action (split/bonus/rights/merger) on that
    ex_date. Dividend ex-dates are excluded from the flag (dividends cause small drops
    well below a 15 % threshold in most cases).

    Returns the count of dates quarantined.
    """
    from app.storage.repository import DataQualityLog

    ca_ex_dates = {
        a.ex_date
        for a in corp_actions
        if a.action_type not in ("dividend",) and a.factor is not None
    }
    quarantined = 0
    for i in range(1, len(bars)):
        prev_close = bars[i - 1].close_raw
        curr_close = bars[i].close_raw
        if prev_close <= 0:
            continue
        move = abs(curr_close / prev_close - 1.0)
        if move > threshold and bars[i].session_date not in ca_ex_dates:
            repo.write_quality_log(DataQualityLog(
                job_id=job_id,
                source="reconcile",
                check_type="abnormal_jump",
                severity="warn",
                status="quarantined",
                stock_id=stock_id,
                session_date=bars[i].session_date,
                detail=(
                    f"raw close moved {move * 100:.1f}% "
                    f"({prev_close:.2f}→{curr_close:.2f}) with no corp action"
                ),
            ))
            quarantined += 1
    return quarantined
