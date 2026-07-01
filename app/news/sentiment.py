"""Finance-tuned sentiment classifier — MVP heuristic baseline (docs/18 §7, M7).

MVP (v0.1-heuristic): keyword-weighted scoring evaluated against the Indian-market
labelled set defined in docs/18 §7.1. The production classifier (v1.0+, step 15)
replaces this with a fine-tuned model that handles finance framing (e.g.
"misses estimates, stock rallies" is not a clean negative).

Contract:
  classify(text) → {label, score, model_version}
  - label ∈ {"positive", "neutral", "negative"}
  - score ∈ [0, 1] (confidence in the label)
  - score < LOW_CONF_THRESHOLD → label stays "neutral" (suppress-not-guess rule)
  - model_version is versioned so regression harness can detect classifier drift.
"""

from __future__ import annotations

import re
from typing import Any

MODEL_VERSION       = "0.1-heuristic"
LOW_CONF_THRESHOLD  = 0.55  # below this → neutral/uncertain (docs/18 §7.1)

# Finance-specific positive signals (not generic "good" — news-context tested).
_POSITIVE: list[tuple[float, list[str]]] = [
    (1.0, ["profit surges", "record profit", "beats estimates", "beats expectations",
           "q1 profit up", "q2 profit up", "q3 profit up", "q4 profit up",
           "revenue up", "turnaround", "upgrade", "order win", "bonus issue",
           "dividend declared", "buy-back", "buyback", "strategic investment"]),
    (0.7, ["profit rose", "profit rises", "revenue grew", "revenue growth",
           "strong results", "above estimates", "margin expansion", "new contract",
           "partnership", "expansion", "capacity addition", "ipo subscribed"]),
    (0.5, ["profit", "revenue", "growth", "margin", "positive", "increased",
           "higher", "up", "gains", "recovery"]),
]

# Finance-specific negative signals.
_NEGATIVE: list[tuple[float, list[str]]] = [
    (1.0, ["net loss", "profit warning", "misses estimates", "misses expectations",
           "profit falls sharply", "writedown", "write-off", "fraud", "scam",
           "default", "insolvency", "downgrade", "sebi action", "regulatory action"]),
    (0.7, ["profit fell", "profit falls", "loss widens", "margin compression",
           "layoffs", "debt rises", "revenue missed", "weak results",
           "below estimates", "plant shutdown", "probe launched"]),
    (0.5, ["loss", "decline", "lower", "fell", "missed", "weak",
           "concerns", "risk", "uncertainty", "delay", "dispute"]),
]


def _score_direction(text: str, rules: list[tuple[float, list[str]]]) -> float:
    """Sum matched phrase weights, clamped to 1.0."""
    text_l  = text.lower()
    total   = 0.0
    for weight, phrases in rules:
        for phrase in phrases:
            if re.search(r"\b" + re.escape(phrase) + r"\b", text_l):
                total += weight
                break  # one phrase per tier is enough
    return min(total, 1.0)


def classify(text: str) -> dict[str, Any]:
    """Return {label, score, model_version}."""
    pos = _score_direction(text, _POSITIVE)
    neg = _score_direction(text, _NEGATIVE)

    # Handle finance framing: if both positive and negative signals are strong,
    # emit "neutral" with moderate confidence (e.g. "misses estimates, stock rallies").
    if pos >= 0.7 and neg >= 0.7:
        return {"label": "neutral", "score": round(0.55, 4), "model_version": MODEL_VERSION}

    if pos > neg:
        raw_score = pos / (pos + neg + 0.001)
        label     = "positive" if raw_score >= LOW_CONF_THRESHOLD else "neutral"
        return {"label": label, "score": round(raw_score, 4), "model_version": MODEL_VERSION}

    if neg > pos:
        raw_score = neg / (pos + neg + 0.001)
        label     = "negative" if raw_score >= LOW_CONF_THRESHOLD else "neutral"
        return {"label": label, "score": round(raw_score, 4), "model_version": MODEL_VERSION}

    return {"label": "neutral", "score": round(0.5, 4), "model_version": MODEL_VERSION}


def update_link_sentiment(conn: Any, article_id: str, headline: str, body: str | None) -> None:
    """Classify sentiment for all surfaced links of an article and persist."""
    text   = headline + " " + (body or "")
    result = classify(text)

    conn.execute(
        """
        UPDATE news_stock_links
           SET sentiment_label     = ?,
               sentiment_score     = ?,
               sentiment_model_ver = ?
         WHERE article_id = ? AND is_surfaced = TRUE
        """,
        [result["label"], result["score"], result["model_version"], article_id],
    )
