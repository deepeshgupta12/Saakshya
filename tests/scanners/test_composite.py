"""Tests for scanners/composite.py (docs/02 §Tests, critical-logic)."""

from __future__ import annotations

import math

import pytest

from app.scanners.composite import compute_composite
from app.scanners.normalize import NEUTRAL
from app.scanners.weights import WEIGHTS_V1


def test_all_neutral_returns_neutral() -> None:
    """All sub-scores NEUTRAL → composite is NEUTRAL (NaN)."""
    sub = {k: NEUTRAL for k in WEIGHTS_V1}
    result = compute_composite(sub, WEIGHTS_V1)
    assert math.isnan(result)


def test_single_sub_score_uses_full_weight() -> None:
    """Only priceMomentum=80 available → composite = 80."""
    sub = {k: NEUTRAL for k in WEIGHTS_V1}
    sub["priceMomentum"] = 80.0
    result = compute_composite(sub, WEIGHTS_V1)
    assert result == pytest.approx(80.0)


def test_all_equal_weights_balance() -> None:
    """All sub-scores = 50 → composite = 50 (regardless of weight distribution)."""
    sub = {k: 50.0 for k in WEIGHTS_V1}
    result = compute_composite(sub, WEIGHTS_V1)
    assert result == pytest.approx(50.0)


def test_renormalization_two_sub_scores() -> None:
    """Two sub-scores with weights that don't sum to 1 are renormalized.

    priceMomentum (0.25) = 100, volumeExpansion (0.20) = 0.
    renormalized weights: pm = 0.25/0.45 = 5/9, ve = 0.20/0.45 = 4/9.
    composite = (5/9)*100 + (4/9)*0 = 55.555...
    """
    sub = {k: NEUTRAL for k in WEIGHTS_V1}
    sub["priceMomentum"] = 100.0
    sub["volumeExpansion"] = 0.0
    result = compute_composite(sub, WEIGHTS_V1)
    expected = 100.0 * (0.25 / (0.25 + 0.20))
    assert result == pytest.approx(expected, rel=1e-6)


def test_weights_stamped_from_config() -> None:
    """Weights sum to 1.0 in WEIGHTS_V1."""
    assert sum(WEIGHTS_V1.values()) == pytest.approx(1.0)


def test_unknown_sub_score_ignored() -> None:
    """Sub-scores not in the weights dict are ignored."""
    sub = {k: 50.0 for k in WEIGHTS_V1}
    sub["phantom_score"] = 99.0   # not in WEIGHTS_V1
    result = compute_composite(sub, WEIGHTS_V1)
    assert result == pytest.approx(50.0)
