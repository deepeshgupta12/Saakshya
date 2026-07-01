"""Tests for strategy condition-tree evaluator and scanner compiler (docs/19)."""

from __future__ import annotations

import pytest

from app.strategy.compiler import compile_scanner_rule, strip_backtest_conditions
from app.strategy.engine import evaluate_tree, evaluate_universe
from app.strategy.schema import (
    BACKTEST_ONLY_TYPES,
    ConditionTree,
    CrossCondition,
    IndicatorCondition,
    StopLossCondition,
    Strategy,
    TargetCondition,
    TimeCondition,
    UniverseFilter,
)
from app.strategy.validate import validate_strategy


# ---------------------------------------------------------------------------
# Condition-tree evaluator
# ---------------------------------------------------------------------------

class TestEvaluateTree:
    def _row(self, **kwargs) -> dict:
        defaults = {
            "rsi_14": 30.0, "close": 695.0, "sma_50": 700.0, "sma_200": 680.0,
            "vol_ratio": 2.5, "adx_14": 28.0,
        }
        defaults.update(kwargs)
        return defaults

    def test_and_all_true(self):
        tree = ConditionTree(op="AND", conditions=[
            IndicatorCondition(type="indicator", expr="rsi_14", cmp="<", value=35),
            IndicatorCondition(type="indicator", expr="vol_ratio", cmp=">", value=2.0),
        ])
        assert evaluate_tree(tree, self._row()) is True

    def test_and_one_false(self):
        tree = ConditionTree(op="AND", conditions=[
            IndicatorCondition(type="indicator", expr="rsi_14", cmp="<", value=35),
            IndicatorCondition(type="indicator", expr="vol_ratio", cmp=">", value=5.0),  # vol_ratio=2.5 < 5
        ])
        assert evaluate_tree(tree, self._row()) is False

    def test_or_one_true(self):
        tree = ConditionTree(op="OR", conditions=[
            IndicatorCondition(type="indicator", expr="rsi_14", cmp="<", value=20),  # False: 30 > 20
            IndicatorCondition(type="indicator", expr="adx_14", cmp=">", value=25.0),   # True: 28 > 25
        ])
        assert evaluate_tree(tree, self._row()) is True

    def test_or_all_false(self):
        tree = ConditionTree(op="OR", conditions=[
            IndicatorCondition(type="indicator", expr="rsi_14", cmp="<", value=20),
            IndicatorCondition(type="indicator", expr="adx_14", cmp=">", value=50.0),
        ])
        assert evaluate_tree(tree, self._row()) is False

    def test_missing_field_treats_as_false(self):
        tree = ConditionTree(op="AND", conditions=[
            IndicatorCondition(type="indicator", expr="macd_hist", cmp=">", value=0),  # missing
        ])
        assert evaluate_tree(tree, self._row()) is False

    def test_cross_above_detected(self):
        tree = ConditionTree(op="AND", conditions=[
            CrossCondition(type="cross", fast="close", dir="crosses_above", slow="sma_50"),
        ])
        row = self._row(
            close=701.0, sma_50=700.0,
            close_prev=698.0, sma_50_prev=700.0,  # prev below
        )
        assert evaluate_tree(tree, row) is True

    def test_cross_above_not_detected_already_above(self):
        tree = ConditionTree(op="AND", conditions=[
            CrossCondition(type="cross", fast="close", dir="crosses_above", slow="sma_50"),
        ])
        row = self._row(
            close=701.0, sma_50=700.0,
            close_prev=702.0, sma_50_prev=700.0,  # was already above
        )
        assert evaluate_tree(tree, row) is False


class TestEvaluateUniverse:
    def test_filters_matching_rows(self):
        tree = ConditionTree(op="AND", conditions=[
            IndicatorCondition(type="indicator", expr="rsi_14", cmp="<", value=40),
        ])
        universe = [
            {"symbol": "INFY",    "rsi_14": 30.0},  # match
            {"symbol": "TCS",     "rsi_14": 55.0},  # no match
            {"symbol": "HDFC",    "rsi_14": 38.0},  # match
        ]
        results = evaluate_universe(tree, universe)
        assert len(results) == 2
        assert {r["symbol"] for r in results} == {"INFY", "HDFC"}


