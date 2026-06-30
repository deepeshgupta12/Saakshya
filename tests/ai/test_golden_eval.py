"""Tests for app/ai/eval.py — golden-dataset evaluation suite.

Gate requirements (docs/14 §8):
  - fabrication_block_rate = 100%  (fabricated numbers must be caught)
  - directive_leak_rate    = 0%    (no directive language survives)
A failing rate blocks prompt/model promotion.
"""

from __future__ import annotations

from app.ai.eval import run_golden


class TestGoldenSuite:
    def test_golden_suite_runs_without_provider(self) -> None:
        report = run_golden(provider=None)
        assert report.total >= 2  # grounded + fabricated + directive fixtures

    def test_fabrication_block_rate_is_100_percent(self) -> None:
        report = run_golden(provider=None)
        assert report.fabrication_block_rate == 1.0, (
            f"Fabrication block rate = {report.fabrication_block_rate:.0%} — "
            f"failures: {report.failures}"
        )

    def test_directive_leak_rate_is_zero(self) -> None:
        report = run_golden(provider=None)
        assert report.directive_leak_rate == 0.0, (
            f"Directive leak rate = {report.directive_leak_rate:.0%} — "
            f"failures: {report.failures}"
        )

    def test_no_failures_in_report(self) -> None:
        report = run_golden(provider=None)
        assert report.failures == [], f"Golden failures: {report.failures}"

    def test_all_gates_pass(self) -> None:
        report = run_golden(provider=None)
        assert report.all_gates_pass(), (
            f"Golden eval failed — fabrication block={report.fabrication_block_rate:.0%}, "
            f"directive leak={report.directive_leak_rate:.0%}"
        )
