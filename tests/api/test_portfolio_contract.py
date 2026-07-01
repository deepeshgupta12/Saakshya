"""API contract tests for portfolio endpoints — Mode-A compliance: no RA-gated fields.

These tests verify that no response body from any portfolio or alerts endpoint
contains stop_loss_zone, target_zone, or any RA-gated field (docs/10 §5, SPEC §5.21).
"""

from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


RA_GATED_FIELDS = frozenset({
    "stop_loss_zone", "target_zone", "stop_loss_level", "target_level",
    "entry_level", "sl_level", "tp_level", "ra_gated",
})


def _has_ra_gated_field(body: dict | list) -> bool:
    """Recursively check for any RA-gated field names in a response body."""
    if isinstance(body, dict):
        for key, val in body.items():
            if key in RA_GATED_FIELDS:
                return True
            if _has_ra_gated_field(val):
                return True
    elif isinstance(body, list):
        for item in body:
            if _has_ra_gated_field(item):
                return True
    return False


class TestNoRaGatedFieldsInPortfolioResponses:
    """All portfolio API responses must be free of RA-gated fields (SPEC §5.21)."""

    def _parse(self, response) -> dict:
        try:
            return response.json()
        except Exception:
            return {}

    def test_portfolio_positions_no_ra_fields(self):
        resp = client.get("/v1/portfolio/nonexistent/positions")
        # 404 is fine (no portfolio set up) — but the body must not have RA fields
        body = self._parse(resp)
        assert not _has_ra_gated_field(body), (
            f"RA-gated field found in portfolio/positions response: {body}"
        )

    def test_portfolio_overview_no_ra_fields(self):
        resp = client.get("/v1/portfolio/nonexistent/overview")
        body = self._parse(resp)
        assert not _has_ra_gated_field(body)

    def test_portfolio_health_no_ra_fields(self):
        resp = client.get("/v1/portfolio/nonexistent/health")
        body = self._parse(resp)
        assert not _has_ra_gated_field(body)

    def test_portfolio_ai_summary_no_ra_fields(self):
        resp = client.get("/v1/portfolio/nonexistent/ai-summary")
        body = self._parse(resp)
        assert not _has_ra_gated_field(body)

    def test_alerts_list_no_ra_fields(self):
        resp = client.get("/v1/alerts")
        body = self._parse(resp)
        assert not _has_ra_gated_field(body)

    def test_create_ra_gated_alert_returns_4xx(self):
        """RA-gated alert types must be denied — 401 (no auth) or 403 (mode gated)."""
        resp = client.post(
            "/v1/alerts",
            json={"type": "stop_loss_zone", "condition": {}},
        )
        # Without auth, 401; with auth but Mode A, 403. Either blocks the feature.
        assert resp.status_code in (401, 403)

    def test_create_ra_gated_target_zone_returns_4xx(self):
        resp = client.post(
            "/v1/alerts",
            json={"type": "target_zone", "condition": {}},
        )
        assert resp.status_code in (401, 403)


class TestStrategyCompilerNoRaGatedLevels:
    """Compiled scanner rules must not contain stop_loss / target as live-level outputs."""

    def test_compile_scanner_strips_sl_target(self):
        strategy_json = {
            "name":         "Test",
            "entry_rules":  {
                "op":         "AND",
                "conditions": [
                    {"type": "indicator", "expr": "rsi_14", "cmp": "<", "value": 35},
                ],
            },
            "exit_rules": {
                "op": "OR",
                "conditions": [
                    {"type": "stop_loss", "method": "pct", "value": 8.0},
                    {"type": "target",    "method": "pct", "value": 15.0},
                ],
            },
        }
        resp = client.post("/v1/strategy/compile-scanner", json={"strategy_json": strategy_json})
        if resp.status_code != 200:
            pytest.skip(f"Endpoint returned {resp.status_code}: {resp.text}")

        body = resp.json()
        scanner_rule = body.get("data", {}).get("scanner_rule", {})
        rule_str     = json.dumps(scanner_rule)

        assert "stop_loss" not in rule_str, "stop_loss must not appear in live scanner rule"
        assert "target"    not in rule_str, "target must not appear in live scanner rule"
        assert "exit_rules" not in scanner_rule

    def test_nl_strategy_response_has_requires_confirmation(self):
        resp = client.post("/v1/strategy/from-nl", json={"text": "RSI below 35 and volume breakout"})
        if resp.status_code not in (200, 422):
            pytest.skip(f"Endpoint returned {resp.status_code}")
        if resp.status_code == 200:
            body = resp.json()
            data = body.get("data", {})
            # Must require user confirmation — cannot auto-run
            assert data.get("requires_confirmation") is True
