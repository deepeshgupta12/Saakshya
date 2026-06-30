"""Tests for app/ai/guardrail.py — blocked-phrase and directive-pattern enforcement."""

from __future__ import annotations

import pytest

from app.ai.guardrail import check

SPEC_WORKED_EXAMPLE = (
    "TATAMOTORS.NS has risen 21.4% over the past three months and trades above its "
    "50-day moving average. Volume has expanded roughly 2.4 times its 20-day average. "
    "Short-term volatility is elevated, with ATR at 3.4% of price. Not investment advice."
)


class TestBlockedPhrases:
    @pytest.mark.parametrize("phrase", [
        "guaranteed",
        "assured",
        "confirmed target",
        "risk-free",
        "sure-shot",
        "multibagger",
        "buy now",
        "sell now",
        "best stock for you",
        "must invest",
        "no risk",
        "100% return",
        "assured returns",
        "profit guaranteed",
        "zero risk",
        "invest now",
    ])
    def test_seed_phrase_blocked(self, phrase: str) -> None:
        report = check(f"This stock has {phrase} potential.")
        assert not report.clean
        assert phrase in report.blocked_phrases or len(report.blocked_phrases) > 0


class TestDirectivePatterns:
    def test_buy_directive_blocked(self) -> None:
        report = check("You should buy this stock at 500.")
        assert not report.clean
        assert len(report.directive_hits) > 0

    def test_sell_directive_blocked(self) -> None:
        report = check("Traders should sell above resistance.")
        assert not report.clean

    def test_stop_loss_blocked(self) -> None:
        report = check("Place a stop-loss at 450.")
        assert not report.clean

    def test_entry_zone_blocked(self) -> None:
        report = check("The entry zone is between 480 and 500.")
        assert not report.clean

    def test_before_fresh_action_blocked(self) -> None:
        report = check("Monitor before fresh action is taken.")
        assert not report.clean

    def test_initiate_long_blocked(self) -> None:
        report = check("Initiate long positions in this sector.")
        assert not report.clean


class TestDescriptiveTextAllowed:
    def test_spec_worked_example_passes(self) -> None:
        report = check(SPEC_WORKED_EXAMPLE)
        assert report.clean
        assert not report.blocked_phrases
        assert not report.directive_hits

    def test_scanner_membership_language_passes(self) -> None:
        report = check(
            "RELIANCE.NS appears in the momentum scanner. "
            "The stock is trading above its 50-day moving average. "
            "Not investment advice."
        )
        assert report.clean

    def test_elevated_volatility_passes(self) -> None:
        report = check(
            "Short-term volatility is elevated. "
            "Volume has expanded relative to the 20-day average. "
            "Not investment advice."
        )
        assert report.clean

    def test_not_investment_advice_not_blocked(self) -> None:
        report = check("Not investment advice.")
        assert report.clean


class TestReportStructure:
    def test_report_has_version(self) -> None:
        report = check("anything")
        assert report.version

    def test_clean_report_on_safe_text(self) -> None:
        report = check("The stock appears in the momentum scanner. Not investment advice.")
        assert report.clean
        assert report.blocked_phrases == []
        assert report.directive_hits == []
