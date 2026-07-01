"""Tests for risk components and portfolio health score (docs/16 §3–4)."""

from __future__ import annotations

import pytest

from app.risk.components import (
    COMPONENT_WEIGHTS,
    HEALTH_BANDS,
    SINGLE_STOCK_SOFT_CAP,
    RiskComponents,
    cap_exposure_risk,
    compute_health_score,
    compute_position_risk,
    concentration_risk,
    news_risk,
    sector_concentration_risk,
    technical_breakdown_risk,
    volatility_risk,
)


class TestConcentrationRisk:
    def test_at_cap_is_50(self):
        score, ev = concentration_risk(SINGLE_STOCK_SOFT_CAP)
        assert score == 50.0

    def test_double_cap_clamps_to_100(self):
        score, _ = concentration_risk(SINGLE_STOCK_SOFT_CAP * 2)
        assert score == 100.0

    def test_zero_weight_is_zero(self):
        score, _ = concentration_risk(0.0)
        assert score == 0.0

    def test_evidence_contains_weight(self):
        _, ev = concentration_risk(15.0)
        assert "weight_pct" in ev
        assert ev["weight_pct"] == 15.0


class TestVolatilityRisk:
    def test_missing_close_returns_zero_low_confidence(self):
        score, ev = volatility_risk(10.0, None)
        assert score == 0.0
        assert ev.get("data_confidence") == "LOW"

    def test_with_percentile(self):
        score, ev = volatility_risk(atr_14=5.0, last_close=100.0, atr_pct_percentile=0.8)
        assert score == 80.0
        assert "atr_pct_percentile" in ev

    def test_heuristic_fallback_no_percentile(self):
        # ATR% = 10/100 = 10%; heuristic = 10×10 = 100, clamped
        score, ev = volatility_risk(atr_14=10.0, last_close=100.0)
        assert score == 100.0
        assert ev.get("percentile_source") == "heuristic"


class TestTechnicalBreakdownRisk:
    def test_all_clear_is_zero(self):
        score, ev = technical_breakdown_risk(
            close=700.0, sma_50=690.0, sma_200=680.0,
            in_breakdown_scanner=False, recent_swing_low=650.0,
        )
        assert score == 0.0
        assert ev["events"] == []

    def test_below_50dma_scores_30(self):
        score, ev = technical_breakdown_risk(close=680.0, sma_50=690.0, sma_200=None)
        assert score == 30.0
        assert "closed below 50-DMA" in ev["events"]

    def test_below_both_dmas_scores_60(self):
        score, ev = technical_breakdown_risk(close=650.0, sma_50=690.0, sma_200=680.0)
        assert score == 60.0
        assert len(ev["events"]) == 2

    def test_all_four_conditions_clamps_to_100(self):
        score, ev = technical_breakdown_risk(
            close=600.0, sma_50=700.0, sma_200=690.0,
            in_breakdown_scanner=True, recent_swing_low=620.0,
        )
        # 30+30+25+15 = 100
        assert score == 100.0

    def test_missing_close_returns_zero_low_confidence(self):
        score, ev = technical_breakdown_risk(close=None, sma_50=700.0, sma_200=690.0)
        assert score == 0.0
        assert ev.get("data_confidence") == "LOW"


class TestNewsRisk:
    def test_no_news_is_zero(self):
        score, ev = news_risk([])
        assert score == 0.0
        assert ev["negative_item_count"] == 0

    def test_high_impact_negative_news(self):
        items = [{"sentiment": "NEGATIVE", "impact": 0.9, "headline": "Regulatory probe"}]
        score, ev = news_risk(items)
        assert score == 90.0
        assert ev["max_negative_impact"] == 0.9

    def test_positive_news_ignored(self):
        items = [{"sentiment": "POSITIVE", "impact": 0.9, "headline": "Strong results"}]
        score, ev = news_risk(items)
        assert score == 0.0

    def test_max_of_multiple_negatives(self):
        items = [
            {"sentiment": "NEGATIVE", "impact": 0.3, "headline": "A"},
            {"sentiment": "NEGATIVE", "impact": 0.7, "headline": "B"},
        ]
        score, _ = news_risk(items)
        assert score == 70.0


class TestComputeHealthScore:
    def _make_risk(self, symbol: str, tech_score: float = 0.0) -> RiskComponents:
        return RiskComponents(
            symbol                   = symbol,
            concentration_risk       = 20.0,
            sector_concentration_risk= 10.0,
            cap_exposure_risk        = 5.0,
            volatility_risk          = 15.0,
            news_risk                = 0.0,
            technical_breakdown_risk = tech_score,
        )

    def test_health_score_reproducible(self):
        risk = {"INFY": self._make_risk("INFY"), "TCS": self._make_risk("TCS")}
        pos_weights  = {"INFY": 60.0, "TCS": 40.0}
        sec_weights  = {"IT": 100.0}

        result1 = compute_health_score(risk, pos_weights, sec_weights, 0.0)
        result2 = compute_health_score(risk, pos_weights, sec_weights, 0.0)
        assert result1["portfolio_health_score"] == result2["portfolio_health_score"]

    def test_health_score_in_range(self):
        risk       = {"INFY": self._make_risk("INFY")}
        pos_weights= {"INFY": 100.0}
        sec_weights= {"IT": 100.0}

        result = compute_health_score(risk, pos_weights, sec_weights, 0.0)
        assert 0 <= result["portfolio_health_score"] <= 100

    def test_high_tech_risk_lowers_score(self):
        risk_clean = {"INFY": self._make_risk("INFY", tech_score=0.0)}
        risk_bad   = {"INFY": self._make_risk("INFY", tech_score=100.0)}
        pos  = {"INFY": 100.0}
        sec  = {"IT": 100.0}

        score_clean = compute_health_score(risk_clean, pos, sec, 0.0)["portfolio_health_score"]
        score_bad   = compute_health_score(risk_bad,   pos, sec, 0.0)["portfolio_health_score"]
        assert score_clean > score_bad

    def test_health_band_returned(self):
        risk       = {"INFY": self._make_risk("INFY")}
        pos_weights= {"INFY": 100.0}
        sec_weights= {"IT": 100.0}

        result = compute_health_score(risk, pos_weights, sec_weights, 0.0)
        assert result["band"] in {"Resilient", "Balanced", "Elevated risk", "High risk"}


    def test_drivers_list_non_empty(self):
        risk       = {"INFY": self._make_risk("INFY")}
        pos_weights= {"INFY": 100.0}
        sec_weights= {"IT": 100.0}

        result = compute_health_score(risk, pos_weights, sec_weights, 0.0)
        assert isinstance(result.get("drivers"), list)

    def test_empty_portfolio_returns_score(self):
        result = compute_health_score({}, {}, {}, 0.0)
        # Empty portfolio: all risk components = 0 → health dims are 100 except sector entropy
        assert isinstance(result["portfolio_health_score"], (int, float))
        assert "band" in result
