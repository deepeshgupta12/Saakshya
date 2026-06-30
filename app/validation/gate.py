"""M3b decision gate: VALIDATED or FAILED_VALIDATION (docs/steps/03, SPEC §6.5).

On VALIDATED: sets scanner_definitions.validated = TRUE for the momentum scanner
and stamps result validation_status = 'VALIDATED'. The blended composite may drive UI.

On FAILED_VALIDATION: composite stays out of UI; redesign scoring before UI ships.

Framing: this is measurement validation — separation evidence is never reworded
into a return / performance claim (SPEC §3.3, docs/15 §0).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import duckdb

from app.validation.analysis import ValidationMetrics
from app.validation.config import GateConfig, load_gate_config

STATUS_VALIDATED        = "VALIDATED"
STATUS_FAILED           = "FAILED_VALIDATION"


@dataclass
class GateVerdict:
    """Result of the M3b gate evaluation."""

    status: str                # VALIDATED | FAILED_VALIDATION
    config_version: str

    # Per-criterion pass/fail
    decile_spearman_pass: dict[int, bool] = field(default_factory=dict)
    top_bottom_spread_pass: dict[int, bool] = field(default_factory=dict)
    ic_mean_pass: dict[int, bool] = field(default_factory=dict)
    ic_tstat_pass: dict[int, bool] = field(default_factory=dict)
    regime_pass: dict[int, bool] = field(default_factory=dict)

    # Full metric snapshot for the decision log
    details: dict[str, Any] = field(default_factory=dict)


def evaluate_gate(
    metrics: ValidationMetrics,
    config: GateConfig | None = None,
) -> GateVerdict:
    """Apply the versioned pass criteria to ValidationMetrics.

    Args:
        metrics: Output of analysis.analyze().
        config:  Gate config (defaults to load_gate_config("v1")).

    Returns:
        GateVerdict with status VALIDATED or FAILED_VALIDATION.
    """
    if config is None:
        config = load_gate_config("v1")

    verdict = GateVerdict(status=STATUS_FAILED, config_version=config.version)

    all_pass = True

    for h in metrics.horizons:
        # 1. Decile Spearman ρ
        rho = metrics.decile_spearman.get(h, 0.0)
        rho_pass = (not math.isnan(rho)) and rho >= config.decile_spearman_min
        verdict.decile_spearman_pass[h] = rho_pass
        if not rho_pass:
            all_pass = False

        # 2. Top-minus-bottom spread must be positive
        spread = metrics.top_bottom_spread.get(h, float("nan"))
        spread_pass = (not math.isnan(spread)) and spread > config.top_bottom_spread_min
        verdict.top_bottom_spread_pass[h] = spread_pass
        if not spread_pass:
            all_pass = False

        # 3. Mean IC positive
        ic_mean = metrics.ic_mean.get(h, 0.0)
        ic_mean_pass = (not math.isnan(ic_mean)) and ic_mean > config.ic_mean_min
        verdict.ic_mean_pass[h] = ic_mean_pass
        if not ic_mean_pass:
            all_pass = False

        # 4. IC t-stat
        ic_tstat = metrics.ic_tstat.get(h, 0.0)
        ic_tstat_pass = (not math.isnan(ic_tstat)) and ic_tstat >= config.ic_tstat_min
        verdict.ic_tstat_pass[h] = ic_tstat_pass
        if not ic_tstat_pass:
            all_pass = False

        # 5. No regime inverts the relationship (all regime spreads must be positive)
        if config.no_regime_inversion:
            regime_spreads = metrics.regime_spread.get(h, {})
            regime_ok = True
            for _regime, rspr in regime_spreads.items():
                if math.isnan(rspr) or rspr <= 0.0:
                    regime_ok = False
                    break
            verdict.regime_pass[h] = regime_ok
            if not regime_ok:
                all_pass = False

    verdict.status = STATUS_VALIDATED if all_pass else STATUS_FAILED
    verdict.details = {
        "decile_spearman":   metrics.decile_spearman,
        "top_bottom_spread": metrics.top_bottom_spread,
        "ic_mean":           metrics.ic_mean,
        "ic_tstat":          metrics.ic_tstat,
        "ic_hit_rate":       metrics.ic_hit_rate,
        "regime_spread":     metrics.regime_spread,
        "n_observations":    metrics.n_observations,
        "n_dates":           metrics.n_dates,
        "n_symbols":         metrics.n_symbols,
    }
    return verdict


def apply_verdict_to_db(
    verdict: GateVerdict,
    conn: duckdb.DuckDBPyConnection,
    scanner_id: str = "momentum",
    weights_version: str = "weights-v1-hypothesis",
) -> None:
    """Persist the verdict to scanner_definitions and update scanner_results rows.

    On VALIDATED:
      - Sets scanner_definitions.validated = TRUE.
      - Updates scanner_results.validation_status = 'VALIDATED' for this scanner/version.
    On FAILED_VALIDATION:
      - scanner_definitions.validated stays FALSE.
      - scanner_results.validation_status = 'FAILED_VALIDATION'.
    """
    validated = verdict.status == STATUS_VALIDATED

    # Upsert the scanner_definitions row (create if missing).
    conn.execute(
        """
        INSERT INTO scanner_definitions (id, name, validated, version)
        VALUES (?, ?, ?, 1)
        ON CONFLICT (id) DO UPDATE SET
            validated  = excluded.validated,
            version    = version + 1
        """,
        [scanner_id, scanner_id, validated],
    )

    # Stamp all scanner_results for this scanner+weights_version.
    conn.execute(
        """
        UPDATE scanner_results
        SET    validation_status = ?
        WHERE  scanner          = ?
          AND  weights_version  = ?
        """,
        [verdict.status, scanner_id, weights_version],
    )
