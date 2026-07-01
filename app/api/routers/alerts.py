"""Alerts API endpoints (docs/10 §6, docs/17, step 08).

GET    /v1/alerts             — list user's alert definitions
POST   /v1/alerts             — create alert definition
PUT    /v1/alerts/{id}        — update alert definition
DELETE /v1/alerts/{id}        — delete alert definition
GET    /v1/alerts/{id}/events — list fired events for an alert

Mode-A discipline: no RA-gated types (stop_loss_zone / target_zone) can be
created via this API in Mode A — any attempt returns 403 MODE_GATED.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Response
from pydantic import BaseModel

from app.alerts.models import AlertDefinition, AlertType, RA_GATED_TYPES
from app.api.deps import AsOfDep, AuthUserDep, DbDep
from app.api.envelope import ok
from app.api.errors import ModeGatedError, NotFoundError

router = APIRouter(prefix="/v1/alerts", tags=["alerts"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class AlertCreate(BaseModel):
    type:          str
    scope_symbol:  str | None = None
    scope_scanner: str | None = None
    scope_sector:  str | None = None
    condition:     dict[str, Any] = {}
    cadence:       str = "EOD"
    channels:      list[str] = ["in_app"]
    throttle:      dict[str, Any] = {"max_per_day": 3, "cooldown_minutes": 720}


class AlertUpdate(BaseModel):
    enabled:   bool | None = None
    channels:  list[str] | None = None
    throttle:  dict[str, Any] | None = None
    condition: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
def list_alerts(
    conn: DbDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    """List all enabled alert definitions for the authenticated user."""
    rows = conn.execute(
        "SELECT alert_id, type, scope_symbol, scope_scanner, scope_sector, "
        "condition_json, cadence, channels_json, throttle_json, ra_gated, enabled, created_at "
        "FROM alert_definitions WHERE user_id = ? ORDER BY created_at DESC",
        [user.user_id],
    ).fetchall()

    data = [
        {
            "alert_id":     r[0],
            "type":         r[1],
            "scope":        {
                "symbol":  r[2],
                "scanner": r[3],
                "sector":  r[4],
            },
            "condition":   _safe_json(r[5]),
            "cadence":     r[6],
            "channels":    _safe_json(r[7]),
            "throttle":    _safe_json(r[8]),
            "ra_gated":    bool(r[9]),
            "enabled":     bool(r[10]),
            "created_at":  str(r[11]),
        }
        for r in rows
    ]
    return ok(data)


@router.post("", status_code=201)
def create_alert(
    body: AlertCreate,
    conn: DbDep,
    user: AuthUserDep,
) -> dict[str, Any]:
    """Create an alert definition.

    RA-gated types (stop_loss_zone, target_zone) return 403 in Mode A.
    """
    if body.type in RA_GATED_TYPES:
        raise ModeGatedError(
            f"Alert type '{body.type}' is gated behind RA registration (Mode B). "
            "Not available in Mode A."
        )

    alert_id = f"alrt-{uuid.uuid4().hex[:12]}"
    conn.execute(
        "INSERT INTO alert_definitions "
        "(alert_id, user_id, type, scope_symbol, scope_scanner, scope_sector, "
        "condition_json, cadence, channels_json, throttle_json, ra_gated, enabled) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            alert_id, user.user_id, body.type,
            body.scope_symbol, body.scope_scanner, body.scope_sector,
            json.dumps(body.condition), body.cadence,
            json.dumps(body.channels), json.dumps(body.throttle),
            False, True,
        ],
    )
    return ok({"alert_id": alert_id}, data_confidence="high")


@router.put("/{alert_id}")
def update_alert(
    alert_id: str,
    body:     AlertUpdate,
    conn:     DbDep,
    user:     AuthUserDep,
) -> dict[str, Any]:
    """Update an alert definition (partial update — only provided fields changed)."""
    row = conn.execute(
        "SELECT alert_id FROM alert_definitions WHERE alert_id = ? AND user_id = ?",
        [alert_id, user.user_id],
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Alert {alert_id!r} not found.")

    if body.enabled is not None:
        conn.execute(
            "UPDATE alert_definitions SET enabled = ?, updated_at = now() WHERE alert_id = ?",
            [body.enabled, alert_id],
        )
    if body.channels is not None:
        conn.execute(
            "UPDATE alert_definitions SET channels_json = ?, updated_at = now() WHERE alert_id = ?",
            [json.dumps(body.channels), alert_id],
        )
    if body.throttle is not None:
        conn.execute(
            "UPDATE alert_definitions SET throttle_json = ?, updated_at = now() WHERE alert_id = ?",
            [json.dumps(body.throttle), alert_id],
        )
    if body.condition is not None:
        conn.execute(
            "UPDATE alert_definitions SET condition_json = ?, updated_at = now() WHERE alert_id = ?",
            [json.dumps(body.condition), alert_id],
        )

    return ok({"alert_id": alert_id, "updated": True})


@router.delete("/{alert_id}")
def delete_alert(
    alert_id: str,
    conn:     DbDep,
    user:     AuthUserDep,
) -> dict[str, Any]:
    """Delete an alert definition."""
    row = conn.execute(
        "SELECT alert_id FROM alert_definitions WHERE alert_id = ? AND user_id = ?",
        [alert_id, user.user_id],
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Alert {alert_id!r} not found.")
    conn.execute("DELETE FROM alert_definitions WHERE alert_id = ?", [alert_id])
    return ok({"deleted": True, "alert_id": alert_id})


@router.get("/{alert_id}/events")
def list_alert_events(
    alert_id: str,
    conn:     DbDep,
    as_of:    AsOfDep,
    user:     AuthUserDep,
) -> dict[str, Any]:
    """Return fired alert events for an alert definition (most recent first)."""
    # Verify ownership
    row = conn.execute(
        "SELECT alert_id FROM alert_definitions WHERE alert_id = ? AND user_id = ?",
        [alert_id, user.user_id],
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Alert {alert_id!r} not found.")

    rows = conn.execute(
        "SELECT event_id, as_of_date, payload_json, dedup_key, rendered_text, "
        "guardrail_status, channels_json, delivery_log_json, created_at "
        "FROM alert_events WHERE alert_id = ? ORDER BY created_at DESC LIMIT 50",
        [alert_id],
    ).fetchall()

    data = [
        {
            "event_id":        r[0],
            "as_of_date":      str(r[1]),
            "payload":         _safe_json(r[2]),
            "dedup_key":       r[3],
            "rendered_text":   r[4],
            "guardrail_status": r[5],
            "channels":        _safe_json(r[6]),
            "delivery_log":    _safe_json(r[7]),
            "created_at":      str(r[8]),
        }
        for r in rows
    ]
    return ok(data, as_of=str(as_of))


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
