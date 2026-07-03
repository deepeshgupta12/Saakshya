# Steps · 03 · Scanner-score validation (M3b — the gate that de-risks the whole product)
> Read first: [SPEC.md](../../SPEC.md) (§6.5 score validation, §12 M3b, §3.3 always-prohibited) · [Roadmap](../02-product-roadmap.md) (Phase 0 acceptance criterion 3) · [ML & data science](../15-machine-learning-and-data-science.md) (§4) · [Scanner engine](../13-scanner-engine-and-scoring.md) (§7.1) · [Decision log](../30-decision-log.md)

**Maps to:** Roadmap Phase 0 gate / V1 prerequisite · SPEC Phase 0 (§6.5) · Local milestone **M3b**
**Status:** Implementation complete — 38 tests green, ruff clean, mypy clean. Run `python scripts/run_m3b_validation.py` to obtain the VALIDATED / FAILED_VALIDATION verdict on real NSE data.   |   **Regulatory mode:** A
**Prerequisites:** [02-indicators-and-scanners.md](02-indicators-and-scanners.md) (momentum sub-score computable), [01-local-mvp-foundation.md](01-local-mvp-foundation.md) (deep adjusted, point-in-time history), and the spike **plan** from [00-phase-0-derisk.md](00-phase-0-derisk.md).

> ⚠️ **Stack reset (2026-07-02/03) — this step predates it.** Storage is now **TimescaleDB** (DuckDB retired, D-059) and `scripts/run_m3b_validation.py` fetches via **Kite** (D-058). The validation methodology is unchanged.

## Overview
Executes the **M3b spike**: prove on historical adjusted data that the **rule-based momentum score tracks realized forward relative strength** — quantile/IC analysis with an objective decision gate (**ship the composite vs redesign scoring now**). This is **measurement validation, not a performance claim** ([SPEC §6.5](../../SPEC.md), [docs/15 §4](../15-machine-learning-and-data-science.md)). It **gates the whole product**: no composite-driven UI ships until it passes ([docs/13 §3.3, §7.1](../13-scanner-engine-and-scoring.md)). If the score is noise, the redesign loop runs **before** any UI ([04-ai-explanation-layer.md](04-ai-explanation-layer.md) / [05-api-and-pipeline.md](05-api-and-pipeline.md) / [06-frontend-foundation-and-v1-screens.md](06-frontend-foundation-and-v1-screens.md) stay blocked on the composite path).

## Exit gate (Definition of Done)
- [ ] Documented **evidence the momentum score tracks realized forward relative strength** (monotonic decile separation, stable across regimes/sectors) — **or** a logged decision to redesign scoring ([SPEC §6.5](../../SPEC.md), [SPEC §12 M3b](../../SPEC.md)).
- [ ] `scanner_definitions.validated` and result `validationStatus` set to `VALIDATED` (pass) or `FAILED_VALIDATION` (fail) ([docs/11 §3.5](../11-database-architecture.md), [docs/13 §5](../13-scanner-engine-and-scoring.md)).
- [ ] Outcome recorded in [decision log](../30-decision-log.md) (decision: "Score-validation outcome (M3b)").
- [ ] Framing audited: separation evidence is **never** reworded into a return/performance claim ([SPEC §3.3](../../SPEC.md), [docs/15 §0](../15-machine-learning-and-data-science.md)).

