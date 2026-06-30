"""Versioned gate thresholds for M3b score validation (docs/13 §7.1, SPEC §6.5).

Thresholds are stored in a versioned registry so the gate.py logic never hard-codes
them — each run records which config version produced the verdict (docs/30 D-025).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GateConfig:
    """Pass criteria for the M3b validation gate.

    All thresholds apply to BOTH 21d and 63d horizons unless horizon-specific.
    """

    version: str
    decile_spearman_min: float
    top_bottom_spread_min: float
    ic_mean_min: float
    ic_tstat_min: float
    no_regime_inversion: bool


# v1: pre-registered thresholds for the weights-v1-hypothesis composite.
# Any change to scoring weights requires a new config version (docs/13 §7).
GATE_CONFIG_V1 = GateConfig(
    version="v1",
    decile_spearman_min=0.6,   # Spearman ρ of decile rank → mean fwd RS
    top_bottom_spread_min=0.0,  # top-minus-bottom decile spread must be positive
    ic_mean_min=0.0,            # mean IC across dates must be positive
    ic_tstat_min=1.5,           # IC t-stat = mean / std * sqrt(n_dates)
    no_regime_inversion=True,   # every regime must have positive top-bottom spread
)

_REGISTRY: dict[str, GateConfig] = {
    "v1": GATE_CONFIG_V1,
}


def load_gate_config(version: str = "v1") -> GateConfig:
    if version not in _REGISTRY:
        raise KeyError(f"Unknown gate config version: {version!r}. Available: {list(_REGISTRY)}")
    return _REGISTRY[version]
