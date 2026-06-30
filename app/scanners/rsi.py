"""RSI scanner (docs/13 §4.3).

Surfaces RSI band conditions descriptively — not directive.
Permitted phrasing: "RSI is elevated, so the risk of a short-term pullback is higher".
"""

from __future__ import annotations

from datetime import date

from app.scanners.normalize import NEUTRAL, is_neutral, scale
from app.scanners.schema import ScannerResult
from app.scanners.vocabulary import FLAG_PHRASES, TAG_PHRASES
from app.scanners.weights import ENGINE_VERSION, VALIDATION_STATUS, WEIGHTS_VERSION

_SCANNER = "rsi"

# Band thresholds (docs/13 §4.3)
_OVERSOLD    = 30.0
_RECOVERY_LO = 30.0
_RECOVERY_HI = 45.0
_BULLISH_LO  = 45.0
_BULLISH_HI  = 65.0
_ELEVATED_HI = 70.0


def rsi_band(rsi: float) -> str:
    """Classify RSI into descriptive bands."""
    if rsi < _OVERSOLD:
        return "OVERSOLD"
    if rsi < _RECOVERY_HI:
        return "RECOVERY_WATCH"
    if rsi <= _BULLISH_HI:
        return "BULLISH_BAND"
    if rsi <= _ELEVATED_HI:
        return "ELEVATED"
    return "OVERBOUGHT"


def rsi_health_score(rsi: float) -> float:
    """Health sub-score that peaks at mid-bullish band (~58), decays toward extremes."""
    if is_neutral(rsi):
        return NEUTRAL
    band = rsi_band(rsi)
    if band == "OVERSOLD":
        return 0.0
    if band == "RECOVERY_WATCH":
        return scale(rsi, _RECOVERY_LO, _RECOVERY_HI) * 0.5
    if band == "BULLISH_BAND":
        return 50.0 + scale(rsi, _BULLISH_LO, _BULLISH_HI) * 0.5
    if band == "ELEVATED":
        return 100.0 - scale(rsi, _BULLISH_HI, _ELEVATED_HI) * 0.5
    return max(0.0, 50.0 - (rsi - _ELEVATED_HI) * 5.0)


def run_rsi_scanner(
    universe: dict[int, dict[str, object]],
    session_date: date,
    as_of_version: int = 1,
) -> list[ScannerResult]:
    """Classify RSI conditions across the universe."""
    return [
        r
        for stock_id, ind in universe.items()
        if (r := _score_one(stock_id, ind, session_date, as_of_version)) is not None
    ]


def _score_one(
    stock_id: int,
    ind: dict[str, object],
    session_date: date,
    as_of_version: int,
) -> ScannerResult | None:
    symbol = str(ind.get("symbol", ""))
    rsi = _f(ind.get("rsi_14"))
    if is_neutral(rsi):
        return None

    band = rsi_band(rsi)
    health = rsi_health_score(rsi)

    signal_tags: list[str] = []
    if band == "BULLISH_BAND":
        signal_tags.append("RSI_BULLISH_BAND")

    risk_flags: list[str] = []
    if band == "OVERBOUGHT":
        risk_flags.append("RSI_OVERBOUGHT")
    elif band == "OVERSOLD":
        risk_flags.append("RSI_OVERSOLD")

    facts: dict[str, float | str] = {
        "rsi_14":   round(rsi, 2),
        "rsi_band": band,
    }

    reasons: list[str] = []
    if band == "OVERBOUGHT":
        reasons.append(FLAG_PHRASES["RSI_OVERBOUGHT"])
    elif band == "OVERSOLD":
        reasons.append(FLAG_PHRASES["RSI_OVERSOLD"])
    elif band == "BULLISH_BAND":
        reasons.append(TAG_PHRASES.get("RSI_BULLISH_BAND", "RSI in a healthy range"))
    else:
        reasons.append(f"RSI in {band.lower().replace('_', ' ')} territory")

    return ScannerResult(
        scanner=_SCANNER,
        symbol=symbol,
        stock_id=stock_id,
        as_of_date=session_date,
        data_confidence="HIGH",
        composite_score=round(health, 1) if not is_neutral(health) else None,
        sub_scores={"rsiHealth": round(health, 1) if not is_neutral(health) else float("nan")},
        facts=facts,
        signal_tags=signal_tags,
        risk_flags=risk_flags,
        reasons=reasons,
        weights_version=WEIGHTS_VERSION,
        validation_status=VALIDATION_STATUS,
        as_of_version=as_of_version,
        engine_version=ENGINE_VERSION,
    )


def _f(v: object) -> float:
    if v is None:
        return NEUTRAL
    try:
        f = float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return NEUTRAL
    return f
