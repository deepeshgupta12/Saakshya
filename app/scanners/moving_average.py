"""Moving-average scanner (docs/13 §4.4).

Classifies trend structure via price-vs-MA and MA stacking.
Output is descriptive Mode-A — no entry/target/SL.
"""

from __future__ import annotations

from datetime import date

from app.scanners.normalize import NEUTRAL, is_neutral, scale
from app.scanners.schema import ScannerResult
from app.scanners.vocabulary import FLAG_PHRASES, TAG_PHRASES
from app.scanners.weights import ENGINE_VERSION, VALIDATION_STATUS, WEIGHTS_VERSION

_SCANNER = "moving_average"
_EXTENDED_PCT = 0.15   # >15% above 50-DMA → EXTENDED_FROM_MA


def run_ma_scanner(
    universe: dict[int, dict[str, object]],
    session_date: date,
    as_of_version: int = 1,
) -> list[ScannerResult]:
    """Classify MA trend structure across the universe."""
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
    close = _f(ind.get("close_adj"))
    sma20 = _f(ind.get("sma_20"))
    sma50 = _f(ind.get("sma_50"))
    sma200 = _f(ind.get("sma_200"))
    # slope_50: (sma50_today - sma50_20ago) / sma50_20ago — caller may pre-compute
    slope_50 = _f(ind.get("slope_50"))

    if any(is_neutral(v) for v in [close, sma20, sma50, sma200]):
        return None

    above_50 = close > sma50
    above_200 = close > sma200
    stacked = sma20 > sma50 > sma200

    # MA trend raw score (docs/13 §4.4). Weights 40/30/20/10 sum to 100; scale() returns
    # 0–100, so the slope term is scaled by 0.1 to contribute at most 10 points (matching
    # the fractional-weight pattern in the rsi / volume-breakout scanners). Using 10.0×
    # here blew the composite past 100 (e.g. neutral slope alone added 10×50 = 500).
    ma_trend_raw = (
        40.0 * (1.0 if above_50 else 0.0)
        + 30.0 * (1.0 if above_200 else 0.0)
        + 20.0 * (1.0 if stacked else 0.0)
        + 0.1 * (scale(slope_50, -0.05, 0.05) if not is_neutral(slope_50) else 50.0)
    )

    # Signal tags
    signal_tags: list[str] = []
    if above_50:
        signal_tags.append("ABOVE_50DMA")
    if above_200:
        signal_tags.append("ABOVE_200DMA")
    if stacked:
        signal_tags.append("MA_STACKED_BULLISH")

    # Risk flags
    risk_flags: list[str] = []
    if above_50 and sma50 > 0.0 and (close / sma50 - 1.0) > _EXTENDED_PCT:
        risk_flags.append("EXTENDED_FROM_MA")

    # Facts
    facts: dict[str, float | str] = {
        "close":  round(close, 2),
        "sma20":  round(sma20, 2),
        "sma50":  round(sma50, 2),
        "sma200": round(sma200, 2),
    }
    if not is_neutral(slope_50):
        facts["slope_50_pct"] = round(slope_50 * 100.0, 2)
    if above_50 and sma50 > 0.0:
        facts["pct_above_50dma"] = round((close / sma50 - 1.0) * 100.0, 2)

    # Reasons
    reasons: list[str] = []
    for tag in signal_tags:
        if tag in TAG_PHRASES:
            reasons.append(TAG_PHRASES[tag])
    if not reasons:
        reasons.append("trading below key moving averages")
    for flag in risk_flags:
        if flag in FLAG_PHRASES:
            reasons.append(f"risk: {FLAG_PHRASES[flag]}")

    return ScannerResult(
        scanner=_SCANNER,
        symbol=symbol,
        stock_id=stock_id,
        as_of_date=session_date,
        data_confidence="HIGH",
        composite_score=round(ma_trend_raw, 1),
        sub_scores={"maTrend": round(ma_trend_raw, 1)},
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
