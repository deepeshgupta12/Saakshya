"""Versioned composite-score weights (docs/13 §3.3, SPEC §6.5).

VALIDATION REQUIRED (M3b): these weights are a starting hypothesis, not a
calibrated result. The composite must not drive any UI until the M3b spike
confirms the momentum sub-score tracks realized forward relative strength.
"""

from __future__ import annotations

# Weights must sum to 1.0. Any change requires a new version key + re-validation.
WEIGHTS_V1: dict[str, float] = {
    "priceMomentum":   0.25,
    "volumeExpansion": 0.20,
    "maTrend":         0.15,
    "sectorStrength":  0.15,
    "rsiHealth":       0.10,
    "newsSentiment":   0.10,
    "riskAdjustment":  0.05,
}

WEIGHTS_VERSION = "weights-v1-hypothesis"
VALIDATION_STATUS = "PENDING_M3B"
ENGINE_VERSION = "1.0.0"
