"""Gate decision tests: VALIDATED on known signal; FAILED_VALIDATION on noise.

Key contracts:
- Thresholds are read from versioned GateConfig, never hard-coded in gate.py.
- A dataset that passes all criteria → VALIDATED.
- A dataset that fails any criterion → FAILED_VALIDATION.
- apply_verdict_to_db writes the scanner_definitions row and updates scanner_results.
"""

from __future__ import annotations

import pytest

from app.validation.analysis import ValidationMetrics
from app.validation.config import GateConfig, load_gate_config
from app.validation.gate import (
    STATUS_FAILED,
    STATUS_VALIDATED,
    apply_verdict_to_db,
    evaluate_gate,
)


def _metrics(
    horizons: tuple[int, ...] = (21, 63),
    rho: float = 0.80,
    spread: float = 0.06,
    ic_mean: float = 0.08,
    ic_std: float = 0.10,
    ic_tstat: float = 2.5,
    regime_spread: float = 0.04,
) -> ValidationMetrics:
    """Convenience factory for ValidationMetrics."""
    return ValidationMetrics(
        horizons=horizons,
        n_observations=5000,
        n_dates=100,
        n_symbols=50,
        decile_spearman={h: rho for h in horizons},
        top_bottom_spread={h: spread for h in horizons},
        ic_mean={h: ic_mean for h in horizons},
        ic_std={h: ic_std for h in horizons},
        ic_tstat={h: ic_tstat for h in horizons},
        ic_hit_rate={h: 0.65 for h in horizons},
        regime_spread={h: {"BULL": regime_spread, "SIDEWAYS": regime_spread / 2} for h in horizons},
    )


# ---------------------------------------------------------------------------
# Basic pass / fail
# ---------------------------------------------------------------------------

def test_validated_on_known_signal() -> None:
    """Metrics that pass all criteria → VALIDATED."""
    m = _metrics()
    config = load_gate_config("v1")
    verdict = evaluate_gate(m, config)
    assert verdict.status == STATUS_VALIDATED


def test_failed_on_low_spearman() -> None:
    """Decile Spearman ρ below threshold → FAILED_VALIDATION."""
    m = _metrics(rho=0.30)  # below the 0.6 threshold
    config = load_gate_config("v1")
    verdict = evaluate_gate(m, config)
    assert verdict.status == STATUS_FAILED
    assert not verdict.decile_spearman_pass[21]
    assert not verdict.decile_spearman_pass[63]


def test_failed_on_negative_top_bottom_spread() -> None:
    """Negative top-minus-bottom spread → FAILED_VALIDATION."""
    m = _metrics(spread=-0.02)
    config = load_gate_config("v1")
    verdict = evaluate_gate(m, config)
    assert verdict.status == STATUS_FAILED
    assert not verdict.top_bottom_spread_pass[21]


def test_failed_on_negative_ic_mean() -> None:
    """Negative mean IC → FAILED_VALIDATION."""
    m = _metrics(ic_mean=-0.02)
    config = load_gate_config("v1")
    verdict = evaluate_gate(m, config)
    assert verdict.status == STATUS_FAILED
    assert not verdict.ic_mean_pass[21]


def test_failed_on_low_ic_tstat() -> None:
    """IC t-stat below threshold → FAILED_VALIDATION."""
    m = _metrics(ic_tstat=0.8)  # below 1.5
    config = load_gate_config("v1")
    verdict = evaluate_gate(m, config)
    assert verdict.status == STATUS_FAILED
    assert not verdict.ic_tstat_pass[21]


def test_failed_on_regime_inversion() -> None:
    """A regime with negative spread → FAILED_VALIDATION when no_regime_inversion=True."""
    m = ValidationMetrics(
        horizons=(21,),
        n_observations=5000,
        n_dates=100,
        n_symbols=50,
        decile_spearman={21: 0.80},
        top_bottom_spread={21: 0.06},
        ic_mean={21: 0.08},
        ic_std={21: 0.10},
        ic_tstat={21: 2.5},
        ic_hit_rate={21: 0.65},
        regime_spread={21: {"BULL": 0.05, "BEAR": -0.03}},  # BEAR inverts
    )
    config = load_gate_config("v1")
    verdict = evaluate_gate(m, config)
    assert verdict.status == STATUS_FAILED
    assert not verdict.regime_pass[21]


