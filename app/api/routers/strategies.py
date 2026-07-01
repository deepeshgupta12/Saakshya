"""Strategy builder API endpoints (docs/10 §7, docs/19, step 09).

GET    /v1/strategy/library           — list prebuilt screeners
GET    /v1/strategy                   — list user strategies
POST   /v1/strategy                   — save strategy
GET    /v1/strategy/{id}              — fetch strategy
PUT    /v1/strategy/{id}              — update strategy (new version)
POST   /v1/strategy/{id}/clone        — clone to new user strategy
POST   /v1/strategy/validate          — validate a strategy JSON (no save)
POST   /v1/strategy/compile-scanner   — compile to live scanner rule
POST   /v1/strategy/from-nl           — NL → strategy (returns editable blocks for user confirmation)

Mode-A discipline:
  - Outputs are LISTS (screener matches), never buy/sell calls.
  - NL→strategy returns proposed blocks for user confirmation — not auto-run.
  - No per-stock entry/target/stop-loss LEVELS are returned as live outputs.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import AuthUserDep, DbDep
from app.api.envelope import ok
from app.api.errors import ModeGatedError, NotFoundError, ValidationError
from app.strategy.catalog import catalog_for_agent
from app.strategy.compiler import compile_scanner_rule, strip_backtest_conditions
from app.strategy.library import all_library_entries, get_library_entry
from app.strategy.nl_agent import nl_to_strategy
from app.strategy.schema import Strategy
from app.strategy.validate import validate_strategy

router = APIRouter(prefix="/v1/strategy", tags=["strategy"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class StrategySaveBody(BaseModel):
    strategy_json: dict


class NLStrategyBody(BaseModel):
    text: str   # user's natural-language description


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/library")
def get_library(
    conn: DbDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    """List prebuilt Mode-A screener library entries."""
    return ok(all_library_entries())


@router.get("/catalog")
def get_catalog(
    conn: DbDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    """List all known catalog fields (for the NL agent and the block builder UI)."""
    return ok(catalog_for_agent())


@router.post("/validate")
def validate_strategy_endpoint(
    body: StrategySaveBody,
    conn: DbDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    """Validate a strategy JSON — returns errors and warnings without saving."""
    try:
        strategy = Strategy.model_validate(body.strategy_json)
    except Exception as exc:
        return ok(
            {"valid": False, "errors": [str(exc)], "warnings": [], "backtest_only": False}
        )
    vresult = validate_strategy(strategy)
    return ok({
        "valid":        vresult.valid,
        "errors":       vresult.errors,
        "warnings":     vresult.warnings,
        "backtest_only": vresult.backtest_only,
    })


@router.post("/compile-scanner")
def compile_scanner(
    body: StrategySaveBody,
    conn: DbDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    """Compile a strategy to a live scanner rule (strips exit/stop/target).

    The result contains ONLY entry_rules + universe — safe to use as a screener.
    """
    try:
        strategy = Strategy.model_validate(body.strategy_json)
    except Exception as exc:
        raise ValidationError(f"Strategy schema error: {exc}")

    vresult = validate_strategy(strategy)
    if not vresult.valid:
        raise ValidationError(f"Strategy has validation errors: {vresult.errors}")

    scanner_rule = compile_scanner_rule(strategy)
    return ok({
        "scanner_rule":  scanner_rule,
        "disclaimer":    "This scanner produces a list of matching stocks, not buy/sell calls.",
    })


@router.post("/from-nl")
def strategy_from_nl(
    body:     NLStrategyBody,
    conn:     DbDep,
    user:     AuthUserDep,
) -> dict[str, Any]:
    """Convert natural language to an editable strategy JSON (requires user confirmation).

    IMPORTANT: The response is proposed blocks for the user to review/edit.
    It is NOT an instruction to trade. "buy" in the user's text maps to an
    entry condition for a screener, not a recommendation.
    """
    result = nl_to_strategy(body.text, conn=conn)

    return ok({
        "strategy":          result.get("strategy"),
        "validation":        result.get("validation"),
        "guardrail_passed":  result.get("guardrail_passed"),
        "requires_confirmation": True,
        "confirmation_note": (
            "Please review the proposed conditions. This is a screener definition — "
            "it produces a list of matching stocks. It is not investment advice."
        ),
        "errors":            result.get("errors"),
    })


@router.get("")
def list_strategies(
    conn: DbDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    """List user's saved strategy definitions."""
    rows = conn.execute(
        "SELECT strategy_id, name, version, validation_status, is_library, created_at "
        "FROM strategy_definitions WHERE owner_user_id = ? ORDER BY created_at DESC",
        [user.user_id],
    ).fetchall()

    data = [
        {
            "strategy_id":       r[0],
            "name":              r[1],
            "version":           r[2],
            "validation_status": r[3],
            "is_library":        bool(r[4]),
            "created_at":        str(r[5]),
        }
        for r in rows
    ]
    return ok(data)


