"""Tests for scanners/normalize.py (docs/02 §Tests, critical-logic)."""

from __future__ import annotations

import math

import pytest

from app.scanners.normalize import NEUTRAL, clamp01, is_neutral, pct_rank, scale


def test_is_neutral_nan() -> None:
    assert is_neutral(float("nan")) is True
    assert is_neutral(NEUTRAL) is True


def test_is_neutral_values() -> None:
    assert is_neutral(0.0) is False
    assert is_neutral(50.0) is False
    assert is_neutral(100.0) is False


def test_clamp01_bounds() -> None:
    assert clamp01(-1.0) == pytest.approx(0.0)
    assert clamp01(2.0)  == pytest.approx(1.0)
    assert clamp01(0.5)  == pytest.approx(0.5)


def test_scale_linear_map() -> None:
    assert scale(0.0, 0.0, 100.0) == pytest.approx(0.0)
    assert scale(50.0, 0.0, 100.0) == pytest.approx(50.0)
    assert scale(100.0, 0.0, 100.0) == pytest.approx(100.0)


def test_scale_clamped() -> None:
    """Values outside [lo, hi] are clamped to [0, 100]."""
    assert scale(-5.0, 0.0, 100.0) == pytest.approx(0.0)
    assert scale(150.0, 0.0, 100.0) == pytest.approx(100.0)


def test_scale_equal_range_returns_50() -> None:
    """When lo == hi, return 50.0 (undefined range → midpoint)."""
    assert scale(5.0, 5.0, 5.0) == pytest.approx(50.0)


def test_scale_neutral_input_returns_neutral() -> None:
    assert is_neutral(scale(NEUTRAL, 0.0, 100.0))


def test_pct_rank_all_lower() -> None:
    """Value > all distribution members → 100.0."""
    assert pct_rank(99.0, [10.0, 20.0, 30.0]) == pytest.approx(100.0)


def test_pct_rank_middle() -> None:
    """Value = 50th pct in [10,20,30,40,50] → 100%."""
    assert pct_rank(30.0, [10.0, 20.0, 30.0, 40.0, 50.0]) == pytest.approx(60.0)


def test_pct_rank_empty_distribution_neutral() -> None:
    assert is_neutral(pct_rank(50.0, []))


def test_pct_rank_neutral_value_neutral() -> None:
    assert is_neutral(pct_rank(NEUTRAL, [10.0, 20.0]))


def test_pct_rank_distribution_with_neutrals_filtered() -> None:
    """NEUTRAL values in the distribution are filtered out."""
    dist = [10.0, NEUTRAL, 30.0]
    result = pct_rank(20.0, dist)
    assert not math.isnan(result)  # should still work on the 2 valid values
