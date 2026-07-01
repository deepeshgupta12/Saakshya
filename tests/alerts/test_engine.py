"""Tests for alert evaluation engine — event-reporting templates, RA-gated contract (docs/17)."""

from __future__ import annotations

from datetime import date

import pytest

from app.alerts.engine import (
    _make_dedup_key,
    _render_template,
    evaluate_scanner_deltas,
    run_alert_evaluation,
)
from app.alerts.models import AlertDefinition, AlertType, RA_GATED_TYPES


AS_OF = date(2024, 6, 1)


class TestRenderTemplate:
    """All templates must be past-tense event-reporting and end with 'Not investment advice.'"""

    def test_price_above_template(self):
        text = _render_template(AlertType.PRICE_ABOVE, {
            "symbol": "INFY", "close": 1520.0, "level": 1500.0, "date": "2024-06-01",
        })
        assert "INFY" in text
        assert "1520.0" in text
        assert "Not investment advice." in text

    def test_scanner_entry_template(self):
        text = _render_template(AlertType.SCANNER_ENTRY, {
            "symbol": "RELIANCE", "scanner": "momentum", "score": 82.5,
            "date": "2024-06-01",
        })
        assert "RELIANCE" in text
        assert "momentum" in text
        assert "Not investment advice." in text
        # Must describe event, not instruct
        assert "buy" not in text.lower()
        assert "sell" not in text.lower()

    def test_portfolio_risk_template(self):
        text = _render_template(AlertType.PORTFOLIO_RISK, {
            "symbol": "TATAMOTORS", "event": "closed below its 50-DMA", "date": "2024-06-01",
        })
        assert "closed below its 50-DMA" in text
        assert "Not investment advice." in text

    def test_all_non_ra_gated_templates_have_disclaimer(self):
        """Every non-RA-gated template must end with the disclaimer."""
        non_gated = [
            t for t in vars(AlertType).values()
            if isinstance(t, str) and t not in RA_GATED_TYPES
            and not t.startswith("_")
        ]
        for alert_type in non_gated:
            try:
                text = _render_template(alert_type, {
                    "symbol": "TEST", "date": "2024-06-01",
                    "scanner": "momentum", "score": 75.0,
                    "sector": "IT", "close": 100.0, "level": 90.0,
                    "sentiment": "NEGATIVE", "window": "7d",
                    "action_type": "BONUS", "detail": "1:1", "record_date": "2024-06-15",
                    "level_type": "resistance", "fast": "20", "slow": "50",
                    "cross_dir": "above", "adv": 1200, "dec": 350,
                    "pct_above_200dma": 60.3, "scanner_entries": 3,
                    "portfolio_notes": 1, "event": "closed below its 50-DMA",
                    "vol_ratio": 2.5, "rsi": 28.0, "direction": "below",
                    "day_change_pct": 3.2, "source": "Reuters", "ts": "10:30",
                    "headline": "Test news headline",
                })
                assert "Not investment advice." in text, (
                    f"Template for {alert_type!r} missing 'Not investment advice.'"
                )
            except RuntimeError:
                pytest.fail(f"Template render raised RuntimeError for non-RA-gated type: {alert_type}")


class TestRaGatedContract:
    """RA-gated types must NEVER be rendered or emitted in Mode A."""

    def test_stop_loss_zone_raises(self):
        with pytest.raises(RuntimeError, match="RA-gated"):
            _render_template(AlertType.STOP_LOSS_ZONE, {"symbol": "INFY", "date": "2024-06-01"})

    def test_target_zone_raises(self):
        with pytest.raises(RuntimeError, match="RA-gated"):
            _render_template(AlertType.TARGET_ZONE, {"symbol": "INFY", "date": "2024-06-01"})

    def test_run_alert_evaluation_drops_ra_gated(self):
        """run_alert_evaluation must emit ZERO events for RA-gated rule types."""
        ra_rule = AlertDefinition(
            alert_id   = "alrt-ra-001",
            user_id    = "user-001",
            type       = AlertType.STOP_LOSS_ZONE,
            ra_gated   = True,
            enabled    = True,
        )
        candidates = [{
            "alert_type": AlertType.STOP_LOSS_ZONE,
            "symbol":     "INFY",
            "date":       "2024-06-01",
        }]
        events = run_alert_evaluation([ra_rule], candidates, AS_OF)
        assert len(events) == 0, "RA-gated alert must produce zero events in Mode A."

    def test_ra_gated_types_frozenset_completeness(self):
        assert AlertType.STOP_LOSS_ZONE in RA_GATED_TYPES
        assert AlertType.TARGET_ZONE    in RA_GATED_TYPES
        assert AlertType.SCANNER_ENTRY  not in RA_GATED_TYPES


class TestScannerDeltas:
    def test_entry_candidate_generated(self):
        today = {"INFY": ["momentum"], "TCS": []}
        prior = {"INFY": [], "TCS": []}
        cands = evaluate_scanner_deltas(today, prior, {"INFY": {"momentum": 82.0}}, AS_OF)
        entry = [c for c in cands if c["alert_type"] == AlertType.SCANNER_ENTRY]
        assert any(c["symbol"] == "INFY" and c["scanner"] == "momentum" for c in entry)

    def test_exit_candidate_generated(self):
        today = {"INFY": []}
        prior = {"INFY": ["momentum"]}
        cands = evaluate_scanner_deltas(today, prior, {}, AS_OF)
        exits = [c for c in cands if c["alert_type"] == AlertType.SCANNER_EXIT]
        assert any(c["symbol"] == "INFY" for c in exits)

    def test_no_change_no_candidates(self):
        today = {"INFY": ["momentum"]}
        prior = {"INFY": ["momentum"]}
        cands = evaluate_scanner_deltas(today, prior, {}, AS_OF)
        assert len(cands) == 0


class TestDeduplication:
    def test_same_event_deduped(self):
        rule = AlertDefinition(
            alert_id = "alrt-001",
            user_id  = "user-001",
            type     = AlertType.SCANNER_ENTRY,
            scope    = {"symbol": "INFY", "scanner": "momentum"},
            enabled  = True,
        )
        cand = {
            "alert_type": AlertType.SCANNER_ENTRY,
            "symbol": "INFY",
            "scanner": "momentum",
            "score": 82.0,
            "date": "2024-06-01",
        }
        events1 = run_alert_evaluation([rule], [cand, cand], AS_OF)
        # Two identical candidates → only one event
        assert len(events1) == 1


class TestDeduplicationKey:
    def test_key_format(self):
        key = _make_dedup_key(AlertType.SCANNER_ENTRY, {
            "symbol": "INFY", "scanner": "momentum",
        }, AS_OF)
        assert key.startswith(AlertType.SCANNER_ENTRY)
        assert "INFY" in key
        assert AS_OF.isoformat() in key
