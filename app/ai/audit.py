"""Immutable AI generation audit log (docs/14 §7, SPEC §6.6).

Every terminal outcome (publish / suppress / degrade) writes exactly one row.
No UPDATE or DELETE API exists — the log is append-only for incident replay and
SEBI Mode-B accountability.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import duckdb


@dataclass
class AuditRecord:
    intent:                str
    agent:                 str
    prompt_id:             str
    prompt_version:        str
    model_tier:            str
    model_id:              str
    payload_hash:          str
    payload_json:          str
    raw_output:            str | None = None
    grounding_report_json: str | None = None
    guardrail_report_json: str | None = None
    compliance_decision:   str        = "PASS"
    user_visible_output:   str | None = None
    suppressed:            bool       = False
    degraded:              bool       = False
    as_of_version:         str | None = None
    tokens_in:             int        = 0
    tokens_out:            int        = 0
    cost_usd:              float      = 0.0
    extra_fields:          dict[str, object] = field(default_factory=dict)


def write_audit(record: AuditRecord, conn: duckdb.DuckDBPyConnection) -> str:
    """Insert an audit record and return the generated audit_id."""
    audit_id  = f"gen-{uuid.uuid4().hex}"
    timestamp = datetime.now(tz=timezone.utc).isoformat()

    conn.execute(
        """
        INSERT INTO ai_audit_log (
            audit_id, timestamp, intent, agent, prompt_id, prompt_version,
            model_tier, model_id, payload_hash, payload_json,
            raw_output, grounding_report_json, guardrail_report_json,
            compliance_decision, user_visible_output,
            suppressed, degraded, as_of_version,
            tokens_in, tokens_out, cost_usd
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?
        )
        """,
        [
            audit_id, timestamp,
            record.intent, record.agent, record.prompt_id, record.prompt_version,
            record.model_tier, record.model_id, record.payload_hash, record.payload_json,
            record.raw_output, record.grounding_report_json, record.guardrail_report_json,
            record.compliance_decision, record.user_visible_output,
            record.suppressed, record.degraded, record.as_of_version,
            record.tokens_in, record.tokens_out, record.cost_usd,
        ],
    )
    return audit_id
