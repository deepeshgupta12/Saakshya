"""Alerts API endpoints (docs/10 §6, docs/17, step 08).

GET    /v1/alerts             — list user's alert definitions
POST   /v1/alerts             — create alert definition
PUT    /v1/alerts/{id}        — update alert definition
DELETE /v1/alerts/{id}        — delete alert definition
GET    /v1/alerts/{id}/events — list fired events for an alert

Storage (D-059): alert definitions + events are MongoDB documents (condition / channels /
throttle stored natively, no JSON strings). Mode-A discipline: RA-gated types
(stop_loss_zone / target_zone) cannot be created — any attempt returns 403 MODE_GATED.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.alerts.models import RA_GATED_TYPES
from app.api.deps import AsOfDep, AuthUserDep, MongoDep
from app.api.envelope import ok
from app.api.errors import ModeGatedError, NotFoundError

router = APIRouter(prefix="/v1/alerts", tags=["alerts"])


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


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


@router.get("")
def list_alerts(mongo: MongoDep, user: AuthUserDep) -> dict[str, Any]:
    """List all alert definitions for the authenticated user."""
    docs = mongo.alert_definitions.find({"user_id": user.user_id}).sort("created_at", -1)
    data = [
        {
            "alert_id":   d["alert_id"],
            "type":       d["type"],
            "scope":      {"symbol": d.get("scope_symbol"), "scanner": d.get("scope_scanner"),
                           "sector": d.get("scope_sector")},
            "condition":  d.get("condition", {}),
            "cadence":    d.get("cadence", "EOD"),
            "channels":   d.get("channels", []),
            "throttle":   d.get("throttle", {}),
            "ra_gated":   bool(d.get("ra_gated", False)),
            "enabled":    bool(d.get("enabled", True)),
            "created_at": str(d["created_at"]),
        }
        for d in docs
    ]
    return ok(data)


@router.post("", status_code=201)
def create_alert(body: AlertCreate, mongo: MongoDep, user: AuthUserDep) -> dict[str, Any]:
    """Create an alert definition. RA-gated types return 403 in Mode A."""
    if body.type in RA_GATED_TYPES:
        raise ModeGatedError(
            f"Alert type '{body.type}' is gated behind RA registration (Mode B). "
            "Not available in Mode A."
        )
    alert_id = f"alrt-{uuid.uuid4().hex[:12]}"
    now = _now()
    mongo.alert_definitions.insert_one({
        "alert_id": alert_id, "user_id": user.user_id, "type": body.type,
        "scope_symbol": body.scope_symbol, "scope_scanner": body.scope_scanner,
        "scope_sector": body.scope_sector, "condition": body.condition,
        "cadence": body.cadence, "channels": body.channels, "throttle": body.throttle,
        "ra_gated": False, "enabled": True, "created_at": now, "updated_at": now,
    })
    return ok({"alert_id": alert_id}, data_confidence="high")


@router.put("/{alert_id}")
def update_alert(
    alert_id: str, body: AlertUpdate, mongo: MongoDep, user: AuthUserDep
) -> dict[str, Any]:
    """Update an alert definition (partial — only provided fields changed)."""
    if mongo.alert_definitions.find_one(
        {"alert_id": alert_id, "user_id": user.user_id}, {"alert_id": 1}
    ) is None:
        raise NotFoundError(f"Alert {alert_id!r} not found.")
    updates: dict[str, Any] = {"updated_at": _now()}
    if body.enabled is not None:
        updates["enabled"] = body.enabled
    if body.channels is not None:
        updates["channels"] = body.channels
    if body.throttle is not None:
        updates["throttle"] = body.throttle
    if body.condition is not None:
        updates["condition"] = body.condition
    mongo.alert_definitions.update_one({"alert_id": alert_id}, {"$set": updates})
    return ok({"alert_id": alert_id, "updated": True})


@router.delete("/{alert_id}")
def delete_alert(alert_id: str, mongo: MongoDep, user: AuthUserDep) -> dict[str, Any]:
    """Delete an alert definition."""
    result = mongo.alert_definitions.delete_one({"alert_id": alert_id, "user_id": user.user_id})
    if result.deleted_count == 0:
        raise NotFoundError(f"Alert {alert_id!r} not found.")
    return ok({"deleted": True, "alert_id": alert_id})


@router.get("/{alert_id}/events")
def list_alert_events(
    alert_id: str, mongo: MongoDep, as_of: AsOfDep, user: AuthUserDep
) -> dict[str, Any]:
    """Return fired alert events for an alert definition (most recent first)."""
    if mongo.alert_definitions.find_one(
        {"alert_id": alert_id, "user_id": user.user_id}, {"alert_id": 1}
    ) is None:
        raise NotFoundError(f"Alert {alert_id!r} not found.")
    docs = mongo.alert_events.find({"alert_id": alert_id}).sort("created_at", -1).limit(50)
    data = [
        {
            "event_id":         d["event_id"],
            "as_of_date":       str(d.get("as_of_date")),
            "payload":          d.get("payload"),
            "dedup_key":        d.get("dedup_key"),
            "rendered_text":    d.get("rendered_text"),
            "guardrail_status": d.get("guardrail_status"),
            "channels":         d.get("channels"),
            "delivery_log":     d.get("delivery_log"),
            "created_at":       str(d.get("created_at")),
        }
        for d in docs
    ]
    return ok(data, as_of=str(as_of))