# ---------------------------------------------------------------------------
# Scanner compiler (strip backtest-only conditions)
# ---------------------------------------------------------------------------

class TestCompiler:
    def _strategy_with_exit(self) -> Strategy:
        return Strategy(
            name        = "Test Strategy",
            entry_rules = ConditionTree(op="AND", conditions=[
                IndicatorCondition(type="indicator", expr="rsi_14", cmp="<", value=35),
            ]),
            exit_rules  = ConditionTree(op="OR", conditions=[
                IndicatorCondition(type="indicator", expr="rsi_14", cmp=">", value=70),
                StopLossCondition(type="stop_loss", method="pct", value=8.0),
                TargetCondition(type="target",    method="pct", value=15.0),
                TimeCondition(type="time",         max_holding_bars=30),
            ]),
        )

    def test_strip_removes_exit_rules(self):
        live = strip_backtest_conditions(self._strategy_with_exit())
        assert live.exit_rules is None

    def test_strip_removes_backtest_config(self):
        s = self._strategy_with_exit()
        from app.strategy.schema import BacktestConfig
        s.backtest = BacktestConfig(start="2020-01-01", end="2024-12-31")
        live = strip_backtest_conditions(s)
        assert live.backtest is None

    def test_compile_scanner_rule_has_only_entry_rules(self):
        rule = compile_scanner_rule(self._strategy_with_exit())
        assert "exit_rules" not in rule
        assert "stop_loss"  not in str(rule)
        assert "target"     not in str(rule)
        assert "entry_rules" in rule
        assert "mode" in rule
        assert rule["mode"] == "live_scanner"

    def test_compile_includes_disclaimer(self):
        rule = compile_scanner_rule(self._strategy_with_exit())
        assert "Past performance" in rule.get("disclaimer", "")

    def test_live_form_delisted_set_to_false(self):
        s = self._strategy_with_exit()
        s.universe.include_delisted = True
        live = strip_backtest_conditions(s)
        assert live.universe.include_delisted is False


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_valid_strategy_passes(self):
        s = Strategy(
            name        = "Valid",
            entry_rules = ConditionTree(op="AND", conditions=[
                IndicatorCondition(type="indicator", expr="rsi_14", cmp="<", value=35),
            ]),
        )
        r = validate_strategy(s)
        assert r.valid is True
        assert r.errors == []

    def test_unknown_field_fails(self):
        s = Strategy(
            name        = "Unknown field",
            entry_rules = ConditionTree(op="AND", conditions=[
                IndicatorCondition(type="indicator", expr="made_up_field", cmp="<", value=10),
            ]),
        )
        r = validate_strategy(s)
        assert r.valid is False
        assert any("unknown field" in e.lower() for e in r.errors)

    def test_stop_loss_in_entry_fails(self):
        s = Strategy(
            name        = "Bad entry",
            entry_rules = ConditionTree(op="AND", conditions=[
                IndicatorCondition(type="indicator", expr="rsi_14", cmp="<", value=35),
                StopLossCondition(type="stop_loss", method="pct", value=8.0),
            ]),
        )
        r = validate_strategy(s)
        assert r.valid is False
        assert any("backtest-only" in e for e in r.errors)

    def test_no_look_ahead_control_blocked(self):
        from app.strategy.schema import BacktestConfig, IntegrityFlags
        s = Strategy(
            name        = "Lookahead risk",
            entry_rules = ConditionTree(op="AND", conditions=[
                IndicatorCondition(type="indicator", expr="rsi_14", cmp="<", value=35),
            ]),
            backtest    = BacktestConfig(start="2020-01-01", end="2024-12-31"),
            integrity   = IntegrityFlags(look_ahead_control=False),
        )
        r = validate_strategy(s)
        assert r.valid is False
        assert any("look_ahead_control" in e for e in r.errors)
