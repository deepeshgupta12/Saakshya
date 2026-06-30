"""Canonical signal-tag and risk-flag vocabulary (docs/13 §3.4).

The scanner engine can only emit tags from SIGNAL_TAGS and flags from RISK_FLAGS.
The AI explanation layer maps these to descriptive Mode-A phrasing and cannot
introduce any tag the engine did not emit.
"""

from __future__ import annotations

# Descriptive membership tags — never directive ("buy" / "sell" absent by design).
SIGNAL_TAGS: frozenset[str] = frozenset({
    "MOMENTUM_STRONG",
    "VOLUME_EXPANSION",
    "ABOVE_50DMA",
    "ABOVE_200DMA",
    "MA_STACKED_BULLISH",
    "RSI_BULLISH_BAND",
    "NEAR_52W_HIGH",
    "RECLAIMED_200DMA",
    "OVERSOLD_RECOVERY",
    "BREAKOUT_CONFIRMED",
    "BREAKDOWN_CONFIRMED",
    "SECTOR_LEADER",
    "SENTIMENT_POSITIVE",
})

# Risk flags — always surfaced; first-class, never hidden.
RISK_FLAGS: frozenset[str] = frozenset({
    "RSI_OVERBOUGHT",
    "RSI_OVERSOLD",
    "ELEVATED_VOLATILITY",
    "EXTENDED_FROM_MA",
    "FALSE_BREAKOUT_RISK",
    "FALSE_BREAKDOWN_RISK",
    "LOW_LIQUIDITY",
    "GAP_RISK",
    "EARNINGS_SOON",
    "DATA_INCOMPLETE",
    "WIDE_BIDASK",
    "NEWS_SENTIMENT_NEGATIVE",
})

# Mode-A descriptive phrases mapped from tags/flags (used by reason builder).
TAG_PHRASES: dict[str, str] = {
    "MOMENTUM_STRONG": "appears in the momentum scanner with strong persistent momentum",
    "VOLUME_EXPANSION": "volume expanded significantly vs its 20-day average",
    "ABOVE_50DMA": "trading above its 50-day moving average",
    "ABOVE_200DMA": "trading above its 200-day moving average",
    "MA_STACKED_BULLISH": (
        "moving averages stacked in an uptrend (20-DMA above 50-DMA above 200-DMA)"
    ),
    "RSI_BULLISH_BAND": "RSI in a healthy range (45–65)",
    "NEAR_52W_HIGH": "trading near its 52-week high",
    "RECLAIMED_200DMA": "recently reclaimed its 200-day moving average",
    "OVERSOLD_RECOVERY": "RSI turned up from oversold territory",
    "BREAKOUT_CONFIRMED": "closed above a level that has historically acted as resistance",
    "BREAKDOWN_CONFIRMED": "closed below a level that has historically acted as support",
    "SECTOR_LEADER": "sector showing relative strength vs the broader market",
    "SENTIMENT_POSITIVE": "recent news sentiment classified as positive",
}

FLAG_PHRASES: dict[str, str] = {
    "RSI_OVERBOUGHT": "RSI is elevated; the risk of a short-term pullback is higher",
    "RSI_OVERSOLD": "RSI indicates oversold conditions",
    "ELEVATED_VOLATILITY": "volatility is elevated relative to the universe",
    "EXTENDED_FROM_MA": "price is significantly extended above its 50-day moving average",
    "FALSE_BREAKOUT_RISK": "the move lacks strong volume confirmation",
    "FALSE_BREAKDOWN_RISK": "the breakdown lacks strong volume confirmation",
    "LOW_LIQUIDITY": "trading liquidity is below typical levels",
    "GAP_RISK": "elevated overnight gap frequency in recent sessions",
    "EARNINGS_SOON": "earnings announcement expected soon",
    "DATA_INCOMPLETE": "some indicators are unavailable due to insufficient history",
    "WIDE_BIDASK": "bid-ask spread is wider than typical",
    "NEWS_SENTIMENT_NEGATIVE": "recent news sentiment classified as negative",
}
