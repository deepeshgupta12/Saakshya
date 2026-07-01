"""Condition-tree evaluator over the indicator layer (docs/19 §1, step 09).

evaluate_tree(tree, row) returns True/False for a single stock×date row.
`row` is a dict of indicator values keyed by catalog field names.

This engine is used by:
  1. The live scanner compiler (evaluate each stock in the universe today).
  2. The backtest engine (evaluate entry/exit signals bar-by-bar).

Look-ahead discipline: the caller must pass ONLY data available as of the
evaluation bar (the pipeline ensures this via point-in-time snapshots).
"""

from __future__ import annotations

import logging
from typing import Any

from app.strategy.schema import (
    AnyCondition,
    ConditionTree,
    CrossCondition,
    IndicatorCondition,
    ScannerCondition,
    TimeCondition,
    UniverseCondition,
)

log = logging.getLogger(__name__)

_VALID_CMPS = {
    "<":  lambda a, b: a < b,
    ">":  lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def _eval_condition(cond: AnyCondition, row: dict[str, Any]) -> bool | None:
    """Evaluate a single condition against a row dict.

    Returns None when a required value is missing from the row (treated as
    False by the caller — a missing input does not pass the condition).
    """
    ctype = getattr(cond, "type", None)

    if ctype == "indicator":
        assert isinstance(cond, IndicatorCondition)
        val = row.get(cond.expr)
        if val is None:
            return None
        op = _VALID_CMPS.get(cond.cmp)
        if op is None:
            log.warning("Unknown comparison operator %r", cond.cmp)
            return None
        try:
            return bool(op(float(val), float(cond.value)))
        except (TypeError, ValueError):
            return None

    if ctype == "cross":
        assert isinstance(cond, CrossCondition)
        fast_today  = row.get(cond.fast)
        slow_today  = row.get(cond.slow)
        fast_prev   = row.get(f"{cond.fast}_prev")
        slow_prev   = row.get(f"{cond.slow}_prev")

        if any(v is None for v in [fast_today, slow_today, fast_prev, slow_prev]):
            return None

        if cond.dir == "crosses_above":
            return float(fast_prev) <= float(slow_prev) and float(fast_today) > float(slow_today)
        if cond.dir == "crosses_below":
            return float(fast_prev) >= float(slow_prev) and float(fast_today) < float(slow_today)
        return None

    if ctype == "scanner":
        assert isinstance(cond, ScannerCondition)
        scanner_key = f"in_scanner_{cond.scanner_name}"
        score_key   = f"scanner_score_{cond.scanner_name}"

        if cond.cmp == "in":
            val = row.get(scanner_key) or row.get("in_scanner")
            return bool(val) if val is not None else None

        score = row.get(score_key) or row.get("scanner_score")
        if score is None:
            return None
        if cond.cmp == "score_gt":
            return float(score) > (cond.value or 0.0)
        if cond.cmp == "score_lt":
            return float(score) < (cond.value or 100.0)
        return None

    if ctype == "universe":
        assert isinstance(cond, UniverseCondition)
        val = row.get(cond.field)
        if val is None:
            return None
        expected = cond.value
        if isinstance(expected, list):
            return str(val) in [str(e) for e in expected]
        return str(val) == str(expected)

    # Backtest-only conditions (stop_loss / target / trailing_stop / time)
    # are skipped in live evaluation — they are stripped by the compiler.
    return None


def evaluate_tree(tree: ConditionTree, row: dict[str, Any]) -> bool:
    """Evaluate a condition tree (AND/OR) against a single stock-row dict.

    Missing values resolve to False (conservative — a missing ATR does not
    accidentally pass an ATR-based condition).
    """
    results = [_eval_condition(c, row) for c in tree.conditions]
    bool_results = [r if r is not None else False for r in results]

    if tree.op == "AND":
        return all(bool_results)
    if tree.op == "OR":
        return any(bool_results)
    return False


def evaluate_universe(
    entry_rules: ConditionTree,
    universe_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Evaluate entry rules over a list of stock rows and return matching rows."""
    return [row for row in universe_rows if evaluate_tree(entry_rules, row)]