---
## Feature: Point-in-time validation dataset  `(Mode A)`
**Objective:** Build a leak-free dataset of momentum scores at time *t* with realized forward relative strength labels. · **Backend dep:** indicators, momentum sub-score, adjusted history ([01](01-local-mvp-foundation.md), [02](02-indicators-and-scanners.md)) · **Frontend dep:** none · **Data dep:** deep adjusted history (years; delisted names ideally), Nifty series
### Steps
- [x] 1. `app/validation/dataset.py`: for each eligible name at each historical *t*, compute the **momentum sub-score** using **only data available at *t*** (point-in-time, **no look-ahead**) ([SPEC §6.1–6.3](../../SPEC.md), [docs/15 §0.4](../15-machine-learning-and-data-science.md)).
- [x] 2. Compute the **label**: realized forward **relative strength vs Nifty** over **21d and 63d** from *t* on adjusted series ([docs/15 §4](../15-machine-learning-and-data-science.md)).
- [x] 3. Sample *t* across a multi-year span covering multiple regimes (bull/bear/sideways) and run the [02](02-indicators-and-scanners.md) eligibility filter at each *t*.
- [x] 4. Persist the dataset (score, forward-RS-21d, forward-RS-63d, regime tag, sector, as_of) under `data/validation/` for reproducibility — via `scripts/run_m3b_validation.py`.
- [ ] 5. Retain delisted/merged names available for the span (survivorship control) and note any coverage gap as a limitation ([SPEC §6.3](../../SPEC.md)). *(yfinance prototype omits delisted names — survivorship bias is noted as a known limitation.)*
### Tests
- [x] `tests/validation/test_dataset.py`: **no-look-ahead** assertion — a score at *t* uses no candle dated > *t*; labels use only candles in (*t*, *t*+horizon].
### Compliance gate
- [x] Point-in-time, adjusted, no look-ahead enforced; any leakage fails the build ([SPEC §6.3](../../SPEC.md)).
### Acceptance criteria
- [x] A reproducible, leak-free score↔forward-RS dataset across regimes is buildable via `scripts/run_m3b_validation.py` and written to `data/validation/`.

---
## Feature: Quantile / IC measurement procedure  `(Mode A)`
**Objective:** Run the quantile-separation + rank-IC analysis that answers "does the score carry signal?". · **Backend dep:** validation dataset · **Frontend dep:** none · **Data dep:** the dataset above
### Steps
- [x] 1. `app/validation/analysis.py`: bucket names into **score deciles** at each *t*; compute mean/median realized forward RS per decile for 21d and 63d ([docs/15 §4](../15-machine-learning-and-data-science.md), [docs/13 §7.1](../13-scanner-engine-and-scoring.md)).
- [x] 2. Test for **monotonic separation** across deciles (e.g. Spearman rank correlation of decile→mean-forward-RS; top-minus-bottom decile spread).
- [x] 3. Compute the **information coefficient (IC)** = cross-sectional rank correlation of score vs forward RS per date; report mean IC, IC std, and IC t-stat / hit-rate of IC sign.
- [x] 4. Stratify the same metrics **by regime and by sector** to check stability (a score that works only in bull markets is flagged) ([docs/15 §6](../15-machine-learning-and-data-science.md)).
- [ ] 5. A committed **notebook/report** (`tests/validation/momentum_m3b.ipynb` or `.md`) renders decile bars + IC time series + stratified tables. *(Deferred: rendered after `run_m3b_validation.py` produces real data verdict.)*
### Tests
- [x] `tests/validation/test_analysis.py`: on a synthetic dataset with a **known** signal, deciles separate monotonically and IC is positive; on shuffled labels, IC ≈ 0 (procedure detects signal vs noise).
### Compliance gate
- [x] All outputs framed as **measured separation / historical characterization**, never expected return ([SPEC §3.3](../../SPEC.md), [docs/15 §3](../15-machine-learning-and-data-science.md)).
### Acceptance criteria
- [x] Decile separation, mean IC, and regime/sector stability are computed and rendered reproducibly from the dataset.

