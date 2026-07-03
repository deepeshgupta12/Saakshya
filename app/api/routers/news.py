"""News API endpoints — GET /api/news, GET /api/stocks/{symbol}/news (docs/10 §4/§10, M7).

Mode A: sentiment is a classification label, never a directive.
Below-SURFACING_THRESHOLD links are never surfaced here (is_surfaced=TRUE filter).
Auth required (Bearer JWT). Both endpoints are Premium-gated (plan != 'free' OR empty).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AuthUserDep, AsOfDep, DbDep
from app.api.envelope import ok, PageMeta
from app.news.resolver import SURFACING_THRESHOLD

router = APIRouter(tags=["news"])

_DISCLAIMER = (
    "Sentiment is a classification, not a trading signal. "
    "Link confidence reflects entity resolution quality. "
    "Saakshya provides analytics only — not investment advice (SEBI Mode A)."
)


def _fmt_article(row: tuple) -> dict[str, Any]:
    """Format a raw DB row (article_id, headline, url, published_at, source_id,
    symbol, link_confidence, sentiment_label, sentiment_score, sentiment_model_ver,
    impact_score, category, reliability) into the API article shape (docs/10 §4)."""
    (
        article_id, headline, url, published_at, source_id,
        symbol, link_confidence, sent_label, sent_score, sent_model,
        impact_score, category, source_rel,
    ) = row
    return {
        "article_id":    article_id,
        "headline":      headline,
        "url":           url,
        "published_at":  str(published_at) if published_at else None,
        "source_id":     source_id,
        "symbol":        symbol,
        "link_confidence": link_confidence,
        "sentiment": {
            "label":         sent_label or "neutral",
            "score":         sent_score,
            "model_version": sent_model or "0.1-heuristic",
        } if sent_label else None,
        "impact_score": impact_score,
        "category":     category,
        "disclaimer":   _DISCLAIMER,
    }


@router.get("/api/stocks/{symbol}/news")
def stock_news(
    symbol: str,
    user:   AuthUserDep,
    conn:   DbDep,
    as_of:  AsOfDep,
    limit:  int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """Resolved news for a single symbol — above-threshold links only (docs/10 §4).

    Premium gate: free-tier users receive an empty list (no 403 — graceful degradation).
    """
    sym = symbol.upper().strip()

    # Validate symbol exists.
    row = conn.execute(
        "SELECT primary_symbol FROM stock_master WHERE primary_symbol = %s", [sym]
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Symbol {sym!r} not found.")

    # Premium gate — free tier gets empty list (graceful, not 403).
    if user.plan == "free":
        return ok([], data_confidence="none")

    date_clause = "AND ni.published_at::DATE = %s" if as_of else ""
    date_args   = [as_of] if as_of else []

    rows = conn.execute(
        f"""
        SELECT
            ni.article_id, ni.headline, ni.url, ni.published_at, ni.source_id,
            nsl.symbol, nsl.link_confidence,
            nsl.sentiment_label, nsl.sentiment_score, nsl.sentiment_model_ver,
            nsl.impact_score, nsl.category,
            ns.reliability
        FROM news_stock_links nsl
        JOIN news_items   ni ON ni.article_id = nsl.article_id
        JOIN news_sources ns ON ns.source_id  = ni.source_id
        WHERE nsl.symbol      = %s
          AND nsl.is_surfaced = TRUE
          {date_clause}
        ORDER BY ni.published_at DESC NULLS LAST
        LIMIT %s OFFSET %s
        """,
        [sym] + date_args + [limit, offset],
    ).fetchall()

    total = conn.execute(
        f"""
        SELECT COUNT(*) FROM news_stock_links nsl
        JOIN news_items ni ON ni.article_id = nsl.article_id
        WHERE nsl.symbol = %s AND nsl.is_surfaced = TRUE {date_clause}
        """,
        [sym] + date_args,
    ).fetchone()[0]

    articles = [_fmt_article(r) for r in rows]
    return ok(articles, page=PageMeta(limit=limit, offset=offset, total=total))


@router.get("/api/news")
def market_news(
    user:   AuthUserDep,
    conn:   DbDep,
    as_of:  AsOfDep,
    limit:  int = 40,
    offset: int = 0,
) -> dict[str, Any]:
    """Market-wide news feed — above-threshold links only (docs/10 §10).

    Premium gate: free-tier returns empty list.
    """
    if user.plan == "free":
        return ok([], data_confidence="none")

    date_clause = "AND ni.published_at::DATE = %s" if as_of else ""
    date_args   = [as_of] if as_of else []

    rows = conn.execute(
        f"""
        SELECT
            ni.article_id, ni.headline, ni.url, ni.published_at, ni.source_id,
            nsl.symbol, nsl.link_confidence,
            nsl.sentiment_label, nsl.sentiment_score, nsl.sentiment_model_ver,
            nsl.impact_score, nsl.category,
            ns.reliability
        FROM news_stock_links nsl
        JOIN news_items   ni ON ni.article_id = nsl.article_id
        JOIN news_sources ns ON ns.source_id  = ni.source_id
        WHERE nsl.is_surfaced = TRUE
          {date_clause}
        ORDER BY ni.published_at DESC NULLS LAST
        LIMIT %s OFFSET %s
        """,
        date_args + [limit, offset],
    ).fetchall()

    total = conn.execute(
        f"""
        SELECT COUNT(*) FROM news_stock_links nsl
        JOIN news_items ni ON ni.article_id = nsl.article_id
        WHERE nsl.is_surfaced = TRUE {date_clause}
        """,
        date_args,
    ).fetchone()[0]

    articles = [_fmt_article(r) for r in rows]
    return ok(articles, page=PageMeta(limit=limit, offset=offset, total=total))
