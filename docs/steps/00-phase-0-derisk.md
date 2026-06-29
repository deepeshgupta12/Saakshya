# Steps · 00 · Phase 0 — De-risk (gating, mostly non-code)
> Read first: [SPEC.md](../../SPEC.md) (§2 regulatory mode, §8 data strategy, §13 decision log, §12 local plan) · [Roadmap](../02-product-roadmap.md) (§3 Phase 0) · [Data ingestion](../12-data-ingestion-and-market-data.md) · [Scanner engine](../13-scanner-engine-and-scoring.md) · [ML & data science](../15-machine-learning-and-data-science.md)

**Maps to:** Roadmap "Phase 0 (precedes V1)" · SPEC Phase 0 · Local milestone (precedes M0; M3b proven in [03-scanner-score-validation.md](03-scanner-score-validation.md))
**Status:** Not started   |   **Regulatory mode:** A
**Prerequisites:** None — this is the first file. Nothing broad is built until these gates pass.

## Overview
Phase 0 retires the three product-killing assumptions **before** any broad feature work ([SPEC §12](../../SPEC.md)): (1) is Mode-A output legal-safe and is the RA track started; (2) can we get correct, adjusted historical data with redistribution rights; (3) does at least one scanner score carry signal. This file owns the **non-code gating work** (legal + data procurement) plus the **plan** for the score-validation spike. The spike is *executed and proven* later in [03-scanner-score-validation.md](03-scanner-score-validation.md) once indicators ([02-indicators-and-scanners.md](02-indicators-and-scanners.md)) exist; the foundation it runs on is built in [01-local-mvp-foundation.md](01-local-mvp-foundation.md).

This is deliberately **mostly non-code**. The only thing that may be built locally in parallel is the Mode-A local MVP (file 01), strictly Mode A — no RA-gated feature is built "just to see it" ([SPEC §12](../../SPEC.md), [§2](../../SPEC.md)).

## Exit gate (Definition of Done)
- [ ] Counsel confirms **Mode-A scope** for v1 and the **RA filing is initiated** in parallel ([SPEC §2](../../SPEC.md), [§10 Phase 0 exit gate](../../SPEC.md)).
- [ ] A **signed data-vendor contract with commercial redistribution rights** is in hand (or an explicit, logged decision to stay prototype-only until launch) ([SPEC §8](../../SPEC.md), [§13](../../SPEC.md)).
- [ ] Documented **evidence that ≥1 scanner score (momentum) tracks realized forward relative strength** — or a logged decision to redesign scoring — produced by [03-scanner-score-validation.md](03-scanner-score-validation.md) ([SPEC §6.5](../../SPEC.md)).
- [ ] Each decision recorded in [decision log](../30-decision-log.md).

---
## Feature: Resolve operating mode + start RA filing  `(Mode A)`
**Objective:** Lock the v1 regulatory mode with qualified Indian securities counsel and begin RA registration as a parallel gating track, so feature scope and AI language are fixed before architecture freezes. · **Backend dep:** none · **Frontend dep:** none · **Data dep:** none
### Steps
- [ ] 1. **Owner: Founder/Legal.** Engage Indian securities counsel; brief them with [SPEC §2](../../SPEC.md) (mode table), [§3](../../SPEC.md) (boundaries), [§4](../../SPEC.md) (feature→mode mapping), and the [compliance doc](../21-compliance-risk-and-guardrails.md). **Artifact:** signed engagement + briefing pack.
- [ ] 2. **Owner: Legal.** Obtain written confirmation that the v1 scope is **Mode A — pure analytics** (data, indicators, charts, scanners with score+reasons, sector/news/risk analytics; **no** entry/target/SL, **no** "candidate" buy-leans, **no** ranked "what to buy") ([SPEC §3.1–3.2](../../SPEC.md)). **Artifact:** counsel memo confirming Mode-A scope.
- [ ] 3. **Owner: Legal.** Confirm the **always-prohibited phrase list** ([SPEC §3.3](../../SPEC.md), [§5](../../SPEC.md), [§6.9](../../SPEC.md)) and that it is enforced **at output time**. **Artifact:** approved seed blocked-phrase/pattern list (feeds [04-ai-explanation-layer.md](04-ai-explanation-layer.md) and the `compliance_rules` table in [docs/11](../11-database-architecture.md)).
- [ ] 4. **Owner: Founder.** Start the **RA (Mode B) filing track** in parallel: NISM Series-XV cert, RAASB enlistment via BSE, FD lien planning, record-keeping plan, and the **mandatory AI-use disclosure** requirement ([SPEC §2](../../SPEC.md), [§6.7](../../SPEC.md)). **Artifact:** RA filing checklist with dates; this track later unlocks Phase-5 RA-gated features ([14-v9-advisory-ra-gated.md](14-v9-advisory-ra-gated.md)).
- [ ] 5. **Owner: Founder/Legal.** Confirm the **SEBI fee-cap (~₹1.51L/yr/family)** constraint is noted for any future RA-operated tier ([SPEC §11](../../SPEC.md)) and the personalization A-vs-C line ([SPEC §7](../../SPEC.md)). **Artifact:** monetization/personalization constraints note.
### Tests
- [ ] N/A (legal milestone). Verification = counsel sign-off artifacts exist and are filed.
### Compliance gate
- [ ] Mode-A scope confirmed in writing; no feature outside Mode A is scheduled for v1 ([SPEC §2 gating principle](../../SPEC.md)).
- [ ] Always-prohibited list approved and earmarked for output-time enforcement.
### Acceptance criteria
- [ ] Counsel memo on file confirming Mode-A scope; RA filing initiated with a dated checklist; both logged in [decision log](../30-decision-log.md) (decision: "v1 operating mode A vs A+RA").

