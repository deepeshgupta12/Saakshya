"""Structured payload contract for the AI layer (docs/14 §4, SPEC §6.6).

The model receives *only* a Payload — no raw price series, no news URLs, no forward
prices.  No field can carry a target / stop / return forecast (rejected at construction).
Grounding is enforced at output time by verify.py against this same object.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Keys that are categorically prohibited in the facts dict — they imply forward prices.
_FORBIDDEN_FACT_KEYS: frozenset[str] = frozenset({
    "target", "stop", "sl", "entry", "invalidation",
    "return_forecast", "price_target", "stop_loss", "target_price",
    "expected_return", "forecast_return",
})


class DataConfidence(str, Enum):
    HIGH       = "HIGH"
    MEDIUM     = "MEDIUM"
    LOW        = "LOW"
    SUPPRESSED = "SUPPRESSED"


class ForbiddenFieldError(ValueError):
    """Raised when a Payload contains a forward-looking / forbidden fact key."""


@dataclass(frozen=True)
class Subject:
    type: str           # "stock" | "market"
    symbol: str | None = None


@dataclass
class ComputedBlock:
    scanner:         str
    composite_score: float | None
    sub_scores:      dict[str, float] = field(default_factory=dict)
    facts:           dict[str, float | bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        bad = _FORBIDDEN_FACT_KEYS & set(self.facts)
        if bad:
            raise ForbiddenFieldError(
                f"Forbidden fact keys (forward-looking / RA-gated): {sorted(bad)}"
            )


@dataclass
class NewsSummary:
    headline:          str
    sentiment:         str   # POSITIVE | NEGATIVE | NEUTRAL
    confidence:        float
    source_url:        str | None = None
    published_at:      str | None = None
    entity_confidence: float | None = None


@dataclass
class Payload:
    intent:              str
    as_of_date:          str
    as_of_version:       str
    subject:             Subject
    computed:            ComputedBlock
    signal_tags:         list[str]       = field(default_factory=list)
    risk_flags:          list[str]       = field(default_factory=list)
    news_summaries:      list[NewsSummary] = field(default_factory=list)
    data_confidence:     DataConfidence  = DataConfidence.HIGH
    permitted_vocabulary: dict[str, str] = field(default_factory=dict)
    mode_context:        str             = "A"

    def to_model_dict(self) -> dict[str, Any]:
        """Canonical dict the model sees — used by to_model_json() and hash()."""
        return {
            "intent":       self.intent,
            "asOfDate":     self.as_of_date,
            "asOfVersion":  self.as_of_version,
            "subject":      {"type": self.subject.type, "symbol": self.subject.symbol},
            "computed": {
                "scanner":        self.computed.scanner,
                "compositeScore": self.computed.composite_score,
                "subScores":      self.computed.sub_scores,
                "facts":          self.computed.facts,
            },
            "signalTags":         self.signal_tags,
            "riskFlags":          self.risk_flags,
            "newsSummaries": [
                {
                    "headline":        ns.headline,
                    "sentiment":       ns.sentiment,
                    "confidence":      ns.confidence,
                    "sourceUrl":       ns.source_url,
                    "publishedAt":     ns.published_at,
                    "entityConfidence": ns.entity_confidence,
                }
                for ns in self.news_summaries
            ],
            "dataConfidence":     self.data_confidence.value,
            "permittedVocabulary": self.permitted_vocabulary,
            "modeContext":        self.mode_context,
        }

    def to_model_json(self) -> str:
        """Exact bytes sent to the model and stored in the audit log."""
        return json.dumps({"payload": self.to_model_dict()}, indent=2, ensure_ascii=False)

    def hash(self) -> str:
        """SHA-256 of the canonical JSON — stable across field ordering."""
        canon = json.dumps(self.to_model_dict(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canon.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Suppression predicate
# ---------------------------------------------------------------------------

def is_suppressed(payload: Payload) -> bool:
    """True when the payload lacks critical inputs — explainer must not call the model."""
    if payload.data_confidence in (DataConfidence.LOW, DataConfidence.SUPPRESSED):
        return True
    if payload.computed.composite_score is None:
        return True
    return "close" not in payload.computed.facts


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------

def build_stock_payload(
    symbol: str,
    indicators: dict[str, float | bool],
    scanner_result: dict[str, Any],
    risk_flags: list[str],
    news: list[dict[str, Any]] | None = None,
    *,
    as_of: str,
    as_of_version: str,
) -> Payload:
    """Build a stock payload from scanner + indicator outputs.

    Forbidden fact keys are silently dropped (the upstream scanner never produces
    targets/SLs in Mode A, but we guard defensively).
    """
    from app.ai.vocab import VOCAB  # noqa: PLC0415

    composite = (
        scanner_result.get("composite_score")
        or scanner_result.get("momentum_raw")
    )
    sub_scores: dict[str, float] = {}
    for k in ("momentum_raw", "priceMomentum", "maTrend", "volumeStrength", "relativeStrength"):
        v = scanner_result.get(k)
        if v is not None:
            sub_scores[k] = float(v)

    clean_facts = {k: v for k, v in indicators.items() if k not in _FORBIDDEN_FACT_KEYS}
    computed = ComputedBlock(
        scanner=scanner_result.get("scanner", "momentum"),
        composite_score=float(composite) if composite is not None else None,
        sub_scores=sub_scores,
        facts=clean_facts,
    )

    signal_tags: list[str] = list(scanner_result.get("signal_tags", []))

    # Data confidence from completeness of critical fields.
    # Keys must match technical_indicators column names (underscores, not camelCase).
    critical = {"close", "ret_21d", "sma_50"}
    missing  = critical - set(indicators)
    if len(missing) >= 2:
        confidence = DataConfidence.LOW
    elif len(missing) == 1:
        confidence = DataConfidence.MEDIUM
    else:
        confidence = DataConfidence.HIGH

    news_sums = _parse_news(news)

    return Payload(
        intent="explain_scanner_result",
        as_of_date=as_of,
        as_of_version=as_of_version,
        subject=Subject(type="stock", symbol=symbol),
        computed=computed,
        signal_tags=signal_tags,
        risk_flags=list(risk_flags),
        news_summaries=news_sums,
        data_confidence=confidence,
        permitted_vocabulary={k: VOCAB[k] for k in (signal_tags + risk_flags) if k in VOCAB},
        mode_context="A",
    )


def build_market_payload(
    indicators: dict[str, float | bool],
    risk_flags: list[str],
    news: list[dict[str, Any]] | None = None,
    *,
    as_of: str,
    as_of_version: str,
) -> Payload:
    """Build a market-level payload for the daily brief."""
    from app.ai.vocab import VOCAB  # noqa: PLC0415

    clean_facts = {k: v for k, v in indicators.items() if k not in _FORBIDDEN_FACT_KEYS}
    computed = ComputedBlock(
        scanner="market",
        composite_score=(
            float(clean_facts["market_breadth"]) if "market_breadth" in clean_facts else None
        ),
        sub_scores={},
        facts=clean_facts,
    )

    missing_critical = {"nifty_close", "advance_decline"} - set(indicators)
    if len(missing_critical) >= 2:
        confidence = DataConfidence.LOW
    elif missing_critical:
        confidence = DataConfidence.MEDIUM
    else:
        confidence = DataConfidence.HIGH

    return Payload(
        intent="explain_market_summary",
        as_of_date=as_of,
        as_of_version=as_of_version,
        subject=Subject(type="market"),
        computed=computed,
        signal_tags=[],
        risk_flags=list(risk_flags),
        news_summaries=_parse_news(news),
        data_confidence=confidence,
        permitted_vocabulary=dict(VOCAB),
        mode_context="A",
    )


def _parse_news(news: list[dict[str, Any]] | None) -> list[NewsSummary]:
    if not news:
        return []
    return [
        NewsSummary(
            headline=n.get("headline", ""),
            sentiment=n.get("sentiment", "NEUTRAL"),
            confidence=float(n.get("confidence", 0.5)),
            source_url=n.get("sourceUrl") or n.get("source_url"),
            published_at=n.get("publishedAt") or n.get("published_at"),
            entity_confidence=n.get("entityConfidence") or n.get("entity_confidence"),
        )
        for n in news
    ]
