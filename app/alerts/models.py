"""Alert definition and fired-alert schemas (docs/17 §4).

All alert types are event-reporting only ("entered the scanner", "closed below its 50-DMA").
ra_gated=True rows (SL/target zone) are NEVER evaluated in Mode A and are documented
here solely for forward-compatibility with Phase 5 (RA registration in force).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


# ---------------------------------------------------------------------------
# Alert type registry
# ---------------------------------------------------------------------------

class AlertType:
    PRICE_ABOVE          = "price_above"
    PRICE_BELOW          = "price_below"
    PCT_MOVEMENT         = "pct_movement"
    VOLUME_BREAKOUT      = "volume_breakout"
    RSI_THRESHOLD        = "rsi_threshold"
    MA_CROSSOVER         = "ma_crossover"
    SCANNER_ENTRY        = "scanner_entry"
    SCANNER_EXIT         = "scanner_exit"
    WATCHLIST_NEG_NEWS   = "watchlist_negative_news"
    WATCHLIST_POS_NEWS   = "watchlist_positive_news"
    PORTFOLIO_RISK       = "portfolio_risk"
    NEWS_SENTIMENT       = "news_sentiment"
    CORPORATE_ACTION     = "corporate_action"
    RESISTANCE_SUPPORT   = "resistance_support"
    DAILY_BRIEF          = "daily_brief"
    SECTOR_WEAKNESS      = "sector_weakness"
    MARKET_BREADTH       = "market_breadth"
    # RA-GATED — NOT evaluated in Mode A (docs/17 §3)
    STOP_LOSS_ZONE       = "stop_loss_zone"    # ra_gated=True
    TARGET_ZONE          = "target_zone"       # ra_gated=True


RA_GATED_TYPES: frozenset[str] = frozenset({
    AlertType.STOP_LOSS_ZONE,
    AlertType.TARGET_ZONE,
})

# Priority ordering for per-user throttle (docs/17 §5)
PRIORITY_ORDER = [
    AlertType.PORTFOLIO_RISK,
    AlertType.WATCHLIST_NEG_NEWS,
    AlertType.SCANNER_ENTRY,
    AlertType.MA_CROSSOVER,
    AlertType.PRICE_ABOVE,
    AlertType.PRICE_BELOW,
    AlertType.RSI_THRESHOLD,
    AlertType.VOLUME_BREAKOUT,
    AlertType.PCT_MOVEMENT,
    AlertType.CORPORATE_ACTION,
    AlertType.NEWS_SENTIMENT,
    AlertType.WATCHLIST_POS_NEWS,
    AlertType.SECTOR_WEAKNESS,
    AlertType.MARKET_BREADTH,
    AlertType.RESISTANCE_SUPPORT,
    AlertType.DAILY_BRIEF,
]

MAX_ALERTS_PER_USER_PER_DAY = 20   # global per-user cap


# ---------------------------------------------------------------------------
# Alert definition
# ---------------------------------------------------------------------------

@dataclass
class AlertDefinition:
    alert_id:      str
    user_id:       str
    type:          str
    scope:         dict[str, Any] = field(default_factory=dict)   # {symbol, scanner, sector}
    condition:     dict[str, Any] = field(default_factory=dict)
    cadence:       str  = "EOD"
    channels:      list[str] = field(default_factory=lambda: ["in_app"])
    throttle:      dict[str, Any] = field(default_factory=lambda: {"max_per_day": 3, "cooldown_minutes": 720})
    ra_gated:      bool = False
    enabled:       bool = True


# ---------------------------------------------------------------------------
# Fired alert event
# ---------------------------------------------------------------------------

@dataclass
class AlertEvent:
    event_id:        str
    alert_id:        str
    as_of_date:      date
    payload:         dict[str, Any]
    dedup_key:       str
    rendered_text:   str
    guardrail_status: str = "passed"    # passed | suppressed
    channels:        list[str] = field(default_factory=list)
    delivery_log:    list[dict[str, Any]] = field(default_factory=list)
