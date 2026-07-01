"""Natural-language → strategy JSON agent (Strategy Builder Agent, docs/19 §2, step 09).

Compliance rules (SPEC §5.17, docs/21):
  - The agent emits ONLY valid condition blocks over KNOWN catalog fields.
  - Unknown fields are rejected, not invented.
  - "buy" in the user prompt maps to entry_rule, not a live recommendation.
  - The generated artifact is a backtest/screener definition, never a trade call.
  - Output is shown to the user for confirmation as EDITABLE blocks — not auto-run.
  - Guardrail check enforced on any agent prose.

Provider: premium model (claude-opus-4-8 or gemma4:12b depending on config).
Audit: every NL→strategy attempt is logged.
"""

from __future__ import annotations

import json
import logging

from app.ai.guardrail import check as guardrail_check
from app.ai.provider import get_default_provider
from app.strategy.catalog import catalog_for_agent
from app.strategy.schema import Strategy
from app.strategy.validate import validate_strategy

log = logging.getLogger(__name__)

_NL_SYSTEM_PROMPT = """\
You are a strategy-building assistant for Saakshya, an evidence-first Indian equity analytics platform.

RULES (non-negotiable):
1. You ONLY emit condition blocks that reference fields from the provided CATALOG. Any field not in the catalog must be OMITTED — never invented.
2. The word "buy" in the user's text means an entry_rule (a condition that opens a screener match). It does NOT mean "recommend buying". You are building a SCREENER DEFINITION, not giving trade advice.
3. You NEVER include per-stock price targets, stop-loss levels, or entry levels as live outputs. If the user requests "buy at X" or "target Y", you convert "buy at X" to an entry condition (e.g., "close crosses above X" if X is a technical level) and include any target/stop ONLY inside exit_rules as backtest simulation parameters.
4. Your output is ALWAYS a valid JSON strategy object. No prose, no preamble, no explanation outside the JSON.
5. You NEVER add fields to the strategy JSON that are not in the schema.

SCHEMA:
{
  "name": str,
  "version": 1,
  "universe": {"market_cap_band": list[str] | null, "sector": list[str] | null, "include_delisted": false},
  "entry_rules": {"op": "AND"|"OR", "conditions": [<condition>, ...]},
  "exit_rules": {"op": "AND"|"OR", "conditions": [<condition>, ...]} | null,
  "disclaimer": "Past performance does not indicate future results."
}

CONDITION TYPES (only these — no others):
- {"type": "indicator", "expr": "<catalog_name>", "cmp": "<"|">"|"<="|">="|"=="|"!=", "value": <number>}
- {"type": "cross", "fast": "<catalog_name>", "dir": "crosses_above"|"crosses_below", "slow": "<catalog_name>"}
- {"type": "scanner", "scanner_name": "momentum"|"volume_breakout"|"rsi"|"moving_average", "cmp": "in"|"score_gt"|"score_lt", "value": <number>|null}
- {"type": "universe", "field": "market_cap_band"|"sector"|"index_member", "value": <str or list>}
- EXIT ONLY: {"type": "stop_loss", "method": "atr"|"pct"|"fixed", "k": <number>|null, "value": <number>|null}
- EXIT ONLY: {"type": "target", "method": "atr"|"pct"|"fixed", "k": <number>|null, "value": <number>|null}
- EXIT ONLY: {"type": "trailing_stop", "method": "atr"|"pct", "k": <number>}
- EXIT ONLY: {"type": "time", "max_holding_bars": <int>}

CATALOG:
{catalog_json}

OUTPUT: valid JSON strategy object ONLY. Nothing else.
"""


def nl_to_strategy(
    user_text: str,
    *,
    provider=None,
    conn=None,
) -> dict:
    """Convert natural-language strategy description to a validated strategy JSON.

    Returns:
        {
            "strategy":        <Strategy dict or None>,
            "validation":      <ValidationResult dict>,
            "guardrail_passed": bool,
            "raw_agent_output": str,
            "errors":          list[str],
        }

    The caller (API layer) MUST show the result to the user for confirmation
    before it can be saved or compiled to a scanner.
    """
    if provider is None:
        provider = get_default_provider()

    catalog_json = json.dumps(catalog_for_agent(), indent=2)
    system = _NL_SYSTEM_PROMPT.replace("{catalog_json}", catalog_json)

    raw_output = ""
    errors: list[str] = []

    try:
        result = provider.complete(
            prompt_id="nl_strategy_agent",
            prompt_version="v1",
            system=system,
            payload_json=json.dumps({"user_request": user_text}),
            model_tier="premium",
        )
        raw_output = result.text
    except Exception as exc:
        log.exception("NL strategy agent provider error")
        errors.append(f"Provider error: {exc}")
        return {
            "strategy": None,
            "validation": {"valid": False, "errors": errors, "warnings": []},
            "guardrail_passed": False,
            "raw_agent_output": raw_output,
            "errors": errors,
        }

    # Guardrail check on any prose around the JSON
    gr = guardrail_check(raw_output)
    guardrail_passed = gr.clean
    if not guardrail_passed:
        log.warning("NL strategy agent guardrail fail: %s", gr.blocked_phrases)
        errors.append(f"Guardrail blocked phrases: {gr.blocked_phrases}")

    # Parse JSON
    strategy_dict: dict | None = None
    strategy_obj:  Strategy | None = None
    validation_dict: dict = {"valid": False, "errors": [], "warnings": []}

    # Extract JSON block from output (model may wrap it in ```json ... ```)
    json_text = raw_output.strip()
    if "```" in json_text:
        parts = json_text.split("```")
        for part in parts:
            stripped = part.strip()
            if stripped.startswith("json"):
                stripped = stripped[4:].strip()
            if stripped.startswith("{"):
                json_text = stripped
                break

    try:
        strategy_dict = json.loads(json_text)
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid JSON from agent: {exc}")
        validation_dict["errors"] = errors
        return {
            "strategy": None,
            "validation": validation_dict,
            "guardrail_passed": guardrail_passed,
            "raw_agent_output": raw_output,
            "errors": errors,
        }

    # Pydantic validation
    try:
        strategy_obj = Strategy.model_validate(strategy_dict)
    except Exception as exc:
        errors.append(f"Strategy schema validation failed: {exc}")
        validation_dict["errors"] = errors
        return {
            "strategy": strategy_dict,
            "validation": validation_dict,
            "guardrail_passed": guardrail_passed,
            "raw_agent_output": raw_output,
            "errors": errors,
        }

    # Catalog validation
    vresult = validate_strategy(strategy_obj)
    validation_dict = {
        "valid":        vresult.valid,
        "errors":       vresult.errors,
        "warnings":     vresult.warnings,
        "backtest_only": vresult.backtest_only,
    }
    if vresult.errors:
        errors.extend(vresult.errors)

    return {
        "strategy":        strategy_obj.model_dump() if strategy_obj else strategy_dict,
        "validation":      validation_dict,
        "guardrail_passed": guardrail_passed,
        "raw_agent_output": raw_output,
        "errors":          errors,
    }