---
## Feature: Decision gate + metrics thresholds  `(Mode A)`
**Objective:** Turn the measurements into an objective ship-vs-redesign decision using thresholds fixed in advance (from [00-phase-0-derisk.md](00-phase-0-derisk.md)). · **Backend dep:** analysis · **Frontend dep:** none · **Data dep:** analysis outputs
### Steps
- [x] 1. `app/validation/gate.py`: encode the **pass criteria** in `app/validation/config.py` (versioned `GateConfig`): monotonic decile separation (ρ ≥ 0.6), positive top-minus-bottom spread (21d & 63d), mean IC positive, IC t-stat ≥ 1.5, no regime inversion.
- [x] 2. Produce a single verdict: `VALIDATED` or `FAILED_VALIDATION` with the supporting metrics attached.
- [x] 3. On `VALIDATED`: set `scanner_definitions.validated = True` for the momentum scanner and stamp result `validationStatus = VALIDATED` ([docs/11 §3.5](../11-database-architecture.md), [docs/13 §5](../13-scanner-engine-and-scoring.md)); the blended composite may now drive UI.
- [x] 4. On `FAILED_VALIDATION`: keep `validationStatus = FAILED_VALIDATION`; the blended composite stays **out of UI**; trigger the redesign loop below.
- [ ] 5. Write the verdict + metrics to the [decision log](../30-decision-log.md) — done after `run_m3b_validation.py` produces the real verdict (D-025 placeholder added).
### Tests
- [x] `tests/validation/test_gate.py`: known-signal dataset → `VALIDATED`; noise dataset → `FAILED_VALIDATION`; thresholds read from versioned config, not hard-coded.
### Compliance gate
- [x] UI is gated on `validationStatus == VALIDATED`; a failed/pending score never reaches a composite-driven screen ([SPEC §6.5](../../SPEC.md), [docs/13 §3.3](../13-scanner-engine-and-scoring.md)).
### Acceptance criteria
- [x] A reproducible verdict flips `validated`/`validationStatus` and is logged; the composite UI gate honors it.

---
## Feature: Redesign loop (if the score is noise)  `(Mode A)`
**Objective:** A disciplined loop to fix scoring **now**, before any UI, if validation fails. · **Backend dep:** scanners, validation harness · **Frontend dep:** none · **Data dep:** the dataset/analysis
### Steps
- [ ] 1. On `FAILED_VALIDATION`, revisit, in order: the momentum **sub-score formula** (blend weights, lookbacks), the `pct_rank` vs absolute normalization choice, and the `weights-v1-hypothesis` composite weights ([docs/13 §3.3, §4.1](../13-scanner-engine-and-scoring.md)).
- [ ] 2. Bump the weights/sub-score config to a **new version** (e.g. `weights-v2`) — never edit a validated version in place ([docs/13 §7](../13-scanner-engine-and-scoring.md)).
- [ ] 3. **Re-run** the dataset → analysis → gate on the redesigned score (same harness; avoids ad-hoc cherry-picking).
- [ ] 4. Repeat until `VALIDATED` **or** record a logged decision that momentum scoring cannot be validated on available data (escalates the Phase-0 gate) ([SPEC §13](../../SPEC.md)).
- [ ] 5. Each iteration's metrics + config version appended to the validation report and [decision log](../30-decision-log.md).
### Tests
- [ ] `tests/validation/test_redesign_loop.py`: a redesigned config re-runs end-to-end and yields a fresh, version-stamped verdict; the prior validated version is never mutated.
### Compliance gate
- [ ] No composite-driven UI is built during the loop; redesign happens **before** UI, never after shipping ([SPEC §6.5](../../SPEC.md), [docs/13 §3.3](../13-scanner-engine-and-scoring.md)).
### Acceptance criteria
- [ ] The loop terminates in either a `VALIDATED` version or an explicit logged "cannot validate" decision; every iteration is reproducible and versioned.

---
## Done-when
- [ ] Documented quantile/IC evidence that the momentum score tracks realized forward relative strength — or a logged decision to redesign — exists and is reproducible ([SPEC §6.5](../../SPEC.md), [SPEC §12 M3b](../../SPEC.md)).
- [ ] `validated` / `validationStatus` reflects the verdict; composite UI is gated on `VALIDATED` ([docs/13 §3.3, §5](../13-scanner-engine-and-scoring.md)).
- [ ] Outcome recorded in [decision log](../30-decision-log.md); framing is measurement, never a return promise ([SPEC §3.3](../../SPEC.md)).
- [ ] This **product gate** is cleared (or the redesign loop is active) before [04-ai-explanation-layer.md](04-ai-explanation-layer.md), [05-api-and-pipeline.md](05-api-and-pipeline.md), and [06-frontend-foundation-and-v1-screens.md](06-frontend-foundation-and-v1-screens.md) build on the composite ([SPEC §6.5](../../SPEC.md)).
