"""Composite scorer: weighted sum of sub-scores with NEUTRAL renormalization (docs/13 §3.3).

NEUTRAL sub-scores are excluded from the weighted sum and their weight
redistributed pro-rata across available sub-scores. A stock is never silently
penalized for a vendor data gap.
"""

from __future__ import annotations

from app.scanners.normalize import NEUTRAL, is_neutral


def compute_composite(
    sub_scores: dict[str, float],
    weights: dict[str, float],
) -> float:
    """Weighted average of available (non-NEUTRAL) sub-scores → 0–100.

    Returns NEUTRAL (NaN) when all sub-scores are NEUTRAL.
    Weights are renormalized over the available sub-scores so they sum to 1.0.
    """
    available = {k: v for k, v in sub_scores.items() if k in weights and not is_neutral(v)}
    if not available:
        return NEUTRAL
    total_weight = sum(weights[k] for k in available)
    if total_weight == 0.0:
        return NEUTRAL
    return sum(weights[k] * v for k, v in available.items()) / total_weight
