"""Runtime verification harness: every number and named fact in AI output must trace
to the payload (docs/14 §6, SPEC §6.6).

Algorithm:
1. Extract numeric tokens, NSE-style symbols, scanner tags from the generated text.
2. Window labels ("50-DMA", "20-day") are resolved against payload facts (sma50, etc.)
   rather than treated as free numbers — no false positives for descriptive phrasing.
3. Each extracted numeric must match a payload value within abs_tol=0.05 OR rel_tol=0.5%.
4. Each extracted tag must appear in payload.signal_tags, riskFlags, or permitted_vocabulary.
5. Any unmatched item → matched=False (regenerate trigger in explainer.py).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.ai.payload import Payload

# Numeric tokens: optional ₹ prefix, optional % or × suffix.
# Matches integers, floats, and comma-formatted numbers (1,650.0).
_NUMERIC_RX = re.compile(
    r'(?:₹|Rs\.?\s*)?'
    r'(-?\d[\d,]*(?:\.\d+)?)'
    r'(?:\s*(?:%|×|x))?',
    re.IGNORECASE,
)

# Window labels: "50-DMA", "200 DMA", "20-day", "52-week", "3-month".
_WINDOW_LABEL_RX = re.compile(
    r'\b(\d+)(?:\s*[-–]\s*)(?:day|DMA|week|month|bar|yr|year)\b',
    re.IGNORECASE,
)

# NSE-style tickers (all-caps, 3–15 chars, optionally suffixed .NS).
_SYMBOL_RX = re.compile(r'\b([A-Z][A-Z0-9]{2,14})(?:\.NS)?\b')

# Scanner/risk tags: SCREAMING_SNAKE_CASE with optional digits (e.g. ABOVE_50DMA).
_TAG_RX = re.compile(r'\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)\b')

_ABS_TOL = 0.05
_REL_TOL = 0.005   # 0.5 %

# Common all-caps words to ignore — not tickers or scanner tags.
_COMMON_CAPS = frozenset({
    "IN", "AT", "BY", "FOR", "OF", "IT", "IS", "OR", "TO", "AN",
    "THE", "AND", "NOT", "NSE", "BSE", "DMA", "ATR", "RSI", "EMA",
    "SMA", "NO", "ITS", "AS", "ON", "UP", "DOWN", "HIGH", "LOW",
    "MID", "AVG", "PCT", "VS", "YTD", "YOY", "QOQ",
})


@dataclass
class ExtractedFacts:
    numerics:     list[float]  = field(default_factory=list)
    symbols:      list[str]    = field(default_factory=list)
    tags:         list[str]    = field(default_factory=list)
    window_nums:  set[int]     = field(default_factory=set)


@dataclass
class GroundingReport:
    matched:         bool
    matched_items:   list[str] = field(default_factory=list)
    unmatched_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "matched":         self.matched,
            "matched_items":   self.matched_items,
            "unmatched_items": self.unmatched_items,
        }


def extract_facts(text: str) -> ExtractedFacts:
    """Extract numeric tokens, symbols, and tags from generated text."""
    # Find window label numbers first so "50" in "50-DMA" is not a free numeric.
    window_nums: set[int] = set()
    scrubbed = text
    for m in _WINDOW_LABEL_RX.finditer(text):
        window_nums.add(int(m.group(1)))
        scrubbed = scrubbed.replace(m.group(0), " ")

    # Extract tags before numeric scan so digits embedded in tag names (ABOVE_50DMA)
    # are not mistaken for free-standing numerics.
    tags = list({m.group(1) for m in _TAG_RX.finditer(text)})
    tag_scrubbed = scrubbed
    for tag in tags:
        tag_scrubbed = tag_scrubbed.replace(tag, " ")

    # Extract numerics from doubly-scrubbed text.
    numerics: list[float] = []
    for m in _NUMERIC_RX.finditer(tag_scrubbed):
        raw = m.group(1).replace(",", "")
        import contextlib  # noqa: PLC0415
        with contextlib.suppress(ValueError):
            numerics.append(float(raw))

    # Symbols — all-caps words not in the common stoplist.
    symbols = [
        m.group(1)
        for m in _SYMBOL_RX.finditer(text)
        if m.group(1) not in _COMMON_CAPS
    ]

    return ExtractedFacts(
        numerics=numerics,
        symbols=symbols,
        tags=tags,
        window_nums=window_nums,
    )


def _payload_numerics(payload: Payload) -> list[float]:
    nums: list[float] = []
    if payload.computed.composite_score is not None:
        nums.append(payload.computed.composite_score)
    for v in payload.computed.sub_scores.values():
        if isinstance(v, int | float):
            nums.append(float(v))
    for v in payload.computed.facts.values():
        if isinstance(v, int | float):
            nums.append(float(v))
    for ns in payload.news_summaries:
        nums.append(ns.confidence)
        if ns.entity_confidence is not None:
            nums.append(ns.entity_confidence)
    return nums


def _matches_any(value: float, candidates: list[float]) -> bool:
    for c in candidates:
        if abs(value - c) <= _ABS_TOL:
            return True
        if abs(c) > 0 and abs(value - c) / abs(c) <= _REL_TOL:
            return True
    return False


# Numerics that are analytically safe and not payload facts (year-like, pure ratios).
_SAFE_NUMERICS = frozenset({0.0, 1.0, 2.0, 100.0})
_YEAR_MIN, _YEAR_MAX = 1990.0, 2100.0


def verify(text: str, payload: Payload) -> GroundingReport:
    """Check that every extracted fact in *text* traces to *payload*.

    Returns GroundingReport(matched=True) when all extracted items are grounded.
    Any unmatched numeric or unknown scanner tag → matched=False.
    """
    extracted    = extract_facts(text)
    payload_nums = _payload_numerics(payload)

    all_tags = set(payload.signal_tags) | set(payload.risk_flags)
    all_tags |= set(payload.permitted_vocabulary.keys())

    subject_symbols: set[str] = set()
    if payload.subject.symbol:
        sym = payload.subject.symbol.removesuffix(".NS")
        subject_symbols.update({sym, payload.subject.symbol, sym + ".NS"})

    matched_items:   list[str] = []
    unmatched_items: list[str] = []

    # --- Numerics ---
    for num in extracted.numerics:
        # Skip window-label numerics already resolved (e.g. 50 from "50-DMA").
        if num == int(num) and int(num) in extracted.window_nums:
            continue
        # Skip years.
        if _YEAR_MIN <= num <= _YEAR_MAX and num == int(num):
            continue
        # Skip analytically safe constants.
        if num in _SAFE_NUMERICS:
            continue
        if _matches_any(num, payload_nums):
            matched_items.append(f"num:{num}")
        else:
            unmatched_items.append(f"num:{num}")

    # --- Tags ---
    for tag in extracted.tags:
        if tag in all_tags:
            matched_items.append(f"tag:{tag}")
        elif "_" in tag:
            # Only flag underscore-joined tags as scanner tags; plain caps words skipped.
            unmatched_items.append(f"tag:{tag}")

    # --- Symbols ---
    for sym in extracted.symbols:
        if sym in subject_symbols or sym + ".NS" in subject_symbols:
            matched_items.append(f"sym:{sym}")
        # Non-subject symbols are not flagged — the model may mention exchange names etc.

    return GroundingReport(
        matched=not unmatched_items,
        matched_items=matched_items,
        unmatched_items=unmatched_items,
    )
