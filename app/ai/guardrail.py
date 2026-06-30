"""Output-time guardrail: enforce the versioned blocked-phrase list on generated text.

Runs AFTER the model generates; enforcement is not just in the system prompt (SPEC §6.9).
A non-clean report triggers regenerate→suppress in explainer.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.ai.blocked_phrases import (
    BLOCKED_PHRASES,
    DIRECTIVE_PATTERNS,
    GUARDRAIL_VERSION,
)

# Pre-compile all patterns for O(1) per-phrase matching.
_PHRASE_RX: list[tuple[str, re.Pattern[str]]] = [
    (phrase, re.compile(re.escape(phrase), re.IGNORECASE))
    for phrase in BLOCKED_PHRASES
]
_DIRECTIVE_RX: list[tuple[str, re.Pattern[str]]] = [
    (pattern, re.compile(pattern, re.IGNORECASE))
    for pattern in DIRECTIVE_PATTERNS
]


@dataclass
class GuardrailReport:
    clean:           bool
    blocked_phrases: list[str] = field(default_factory=list)
    directive_hits:  list[str] = field(default_factory=list)
    version:         str       = GUARDRAIL_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "clean":           self.clean,
            "blocked_phrases": self.blocked_phrases,
            "directive_hits":  self.directive_hits,
            "version":         self.version,
        }


def check(text: str) -> GuardrailReport:
    """Check generated text for blocked phrases and directive patterns.

    Returns a GuardrailReport; ``clean=False`` means the text must not reach the user.
    """
    blocked  = [phrase  for phrase, rx  in _PHRASE_RX    if rx.search(text)]
    directives = [pattern for pattern, rx in _DIRECTIVE_RX if rx.search(text)]
    return GuardrailReport(
        clean=not blocked and not directives,
        blocked_phrases=blocked,
        directive_hits=directives,
    )
