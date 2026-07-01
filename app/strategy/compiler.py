"""Scanner-rule compiler: extracts entry_rules, strips backtest-only exit conditions.

From docs/19 §2.1 and SPEC §5.17:
  - Entry conditions compile to a live scanner rule (produces a LIST of matching stocks).
  - Exit/stop/target/trailing_stop/time conditions are BACKTEST simulation parameters.
  - The live scanner form MUST NOT contain stop_loss / target / trailing_stop / time
    (those would be RA-gated per-stock levels if shown as live outputs).

The compiled scanner rule is safe to evaluate over today's universe.
"""

from __future__ import annotations

import copy

from app.strategy.schema import (
    BACKTEST_ONLY_TYPES,
    ConditionTree,
    Strategy,
)


def strip_backtest_conditions(strategy: Strategy) -> Strategy:
    """Return a copy of the strategy with backtest-only exit conditions removed.

    - `exit_rules` are removed entirely (stop/target/time).
    - `backtest` config is removed.
    - `execution` config is removed.
    - `universe.include_delisted` is reset to False (only live members matter for scanner).
    - `disclaimer` is preserved.
    """
    data = strategy.model_dump()

    # Remove backtest-only sections
    data["exit_rules"] = None
    data["backtest"]   = None
    data["execution"]  = {
        "transaction_cost_bps": 0,
        "slippage_bps":         0,
        "volume_cap_pct":       100.0,
        "fill_price":           "close",
    }

    # Live universe: exclude delisted (they are only relevant for historical sims)
    if data.get("universe"):
        data["universe"]["include_delisted"] = False

    # Explicitly re-validate entry_rules — strip any backtest-only conditions
    # that somehow ended up there (should be caught by validate, but defensive).
    if data.get("entry_rules"):
        data["entry_rules"]["conditions"] = [
            c for c in data["entry_rules"]["conditions"]
            if c.get("type") not in BACKTEST_ONLY_TYPES
        ]

    return Strategy.model_validate(data)


def compile_scanner_rule(strategy: Strategy) -> dict:
    """Compile a strategy into a minimal scanner-rule dict.

    The result can be serialised and stored in strategy_definitions as the
    live scanner variant. It contains ONLY entry_rules + universe.
    """
    live = strip_backtest_conditions(strategy)
    return {
        "name":        live.name,
        "version":     live.version,
        "universe":    live.universe.model_dump(exclude_none=True),
        "entry_rules": live.entry_rules.model_dump(),
        "disclaimer":  live.disclaimer,
        "mode":        "live_scanner",
    }
