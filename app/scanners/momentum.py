"""Momentum scanner (docs/13 §4.1, docs/02 §Feature: Momentum scanner).

Surfaces stocks with strong persistent price momentum and positive relative
strength vs Nifty 50. Output is descriptive Mode-A — no entry/target/SL.
"""

from __future__ import annotations

import math
from datetime import date

from app.scanners.composite import compute_composite
from app.scanners.normalize import NEUTRAL, is_neutral, pct_rank
from app.scanners.schema import ScannerResult
from app.scanners.vocabulary import FLAG_PHRASES, TAG_PHRASES
from app.scanners.weights import WEIGHTS_V1

_SCANNER = "momentum"

# Thresholds (versioned config; docs/13 §7)
_ENTER_RAW      = 70.0   # minimum momentumRaw to appear in scanner
_STRONG_TAG_RAW = 85.0   # threshold for MOMENTUM_STRONG tag
_EXTENDED_PCT   = 0.15   # price > 15% above 50-DMA → EXTENDED_FROM_MA
_ATR_PCT_90TH   = 90.0   # ATR% pct-rank threshold for ELEVATED_VOLATILITY


def run_momentum_scanner(
    universe: dict[int, dict[str, object]],
    session_date: date,
    as_of_version: int = 1,
) -> list[ScannerResult]:
    """Score and filter the universe through the momentum scanner.

    Args:
        universe: {stock_id → indicator dict} loaded from technical_indicators.
                  Expected keys: symbol, ret_21d, ret_63d, ret_126d,
                  rel_strength_63d, atr_14, close_adj, sma_50, rsi_14.
        session_date: The as-of date for this scan run.
        as_of_version: Underlying OHLC/indicator version.
    """
    # Phase 1 — collect blended returns and RS for cross-sectional ranking
    blended_rets: list[float] = []
    rs3m_vals: list[float] = []

    for ind in universe.values():
        r1  = _f(ind.get("ret_21d"))
        r3  = _f(ind.get("ret_63d"))
        r6  = _f(ind.get("ret_126d"))
        rs3 = _f(ind.get("rel_strength_63d"))
        if not (is_neutral(r1) or is_neutral(r3) or is_neutral(r6) or is_neutral(rs3)):
            bl = 0.5 * r3 + 0.3 * r6 + 0.2 * r1
            blended_rets.append(bl)
            rs3m_vals.append(rs3)

    # Phase 2 — score each stock
    results: list[ScannerResult] = []
    for stock_id, ind in universe.items():
        result = _score_one(
            stock_id, ind, session_date, as_of_version,
            blended_rets, rs3m_vals,
        )
        if result is not None:
            results.append(result)

    return results


