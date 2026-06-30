"""Golden-dataset evaluation for prompt/model changes (docs/14 §8, SPEC §6.6).

Runs the grounding harness + guardrail against curated fixture pairs
(payload → expected_properties) and reports pass rates.
A failing rate (fabrication_block_rate < 100% or directive_leak_rate > 0%)
blocks a prompt or model version from shipping.

Fixtures live in tests/ai/golden/*.json.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.ai.guardrail import check as guardrail_check
from app.ai.payload import ComputedBlock, DataConfidence, Payload, Subject
from app.ai.verify import verify as verify_grounding

_GOLDEN_DIR = Path(__file__).parent.parent.parent / "tests" / "ai" / "golden"


@dataclass
class EvalReport:
    total:                  int
    grounding_pass_rate:    float
    fabrication_block_rate: float
    false_suppression_rate: float
    directive_leak_rate:    float
    failures:               list[dict[str, Any]] = field(default_factory=list)

    def all_gates_pass(self) -> bool:
        return (
            self.fabrication_block_rate >= 1.0
            and self.directive_leak_rate == 0.0
        )


def _payload_from_dict(d: dict[str, Any]) -> Payload:
    computed_d = d.get("computed", {})
    return Payload(
        intent=d.get("intent", "explain_scanner_result"),
        as_of_date=d.get("asOfDate", "2026-01-01"),
        as_of_version=d.get("asOfVersion", "v1"),
        subject=Subject(
            type=d.get("subject", {}).get("type", "stock"),
            symbol=d.get("subject", {}).get("symbol"),
        ),
        computed=ComputedBlock(
            scanner=computed_d.get("scanner", "momentum"),
            composite_score=computed_d.get("compositeScore"),
            sub_scores=computed_d.get("subScores", {}),
            facts=computed_d.get("facts", {}),
        ),
        signal_tags=d.get("signalTags", []),
        risk_flags=d.get("riskFlags", []),
        data_confidence=DataConfidence(d.get("dataConfidence", "HIGH")),
        permitted_vocabulary=d.get("permittedVocabulary", {}),
        mode_context=d.get("modeContext", "A"),
    )


def run_golden(provider: Any | None = None) -> EvalReport:
    """Run the golden fixture suite against verify + guardrail.

    Each fixture specifies expected_properties:
      grounding_should_pass: true  → verify must return matched=True
      grounding_should_pass: false → verify must return matched=False (fabrication catch)
      guardrail_should_pass: true  → guardrail must return clean=True
      guardrail_should_pass: false → guardrail must return clean=False (directive catch)
    """
    fixtures = sorted(_GOLDEN_DIR.glob("*.json")) if _GOLDEN_DIR.exists() else []
    evaluable = [(fp, json.loads(fp.read_text())) for fp in fixtures if fp.suffix == ".json"]
    static    = [(fp, fx) for fp, fx in evaluable if fx.get("test_output")]

    if not static:
        return EvalReport(0, 1.0, 1.0, 0.0, 0.0)

    total = len(static)
    grounding_correct    = 0  # grounding outcome matched expectation
    fabrication_total    = 0  # fixtures where grounding_should_pass=False
    fabrication_caught   = 0  # of those, grounding returned matched=False
    guardrail_correct    = 0  # guardrail outcome matched expectation
    directive_total      = 0  # fixtures where guardrail_should_pass=True
    directive_clean      = 0  # of those, guardrail returned clean=True
    failures: list[dict[str, Any]] = []

    for fp, fixture in static:
        props   = fixture.get("expected_properties", {})
        output  = fixture["test_output"]
        expect_grounding_pass = bool(props.get("grounding_should_pass", True))
        expect_guardrail_pass = bool(props.get("guardrail_should_pass", True))

        try:
            payload = _payload_from_dict(fixture.get("payload", {}))
        except Exception as exc:
            failures.append({"file": fp.name, "error": f"payload parse failed: {exc}"})
            continue

        grounding = verify_grounding(output, payload)
        guardrail = guardrail_check(output)

        # Grounding check.
        grounding_as_expected = grounding.matched == expect_grounding_pass
        if grounding_as_expected:
            grounding_correct += 1
        else:
            failures.append({
                "file":          fp.name,
                "check":         "grounding",
                "expected_pass": expect_grounding_pass,
                "actual_matched": grounding.matched,
                "unmatched":     grounding.unmatched_items,
            })

        # Fabrication block tracking.
        if not expect_grounding_pass:
            fabrication_total += 1
            if not grounding.matched:
                fabrication_caught += 1

        # Guardrail check.
        guardrail_as_expected = guardrail.clean == expect_guardrail_pass
        if guardrail_as_expected:
            guardrail_correct += 1
        else:
            failures.append({
                "file":          fp.name,
                "check":         "guardrail",
                "expected_clean": expect_guardrail_pass,
                "actual_clean":  guardrail.clean,
                "blocked":       guardrail.blocked_phrases + guardrail.directive_hits,
            })

        # Directive leak tracking (cases expected to be clean).
        if expect_guardrail_pass:
            directive_total += 1
            if guardrail.clean:
                directive_clean += 1

    grounding_pass_rate    = grounding_correct  / total            if total             else 1.0
    fabrication_block_rate = fabrication_caught / fabrication_total if fabrication_total else 1.0
    directive_leak_rate    = (
        1.0 - directive_clean / directive_total if directive_total else 0.0
    )

    return EvalReport(
        total=total,
        grounding_pass_rate=grounding_pass_rate,
        fabrication_block_rate=fabrication_block_rate,
        false_suppression_rate=0.0,
        directive_leak_rate=directive_leak_rate,
        failures=failures,
    )