---
## Feature: Data-vendor selection + adjusted-history procurement  `(Mode A)`
**Objective:** Decide and (for production) contract the data feed, with explicit commercial redistribution rights and deep adjusted history incl. delisted names — while using **yfinance for the local prototype only**. · **Backend dep:** the `DataSource` adapter ([01-local-mvp-foundation.md](01-local-mvp-foundation.md)) · **Frontend dep:** none · **Data dep:** the whole product depends on this from Phase 1 onward ([SPEC §13](../../SPEC.md)).
### Steps
- [ ] 1. **Owner: Eng/Founder.** Stand up the **yfinance prototype** as the *local-only* source: pull ~50 Nifty names' adjusted OHLCV ([SPEC §8](../../SPEC.md), [docs/12 §3](../12-data-ingestion-and-market-data.md)). This is the M0 spike, built in [01-local-mvp-foundation.md](01-local-mvp-foundation.md). **Artifact:** working pull into DuckDB; explicit note that yfinance is **prototype-only, no redistribution, no delivery %**.
- [ ] 2. **Owner: Eng.** Evaluate the **authoritative EOD supplements** — NSE Bhavcopy (CM-UDiFF) and `sec_bhavdata` (delivery %) — for coverage and redistribution review ([docs/12 §3](../12-data-ingestion-and-market-data.md)). **Artifact:** feasibility note + redistribution-review status.
- [ ] 3. **Owner: Founder/Legal.** Evaluate **licensed production vendors** (TrueData / Global Datafeeds and peers) on: commercial **redistribution rights**, corp-action adjustment quality, symbol mapping, **historical adjusted depth incl. delisted/merged names**, delivery data, and price/lead-time ([SPEC §8](../../SPEC.md), [§13](../../SPEC.md)). **Artifact:** vendor comparison matrix.
- [ ] 4. **Owner: Founder/Legal.** Decide **build-vs-buy for corp-action adjustment** ([SPEC §13](../../SPEC.md)): the production engine is not yfinance auto-adjustment ([SPEC §6.1](../../SPEC.md)). **Artifact:** logged decision.
- [ ] 5. **Owner: Founder.** Negotiate and **sign the production data contract** (or log an explicit decision to remain prototype-only until launch). **Artifact:** signed contract or logged deferral.
- [ ] 6. **Owner: Eng.** Confirm all sources sit **behind the one `DataSource` adapter** so the production vendor swaps in without touching scanners/indicators/AI ([SPEC §8](../../SPEC.md), [docs/12 §3.1](../12-data-ingestion-and-market-data.md)); adapter built in [01-local-mvp-foundation.md](01-local-mvp-foundation.md). **Artifact:** confirmation that `supports("redistribution")` gates commercial publish.
### Tests
- [ ] N/A here (adapter consistency + schema tests live in [01-local-mvp-foundation.md](01-local-mvp-foundation.md)). Verification = procurement artifacts + a working local pull.
### Compliance gate
- [ ] yfinance is used **prototype-only**; the platform refuses to publish commercially from any source where `supports("redistribution") == False` ([SPEC §8](../../SPEC.md), [docs/12 §3.1](../12-data-ingestion-and-market-data.md)).
### Acceptance criteria
- [ ] Vendor comparison matrix complete; production contract signed (or deferral logged) with redistribution rights and delisted-name history identified; corp-action build-vs-buy decision in [decision log](../30-decision-log.md).

