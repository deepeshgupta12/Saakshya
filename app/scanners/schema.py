"""Canonical scanner output schema (docs/13 §5, §6).

Every scanner emits a ScannerResult. The AI-explanation payload is a subset of
ScannerResult containing only computed facts — no forward-looking fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.scanners.weights import ENGINE_VERSION, VALIDATION_STATUS, WEIGHTS_VERSION


@dataclass
class ScannerResult:
    """One scanner result record — Mode-A compliant (no entry/target/SL)."""

    scanner: str
    symbol: str
    stock_id: int
    as_of_date: date
    data_confidence: str = "MEDIUM"          # HIGH | MEDIUM | LOW
    composite_score: float | None = None      # 0–100; None if all sub-scores NEUTRAL
    sub_scores: dict[str, float] = field(default_factory=dict)
    facts: dict[str, float | str] = field(default_factory=dict)
    signal_tags: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    weights_version: str = WEIGHTS_VERSION
    validation_status: str = VALIDATION_STATUS
    as_of_version: int = 1
    engine_version: str = ENGINE_VERSION

    def ai_payload(self) -> dict[str, object]:
        """Return the AI-explanation payload — computed facts only, no forward fields.

        The runtime verification harness checks every number in AI output against
        this payload (docs/14, docs/13 §6).
        """
        return {
            "symbol":          self.symbol,
            "asOfDate":        self.as_of_date.isoformat(),
            "scanner":         self.scanner,
            "compositeScore":  self.composite_score,
            "subScores":       self.sub_scores,
            "signalTags":      self.signal_tags,
            "riskFlags":       self.risk_flags,
            "facts":           self.facts,
            "dataConfidence":  self.data_confidence,
            "weightsVersion":  self.weights_version,
            "validationStatus": self.validation_status,
        }
