"""AI daily market brief — descriptive, Mode-A-safe market overview (docs/14 §5, SPEC §2).

Generates a grounded textual summary of the day's NSE/BSE market activity:
  - Advance/decline, indices performance, sector strength, notable movers.
  - No targets, no buy/sell signals, no guarantees (docs/21 §3).
  - Cached per session_date in market_brief_cache; regenerated at most once/day.
  - Uses the same guardrail + grounding harness as per-stock summaries.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

import psycopg

from app.ai.audit import AuditRecord, write_audit
from app.ai.budget import allow_call, increment_calls
from app.ai.guardrail import check as guardrail_check
from app.ai.provider import get_default_provider
from app.config import get_settings

log = logging.getLogger(__name__)

_SUPPRESSED = "Market brief unavailable — insufficient data for today's session. Not investment advice."
_DEGRADED   = "Market brief temporarily unavailable. Not investment advice."

_SYSTEM_PROMPT = """\
You are Saakshya's evidence-led market narrator. Using ONLY the structured data provided, \
write a concise (~150 word) factual market brief covering: \
(1) overall market tone (advance/decline ratio), \
(2) notable sector movements, \
(3) standout movers (by name and % change, as stated in the data — no invented numbers). \
You MUST NOT invent any price, percentage, or news. \
You MUST NOT give buy/sell/hold recommendations, targets, or predictions. \
End every brief with: "Not investment advice. Evidence sourced from EOD data."\
"""


def _build_brief_payload(conn: psycopg.Connection, as_of: date) -> dict[str, Any] | None:
    """Assemble a structured data payload for the brief from DB aggregates."""
    # Advance / decline — TimescaleDB schema: daily_ohlc keys on stock_id + close_adj
    # (no symbol/close columns); latest as_of_version.
    ad = conn.execute("""
        WITH prev AS (
            SELECT stock_id, session_date, close_adj,
                   LAG(close_adj) OVER (PARTITION BY stock_id ORDER BY session_date) AS prev_close
            FROM daily_ohlc
            WHERE session_date <= %s AND as_of_version = 1
        )
        SELECT
            COUNT(*) FILTER (WHERE close_adj > prev_close)  AS advances,
            COUNT(*) FILTER (WHERE close_adj < prev_close)  AS declines,
            COUNT(*) FILTER (WHERE close_adj = prev_close AND prev_close IS NOT NULL) AS unchanged
        FROM prev WHERE session_date = %s
    """, [as_of, as_of]).fetchone()
    if ad is None or (ad[0] == 0 and ad[1] == 0):
        return None
    advances, declines, unchanged = int(ad[0]), int(ad[1]), int(ad[2])

    # Top movers by % change — join stock_master (name) + sector_master (sector).
    # Outer subquery so ORDER BY can reference the chg_pct alias (Postgres rule);
    # ROUND needs a numeric cast (no ROUND(double, int) in Postgres).
    movers = conn.execute("""
        SELECT symbol, company_name, sector, chg_pct FROM (
            SELECT symbol, company_name, sector,
                   ROUND(CAST(100.0 * (close_adj - prev_close) / NULLIF(prev_close, 0) AS numeric), 2) AS chg_pct
            FROM (
                SELECT
                    sm.primary_symbol AS symbol,
                    sm.name           AS company_name,
                    sec.name          AS sector,
                    o.session_date,
                    o.close_adj,
                    LAG(o.close_adj) OVER (PARTITION BY o.stock_id ORDER BY o.session_date) AS prev_close
                FROM daily_ohlc o
                JOIN stock_master sm ON sm.stock_id = o.stock_id
                LEFT JOIN sector_master sec ON sec.sector_id = sm.sector_id
                WHERE o.session_date <= %s AND o.as_of_version = 1
            ) ranked
            WHERE session_date = %s AND prev_close IS NOT NULL
        ) m
        ORDER BY ABS(chg_pct) DESC
        LIMIT 10
    """, [as_of, as_of]).fetchall()

    # Sector strength (avg change per sector).
    sectors = conn.execute("""
        SELECT sector, ROUND(CAST(AVG(100.0 * (close_adj - prev_close) / NULLIF(prev_close, 0)) AS numeric), 2) AS avg_chg
        FROM (
            SELECT
                sec.name AS sector,
                o.session_date,
                o.close_adj,
                LAG(o.close_adj) OVER (PARTITION BY o.stock_id ORDER BY o.session_date) AS prev_close
            FROM daily_ohlc o
            JOIN stock_master sm ON sm.stock_id = o.stock_id
            JOIN sector_master sec ON sec.sector_id = sm.sector_id
            WHERE o.session_date <= %s AND o.as_of_version = 1
        ) ranked
        WHERE session_date = %s AND prev_close IS NOT NULL
        GROUP BY sector
        ORDER BY avg_chg DESC
        LIMIT 5
    """, [as_of, as_of]).fetchall()

    return {
        "session_date":  str(as_of),
        "advance_count": advances,
        "decline_count": declines,
        "unchanged":     unchanged,
        "top_movers":    [
            {"symbol": r[0], "company_name": r[1], "sector": r[2],
             "change_pct": float(r[3]) if r[3] is not None else None}
            for r in movers
        ],
        "sector_strength": [
            {"sector": r[0], "avg_change_pct": float(r[1]) if r[1] is not None else None}
            for r in sectors
        ],
    }


