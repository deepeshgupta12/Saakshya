"""Universe eligibility gate — runs before every scanner (docs/13 §3.1).

Checks that a stock meets minimum data quality, liquidity, and listing-status
requirements before any indicator or score is computed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EligibilityResult:
    eligible: bool
    reason: str | None = None   # populated when eligible is False


# Configurable thresholds (docs/13 §3.1 — live in versioned config, not hard-coded magic).
_DEFAULTS: dict[str, float] = {
    "min_close_adj": 10.0,          # ₹10 price floor (penny-stock filter)
    "min_median_tv_crore": 1.0,     # 20-day median traded value ≥ ₹1 crore
    "min_candles_200": 200,         # required for 200-DMA scanners
    "min_candles_default": 63,      # minimum lookback for most scanners
}


def check_eligibility(
    *,
    status: str,
    close_adj: float,
    median_tv_20d: float | None,
    candle_count: int,
    has_quarantined_candle: bool,
    corp_action_reconciled: bool,
    require_200d: bool = False,
    thresholds: dict[str, float] | None = None,
) -> EligibilityResult:
    """Evaluate a single stock against the universe gate.

    Args:
        status: Listing status ('listed' | 'delisted' | 'merged').
        close_adj: Latest adjusted close price (₹).
        median_tv_20d: 20-day median traded value in crore (None if unavailable).
        candle_count: Number of available adjusted candles.
        has_quarantined_candle: True if any candle in the lookback is quarantined.
        corp_action_reconciled: True if corp-action master is reconciled.
        require_200d: True for scanners that need 200 candles (200-DMA, reclaim-200DMA).
        thresholds: Override defaults (for per-tier config).
    """
    t = {**_DEFAULTS, **(thresholds or {})}

    if status != "listed":
        return EligibilityResult(False, f"status={status}")
    if close_adj < t["min_close_adj"]:
        return EligibilityResult(False, f"close_adj={close_adj} < ₹{t['min_close_adj']}")
    if median_tv_20d is not None and median_tv_20d < t["min_median_tv_crore"]:
        return EligibilityResult(
            False, f"median_tv_20d={median_tv_20d:.2f}cr < {t['min_median_tv_crore']}cr"
        )
    min_candles = t["min_candles_200"] if require_200d else t["min_candles_default"]
    if candle_count < min_candles:
        return EligibilityResult(False, f"candle_count={candle_count} < {min_candles}")
    if has_quarantined_candle:
        return EligibilityResult(False, "quarantined candle in lookback")
    if not corp_action_reconciled:
        return EligibilityResult(False, "corp-action master not reconciled")

    return EligibilityResult(True)