---
## Feature: Scanner-score validation SPIKE plan  `(Mode A)`
**Objective:** Define — now — the measurement-validation procedure that will prove (in [03-scanner-score-validation.md](03-scanner-score-validation.md)) that the momentum score tracks realized forward relative strength, so the team knows the gate before building toward it. · **Backend dep:** indicators ([02-indicators-and-scanners.md](02-indicators-and-scanners.md)) + adjusted history ([01-local-mvp-foundation.md](01-local-mvp-foundation.md)) · **Frontend dep:** none · **Data dep:** deep adjusted, point-in-time history.
### Steps
- [ ] 1. **Owner: Data science.** Write the **spike charter** restating the question: *does the rule-based momentum sub-score track realized relative strength?* — measurement validation, **not** a performance claim ([SPEC §6.5](../../SPEC.md), [docs/15 §4](../15-machine-learning-and-data-science.md)). **Artifact:** one-page charter.
- [ ] 2. **Owner: Data science.** Specify the **method** to be executed in [03](03-scanner-score-validation.md): compute the momentum sub-score per eligible name at time *t* (point-in-time, no look-ahead) → bucket into deciles → measure realized forward relative strength vs Nifty over 21d/63d → test for **monotonic separation** across deciles, stable across regimes/sectors ([docs/15 §4](../15-machine-learning-and-data-science.md), [docs/13 §7.1](../13-scanner-engine-and-scoring.md)). **Artifact:** documented procedure.
- [ ] 3. **Owner: Data science.** Define **pass/fail metrics + thresholds** up front (decile monotonicity, top-vs-bottom spread, rank IC, regime/sector stability) so the decision gate is objective. **Artifact:** acceptance-criteria spec (detailed in [03](03-scanner-score-validation.md)).
- [ ] 4. **Owner: Data science.** Define the **redesign loop**: if noise, what gets revisited (sub-score formula, weights `weights-v1-hypothesis`, lookbacks) and re-tested **before any UI** ([docs/13 §3.3](../13-scanner-engine-and-scoring.md)). **Artifact:** redesign-loop note.
- [ ] 5. **Owner: Data science.** Define **how results are recorded**: notebook/report committed under `tests/validation/`, outcome (`VALIDATED` / `FAILED_VALIDATION`) written to the [decision log](../30-decision-log.md) and stamped onto `scanner_definitions.validated` ([docs/11 §3.5](../11-database-architecture.md)). **Artifact:** recording convention.
### Tests
- [ ] N/A (planning). The executable validation harness + its tests are built in [03-scanner-score-validation.md](03-scanner-score-validation.md).
### Compliance gate
- [ ] The spike is framed as **measurement validation, never a return promise**; separation evidence may never be reworded into a performance/return claim ([SPEC §3.3](../../SPEC.md), [§6.5](../../SPEC.md), [docs/15 §0](../15-machine-learning-and-data-science.md)).
### Acceptance criteria
- [ ] A committed spike plan (charter, method, metrics+thresholds, redesign loop, recording convention) exists and is referenced by [03-scanner-score-validation.md](03-scanner-score-validation.md); product UI is understood to be **gated** on its outcome ([SPEC §6.5](../../SPEC.md)).

---
## Done-when
- [ ] Counsel confirms Mode-A scope and the RA filing is initiated ([SPEC §2](../../SPEC.md)).
- [ ] A signed data contract with redistribution rights exists (or a logged prototype-only deferral), and corp-action build-vs-buy is decided ([SPEC §8](../../SPEC.md), [§13](../../SPEC.md)).
- [ ] The score-validation spike is fully planned (metrics + gate + redesign loop) and ready to execute in [03-scanner-score-validation.md](03-scanner-score-validation.md) ([SPEC §6.5](../../SPEC.md)).
- [ ] All three decisions are logged in [decision log](../30-decision-log.md). Only then is broad build (Phase 1 / [01-local-mvp-foundation.md](01-local-mvp-foundation.md) onward) and cloud spend justified ([SPEC §12](../../SPEC.md)).