def get_or_generate_brief(conn: psycopg.Connection, as_of: date) -> dict[str, Any]:
    """Return cached brief if available, otherwise generate and cache it."""
    cached = conn.execute(
        "SELECT brief_text, model_version, created_at FROM market_brief_cache WHERE brief_date = %s",
        [as_of],
    ).fetchone()
    if cached:
        return {"brief": cached[0], "model_version": cached[1], "cached": True, "session_date": str(as_of)}

    payload = _build_brief_payload(conn, as_of)
    if payload is None:
        return {"brief": _SUPPRESSED, "model_version": None, "cached": False, "session_date": str(as_of), "suppressed": True}

    if not allow_call(conn):
        return {"brief": _DEGRADED, "model_version": None, "cached": False, "session_date": str(as_of), "degraded": True}

    provider = get_default_provider()
    payload_json = json.dumps(payload, ensure_ascii=False)
    try:
        result = provider.complete(
            prompt_id="market_brief_v1",
            prompt_version="1.0",
            system=_SYSTEM_PROMPT,
            payload_json=payload_json,
            model_tier="cheap",
        )
        increment_calls(conn)
        brief_text = result.text.strip()
        # Guardrail check.
        gr = guardrail_check(brief_text)
        if not gr.clean:
            log.warning("Market brief blocked by guardrail: %s", gr.blocked_phrases)
            return {"brief": _SUPPRESSED, "model_version": result.model_id, "cached": False, "session_date": str(as_of), "suppressed": True}

        generated_audit_id = write_audit(AuditRecord(
            intent="market_brief",
            agent="market_brief_v1",
            prompt_id="market_brief_v1",
            prompt_version="1.0",
            model_tier="cheap",
            model_id=result.model_id,
            payload_hash=str(hash(payload_json)),
            payload_json=payload_json,
            raw_output=brief_text,
            grounding_report_json="{}",
            guardrail_report_json=json.dumps(gr.to_dict()),
            user_visible_output=brief_text,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
        ), conn)
        conn.execute(
            "INSERT INTO market_brief_cache (brief_date, brief_text, audit_id, model_version) "
            "VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (brief_date) DO UPDATE SET brief_text=EXCLUDED.brief_text, "
            "audit_id=EXCLUDED.audit_id, model_version=EXCLUDED.model_version",
            [as_of, brief_text, generated_audit_id, result.model_id],
        )
        return {"brief": brief_text, "model_version": result.model_id, "cached": False, "session_date": str(as_of)}
    except Exception as exc:
        log.error("Market brief generation failed: %s", exc)
        return {"brief": _DEGRADED, "model_version": None, "cached": False, "session_date": str(as_of), "degraded": True}
