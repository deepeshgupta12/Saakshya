"""Versioned blocked-phrase list for the output-time guardrail (SPEC §3.3, §6.9, docs/14 §10).

Enforcement is at *output time* on generated text — not only in the system prompt.
This list is versioned; a version bump is required to add or remove phrases.
It is exportable to the admin console and mirrored to the frontend (step 06).
"""

from __future__ import annotations

GUARDRAIL_VERSION = "v1"

# Exact phrases — matched case-insensitively, word-boundary optional.
BLOCKED_PHRASES: list[str] = [
    "guaranteed",
    "assured",
    "confirmed target",
    "target confirmed",
    "risk-free",
    "riskfree",
    "sure-shot",
    "sureshot",
    "multibagger",
    "multi-bagger",
    "buy now",
    "sell now",
    "best stock for you",
    "must invest",
    "no risk",
    "100% return",
    "assured return",
    "assured returns",
    "profit guaranteed",
    "zero risk",
    "invest now",
]

# Regex patterns — directive language patterns (case-insensitive, word-boundary where \b).
DIRECTIVE_PATTERNS: list[str] = [
    r"\bbuy\b",
    r"\bsell\b",
    r"stop[- ]?loss",
    r"entry\s+zone",
    r"target\s+zone",
    r"before\s+fresh\s+action",
    r"entry\s+level",
    r"price\s+target",
    r"profit\s+target",
    r"\bstraddle\b",
    r"book\s+profit",
    r"exit\s+now",
    r"recommended\s+stock",
    r"top\s+pick",
    r"hot\s+stock",
    r"initiate\s+(long|short)",
]


def blocked_phrases_export() -> dict[str, object]:
    """Return the full list for admin console / frontend mirror (step 06)."""
    return {
        "version":           GUARDRAIL_VERSION,
        "blocked_phrases":   BLOCKED_PHRASES,
        "directive_patterns": DIRECTIVE_PATTERNS,
    }
