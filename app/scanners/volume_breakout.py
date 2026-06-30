"""Volume breakout scanner (docs/13 §4.2).

Surfaces unusual volume expansion confirmed by delivery quality.
Output is descriptive Mode-A — "volume expanded N× vs its 20-day average".
"""

from __future__ import annotations

from datetime import date

from app.scanners.normalize import NEUTRAL, is_neutral, scale
from app.scanners.schema import ScannerResult
from app.scanners.vocabulary import FLAG_PHRASES, TAG_PHRASES
from app.scanners.weights import ENGINE_VERSION, VALIDATION_STATUS, WEIGHTS_VERSION

_SCANNER = "volume_breakout"
_ENTER_VOL_RATIO = 2.0
_HIGH_CONV_VOL   = 3.0
_HIGH_CONV_DEL_Z = 1.0


def run_volume_breakout_scanner(
    universe: dict[int, dict[str, object]],
    session_date: date,
    as_of_version: int = 1,
) -> list[ScannerResult]:
    """Score volume breakouts across the universe."""
    results: list[ScannerResult] = []
    for stock_id, ind in universe.items():
        result = _score_one(stock_id, ind, session_date, as_of_version)
        if result is not None:
            results.append(result)
    return results


def _score_one(
    stock_id: int,
    ind: dict[str, object],
    session_date: date,
    as_of_version: int,
) -> ScannerResult | None:
    symbol = str(ind.get("symbol", ""))
    vol_ratio = _f(ind.get("volume_ratio_20"))
    delivery_pct = _f(ind.get("delivery_pct"))
    delivery_pct_20d_mean = _f(ind.get("delivery_pct_20d_mean"))
    delivery_pct_20d_std  = _f(ind.get("delivery_pct_20d_std"))
    price_change_pct = _f(ind.get("price_change_pct"))

    if is_neutral(vol_ratio) or vol_ratio < _ENTER_VOL_RATIO:
        return None

    # delivery_z: NEUTRAL when delivery data missing (never substitute 0)
    if not (is_neutral(delivery_pct) or is_neutral(delivery_pct_20d_mean)
            or is_neutral(delivery_pct_20d_std)) and delivery_pct_20d_std > 0.0:
        delivery_z: float = (delivery_pct - delivery_pct_20d_mean) / delivery_pct_20d_std
    else:
        delivery_z = NEUTRAL

    volume_raw = 0.6 * scale(vol_ratio, 1.0, 4.0) + (
        0.4 * scale(delivery_z, -1.0, 3.0) if not is_neutral(delivery_z) else 0.0
    )

    # Signal tags
    signal_tags: list[str] = []
    if vol_ratio >= _ENTER_VOL_RATIO:
        signal_tags.append("VOLUME_EXPANSION")

    # Risk flags
    risk_flags: list[str] = []
    if is_neutral(delivery_z):
        risk_flags.append("DATA_INCOMPLETE")

    # Facts (only computed values)
    facts: dict[str, float | str] = {"vol_ratio": round(vol_ratio, 2)}
    if not is_neutral(delivery_pct):
        facts["delivery_pct"] = round(delivery_pct, 2)
    if not is_neutral(delivery_z):
        facts["delivery_z"] = round(delivery_z, 2)
    if not is_neutral(price_change_pct):
        facts["price_change_pct"] = round(price_change_pct, 2)

    # Reasons (descriptive; no "buy the breakout" language)
    reasons: list[str] = [
        f"volume expanded {vol_ratio:.1f}× vs its 20-day average"
    ]
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
        data_confidence="MEDIUM" if is_neutral(delivery_z) else "HIGH",
        composite_score=round(volume_raw, 1),
        sub_scores={},
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