# ---------------------------------------------------------------------------
# Config is versioned and read by the gate (not hard-coded)
# ---------------------------------------------------------------------------

def test_thresholds_from_versioned_config() -> None:
    """Gate reads thresholds from GateConfig, not magic constants in gate.py."""
    config = load_gate_config("v1")
    assert isinstance(config, GateConfig)
    assert hasattr(config, "decile_spearman_min")
    assert hasattr(config, "ic_tstat_min")
    assert hasattr(config, "top_bottom_spread_min")
    assert hasattr(config, "no_regime_inversion")


def test_verdict_records_config_version() -> None:
    """GateVerdict records which config version produced it."""
    m = _metrics()
    config = load_gate_config("v1")
    verdict = evaluate_gate(m, config)
    assert verdict.config_version == "v1"


def test_unknown_config_version_raises() -> None:
    """Requesting an unknown config version raises KeyError."""
    with pytest.raises(KeyError, match="Unknown gate config version"):
        load_gate_config("v99")


def test_custom_config_different_thresholds() -> None:
    """A stricter custom config rejects metrics that the default v1 would accept."""
    strict = GateConfig(
        version="custom-strict",
        decile_spearman_min=0.95,   # impossibly high
        top_bottom_spread_min=0.0,
        ic_mean_min=0.0,
        ic_tstat_min=1.5,
        no_regime_inversion=True,
    )
    m = _metrics(rho=0.80)
    verdict = evaluate_gate(m, strict)
    assert verdict.status == STATUS_FAILED  # fails the strict Spearman threshold


# ---------------------------------------------------------------------------
# Details populated in verdict
# ---------------------------------------------------------------------------

def test_verdict_details_populated() -> None:
    """verdict.details carries metric snapshot for the decision log."""
    m = _metrics()
    verdict = evaluate_gate(m, load_gate_config("v1"))
    assert "decile_spearman" in verdict.details
    assert "ic_tstat" in verdict.details
    assert "n_observations" in verdict.details
    assert verdict.details["n_observations"] == 5000


# ---------------------------------------------------------------------------
# apply_verdict_to_db
# ---------------------------------------------------------------------------

def _in_memory_db():
    from tests.dbutil import open_fresh_pg
    return open_fresh_pg()


def test_apply_validated_verdict_sets_db_flag() -> None:
    """VALIDATED verdict sets scanner_definitions.validated = TRUE in the DB."""
    conn = _in_memory_db()
    m = _metrics()
    verdict = evaluate_gate(m, load_gate_config("v1"))
    assert verdict.status == STATUS_VALIDATED

    apply_verdict_to_db(verdict, conn, scanner_id="momentum")

    row = conn.execute(
        "SELECT validated FROM scanner_definitions WHERE id = 'momentum'"
    ).fetchone()
    assert row is not None
    assert row[0] is True


def test_apply_failed_verdict_sets_db_flag_false() -> None:
    """FAILED_VALIDATION verdict sets scanner_definitions.validated = FALSE."""
    conn = _in_memory_db()
    m = _metrics(rho=0.1)
    verdict = evaluate_gate(m, load_gate_config("v1"))
    assert verdict.status == STATUS_FAILED

    apply_verdict_to_db(verdict, conn, scanner_id="momentum")

    row = conn.execute(
        "SELECT validated FROM scanner_definitions WHERE id = 'momentum'"
    ).fetchone()
    assert row is not None
    assert row[0] is False


def test_apply_verdict_updates_scanner_results_status() -> None:
    """apply_verdict_to_db updates validation_status on existing scanner_results rows."""
    conn = _in_memory_db()

    # Insert a dummy scanner_results row
    conn.execute(
        """
        INSERT INTO scanner_results
            (scanner, stock_id, session_date, weights_version, validation_status)
        VALUES ('momentum', 1, '2024-01-15', 'weights-v1-hypothesis', 'PENDING_M3B')
        """
    )

    m = _metrics()
    verdict = evaluate_gate(m, load_gate_config("v1"))
    apply_verdict_to_db(verdict, conn, scanner_id="momentum")

    row = conn.execute(
        "SELECT validation_status FROM scanner_results WHERE scanner='momentum'"
    ).fetchone()
    assert row is not None
    assert row[0] == STATUS_VALIDATED