@router.post("", status_code=201)
def save_strategy(
    body: StrategySaveBody,
    conn: DbDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    """Save a validated strategy definition."""
    try:
        strategy = Strategy.model_validate(body.strategy_json)
    except Exception as exc:
        raise ValidationError(f"Strategy schema error: {exc}")

    vresult = validate_strategy(strategy)
    validation_status = "VALID" if vresult.valid else "INVALID"

    if not vresult.valid:
        raise ValidationError(f"Strategy validation failed: {vresult.errors}")

    strategy_id = f"st-{uuid.uuid4().hex[:12]}"
    if strategy.strategy_id is None:
        strategy.strategy_id = strategy_id

    conn.execute(
        "INSERT INTO strategy_definitions "
        "(strategy_id, owner_user_id, name, version, strategy_json, is_library, validation_status) "
        "VALUES (?,?,?,?,?,?,?)",
        [
            strategy_id, user.user_id, strategy.name, strategy.version,
            json.dumps(strategy.model_dump()), False, validation_status,
        ],
    )
    return ok({"strategy_id": strategy_id, "validation_status": validation_status})


@router.get("/{strategy_id}")
def get_strategy(
    strategy_id: str,
    conn:        DbDep,
    user:        AuthUserDep,
) -> dict[str, Any]:
    """Fetch a saved strategy by ID."""
    row = conn.execute(
        "SELECT strategy_id, owner_user_id, name, version, strategy_json, "
        "is_library, validation_status, created_at "
        "FROM strategy_definitions WHERE strategy_id = ?",
        [strategy_id],
    ).fetchone()

    if row is None:
        raise NotFoundError(f"Strategy {strategy_id!r} not found.")
    # Library strategies are public; owned strategies check user_id
    if not bool(row[5]) and row[1] != user.user_id:
        raise NotFoundError(f"Strategy {strategy_id!r} not found.")

    return ok({
        "strategy_id":       row[0],
        "name":              row[2],
        "version":           row[3],
        "strategy_json":     _safe_json(row[4]),
        "is_library":        bool(row[5]),
        "validation_status": row[6],
        "created_at":        str(row[7]),
    })


@router.put("/{strategy_id}")
def update_strategy(
    strategy_id: str,
    body:        StrategySaveBody,
    conn:        DbDep,
    user:        AuthUserDep,
) -> dict[str, Any]:
    """Update a strategy (bumps version, re-validates)."""
    row = conn.execute(
        "SELECT strategy_id, version FROM strategy_definitions "
        "WHERE strategy_id = ? AND owner_user_id = ?",
        [strategy_id, user.user_id],
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Strategy {strategy_id!r} not found.")

    try:
        strategy = Strategy.model_validate(body.strategy_json)
    except Exception as exc:
        raise ValidationError(f"Strategy schema error: {exc}")

    vresult      = validate_strategy(strategy)
    new_version  = int(row[1]) + 1
    val_status   = "VALID" if vresult.valid else "INVALID"
    strategy.version = new_version

    conn.execute(
        "UPDATE strategy_definitions SET version=?, strategy_json=?, validation_status=?, updated_at=now() "
        "WHERE strategy_id=?",
        [new_version, json.dumps(strategy.model_dump()), val_status, strategy_id],
    )
    return ok({"strategy_id": strategy_id, "version": new_version, "validation_status": val_status})


@router.post("/{strategy_id}/clone", status_code=201)
def clone_strategy(
    strategy_id: str,
    conn:        DbDep,
    user:        AuthUserDep,
) -> dict[str, Any]:
    """Clone a strategy (own or library) to the user's account."""
    row = conn.execute(
        "SELECT strategy_json, name FROM strategy_definitions WHERE strategy_id = ?",
        [strategy_id],
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Strategy {strategy_id!r} not found.")

    new_id = f"st-{uuid.uuid4().hex[:12]}"
    name   = f"{row[1]} (copy)"
    conn.execute(
        "INSERT INTO strategy_definitions "
        "(strategy_id, owner_user_id, name, version, strategy_json, is_library, validation_status) "
        "VALUES (?,?,?,?,?,?,?)",
        [new_id, user.user_id, name, 1, row[0], False, "VALID"],
    )
    return ok({"strategy_id": new_id, "cloned_from": strategy_id})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_json(raw: str | None) -> Any:
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return raw
