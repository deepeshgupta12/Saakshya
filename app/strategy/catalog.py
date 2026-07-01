"""Versioned field/block catalog — the only fields the strategy builder and NL agent may reference.

Any field NOT in this catalog is rejected at validation time. The NL agent is given
this catalog and must not invent fields outside it (docs/19 §2.1, SPEC §6.6).

Version: v1 — Mode-A indicator layer (EOD data only, no intraday).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


# ---------------------------------------------------------------------------
# Catalog entry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CatalogField:
    name:     str        # canonical identifier used in condition JSON
    label:    str        # human-readable label shown in the UI
    category: str        # indicator | price | volume | scanner | universe | cross
    dtype:    str        # float | bool | str | int
    unit:     str        # % | price | ratio | count | n/a
    note:     str = ""   # brief description for NL agent context


# ---------------------------------------------------------------------------
# v1 catalog
# ---------------------------------------------------------------------------

CATALOG_V1: list[CatalogField] = [
    # --- Price ---
    CatalogField("close",          "Close Price",              "price",     "float", "price"),
    CatalogField("close_adj",      "Adj. Close",               "price",     "float", "price"),
    CatalogField("open",           "Open",                     "price",     "float", "price"),
    CatalogField("high",           "High",                     "price",     "float", "price"),
    CatalogField("low",            "Low",                      "price",     "float", "price"),

    # --- Price-level references ---
    CatalogField("prior_high",     "Prior-N-bar High",         "price",     "float", "price",
                 "Highest close/high over N bars. Param: n (int)."),
    CatalogField("prior_low",      "Prior-N-bar Low",          "price",     "float", "price",
                 "Lowest close/low over N bars. Param: n (int)."),

    # --- Volume ---
    CatalogField("volume",         "Volume",                   "volume",    "float", "count"),
    CatalogField("avg_vol",        "Avg Volume (N-bar)",        "volume",    "float", "count",
                 "Rolling mean volume. Param: n (int, typical 20)."),
    CatalogField("vol_ratio",      "Volume Ratio vs 20-day",   "volume",    "float", "ratio"),

    # --- Moving averages ---
    CatalogField("sma_20",         "SMA(20)",                  "indicator", "float", "price"),
    CatalogField("sma_50",         "SMA(50)",                  "indicator", "float", "price"),
    CatalogField("sma_200",        "SMA(200)",                 "indicator", "float", "price"),
    CatalogField("ema_20",         "EMA(20)",                  "indicator", "float", "price"),
    CatalogField("ema_50",         "EMA(50)",                  "indicator", "float", "price"),

    # --- Momentum / oscillators ---
    CatalogField("rsi_14",         "RSI(14)",                  "indicator", "float", "%",
                 "14-period RSI. Range 0–100."),
    CatalogField("rsi_9",          "RSI(9)",                   "indicator", "float", "%"),
    CatalogField("macd",           "MACD Line",                "indicator", "float", "price"),
    CatalogField("macd_signal",    "MACD Signal",              "indicator", "float", "price"),
    CatalogField("macd_hist",      "MACD Histogram",           "indicator", "float", "price"),
    CatalogField("adx_14",         "ADX(14)",                  "indicator", "float", "%",
                 "14-period ADX. >25 indicates trend."),

    # --- Volatility ---
    CatalogField("atr_14",         "ATR(14)",                  "indicator", "float", "price"),
    CatalogField("atr_pct",        "ATR% (ATR÷Close)",         "indicator", "float", "%"),
    CatalogField("bb_upper",       "BB Upper (20,2)",          "indicator", "float", "price"),
    CatalogField("bb_lower",       "BB Lower (20,2)",          "indicator", "float", "price"),
    CatalogField("bb_width",       "BB Width",                 "indicator", "float", "ratio"),

    # --- Returns ---
    CatalogField("day_return_pct", "Day Return %",             "indicator", "float", "%"),
    CatalogField("ret_21d",        "21-day Return %",          "indicator", "float", "%"),
    CatalogField("ret_63d",        "63-day Return %",          "indicator", "float", "%"),
    CatalogField("ret_126d",       "126-day Return %",         "indicator", "float", "%"),

    # --- Scanner membership ---
    CatalogField("in_scanner",     "In Scanner",               "scanner",   "bool",  "n/a",
                 "True when stock appears in named scanner. Param: scanner_name (str)."),
    CatalogField("scanner_score",  "Scanner Score",            "scanner",   "float", "%",
                 "Composite score 0–100 for named scanner. Param: scanner_name (str)."),

    # --- Universe filters ---
    CatalogField("market_cap_band","Market-Cap Band",          "universe",  "str",   "n/a",
                 "LARGE | MID | SMALL | MICRO"),
    CatalogField("sector",         "Sector",                   "universe",  "str",   "n/a",
                 "NSE sector string e.g. 'BANKING', 'IT', 'PHARMA'."),
    CatalogField("index_member",   "Index Member",             "universe",  "bool",  "n/a",
                 "True if stock is in named index (point-in-time). Param: index_name (str)."),

    # --- Cross signals ---
    CatalogField("sma_20_cross",   "Price × SMA(20) Cross",    "cross",     "bool",  "n/a",
                 "True when close crosses above/below SMA(20) today."),
    CatalogField("sma_50_cross",   "Price × SMA(50) Cross",    "cross",     "bool",  "n/a"),
    CatalogField("sma_200_cross",  "Price × SMA(200) Cross",   "cross",     "bool",  "n/a"),
    CatalogField("macd_signal_cross", "MACD × Signal Cross",   "cross",     "bool",  "n/a"),
]

# Fast lookup dicts
_BY_NAME:     dict[str, CatalogField] = {f.name: f for f in CATALOG_V1}
_BY_CATEGORY: dict[str, list[CatalogField]] = {}
for _f in CATALOG_V1:
    _BY_CATEGORY.setdefault(_f.category, []).append(_f)

KNOWN_FIELD_NAMES: frozenset[str] = frozenset(_BY_NAME)


def get_field(name: str) -> CatalogField | None:
    return _BY_NAME.get(name)


def fields_by_category(category: str) -> list[CatalogField]:
    return list(_BY_CATEGORY.get(category, []))


def catalog_for_agent() -> list[dict[str, str]]:
    """Serialisable catalog summary passed to the NL agent as context."""
    return [
        {"name": f.name, "label": f.label, "category": f.category,
         "dtype": f.dtype, "unit": f.unit, "note": f.note}
        for f in CATALOG_V1
    ]
