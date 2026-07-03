"""Corporate-action back-adjuster (SPEC §6.1, docs/12 §4, docs/steps/01).

Two entry points:
  ``compute_adj_factors`` — pure function; given a list of CorpActionRecord and a list
    of session dates, returns the cumulative backward price-adjustment factor for each date.

  ``adjust_all`` — orchestrates the full stock-universe pass: for each stock, reads corp
    actions and raw bars from the DB, computes adj factors, reconciles vs a 2nd
    adj-close baseline (2nd-source cross-check), and bulk-updates the *_adj columns.

Adjustment convention:
  adj_price = raw_price * adj_factor

  adj_factor for a date = product of all single-event factors for corp actions whose
  ex_date is STRICTLY AFTER the bar's session_date. (Bars on the ex_date itself trade
  ex-adjustment, so their adj_factor = product of remaining LATER events only.)

  Example: split (ex 2020-01-15, factor=0.5) and bonus (ex 2022-06-10, factor=0.5):
    bars before 2020-01-15   → factor = 0.5 × 0.5 = 0.25
    bars on / after 2020-01-15 but before 2022-06-10 → factor = 0.5
    bars on / after 2022-06-10 → factor = 1.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.storage.repository import CorpActionRecord, OhlcBar, Repository

_DEFAULT_TOL = 0.01       # 1 % relative tolerance for reconciliation
_JUMP_THRESHOLD = 0.15    # 15 % single-session move triggers abnormal-jump check


def compute_adj_factors(
    actions: list[CorpActionRecord],
    dates: list[date],
) -> list[float]:
    """Compute per-date cumulative backward adjustment factors (pure, no I/O).

    Returns a parallel list of floats; each element corresponds to the same-index date.
    Actions with no computable factor (None) are skipped.
    """
    # Only actions that have a numeric single-event factor.
    actionable = [(a.ex_date, a.factor) for a in actions if a.factor is not None]
    if not actionable or not dates:
        return [1.0] * len(dates)

    # Sort newest → oldest so we accumulate the cumulative multiplier going backward.
    actionable.sort(key=lambda x: x[0], reverse=True)

    factors = [1.0] * len(dates)
    cum = 1.0
    for ex_d, ev_factor in actionable:
        assert ev_factor is not None  # already filtered above; satisfies mypy
        cum *= ev_factor
        for i, d in enumerate(dates):
            if d < ex_d:
                factors[i] = cum
    return factors


@dataclass
class AdjustResult:
    stock_id: int
    bars_updated: int = 0
    reconciled: int = 0
    mismatches: int = 0
    abnormal_jumps: int = 0
    skipped_no_actions: bool = False


@dataclass
class AdjustSummary:
    stocks_processed: int = 0
    bars_updated: int = 0
    reconciled: int = 0
    mismatches: int = 0
    abnormal_jumps: int = 0
    skipped: list[int] = field(default_factory=list)


def adjust_all(
    repo: Repository,
    ticker_to_stock_id: dict[str, int],
    yf_adj_close: dict[str, dict[date, float]],
    as_of_version: int = 1,
    job_id: str = "m1_adjust",
    tol: float = _DEFAULT_TOL,
    jump_threshold: float = _JUMP_THRESHOLD,
) -> AdjustSummary:
    """Adjust every stock in the universe and reconcile against a 2nd source.

    ``yf_adj_close``: ticker → {session_date → adj_close_from_yfinance}.
    Reconciliation compares our computed adj_close vs the 2nd-source adj_close for each date.
    """
    from app.storage.repository import DataQualityLog

    summary = AdjustSummary()
    for ticker, stock_id in ticker_to_stock_id.items():
        yf_map = yf_adj_close.get(ticker, {})
        result = _adjust_stock(repo, stock_id, yf_map, as_of_version, job_id, tol,
                               jump_threshold)
        summary.stocks_processed += 1
        summary.bars_updated += result.bars_updated
        summary.reconciled += result.reconciled
        summary.mismatches += result.mismatches
        summary.abnormal_jumps += result.abnormal_jumps
        if result.skipped_no_actions:
            summary.skipped.append(stock_id)

        # Log mismatches to data_quality_logs.
        if result.mismatches > 0:
            repo.write_quality_log(DataQualityLog(
                job_id=job_id,
                source="adj_reconcile",
                check_type="reconcile_mismatch",
                severity="warn",
                status="quarantined",
                stock_id=stock_id,
                detail=f"{result.mismatches} date(s) differ >  {tol * 100:.0f}% from the 2nd-source adj",
            ))

    return summary


def _adjust_stock(
    repo: Repository,
    stock_id: int,
    yf_adj_map: dict[date, float],
    as_of_version: int,
    job_id: str,
    tol: float,
    jump_threshold: float,
) -> AdjustResult:
    from app.storage.repository import DataQualityLog

    result = AdjustResult(stock_id=stock_id)

    actions = repo.get_corporate_actions(stock_id)
    bars = repo.get_all_bars(stock_id, as_of_version)
    if not bars:
        return result

    # Detect and quarantine abnormal jumps before adjustment.
    ca_ex_dates = {a.ex_date for a in actions if a.factor is not None}
    jumps = _find_abnormal_jumps(bars, ca_ex_dates, jump_threshold)
    for jump_date in jumps:
        repo.write_quality_log(DataQualityLog(
            job_id=job_id,
            source="adj_adjuster",
            check_type="abnormal_jump",
            severity="warn",
            status="quarantined",
            stock_id=stock_id,
            detail=f"unexplained price jump on {jump_date}; no corp action found",
        ))
    result.abnormal_jumps = len(jumps)

    # Compute cumulative adj_factor per date.
    dates = [b.session_date for b in bars]
    factors = compute_adj_factors(actions, dates)

    # Build updates; reconcile vs the 2nd-source adj_close.
    updates: list[tuple[float, float, float, float, float, bool, bool, date]] = []
    for bar, adj_f in zip(bars, factors, strict=True):
        o_adj = bar.open_raw * adj_f
        h_adj = bar.high_raw * adj_f
        l_adj = bar.low_raw * adj_f
        c_adj = bar.close_raw * adj_f

        # Reconciliation: compare our adj_close vs yfinance adj_close.
        yf_c = yf_adj_map.get(bar.session_date)
        if yf_c and yf_c > 0:
            rel_diff = abs(c_adj - yf_c) / yf_c
            reconciled = rel_diff <= tol
            if reconciled:
                result.reconciled += 1
            else:
                result.mismatches += 1
        else:
            # No 2nd-source reference → cannot reconcile; store False (conservative).
            reconciled = False

        updates.append((adj_f, o_adj, h_adj, l_adj, c_adj, True, reconciled, bar.session_date))

    result.bars_updated = repo.update_bar_adjustments(stock_id, as_of_version, updates)
    return result


def _find_abnormal_jumps(
    bars: list[OhlcBar],
    ca_ex_dates: set[date],
    threshold: float,
) -> list[date]:
    """Return session_dates where the close move exceeds threshold with no corp action."""
    flagged: list[date] = []
    for i in range(1, len(bars)):
        prev_close = bars[i - 1].close_raw
        curr_close = bars[i].close_raw
        if prev_close <= 0:
            continue
        move = abs(curr_close / prev_close - 1.0)
        if move > threshold and bars[i].session_date not in ca_ex_dates:
            flagged.append(bars[i].session_date)
    return flagged