def _score_one(
    stock_id: int,
    ind: dict[str, object],
    session_date: date,
    as_of_version: int,
    blended_rets: list[float],
    rs3m_vals: list[float],
) -> ScannerResult | None:
    symbol = str(ind.get("symbol", ""))
    r1  = _f(ind.get("ret_21d"))
    r3  = _f(ind.get("ret_63d"))
    r6  = _f(ind.get("ret_126d"))
    rs3 = _f(ind.get("rel_strength_63d"))
    rsi = _f(ind.get("rsi_14"))
    close_adj = _f(ind.get("close_adj"))
    sma50_v   = _f(ind.get("sma_50"))
    atr14_v   = _f(ind.get("atr_14"))

    if any(is_neutral(v) for v in [r1, r3, r6, rs3]):
        return None

    blended_ret = 0.5 * r3 + 0.3 * r6 + 0.2 * r1
    momentum_raw = (
        0.6 * pct_rank(blended_ret, blended_rets)
        + 0.4 * pct_rank(rs3, rs3m_vals)
    )

    if is_neutral(momentum_raw) or momentum_raw < _ENTER_RAW or rs3 <= 0.0:
        return None

    # Sub-scores
    price_momentum = momentum_raw
    rsi_health = _rsi_health(rsi)

    ma_trend = NEUTRAL
    if not (is_neutral(close_adj) or is_neutral(sma50_v)):
        above_50 = 1.0 if close_adj > sma50_v else 0.0
        ma_trend = above_50 * 50.0  # simplified (full MA scanner has more sub-scores)

    sub_scores: dict[str, float] = {
        "priceMomentum":   price_momentum,
        "rsiHealth":       rsi_health,
        "maTrend":         ma_trend,
        "volumeExpansion": NEUTRAL,   # not computed here — requires volume scanner
        "sectorStrength":  NEUTRAL,   # requires sector engine (later milestone)
        "newsSentiment":   NEUTRAL,   # requires sentiment engine (later milestone)
        "riskAdjustment":  NEUTRAL,   # populated via risk flags below
    }

    # Signal tags
    signal_tags: list[str] = []
    if momentum_raw >= _STRONG_TAG_RAW:
        signal_tags.append("MOMENTUM_STRONG")
    if not is_neutral(close_adj) and not is_neutral(sma50_v) and close_adj > sma50_v:
        signal_tags.append("ABOVE_50DMA")

    # Risk flags
    risk_flags: list[str] = []
    if not is_neutral(rsi) and rsi > 70.0:
        risk_flags.append("RSI_OVERBOUGHT")
    if (
        not (is_neutral(close_adj) or is_neutral(sma50_v))
        and sma50_v > 0.0
        and (close_adj / sma50_v - 1.0) > _EXTENDED_PCT
    ):
        risk_flags.append("EXTENDED_FROM_MA")

    # ATR% pct-rank for volatility flag (needs universe ATR data — simplified here)
    if not is_neutral(atr14_v) and not is_neutral(close_adj) and close_adj > 0.0:
        atr_pct_val = (atr14_v / close_adj) * 100.0
    else:
        atr_pct_val = float("nan")

    composite = compute_composite(sub_scores, WEIGHTS_V1)

    # Facts (Mode-A: computed values only, no forward fields)
    facts: dict[str, float | str] = {}
    if not is_neutral(r1):
        facts["ret_1m_pct"] = round(r1 * 100.0, 2)
    if not is_neutral(r3):
        facts["ret_3m_pct"] = round(r3 * 100.0, 2)
    if not is_neutral(r6):
        facts["ret_6m_pct"] = round(r6 * 100.0, 2)
    if not is_neutral(rs3):
        facts["rs_3m_pct"] = round(rs3 * 100.0, 2)
    if not math.isnan(atr_pct_val):
        facts["atr_pct"] = round(atr_pct_val, 2)
    if not (is_neutral(close_adj) or is_neutral(sma50_v)) and sma50_v > 0.0:
        facts["pct_above_50dma"] = round((close_adj / sma50_v - 1.0) * 100.0, 2)

    # Reasons (descriptive Mode-A phrasing; no buy-lean language)
    reasons: list[str] = ["appears in the momentum scanner"]
    for tag in signal_tags:
        if tag in TAG_PHRASES:
            reasons.append(TAG_PHRASES[tag])
    for flag in risk_flags:
        if flag in FLAG_PHRASES:
            reasons.append(f"risk: {FLAG_PHRASES[flag]}")

    return ScannerResult(
        scanner=_SCANNER,
        symbol=symbol,
        stock_id=stock_id,
        as_of_date=session_date,
        data_confidence="HIGH" if not risk_flags else "MEDIUM",
        composite_score=None if is_neutral(composite) else round(composite, 1),
        sub_scores={k: (round(v, 1) if not is_neutral(v) else float("nan"))
                    for k, v in sub_scores.items()},
        facts=facts,
        signal_tags=signal_tags,
        risk_flags=risk_flags,
        reasons=reasons,
        as_of_version=as_of_version,
    )


def _rsi_health(rsi: float) -> float:
    """RSI health sub-score: peaks at mid-bullish band (~58), decays toward extremes."""
    if is_neutral(rsi):
        return NEUTRAL
    if rsi < 30.0:
        return 0.0
    if rsi <= 45.0:
        return (rsi - 30.0) / 15.0 * 50.0       # 0 → 50
    if rsi <= 65.0:
        return 50.0 + (rsi - 45.0) / 20.0 * 50.0  # 50 → 100, peaks at 65
    if rsi <= 70.0:
        return 100.0 - (rsi - 65.0) / 5.0 * 50.0  # 100 → 50
    return max(0.0, 50.0 - (rsi - 70.0) * 5.0)    # decays below 50


def _f(v: object) -> float:
    """Coerce indicator value to float; return NEUTRAL (NaN) on failure."""
    if v is None:
        return NEUTRAL
    try:
        f = float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return NEUTRAL
    return f
