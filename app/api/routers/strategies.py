"""Strategy builder API endpoints (docs/10 §7, docs/19, step 09).

GET    /v1/strategy/library           — list prebuilt screeners
GET    /v1/strategy                   — list user strategies
POST   /v1/strategy                   — save strategy
GET    /v1/strategy/{id}              — fetch strategy
PUT    /v1/strategy/{id}              — update strategy (new version)
POST   /v1/strategy/{id}/clone        — clone to new user strategy
POST   /v1/strategy/validate          — validate a strategy JSON (no save)
POST   /v1/strategy/compile-scanner   — compile to live scanner rule
POST   /v1/strategy/from-nl           — NL → strategy (editable blocks for confirmation)

Storage (D-059): strategy documents live in MongoDB (`strategy_definitions`); the
prebuilt library is served from app/strategy/library.py (in-memory, not the DB).

Mode-A discipline:
  - Outputs are LISTS (screener matches), never buy/sell calls.
  - NL→strategy returns proposed blocks for user confirmation — not auto-run.
  - No per-stock entry/target/stop-loss LEVELS are returned as live outputs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import AuthUserDep, MongoDep
from app.api.envelope import ok
from app.api.errors import NotFoundError, ValidationError
from app.strategy.catalog import catalog_for_agent
from app.strategy.compiler import compile_scanner_rule
from app.strategy.library import all_library_entries
from app.strategy.nl_agent import nl_to_strategy
from app.strategy.schema import Strategy
from app.strategy.validate import validate_strategy

router = APIRouter(prefix="/v1/strategy", tags=["strategy"])


class StrategySaveBody(BaseModel):
    strategy_json: dict


class NLStrategyBody(BaseModel):
    text: str


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


# ── Stateless endpoints (no DB) ─────────────────────────────────────────────

@router.get("/library")
def get_library(user: AuthUserDep) -> dict[str, Any]:
    """List prebuilt Mode-A screener library entries."""
    return ok(all_library_entries())


@router.get("/catalog")
def get_catalog(user: AuthUserDep) -> dict[str, Any]:
    """List all known catalog fields (for the NL agent and the block builder UI)."""
    return ok(catalog_for_agent())


@router.post("/validate")
def validate_strategy_endpoint(body: StrategySaveBody, user: AuthUserDep) -> dict[str, Any]:
    """Validate a strategy JSON — returns errors and warnings without saving."""
    try:
        strategy = Strategy.model_validate(body.strategy_json)
    except Exception as exc:
        return ok({"valid": False, "errors": [str(exc)], "warnings": [], "backtest_only": False})
    vresult = validate_strategy(strategy)
    return ok({
        "valid":         vresult.valid,
        "errors":        vresult.errors,
        "warnings":      vresult.warnings,
        "backtest_only": vresult.backtest_only,
    })


@router.post("/compile-scanner")
def compile_scanner(body: StrategySaveBody, user: AuthUserDep) -> dict[str, Any]:
    """Compile a strategy to a live scanner rule (strips exit/stop/target)."""
    try:
        strategy = Strategy.model_validate(body.strategy_json)
    except Exception as exc:
        raise ValidationError(f"Strategy schema error: {exc}")
    vresult = validate_strategy(strategy)
    if not vresult.valid:
        raise ValidationError(f"Strategy has validation errors: {vresult.errors}")
    scanner_rule = compile_scanner_rule(strategy)
    return ok({
        "scanner_rule": scanner_rule,
        "disclaimer":   "This scanner produces a list of matching stocks, not buy/sell calls.",
    })


@router.post("/from-nl")
def strategy_from_nl(body: NLStrategyBody, user: AuthUserDep) -> dict[str, Any]:
    """Convert natural language to an editable strategy JSON (requires user confirmation)."""
    result = nl_to_strategy(body.text)
    return ok({
        "strategy":              result.get("strategy"),
        "validation":            result.get("validation"),
        "guardrail_passed":      result.get("guardrail_passed"),
        "requires_confirmation": True,
        "confirmation_note": (
            "Please review the proposed conditions. This is a screener definition — "
            "it produces a list of matching stocks. It is not investment advice."
        ),
        "errors":                result.get("errors"),
    })


# ── Persisted strategy CRUD (MongoDB) ───────────────────────────────────────

@router.get("")
def list_strategies(mongo: MongoDep, user: AuthUserDep) -> dict[str, Any]:
    """List the user's saved strategy definitions."""
    docs = mongo.strategy_definitions.find({"owner_user_id": user.user_id}).sort("created_at", -1)
    data = [
        {
            "strategy_id":       d["strategy_id"],
            "name":              d["name"],
            "version":           d["version"],
            "validation_status": d["validation_status"],
            "is_library":        bool(d.get("is_library", False)),
            "created_at":        str(d["created_at"]),
        }
        for d in docs
    ]
    return ok(data)


