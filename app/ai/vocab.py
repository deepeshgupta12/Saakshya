"""Versioned permitted-vocabulary map: scanner tag → descriptive phrase (Mode A).

Every phrase describes evidence; none implies a buy-lean or return promise (SPEC §3.1–3.2).
The AI layer uses these phrases when summarising a stock's scanner membership.
"""

from __future__ import annotations

VOCAB_VERSION = "v1"

# tag → descriptive phrase (all Mode-A safe — no directive, no buy-lean).
VOCAB: dict[str, str] = {
    "MOMENTUM_STRONG":   "appears in the momentum scanner",
    "MOMENTUM_WEAK":     "momentum indicators are weak",
    "ABOVE_50DMA":       "trading above its 50-day moving average",
    "ABOVE_200DMA":      "trading above its 200-day moving average",
    "BELOW_50DMA":       "trading below its 50-day moving average",
    "BELOW_200DMA":      "trading below its 200-day moving average",
    "GOLDEN_CROSS":      "50-day moving average has crossed above the 200-day moving average",
    "DEATH_CROSS":       "50-day moving average has crossed below the 200-day moving average",
    "VOLUME_SURGE":      "volume has expanded significantly relative to its 20-day average",
    "VOLUME_LOW":        "volume is below its 20-day average",
    "HIGH_RS":           "outperforming Nifty on a relative-strength basis",
    "LOW_RS":            "underperforming Nifty on a relative-strength basis",
    "OVERBOUGHT_RSI":    "RSI is in overbought territory",
    "OVERSOLD_RSI":      "RSI is in oversold territory",
    "NEAR_52W_HIGH":     "trading near its 52-week high",
    "NEAR_52W_LOW":      "trading near its 52-week low",
    "ELEVATED_VOLATILITY": "short-term volatility is elevated",
    "LOW_VOLATILITY":    "short-term volatility is low",
    "NEAR_SUPPORT":      "trading near a historically observed support zone",
    "NEAR_RESISTANCE":   "trading near a historically observed resistance zone",
}


def permitted_vocabulary(tags: list[str] | None = None) -> dict[str, str]:
    """Return the vocabulary subset relevant to the given tags (or the full map if None)."""
    if tags is None:
        return dict(VOCAB)
    return {t: VOCAB[t] for t in tags if t in VOCAB}
