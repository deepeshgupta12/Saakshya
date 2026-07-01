"""Pydantic models for the strategy JSON schema (docs/19 §7, step 09).

A Strategy is a condition tree with entry_rules + optional exit_rules +
optional universe filter + optional backtest config + integrity flags.

Key rule (docs/19 §1.1, SPEC §5.17):
  - stop_loss / target / trailing_stop live inside exit_rules as BACKTEST
    simulation parameters only.
  - The live scanner compiler STRIPS them; they are never surfaced as live
    per-stock levels (RA-gated, SPEC §5.21).
"""

from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Condition types
# ---------------------------------------------------------------------------

class IndicatorCondition(BaseModel):
    type:  Literal["indicator"]
    expr:  str          # catalog field name, e.g. "rsi_14"
    cmp:   str          # "<" | ">" | "<=" | ">=" | "==" | "!="
    value: float


class CrossCondition(BaseModel):
    type:  Literal["cross"]
    fast:  str          # catalog field name
    dir:   Literal["crosses_above", "crosses_below"]
    slow:  str          # catalog field name


class ScannerCondition(BaseModel):
    type:         Literal["scanner"]
    scanner_name: str
    cmp:          Literal["in", "score_gt", "score_lt"] = "in"
    value:        float | None = None   # score threshold when cmp != "in"


class UniverseCondition(BaseModel):
    type:        Literal["universe"]
    field:       str    # "market_cap_band" | "sector" | "index_member"
    value:       Any    # str | list[str] | bool


# Backtest-only exit conditions (stripped by scanner compiler)
class StopLossCondition(BaseModel):
    type:   Literal["stop_loss"]
    method: Literal["atr", "pct", "fixed"]
    k:      float | None = None      # ATR multiplier
    value:  float | None = None      # pct or fixed amount

    @property
    def is_backtest_only(self) -> bool:
        return True


class TargetCondition(BaseModel):
    type:   Literal["target"]
    method: Literal["atr", "pct", "fixed"]
    k:      float | None = None
    value:  float | None = None

    @property
    def is_backtest_only(self) -> bool:
        return True


class TrailingStopCondition(BaseModel):
    type:   Literal["trailing_stop"]
    method: Literal["atr", "pct"]
    k:      float | None = None
    value:  float | None = None

    @property
    def is_backtest_only(self) -> bool:
        return True


class TimeCondition(BaseModel):
    type:             Literal["time"]
    max_holding_bars: int


AnyCondition = Union[
    IndicatorCondition,
    CrossCondition,
    ScannerCondition,
    UniverseCondition,
    StopLossCondition,
    TargetCondition,
    TrailingStopCondition,
    TimeCondition,
]

BACKTEST_ONLY_TYPES: frozenset[str] = frozenset({
    "stop_loss", "target", "trailing_stop", "time",
})


# ---------------------------------------------------------------------------
# Condition tree
# ---------------------------------------------------------------------------

class ConditionTree(BaseModel):
    op:         Literal["AND", "OR"]
    conditions: list[AnyCondition] = Field(min_length=1)


# ---------------------------------------------------------------------------
# Universe filter
# ---------------------------------------------------------------------------

class UniverseFilter(BaseModel):
    index_membership:      str | None            = None   # e.g. "NIFTY100"
    membership_mode:       Literal["point_in_time", "current"] = "point_in_time"
    market_cap_band:       list[str] | None      = None   # ["LARGE", "MID"]
    sector:                list[str] | None      = None
    include_delisted:      bool                  = True   # mandatory for honest backtests


# ---------------------------------------------------------------------------
# Execution config (backtest only)
# ---------------------------------------------------------------------------

class ExecutionConfig(BaseModel):
    transaction_cost_bps: int   = 12
    slippage_bps:         int   = 15
    volume_cap_pct:       float = 5.0
    fill_price:           Literal["next_open", "close"] = "next_open"


# ---------------------------------------------------------------------------
# Backtest config (backtest only)
# ---------------------------------------------------------------------------

class BacktestConfig(BaseModel):
    start:           str            # ISO date
    end:             str            # ISO date
    benchmark:       str    = "NIFTY50"
    initial_capital: float  = 1_000_000


# ---------------------------------------------------------------------------
# Integrity flags (backtest only — all must be True to run)
# ---------------------------------------------------------------------------

class IntegrityFlags(BaseModel):
    survivorship_control:     bool = True
    look_ahead_control:       bool = True
    point_in_time_membership: bool = True
    realistic_fills:          bool = True


# ---------------------------------------------------------------------------
# Strategy root
# ---------------------------------------------------------------------------

class Strategy(BaseModel):
    strategy_id:   str | None            = None
    name:          str
    version:       int                   = 1
    universe:      UniverseFilter        = Field(default_factory=UniverseFilter)
    entry_rules:   ConditionTree
    exit_rules:    ConditionTree | None  = None   # None = open-ended scanner / screener
    execution:     ExecutionConfig       = Field(default_factory=ExecutionConfig)
    backtest:      BacktestConfig | None = None
    integrity:     IntegrityFlags        = Field(default_factory=IntegrityFlags)
    disclaimer:    str = "Past performance does not indicate future results."

    @model_validator(mode="after")
    def _check_entry_not_empty(self) -> "Strategy":
        if not self.entry_rules.conditions:
            raise ValueError("entry_rules must have at least one condition.")
        return self

    def live_scanner_form(self) -> "Strategy":
        """Return a copy with backtest-only exit conditions stripped.

        The resulting strategy is safe to use as a live scanner rule — it
        produces a list of matching stocks, never a per-stock level / directive.
        """
        from app.strategy.compiler import strip_backtest_conditions
        return strip_backtest_conditions(self)
