"""Strategy tree validation (docs/19 §1.1, SPEC §6.6, step 09).

Validation rules:
  1. Every indicator/cross field name must exist in the v1 catalog.
  2. Unknown fields are REJECTED — never invented (SPEC §6.6).
  3. exit_rules cannot exist without entry_rules (enforced by schema but double-checked).
  4. RA-gated live-level fields (stop_loss_zone, target_zone as per-stock outputs) are
     NEVER valid as live scanner conditions. stop_loss / target inside exit_rules are
     BACKTEST simulation params — they pass validation but are flagged backtest_only.
  5. comparison operator must be one of the allowed set.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.strategy.catalog import KNOWN_FIELD_NAMES
from app.strategy.schema import (
    AnyCondition,
    BACKTEST_ONLY_TYPES,
    ConditionTree,
    CrossCondition,
    IndicatorCondition,
    ScannerCondition,
    Strategy,
    UniverseCondition,
)

_VALID_CMPS = frozenset({"<", ">", "<=", ">=", "==", "!="})


@dataclass
class ValidationResult:
    valid:           bool
    errors:          list[str]   = field(default_factory=list)
    warnings:        list[str]   = field(default_factory=list)
    backtest_only:   bool        = False   # True if exit_rules contain stop/target/time


def _validate_condition(cond: AnyCondition, path: str, result: ValidationResult) -> None:
    ctype = getattr(cond, "type", None)

    if ctype == "indicator":
        assert isinstance(cond, IndicatorCondition)
        if cond.expr not in KNOWN_FIELD_NAMES:
            result.errors.append(
                f"{path}: unknown field '{cond.expr}'. "
                f"Only catalog v1 fields are permitted (SPEC §6.6)."
            )
        if cond.cmp not in _VALID_CMPS:
            result.errors.append(
                f"{path}: invalid comparison operator '{cond.cmp}'. "
                f"Must be one of {sorted(_VALID_CMPS)}."
            )

    elif ctype == "cross":
        assert isinstance(cond, CrossCondition)
        for fname, role in [(cond.fast, "fast"), (cond.slow, "slow")]:
            if fname not in KNOWN_FIELD_NAMES:
                result.errors.append(
                    f"{path} cross.{role}: unknown field '{fname}'. "
                    f"Only catalog v1 fields are permitted."
                )

    elif ctype == "scanner":
        assert isinstance(cond, ScannerCondition)
        # Scanner names are not validated against a registry here (registry is DB-backed);
        # API layer validates names at runtime.

    elif ctype == "universe":
        assert isinstance(cond, UniverseCondition)
        valid_ufields = {"market_cap_band", "sector", "index_member"}
        if cond.field not in valid_ufields:
            result.errors.append(
                f"{path}: unknown universe field '{cond.field}'. "
                f"Must be one of {sorted(valid_ufields)}."
            )

    elif ctype in BACKTEST_ONLY_TYPES:
        result.backtest_only = True
        # Backtest-only conditions in entry_rules are an error.
        if "entry_rules" in path:
            result.errors.append(
                f"{path}: '{ctype}' is a backtest-only exit condition and cannot "
                f"appear in entry_rules."
            )

    else:
        result.errors.append(f"{path}: unrecognised condition type '{ctype}'.")


def _validate_tree(tree: ConditionTree, path: str, result: ValidationResult) -> None:
    if not tree.conditions:
        result.errors.append(f"{path}: condition tree must have at least one condition.")
        return
    for i, cond in enumerate(tree.conditions):
        _validate_condition(cond, f"{path}[{i}]", result)


def validate_strategy(strategy: Strategy) -> ValidationResult:
    """Validate a Strategy object against catalog v1 and compliance rules.

    Returns a ValidationResult with errors (blocking) and warnings (advisory).
    A strategy with any errors is not safe to save or compile.
    """
    result = ValidationResult(valid=True)

    # 1. Entry rules — always required
    if strategy.entry_rules is None:
        result.errors.append("entry_rules is required.")
    else:
        _validate_tree(strategy.entry_rules, "entry_rules", result)

    # 2. Exit rules — optional; backtest-only conditions allowed here
    if strategy.exit_rules is not None:
        _validate_tree(strategy.exit_rules, "exit_rules", result)

    # 3. Warn if backtest config is absent but exit rules have stop/target/trailing
    if result.backtest_only and strategy.backtest is None:
        result.warnings.append(
            "exit_rules contains backtest-only conditions (stop_loss / target / "
            "trailing_stop) but no backtest config is provided. These conditions "
            "will be stripped from the live scanner form."
        )

    # 4. Integrity flags warning if disabled for backtest
    if strategy.backtest is not None:
        flags = strategy.integrity
        if not flags.survivorship_control:
            result.warnings.append("survivorship_control=false — backtest will not include delisted names.")
        if not flags.look_ahead_control:
            result.errors.append(
                "look_ahead_control must be true to prevent look-ahead bias (SPEC §6.3)."
            )
        if not flags.point_in_time_membership:
            result.warnings.append(
                "point_in_time_membership=false — index membership may not be historically accurate."
            )

    result.valid = len(result.errors) == 0
    return result
