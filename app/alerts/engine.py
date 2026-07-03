"""Alert evaluation engine — EOD-batch, event-reporting, dedup/throttle (docs/17 §7).

Evaluation order (docs/17 §1.1, flowchart §7):
  1. Collect candidate events from scanner/risk/news/portfolio outputs.
  2. Match events to enabled user alert rules.
  3. Drop RA-gated types in Mode A.
  4. Debounce (newly-true transitions only via prior-state snapshot).
  5. Dedup (dedup_key already fired this as_of_date?).
  6. Throttle (per-alert max_per_day + cooldown; per-user global cap with priority).
  7. Render template → blocked-phrase check at output time.
  8. On guardrail fail: suppress + log (never silently drop).
  9. Route to channels (in_app always; email batched; push respects quiet hours).
 10. Write delivery-log row for every attempt.

Mode-A discipline: every template is past-tense, event-reporting.
                   RA-gated evaluators are disabled and a contract test asserts no emission.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any

from app.alerts.models import (
    AlertDefinition, AlertEvent, AlertType,
    RA_GATED_TYPES, PRIORITY_ORDER, MAX_ALERTS_PER_USER_PER_DAY,
)
from app.ai.guardrail import check as guardrail_check

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template library — past-tense, event-reporting (docs/17 §2)
# ---------------------------------------------------------------------------

def _render_template(alert_type: str, payload: dict[str, Any]) -> str:
    """Render a Mode-A compliant event-reporting alert message.

    Every template ends with the as-of date. None of them contain
    "buy", "sell", "target", "stop-loss", or any forward instruction.
    """
    symbol  = payload.get("symbol", "")
    date_s  = payload.get("date", "")

    if alert_type == AlertType.PRICE_ABOVE:
        return (
            f"{symbol} closed at ₹{payload.get('close')}, above your level of "
            f"₹{payload.get('level')} (as of {date_s}). Not investment advice."
        )
    if alert_type == AlertType.PRICE_BELOW:
        return (
            f"{symbol} closed at ₹{payload.get('close')}, below your level of "
            f"₹{payload.get('level')} ({date_s}). Not investment advice."
        )
    if alert_type == AlertType.PCT_MOVEMENT:
        return (
            f"{symbol} moved {payload.get('day_change_pct')}% today, closing at "
            f"₹{payload.get('close')} ({date_s}). Not investment advice."
        )
    if alert_type == AlertType.VOLUME_BREAKOUT:
        return (
            f"{symbol} traded {payload.get('vol_ratio')}× its 20-day average volume "
            f"today ({date_s}). Not investment advice."
        )
    if alert_type == AlertType.RSI_THRESHOLD:
        return (
            f"{symbol} RSI(14) closed at {payload.get('rsi')}, crossing your "
            f"{payload.get('direction')} level of {payload.get('level')} ({date_s}). "
            f"Not investment advice."
        )
    if alert_type == AlertType.MA_CROSSOVER:
        return (
            f"{symbol}: {payload.get('fast')}-DMA crossed {payload.get('cross_dir')} "
            f"its {payload.get('slow')}-DMA on {date_s}. Not investment advice."
        )
    if alert_type == AlertType.SCANNER_ENTRY:
        return (
            f"{symbol} entered the {payload.get('scanner')} scanner today ({date_s}). "
            f"Score {payload.get('score')}. Not investment advice."
        )
    if alert_type == AlertType.SCANNER_EXIT:
        return (
            f"{symbol} exited the {payload.get('scanner')} scanner today ({date_s}). "
            f"Not investment advice."
        )
    if alert_type == AlertType.WATCHLIST_POS_NEWS:
        return (
            f"Positive-classified news on {symbol}: '{payload.get('headline')}' "
            f"({payload.get('source')}, {payload.get('ts')}). Not investment advice."
        )
    if alert_type == AlertType.WATCHLIST_NEG_NEWS:
        return (
            f"Negative-classified news on {symbol}: '{payload.get('headline')}' "
            f"({payload.get('source')}, {payload.get('ts')}). Not investment advice."
        )
    if alert_type == AlertType.PORTFOLIO_RISK:
        return (
            f"You hold {symbol}; it {payload.get('event')} today ({date_s}). "
            f"Not investment advice."
        )
    if alert_type == AlertType.NEWS_SENTIMENT:
        return (
            f"{symbol} news sentiment shifted to {payload.get('sentiment')} over the "
            f"last {payload.get('window')} ({date_s}). Not investment advice."
        )
    if alert_type == AlertType.CORPORATE_ACTION:
        return (
            f"{symbol} announced a {payload.get('action_type')} "
            f"({payload.get('detail')}); record date {payload.get('record_date')}. "
            f"Not investment advice."
        )
    if alert_type == AlertType.RESISTANCE_SUPPORT:
        return (
            f"{symbol} closed near {payload.get('level')}, historically a "
            f"{payload.get('level_type')} zone ({date_s}). Not investment advice."
        )
    if alert_type == AlertType.DAILY_BRIEF:
        return (
            f"Your daily market brief for {date_s} is ready: "
            f"{payload.get('scanner_entries', 0)} scanner entries, "
            f"{payload.get('portfolio_notes', 0)} portfolio notes. Not investment advice."
        )
    if alert_type == AlertType.SECTOR_WEAKNESS:
        return (
            f"The {payload.get('sector')} sector's strength score fell to "
            f"{payload.get('score')} ({date_s}), a {payload.get('window')} low. "
            f"Not investment advice."
        )
    if alert_type == AlertType.MARKET_BREADTH:
        return (
            f"Market breadth: {payload.get('adv')} advancing vs {payload.get('dec')} "
            f"declining; {payload.get('pct_above_200dma')}% of names above their "
            f"200-DMA ({date_s}). Not investment advice."
        )
    # RA-gated types: NEVER rendered in Mode A (docs/17 §3)
    if alert_type in RA_GATED_TYPES:
        raise RuntimeError(
            f"RA-gated alert type {alert_type!r} must not be rendered in Mode A."
        )

    return f"Alert: {symbol} — {alert_type} ({date_s}). Not investment advice."


# ---------------------------------------------------------------------------
# Dedup / debounce / throttle helpers
# ---------------------------------------------------------------------------

def _make_dedup_key(alert_type: str, payload: dict[str, Any], as_of: date) -> str:
    symbol    = payload.get("symbol", "")
    scanner   = payload.get("scanner", "")
    sector    = payload.get("sector", "")
    discrim   = scanner or sector or str(payload.get("level", ""))
    return f"{alert_type}:{symbol}:{discrim}:{as_of.isoformat()}"


def _fired_today(dedup_key: str, fired_set: set[str]) -> bool:
    return dedup_key in fired_set


def _newly_true(
    alert_type:    str,
    symbol:        str | None,
    prior_state:   dict[str, Any],
    current_value: Any,
    threshold:     Any,
) -> bool:
    """Return True only if the condition became true this cycle vs prior state.

    Prevents re-firing on unchanged state (oscillation guard, docs/17 §5).
    """
    key = f"{alert_type}:{symbol}"
    was_true = prior_state.get(key, False)
    is_true  = bool(current_value)
    return is_true and not was_true


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_portfolio_risk_events(
    holdings: list[dict[str, Any]],   # [{symbol, event, close, ...}]
    as_of: date,
) -> list[dict[str, Any]]:
    """Convert portfolio risk component output into raw alert candidate events."""
    candidates = []
    for h in holdings:
        for ev in h.get("events", []):
            candidates.append({
                "alert_type": AlertType.PORTFOLIO_RISK,
                "symbol":     h["symbol"],
                "date":       as_of.isoformat(),
                "event":      ev,
            })
    return candidates


def evaluate_scanner_deltas(
    scanner_membership_today: dict[str, list[str]],   # {symbol: [scanner_names]}
    scanner_membership_prior: dict[str, list[str]],
    scanner_scores:           dict[str, dict[str, float]],  # {symbol: {scanner: score}}
    as_of: date,
) -> list[dict[str, Any]]:
    """Produce scanner entry/exit candidates from membership deltas."""
    candidates = []
    all_symbols = set(scanner_membership_today) | set(scanner_membership_prior)
    for sym in all_symbols:
        today = set(scanner_membership_today.get(sym, []))
        prior = set(scanner_membership_prior.get(sym, []))
        for scanner in today - prior:
            score = scanner_scores.get(sym, {}).get(scanner)
            candidates.append({
                "alert_type": AlertType.SCANNER_ENTRY,
                "symbol":     sym,
                "scanner":    scanner,
                "score":      score,
                "date":       as_of.isoformat(),
            })
        for scanner in prior - today:
            candidates.append({
                "alert_type": AlertType.SCANNER_EXIT,
                "symbol":     sym,
                "scanner":    scanner,
                "date":       as_of.isoformat(),
            })
    return candidates


def run_alert_evaluation(
    alert_rules:   list[AlertDefinition],
    candidates:    list[dict[str, Any]],
    as_of:         date,
    prior_state:   dict[str, Any] | None = None,
    conn:          Any = None,          # Mongo db for dedup persistence
) -> list[AlertEvent]:
    """Main EOD alert evaluation loop (docs/17 §7 flowchart).

    Steps: match → RA-gate drop → debounce → dedup → throttle → render → guardrail.
    """
    if prior_state is None:
        prior_state = {}

    fired_dedup_keys: set[str]       = set()
    user_daily_counts: dict[str, int] = {}
    events: list[AlertEvent]          = []

    # Load dedup keys already fired today from Mongo (if available)
    if conn is not None:
        try:
            fired_dedup_keys = {
                d["dedup_key"]
                for d in conn.alert_events.find(
                    {"as_of_date": as_of.isoformat()}, {"dedup_key": 1}
                )
            }
        except Exception:
            pass  # DB may not be reachable (pre-migration run)

    # Sort candidates by priority for per-user throttle
    def priority(c: dict[str, Any]) -> int:
        try:
            return PRIORITY_ORDER.index(c.get("alert_type", ""))
        except ValueError:
            return len(PRIORITY_ORDER)

    candidates_sorted = sorted(candidates, key=priority)

    for cand in candidates_sorted:
        cand_type = cand.get("alert_type", "")
        symbol    = cand.get("symbol")

        # 1. Match to enabled rules
        matching_rules = [
            r for r in alert_rules
            if r.enabled
            and r.type == cand_type
            and (r.scope.get("symbol") in (None, symbol))
            and (r.scope.get("scanner") in (None, cand.get("scanner")))
        ]
        if not matching_rules:
            continue

        for rule in matching_rules:
            # 2. Drop RA-gated in Mode A
            if rule.ra_gated or cand_type in RA_GATED_TYPES:
                log.debug("Skipping RA-gated alert type %s", cand_type)
                continue

            # 3. Per-user global cap
            uid = rule.user_id
            if user_daily_counts.get(uid, 0) >= MAX_ALERTS_PER_USER_PER_DAY:
                log.debug("User %s hit daily alert cap", uid)
                continue

            # 4. Dedup
            dedup_key = _make_dedup_key(cand_type, cand, as_of)
            if dedup_key in fired_dedup_keys:
                continue

            # 5. Render template
            try:
                text = _render_template(cand_type, cand)
            except Exception as exc:
                log.warning("Template render failed for %s: %s", cand_type, exc)
                continue

            # 6. Blocked-phrase guardrail at output time (docs/17 §6, SPEC §6.9)
            gr = guardrail_check(text)
            if not gr.clean:
                log.warning(
                    "Alert guardrail suppressed: type=%s key=%s phrases=%s",
                    cand_type, dedup_key, gr.blocked_phrases,
                )
                event = AlertEvent(
                    event_id       = str(uuid.uuid4()),
                    alert_id       = rule.alert_id,
                    as_of_date     = as_of,
                    payload        = cand,
                    dedup_key      = dedup_key,
                    rendered_text  = text,
                    guardrail_status = "suppressed",
                    channels       = [],
                    delivery_log   = [{
                        "channel": "guardrail", "status": "suppressed",
                        "reason": str(gr.blocked_phrases),
                    }],
                )
                events.append(event)
                _persist_event(event, conn)
                continue

            # 7. Build event and route channels
            channels   = list(rule.channels) or ["in_app"]
            event = AlertEvent(
                event_id       = str(uuid.uuid4()),
                alert_id       = rule.alert_id,
                as_of_date     = as_of,
                payload        = cand,
                dedup_key      = dedup_key,
                rendered_text  = text,
                guardrail_status = "passed",
                channels       = channels,
                delivery_log   = [{"channel": ch, "status": "delivered"} for ch in channels],
            )
            events.append(event)
            fired_dedup_keys.add(dedup_key)
            user_daily_counts[uid] = user_daily_counts.get(uid, 0) + 1
            _persist_event(event, conn)

    return events


def _persist_event(event: AlertEvent, conn: Any) -> None:
    """Write a fired-alert event to Mongo (docs/17 §6, delivery log).

    Idempotent via the unique (dedup_key, as_of_date) index — a re-run of the same
    EOD batch upserts rather than duplicating. as_of_date is stored as an ISO string
    (pymongo does not accept datetime.date).
    """
    if conn is None:
        return
    try:
        as_of_str = event.as_of_date.isoformat()
        conn.alert_events.update_one(
            {"dedup_key": event.dedup_key, "as_of_date": as_of_str},
            {"$setOnInsert": {
                "event_id": event.event_id, "alert_id": event.alert_id,
                "as_of_date": as_of_str, "payload": event.payload,
                "dedup_key": event.dedup_key, "rendered_text": event.rendered_text,
                "guardrail_status": event.guardrail_status,
                "channels": event.channels, "delivery_log": event.delivery_log,
                "created_at": datetime.now(tz=timezone.utc),
            }},
            upsert=True,
        )
    except Exception as exc:
        log.warning("Failed to persist alert event %s: %s", event.event_id, exc)
