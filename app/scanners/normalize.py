"""Sub-score normalization helpers (docs/13 §3.2).

Every sub-score is normalized to 0–100 so the composite is a clean weighted sum.
Missing input → NaN sentinel (treated as NEUTRAL by composite.py — excluded from
the weighted sum, weight redistributed pro-rata; stock is never silently penalized).
"""

from __future__ import annotations

import math

# NaN is the NEUTRAL sentinel for missing sub-scores.
NEUTRAL: float = float("nan")


def is_neutral(v: float) -> bool:
    """Return True if v is the NEUTRAL sentinel (NaN)."""
    return math.isnan(v)


def clamp01(x: float) -> float:
    """Clamp x to [0, 1]."""
    return max(0.0, min(1.0, x))


def scale(value: float, lo: float, hi: float) -> float:
    """Linear map [lo, hi] → [0, 100].

    Returns 50.0 when hi == lo (undefined range); clamps outside range.
    Returns NEUTRAL when value is NaN.
    """
    if is_neutral(value):
        return NEUTRAL
    if hi == lo:
        return 50.0
    return 100.0 * clamp01((value - lo) / (hi - lo))


def pct_rank(value: float, distribution: list[float]) -> float:
    """Cross-sectional percentile rank → [0, 100].

    Rank of `value` within today's eligible-universe distribution.
    Returns NEUTRAL when value or distribution is empty/NaN.
    """
    if is_neutral(value) or not distribution:
        return NEUTRAL
    valid = [v for v in distribution if not is_neutral(v)]
    if not valid:
        return NEUTRAL
    count_lte = sum(1 for v in valid if v <= value)
    return 100.0 * count_lte / len(valid)
