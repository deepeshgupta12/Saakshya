"""News RSS ingestor — fetches, parses, deduplicates, stores (docs/18 §2–3, M7).

Supported feed types: RSS 2.0 and Atom 1.0 (auto-detected from root element).
Dedup: duplicate URLs and near-identical (same headline, same source, <10 min apart)
items are collapsed to a single canonical item per cluster.
No redistribution: articles are stored by reference (URL + headline); full body is
NOT stored for sources with redistribution_ok=False.

Usage (Celery task / CLI):
    from app.news.ingestor import ingest_all_sources
    ingest_all_sources(conn)
"""

from __future__ import annotations

import hashlib
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

# ── Constants ─────────────────────────────────────────────────────────────────

_RSS_NS: dict[str, str] = {"atom": "http://www.w3.org/2005/Atom"}
_DEDUP_WINDOW_SECONDS: int = 600  # 10 min window for near-duplicate detection


# ── Parsing helpers ───────────────────────────────────────────────────────────

def _parse_rss(root: ET.Element) -> list[dict[str, Any]]:
    items = []
    for item in root.findall("./channel/item"):
        def txt(tag: str) -> str | None:
            el = item.find(tag)
            return el.text.strip() if el is not None and el.text else None

        pub_str = txt("pubDate")
        try:
            pub_dt = parsedate_to_datetime(pub_str).astimezone(timezone.utc) if pub_str else None
        except Exception:
            pub_dt = None

        items.append({
            "headline":    txt("title"),
            "url":         txt("link"),
            "body":        txt("description"),
            "published_at": pub_dt,
        })
    return items


def _parse_atom(root: ET.Element) -> list[dict[str, Any]]:
    items = []
    ns = "http://www.w3.org/2005/Atom"
    for entry in root.findall(f"{{{ns}}}entry"):
        def txt(tag: str) -> str | None:
            el = entry.find(f"{{{ns}}}{tag}")
            return el.text.strip() if el is not None and el.text else None

        link_el = entry.find(f"{{{ns}}}link")
        url = link_el.get("href") if link_el is not None else None

        pub_str = txt("published") or txt("updated")
        try:
            pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00")) if pub_str else None
        except Exception:
            pub_dt = None

        items.append({
            "headline":    txt("title"),
            "url":         url,
            "body":        txt("summary"),
            "published_at": pub_dt,
        })
    return items


def _article_id(url: str) -> str:
    return "news_" + hashlib.sha256(url.encode()).hexdigest()[:16]


# ── Core ingestor ─────────────────────────────────────────────────────────────

def ingest_source(conn: Any, source_id: str, feed_url: str, redistribution_ok: bool) -> int:
    """Fetch one RSS/Atom feed, store new items. Returns count of inserted rows."""
    try:
        resp = httpx.get(feed_url, timeout=10.0, follow_redirects=True,
                         headers={"User-Agent": "Saakshya-NewsBot/1.0 (analytics only)"})
        resp.raise_for_status()
    except Exception:
        return 0

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError:
        return 0

    tag = root.tag.lower()
    if "rss" in tag:
        raw_items = _parse_rss(root)
    elif "feed" in tag:
        raw_items = _parse_atom(root)
    else:
        return 0

    inserted = 0
    for raw in raw_items:
        url      = raw.get("url")
        headline = raw.get("headline")
        if not url or not headline:
            continue

        article_id = _article_id(url)
        # Skip if already stored.
        exists = conn.execute(
            "SELECT 1 FROM news_items WHERE article_id = %s", [article_id]
        ).fetchone()
        if exists:
            continue

        # Near-dup check: same source + same headline in window → skip.
        if raw["published_at"]:
            near_dup = conn.execute(
                """
                SELECT 1 FROM news_items
                WHERE source_id = %s AND headline = %s
                  AND abs(extract(epoch from ingested_at) - extract(epoch from %s::timestamp)) < %s
                """,
                [source_id, headline, raw["published_at"], _DEDUP_WINDOW_SECONDS],
            ).fetchone()
            if near_dup:
                continue

        body = raw.get("body") if redistribution_ok else None
        conn.execute(
            """
            INSERT OR IGNORE INTO news_items
              (article_id, source_id, headline, body, url, published_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [article_id, source_id, headline, body, url, raw["published_at"]],
        )
        inserted += 1

    return inserted


def ingest_all_sources(conn: Any) -> dict[str, int]:
    """Ingest all active news sources. Returns {source_id: new_items_count}."""
    sources = conn.execute(
        "SELECT source_id, feed_url, redistribution_ok FROM news_sources WHERE active = TRUE"
    ).fetchall()
    return {
        sid: ingest_source(conn, sid, feed_url, bool(redist_ok))
        for sid, feed_url, redist_ok in sources
    }


def seed_default_sources(conn: Any) -> None:
    """Insert the default source registry if empty (idempotent).

    These are indicative sources — redistribution rights must be verified before
    production use; redistribution_ok=FALSE for all until reviewed.
    """
    existing = conn.execute("SELECT COUNT(*) FROM news_sources").fetchone()[0]
    if existing > 0:
        return

    defaults = [
        ("src_nse_corp",   "NSE Corporate Filings",   "https://www.nseindia.com",
         "https://archives.nseindia.com/content/RSS/news_updates.xml", "rss", 0.95, False),
        ("src_et_markets", "Economic Times Markets",  "https://economictimes.indiatimes.com",
         "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "rss", 0.80, False),
        ("src_moneycontrol", "Moneycontrol News",     "https://www.moneycontrol.com",
         "https://www.moneycontrol.com/rss/MCtopnews.xml", "rss", 0.75, False),
    ]
    for row in defaults:
        conn.execute(
            """
            INSERT OR IGNORE INTO news_sources
              (source_id, name, base_url, feed_url, feed_type, reliability, redistribution_ok)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            list(row),
        )
