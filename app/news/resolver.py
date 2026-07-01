"""Entity resolver — news → stock symbol with link_confidence (docs/18 §4, M7).

Approach (MVP, rule-based):
  1. Load primary_symbol + name from stock_master as the alias map.
  2. For each article headline + body, search for exact ticker, exact company name
     (case-insensitive), and stripped name matches (drops Ltd/Limited/Corp).
  3. Sum weighted signals (ticker exact=1.0, exact name=0.8, stripped name=0.6)
     clamped to [0,1].
  4. Apply SURFACING_THRESHOLD: below-threshold links go to review queue (is_surfaced=False).

This is a deterministic, auditable baseline. Finance-tuned NER-based resolution
replaces it in step 15 (ML phase).
"""

from __future__ import annotations

import re
import uuid
from typing import Any

SURFACING_THRESHOLD: float = 0.75


def _strip_suffix(name: str) -> str:
    """Remove common corporate suffixes from a company name."""
    return re.sub(
        r"\s+(limited|ltd|corp|corporation|industries|pvt|private|inc|co)\b",
        "",
        name.strip(),
        flags=re.IGNORECASE,
    ).strip()


def _load_alias_map(conn: Any) -> list[dict[str, Any]]:
    """Return list of {symbol, name, stripped} from stock_master."""
    rows = conn.execute("SELECT primary_symbol, name FROM stock_master").fetchall()
    return [
        {
            "symbol":  row[0],
            "name":    row[1].lower() if row[1] else "",
            "stripped": _strip_suffix(row[1]).lower() if row[1] else "",
        }
        for row in rows
    ]


def resolve_article(
    text: str,
    alias_map: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return list of {symbol, link_confidence} matches for ``text``."""
    text_lower = text.lower()
    results: dict[str, float] = {}

    for entry in alias_map:
        sym     = entry["symbol"]
        score   = 0.0

        # Exact ticker match (case-insensitive, word boundary).
        if re.search(r"\b" + re.escape(sym.lower()) + r"\b", text_lower):
            score = max(score, 1.0)

        # Exact company name match.
        if entry["name"] and entry["name"] in text_lower:
            score = max(score, 0.8)

        # Stripped name match (without Ltd/Corp).
        if entry["stripped"] and len(entry["stripped"]) >= 4 and entry["stripped"] in text_lower:
            score = max(score, 0.6)

        if score > 0:
            results[sym] = min(results.get(sym, 0.0) + score, 1.0)

    return [
        {"symbol": sym, "link_confidence": round(conf, 4)}
        for sym, conf in results.items()
    ]


def resolve_and_store(conn: Any, article_id: str, headline: str, body: str | None) -> list[str]:
    """Resolve article → symbols; write links to news_stock_links. Return surfaced symbols."""
    alias_map = _load_alias_map(conn)
    text      = headline + " " + (body or "")
    matches   = resolve_article(text, alias_map)

    surfaced_symbols: list[str] = []
    for m in matches:
        sym        = m["symbol"]
        confidence = m["link_confidence"]
        is_surfaced = confidence >= SURFACING_THRESHOLD
        link_id    = str(uuid.uuid4())

        # Skip if link already exists for this article + symbol pair.
        exists = conn.execute(
            "SELECT 1 FROM news_stock_links WHERE article_id = ? AND symbol = ?",
            [article_id, sym],
        ).fetchone()
        if exists:
            continue

        conn.execute(
            """
            INSERT OR IGNORE INTO news_stock_links
              (link_id, article_id, symbol, link_confidence, is_surfaced)
            VALUES (?, ?, ?, ?, ?)
            """,
            [link_id, article_id, sym, confidence, is_surfaced],
        )
        if is_surfaced:
            surfaced_symbols.append(sym)

    return surfaced_symbols
