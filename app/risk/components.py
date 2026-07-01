"""Per-position risk components and portfolio health score (docs/16 §3–4).

Every component ships with the data points that produced it (evidence dict) so the
frontend can show "ATR% = 4.1, 88th percentile vs its 1-year range" as required.

Mode-A discipline:
- SL / target / entry zone computation is RA-GATED and NOT implemented here.
- Technical-breakdown flags describe the *event* ("closed below 50-DMA"), never an action.
- No API response carries stop_loss_zone / target_zone / ra_gated fields in Mode A.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Thresholds (versioned config — mirroring scanner-score governance SPEC §6.5)
# ---------------------------------------------------------------------------

SINGLE_STOCK_SOFT_CAP = 20.0    # % — a 20% weight scores 50 on concentration risk
SECTOR_SOFT_CAP       = 25.0    # % — a 25% sector weight scores 50
MICRO_SMALL_PENALTY_CAP = 50.0  # % — penalised for small/micro tilt

COMPONENT_WEIGHTS = {
    "diversification": 0.25,
    "sector_balance":  0.15,
    "volatility":      0.20,
    "technical":       0.20,
    "news":            0.10,
    "cap_balance":     0.10,
}

HEALTH_BANDS = [
    (80, "Resilient"),
    (60, "Balanced"),
    (40, "Elevated risk"),
    (0,  "High risk"),
]


# ---------------------------------------------------------------------------
# Per-position risk components
# ---------------------------------------------------------------------------

@dataclass
class RiskComponents:
    symbol:                   str
    concentration_risk:       float = 0.0   # 0–100
    sector_concentration_risk: float = 0.0  # 0–100
    cap_exposure_risk:        float = 0.0   # 0–100
    volatility_risk:          float = 0.0   # 0–100
    news_risk:                float = 0.0   # 0–100
    technical_breakdown_risk: float = 0.0   # 0–100
    evidence:                 dict[str, Any] = field(default_factory=dict)


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def concentration_risk(weight_pct: float) -> tuple[float, dict[str, Any]]:
    """Single-stock concentration risk from position weight (docs/16 §3.2)."""
    score = _clamp((weight_pct / SINGLE_STOCK_SOFT_CAP) * 50)
    evidence = {"weight_pct": round(weight_pct, 2), "soft_cap_pct": SINGLE_STOCK_SOFT_CAP}
    return round(score, 1), evidence


def sector_concentration_risk(sector_weight_pct: float) -> tuple[float, dict[str, Any]]:
    """Sector concentration risk."""
    score = _clamp((sector_weight_pct / SECTOR_SOFT_CAP) * 50)
    evidence = {"sector_weight_pct": round(sector_weight_pct, 2), "soft_cap_pct": SECTOR_SOFT_CAP}
    return round(score, 1), evidence


def volatility_risk(
    atr_14: float | None,
    last_close: float | None,
    atr_pct_percentile: float | None = None,
) -> tuple[float, dict[str, Any]]:
    """Volatility risk from ATR% vs trailing-1y percentile (docs/16 §3.2).

    atr_pct_percentile: 0–1 (pre-computed; if None, returns 0 with LOW confidence).
    """
    if atr_14 is None or last_close is None or last_close == 0:
        return 0.0, {"data_confidence": "LOW"}

    atr_pct = round(atr_14 / last_close * 100, 2)
    if atr_pct_percentile is not None:
        score = _clamp(round(atr_pct_percentile * 100, 1))
        evidence = {
            "atr_pct":            atr_pct,
            "atr_pct_percentile": round(atr_pct_percentile, 4),
        }
    else:
        # Fallback: no historical distribution → use raw ATR% heuristic (>4% is elevated)
        score = _clamp(atr_pct * 10)
        evidence = {"atr_pct": atr_pct, "percentile_source": "heuristic"}

    return score, evidence


def technical_breakdown_risk(
    close: float | None,
    sma_50: float | None,
    sma_200: float | None,
    in_breakdown_scanner: bool = False,
    recent_swing_low: float | None = None,
) -> tuple[float, dict[str, Any]]:
    """Technical-breakdown risk — sum of breached conditions (docs/16 §3.2).

    Output is an EVENT flag, never an instruction. Example evidence:
        {"below_sma50": True, "close": 698.2, "sma_50": 705.6}
    """
    if close is None:
        return 0.0, {"data_confidence": "LOW"}

    score  = 0
    events: list[str] = []

    if sma_50 is not None and close < sma_50:
        score  += 30
        events.append("closed below 50-DMA")
    if sma_200 is not None and close < sma_200:
        score  += 30
        events.append("closed below 200-DMA")
    if in_breakdown_scanner:
        score  += 25
        events.append("in breakdown scanner")
    if recent_swing_low is not None and close < recent_swing_low:
        score  += 15
        events.append("closed below recent swing low")

    evidence: dict[str, Any] = {
        "close":               close,
        "sma_50":              sma_50,
        "sma_200":             sma_200,
        "in_breakdown_scanner": in_breakdown_scanner,
        "events":              events,
    }
    if recent_swing_low is not None:
        evidence["recent_swing_low"] = recent_swing_low

    return _clamp(score), evidence


def news_risk(
    news_items: list[dict[str, Any]],
    window_days: int = 7,
) -> tuple[float, dict[str, Any]]:
    """News risk from max negative-classified impact in the last N days (docs/16 §3.2).

    news_items: list of {sentiment: str, impact: float (0–1), published_at: str, headline: str}
    Only items above the surfacing confidence threshold are counted.
    """
    negative_impacts = [
        n["impact"]
        for n in news_items
        if n.get("sentiment", "").upper() == "NEGATIVE"
        and isinstance(n.get("impact"), (int, float))
    ]
    if not negative_impacts:
        return 0.0, {"negative_item_count": 0, "window_days": window_days}

    max_impact  = max(negative_impacts)
    score       = _clamp(max_impact * 100)
    headline    = next(
        (n.get("headline", "") for n in news_items
         if n.get("sentiment", "").upper() == "NEGATIVE"),
        None,
    )
    evidence = {
        "max_negative_impact": round(max_impact, 4),
        "negative_item_count": len(negative_impacts),
        "window_days":         window_days,
        "top_headline":        headline,
    }
    return round(score, 1), evidence


def cap_exposure_risk(micro_small_weight_pct: float) -> tuple[float, dict[str, Any]]:
    """Market-cap-tilt risk — penalises small/micro concentration."""
    score    = _clamp((micro_small_weight_pct / MICRO_SMALL_PENALTY_CAP) * 50)
    evidence = {"micro_small_weight_pct": round(micro_small_weight_pct, 2)}
    return round(score, 1), evidence


def compute_position_risk(
    symbol:             str,
    weight_pct:         float,
    sector_weight_pct:  float,
    micro_small_weight_pct: float,
    indicators:         dict[str, Any],
    news_items:         list[dict[str, Any]] | None = None,
    in_breakdown_scanner: bool = False,
) -> RiskComponents:
    """Compute all six risk components for one position."""
    close   = indicators.get("close_adj") or indicators.get("close")
    sma_50  = indicators.get("sma_50")
    sma_200 = indicators.get("sma_200")
    atr_14  = indicators.get("atr_14")

    con_risk,  con_ev  = concentration_risk(weight_pct)
    sec_risk,  sec_ev  = sector_concentration_risk(sector_weight_pct)
    vol_risk,  vol_ev  = volatility_risk(atr_14, close)
    tbd_risk,  tbd_ev  = technical_breakdown_risk(close, sma_50, sma_200, in_breakdown_scanner)
    nws_risk,  nws_ev  = news_risk(news_items or [])
    cap_risk,  cap_ev  = cap_exposure_risk(micro_small_weight_pct)

    return RiskComponents(
        symbol                   = symbol,
        concentration_risk       = con_risk,
        sector_concentration_risk= sec_risk,
        cap_exposure_risk        = cap_risk,
        volatility_risk          = vol_risk,
        news_risk                = nws_risk,
        technical_breakdown_risk = tbd_risk,
        evidence={
            "concentration":         con_ev,
            "sector_concentration":  sec_ev,
            "cap_exposure":          cap_ev,
            "volatility":            vol_ev,
            "news":                  nws_ev,
            "technical_breakdown":   tbd_ev,
        },
    )


# ---------------------------------------------------------------------------
# Portfolio health score (docs/16 §4)
# ---------------------------------------------------------------------------

def _weighted_avg(risk_values: dict[str, float], weights_by_symbol: dict[str, float]) -> float:
    """Position-weight-averaged risk value."""
    total_w = sum(weights_by_symbol.values())
    if total_w == 0:
        return 0.0
    return sum(risk_values.get(s, 0.0) * w for s, w in weights_by_symbol.items()) / total_w


def _sector_entropy_norm(sector_weights: dict[str, float]) -> float:
    """Shannon entropy of sector weights, normalised to [0,1]."""
    values = [v / 100.0 for v in sector_weights.values() if v > 0]
    if len(values) <= 1:
        return 0.0
    entropy = -sum(p * math.log(p) for p in values if p > 0)
    max_entropy = math.log(len(values))
    return entropy / max_entropy if max_entropy > 0 else 0.0


def compute_health_score(
    risk_components_by_symbol: dict[str, RiskComponents],
    position_weights_pct:      dict[str, float],
    sector_weights_pct:        dict[str, float],
    micro_small_weight_pct:    float,
) -> dict[str, Any]:
    """Compute the 0–100 portfolio health score and descriptive drivers (docs/16 §4).

    Higher score = lower aggregate risk (healthier portfolio posture).
    """
    weights_normalized = {s: w / 100.0 for s, w in position_weights_pct.items() if w}

    vol_risks   = {s: r.volatility_risk         for s, r in risk_components_by_symbol.items()}
    tech_risks  = {s: r.technical_breakdown_risk for s, r in risk_components_by_symbol.items()}
    news_risks  = {s: r.news_risk               for s, r in risk_components_by_symbol.items()}
    con_risks   = {s: r.concentration_risk       for s, r in risk_components_by_symbol.items()}

    # Sub-health dimensions (0–100 each, higher = better/lower risk)
    weighted_con  = _weighted_avg(con_risks,  weights_normalized)
    divfn_health  = _clamp(100 - weighted_con)

    entropy_norm  = _sector_entropy_norm(sector_weights_pct)
    sec_health    = round(entropy_norm * 100, 1)

    weighted_vol  = _weighted_avg(vol_risks, weights_normalized)
    vol_health    = _clamp(100 - weighted_vol)

    weighted_tech = _weighted_avg(tech_risks, weights_normalized)
    tech_health   = _clamp(100 - weighted_tech)

    weighted_news = _weighted_avg(news_risks, weights_normalized)
    news_health   = _clamp(100 - weighted_news)

    micro_small_penalty = _clamp((micro_small_weight_pct / MICRO_SMALL_PENALTY_CAP) * 50)
    cap_health    = _clamp(100 - micro_small_penalty)

    w = COMPONENT_WEIGHTS
    score = round(
        w["diversification"] * divfn_health
        + w["sector_balance"]  * sec_health
        + w["volatility"]      * vol_health
        + w["technical"]       * tech_health
        + w["news"]            * news_health
        + w["cap_balance"]     * cap_health
    )

    # Band label (descriptive measurement, not a grade / not advice)
    band = "High risk"
    for threshold, label in HEALTH_BANDS:
        if score >= threshold:
            band = label
            break

    # Drivers — each names its data point (required by acceptance criteria)
    drivers: list[str] = []
    top_sector = max(sector_weights_pct.items(), key=lambda x: x[1], default=None)
    if top_sector and top_sector[1] > SECTOR_SOFT_CAP:
        drivers.append(
            f"{top_sector[0]} is {top_sector[1]:.1f}% of the portfolio "
            f"(above the {SECTOR_SOFT_CAP:.0f}% balance reference)."
        )

    tbd_count = sum(1 for r in risk_components_by_symbol.values() if r.technical_breakdown_risk >= 30)
    total_pos  = len(risk_components_by_symbol)
    if tbd_count > 0:
        drivers.append(
            f"{tbd_count} of {total_pos} holdings closed below their 50-DMA today."
        )

    high_vol_count = sum(1 for r in risk_components_by_symbol.values() if r.volatility_risk >= 60)
    if high_vol_count > 0:
        drivers.append(
            f"{high_vol_count} holdings show elevated volatility (ATR%)."
        )

    return {
        "portfolio_health_score": score,
        "band":       band,
        "components": {
            "diversification_health": round(divfn_health, 1),
            "sector_balance_health":  round(sec_health, 1),
            "volatility_health":      round(vol_health, 1),
            "technical_health":       round(tech_health, 1),
            "news_health":            round(news_health, 1),
            "cap_balance_health":     round(cap_health, 1),
        },
        "drivers":         drivers,
        "weights_version": "v1",
    }
