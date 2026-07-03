"""Regenerate-on-change summary cache (docs/14 §3, SPEC §6.8).

Keyed by (symbol, signal_category) where signal_category is a hash of the signal
fingerprint — sorted tags + risk flags + scanner name + composite-score band.
An unchanged signal category → cached summary served, no model call made.
"""

from __future__ import annotations

import hashlib
import json

import psycopg

from app.ai.payload import Payload


def signal_category(payload: Payload) -> str:
    """Stable 32-char hex key for the signal fingerprint of this payload.

    Changes when signal tags, risk flags, scanner name, or composite score band change.
    Does NOT change on minor price fluctuations within the same score band.
    """
    data = {
        "scanner": payload.computed.scanner,
        "tags":    sorted(payload.signal_tags),
        "flags":   sorted(payload.risk_flags),
        "band":    _score_band(payload.computed.composite_score),
    }
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:32]


def _score_band(score: float | None) -> int:
    """Map composite score to a 10-point band (0–9 for 0–100)."""
    if score is None:
        return -1
    return max(0, min(9, int(score // 10)))


def get_cached(
    symbol: str,
    category: str,
    conn: psycopg.Connection,
) -> str | None:
    """Return cached summary if one exists for (symbol, category), else None."""
    row = conn.execute(
        "SELECT summary FROM ai_summary_cache WHERE symbol = %s AND signal_category = %s",
        [symbol, category],
    ).fetchone()
    return str(row[0]) if row else None


def put_cached(
    symbol:        str,
    category:      str,
    summary:       str,
    audit_id:      str,
    as_of:         str,
    model_version: str,
    conn:          psycopg.Connection,
) -> None:
    """Upsert a summary into the cache for (symbol, category)."""
    conn.execute(
        """
        INSERT INTO ai_summary_cache
            (symbol, signal_category, summary, audit_id, as_of, model_version, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, now())
        ON CONFLICT (symbol, signal_category) DO UPDATE SET
            summary       = excluded.summary,
            audit_id      = excluded.audit_id,
            as_of         = excluded.as_of,
            model_version = excluded.model_version,
            created_at    = excluded.created_at
        """,
        [symbol, category, summary, audit_id, as_of, model_version],
    )
