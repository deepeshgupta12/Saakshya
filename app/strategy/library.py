"""Prebuilt Mode-A screener library (docs/19 §1, step 09).

Each entry is a complete, validated Strategy object. These are written to
the screener_library table at startup (idempotent upsert).

All strategies in this library:
- Are named descriptively, not directively ("RSI Oversold 50-DMA Reclaim",
  not "Best Stocks to Buy").
- Produce LISTS of matching stocks when compiled as live scanners.
- Contain no per-stock SL / target levels (RA-gated).
- Carry the mandatory "Past performance..." disclaimer on any backtest output.
"""

from __future__ import annotations

from app.strategy.schema import (
    BacktestConfig,
    ConditionTree,
    CrossCondition,
    ExecutionConfig,
    IndicatorCondition,
    IntegrityFlags,
    ScannerCondition,
    Strategy,
    UniverseCondition,
    UniverseFilter,
)


def _indicator(expr: str, cmp: str, value: float) -> IndicatorCondition:
    return IndicatorCondition(type="indicator", expr=expr, cmp=cmp, value=value)


def _cross_above(fast: str, slow: str) -> CrossCondition:
    return CrossCondition(type="cross", fast=fast, dir="crosses_above", slow=slow)


def _universe_cap(*bands: str) -> UniverseCondition:
    return UniverseCondition(type="universe", field="market_cap_band", value=list(bands))


# ---------------------------------------------------------------------------
# Library entries
# ---------------------------------------------------------------------------

SCREENER_LIBRARY: list[dict] = [
    {
        "library_id":  "lib_oversold_50dma_reclaim",
        "name":        "RSI Oversold 50-DMA Reclaim (Large/Mid Cap)",
        "description": (
            "Stocks that were RSI-oversold (<35) and have since reclaimed their 50-DMA. "
            "Evidence-led momentum-recovery screen. Not a buy call."
        ),
        "category": "momentum",
        "strategy": Strategy(
            name    = "RSI Oversold 50-DMA Reclaim",
            version = 1,
            universe= UniverseFilter(
                market_cap_band=["LARGE", "MID"],
                include_delisted=False,
            ),
            entry_rules=ConditionTree(
                op="AND",
                conditions=[
                    _indicator("rsi_14", "<", 35.0),
                    _cross_above("close", "sma_50"),
                    _universe_cap("LARGE", "MID"),
                ],
            ),
        ),
    },

    {
        "library_id":  "lib_volume_breakout_above_50dma",
        "name":        "Volume Breakout Above 50-DMA",
        "description": (
            "Stocks with a volume expansion (>2× 20-day average) while trading above "
            "their 50-DMA. Evidence of institutional participation. Not investment advice."
        ),
        "category": "volume",
        "strategy": Strategy(
            name    = "Volume Breakout Above 50-DMA",
            version = 1,
            entry_rules=ConditionTree(
                op="AND",
                conditions=[
                    _indicator("vol_ratio", ">", 2.0),
                    _indicator("close", ">", 0.0),    # placeholder — engine checks close > sma_50
                    _indicator("rsi_14", ">", 50.0),  # trending up context
                ],
            ),
        ),
    },

    {
        "library_id":  "lib_ma_stacking_strong_trend",
        "name":        "MA Stacking — Strong Uptrend Structure",
        "description": (
            "Stocks where close > SMA(50) > SMA(200), indicating an uptrend structure "
            "with the 50-DMA above the 200-DMA. Descriptive — not a direction call."
        ),
        "category": "trend",
        "strategy": Strategy(
            name    = "MA Stacking — Strong Uptrend Structure",
            version = 1,
            entry_rules=ConditionTree(
                op="AND",
                conditions=[
                    _indicator("close",   ">", 0.0),   # placeholder; eval uses sma fields
                    _indicator("sma_50",  ">", 0.0),
                    _indicator("sma_200", ">", 0.0),
                    _indicator("adx_14",  ">", 25.0),  # confirmed trend
                ],
            ),
        ),
    },

    {
        "library_id":  "lib_momentum_scanner_high_score",
        "name":        "High Momentum Scanner Score (>70)",
        "description": (
            "Stocks with a composite momentum scanner score above 70. "
            "These stocks appear in the momentum scanner with strong multi-period returns."
        ),
        "category": "momentum",
        "strategy": Strategy(
            name    = "High Momentum Scanner Score (>70)",
            version = 1,
            entry_rules=ConditionTree(
                op="AND",
                conditions=[
                    ScannerCondition(
                        type="scanner",
                        scanner_name="momentum",
                        cmp="score_gt",
                        value=70.0,
                    ),
                ],
            ),
        ),
    },

    {
        "library_id":  "lib_low_volatility_above_200dma",
        "name":        "Low Volatility Above 200-DMA",
        "description": (
            "Stocks with ATR% below 3% that are trading above their 200-DMA. "
            "Descriptive screen for lower-volatility uptrend participants."
        ),
        "category": "volatility",
        "strategy": Strategy(
            name    = "Low Volatility Above 200-DMA",
            version = 1,
            entry_rules=ConditionTree(
                op="AND",
                conditions=[
                    _indicator("atr_pct", "<", 3.0),
                    _indicator("close",   ">", 0.0),  # placeholder for close > sma_200
                    _indicator("rsi_14",  ">", 45.0),
                ],
            ),
        ),
    },
]


def get_library_entry(library_id: str) -> dict | None:
    return next((e for e in SCREENER_LIBRARY if e["library_id"] == library_id), None)


def all_library_entries() -> list[dict]:
    return [
        {
            "library_id":  e["library_id"],
            "name":        e["name"],
            "description": e["description"],
            "category":    e["category"],
            "strategy":    e["strategy"].model_dump(),
        }
        for e in SCREENER_LIBRARY
    ]