@router.post("", status_code=201)
def save_strategy(body: StrategySaveBody, mongo: MongoDep, user: AuthUserDep) -> dict[str, Any]:
    """Save a validated strategy definition."""
    try:
        strategy = Strategy.model_validate(body.strategy_json)
    except Exception as exc:
        raise ValidationError(f"Strategy schema error: {exc}")
    vresult = validate_strategy(strategy)
    if not vresult.valid:
        raise ValidationError(f"Strategy validation failed: {vresult.errors}")

    strategy_id = f"st-{uuid.uuid4().hex[:12]}"
    if strategy.strategy_id is None:
        strategy.strategy_id = strategy_id
    now = _now()
    mongo.strategy_definitions.insert_one({
        "strategy_id": strategy_id, "owner_user_id": user.user_id,
        "name": strategy.name, "version": strategy.version,
        "strategy_json": strategy.model_dump(mode="json"),
        "is_library": False, "validation_status": "VALID",
        "created_at": now, "updated_at": now,
    })
    return ok({"strategy_id": strategy_id, "validation_status": "VALID"})


@router.get("/{strategy_id}")
def get_strategy(strategy_id: str, mongo: MongoDep, user: AuthUserDep) -> dict[str, Any]:
    """Fetch a saved strategy by ID (library strategies are public)."""
    d = mongo.strategy_definitions.find_one({"strategy_id": strategy_id})
    if d is None or (not bool(d.get("is_library", False)) and d["owner_user_id"] != user.user_id):
        raise NotFoundError(f"Strategy {strategy_id!r} not found.")
    return ok({
        "strategy_id":       d["strategy_id"],
        "name":              d["name"],
        "version":           d["version"],
        "strategy_json":     d.get("strategy_json"),
        "is_library":        bool(d.get("is_library", False)),
        "validation_status": d["validation_status"],
        "created_at":        str(d["created_at"]),
    })


@router.put("/{strategy_id}")
def update_strategy(
    strategy_id: str, body: StrategySaveBody, mongo: MongoDep, user: AuthUserDep
) -> dict[str, Any]:
    """Update a strategy (bumps version, re-validates)."""
    d = mongo.strategy_definitions.find_one(
        {"strategy_id": strategy_id, "owner_user_id": user.user_id}, {"version": 1}
    )
    if d is None:
        raise NotFoundError(f"Strategy {strategy_id!r} not found.")
    try:
        strategy = Strategy.model_validate(body.strategy_json)
    except Exception as exc:
        raise ValidationError(f"Strategy schema error: {exc}")
    vresult = validate_strategy(strategy)
    new_version = int(d["version"]) + 1
    val_status = "VALID" if vresult.valid else "INVALID"
    strategy.version = new_version
    mongo.strategy_definitions.update_one(
        {"strategy_id": strategy_id},
        {"$set": {
            "version": new_version, "strategy_json": strategy.model_dump(mode="json"),
            "validation_status": val_status, "updated_at": _now(),
        }},
    )
    return ok({"strategy_id": strategy_id, "version": new_version, "validation_status": val_status})


@router.post("/{strategy_id}/clone", status_code=201)
def clone_strategy(strategy_id: str, mongo: MongoDep, user: AuthUserDep) -> dict[str, Any]:
    """Clone a strategy (own or library) to the user's account."""
    d = mongo.strategy_definitions.find_one({"strategy_id": strategy_id})
    if d is None:
        raise NotFoundError(f"Strategy {strategy_id!r} not found.")
    new_id = f"st-{uuid.uuid4().hex[:12]}"
    now = _now()
    mongo.strategy_definitions.insert_one({
        "strategy_id": new_id, "owner_user_id": user.user_id,
        "name": f"{d['name']} (copy)", "version": 1,
        "strategy_json": d.get("strategy_json"),
        "is_library": False, "validation_status": "VALID",
        "created_at": now, "updated_at": now,
    })
    return ok({"strategy_id": new_id, "cloned_from": strategy_id})
