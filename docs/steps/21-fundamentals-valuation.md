# Steps · 21 · Fundamentals & valuation

> Read first: [SPEC.md](../../SPEC.md) (§4 row "Fundamentals / valuation / earnings" 5.24–5.28 Phase 3, §3/§5 Mode-A language, §3.3 always-prohibited, §6.2 as-of versioning, §6.6 grounding, §8 licensing) · [Roadmap](../02-product-roadmap.md) (V4 descriptive parts / Phase 3) · [Feature modules](../04-feature-modules.md) (§10 stock page, §19 peer comparison) · [Data ingestion](../12-data-ingestion-and-market-data.md) (§3 sources, §8 licensing) · [API contracts](../10-api-contracts.md) · [Database](../11-database-architecture.md)

**Maps to:** Roadmap V4 (descriptive parts) · SPEC Phase 3
**Status:** Not started   |   **Regulatory mode:** A
**Prerequisites:** [01-local-mvp-foundation.md](01-local-mvp-foundation.md) (DataSource adapter, as-of-versioned store) · [05-api-and-pipeline.md](05-api-and-pipeline.md) (pipeline + envelope) · [06-frontend-foundation-and-v1-screens.md](06-frontend-foundation-and-v1-screens.md) (stock page) · [04-ai-explanation-layer.md](04-ai-explanation-layer.md) (payload contract, runtime verifier, guardrails, audit log) · sibling [16-scanners-extended.md](16-scanners-extended.md) (peer/comparison surfaces)

## Overview
This phase adds **fundamentals, valuation bands, and earnings summaries** to the stock page — the descriptive, Mode-A slice of the "Fundamentals / valuation / earnings" feature ([SPEC §4, rows 5.24–5.28](../../SPEC.md)). It ingests fundamentals **where licensed and available**, computes valuation multiples (P/E, P/B, EV/EBITDA, dividend yield) and positions each **as a descriptive band against the instrument's own history and its peers**, summarizes earnings releases factually, and renders all of it on the stock page beside the existing technical/scanner/risk panels.

**The single hardest rule (non-negotiable):** valuation is framed as a **descriptive band, NEVER a buy/sell trigger** ([SPEC §4, row 5.24–5.28](../../SPEC.md), [02 §7](../02-product-roadmap.md)). Permitted: *"P/E is 28, in the 82nd percentile of its 5-year range and above its sector median of 19 — historically an elevated band."* Prohibited: *"cheap, buy"* / *"overvalued, sell"* / *"undervalued — accumulate"* / any fair-value target or implied return. A high or low multiple is a **measurement of where the stock sits**, not a recommendation to act, exactly as RSI bands and scanner scores are descriptive ([02 §2](02-indicators-and-scanners.md), [SPEC §5](../../SPEC.md)).

**Licensing reality ([SPEC §8](../../SPEC.md)):** fundamentals depth is a **separate procurement and a gating dependency**, like adjusted-history depth. Free/unofficial fundamentals are **prototype-only**; a commercial product needs a licensed vendor with redistribution rights. Where a metric is unlicensed or unavailable for an instrument, the surface shows it as **unavailable, not guessed** ([SPEC §6.2](../../SPEC.md)) — the data gate, not a fabricated number.

## Exit gate (Definition of Done)
- [ ] Fundamentals ingest behind the `DataSource` adapter (licensed/available only), normalize to a canonical statement schema, and persist as-of versioned; an unlicensed/missing metric reads as **unavailable**, never a guessed value ([SPEC §6.2, §8](../../SPEC.md)).
- [ ] Valuation multiples (P/E, P/B, EV/EBITDA, dividend yield) compute reproducibly from persisted fundamentals + adjusted price, each carrying its inputs and `as_of_version`.
- [ ] Every valuation reading is a **descriptive band** (percentile vs own history + vs peer/sector median) with **no fair-value target, no buy/sell trigger, no implied return** — asserted by a contract test ([SPEC §3.3](../../SPEC.md)).
- [ ] Earnings summaries are grounded, runtime-verified (no invented numbers), retain source + as-of date, and pass the blocked-phrase guardrail at output time ([SPEC §6.6](../../SPEC.md)).
- [ ] The stock page renders fundamentals + valuation bands + earnings summary with a data-confidence badge and a "descriptive, not advice" caveat; no band, label, or summary contains an always-prohibited phrase ([SPEC §3.3](../../SPEC.md)).

---
## Feature: Fundamentals ingestion  `(Mode A · data-licensing gated)`
**Objective:** Ingest fundamentals (income statement, balance sheet, cash flow, key ratios, shares outstanding) **where licensed and available** behind the `DataSource` adapter, normalize to a canonical schema, and persist as-of versioned — with explicit unavailable handling where a metric is unlicensed or missing.
**Backend dep:** `DataSource.fetch_fundamentals`, normalizer, as-of-versioned store writer, data-confidence tagging · **Frontend dep:** none (consumed by valuation + display below) · **Data dep:** licensed fundamentals vendor (production) / prototype source (local); stock master (sector, ISIN); `data_quality_logs`.

### Steps
- [ ] 1. Extend the adapter in `app/data/sources/base.py`: `fetch_fundamentals(self, symbols, as_of)` and `supports("fundamentals")`; free/unofficial sources return `supports("redistribution") == False` and are **prototype-only** ([12 §3.1](../12-data-ingestion-and-market-data.md), [SPEC §8](../../SPEC.md)). Document the licensing note: fundamentals depth is a separate procurement / gating dependency.
- [ ] 2. `app/fundamentals/models.py`: canonical statement schema — `financials` (period, type ANNUAL|QUARTERLY, revenue, net_profit, ebitda, eps, book_value, shares_outstanding, debt, …) and `key_ratios` derived — keyed to `stock_id`, with `source`, `period_end`, `as_of_version` ([11 §3](../11-database-architecture.md)).
- [ ] 3. `app/fundamentals/ingest.py`: ingest → normalize → persist; a missing/unlicensed field is stored as **null with `availability=unavailable`**, never zero/guessed; restatements bump `as_of_version` (point-in-time preserved, [12 §4.1](../12-data-ingestion-and-market-data.md)).
- [ ] 4. Set `data_confidence` per instrument ([12 §4.2](../12-data-ingestion-and-market-data.md)): `high` for licensed+complete+fresh, `low`/`suppressed` for stale/partial; write a `data_quality_logs` row on gaps.

### Tests
- [ ] `tests/fundamentals/test_ingest.py`: a sample fundamentals payload normalizes to the canonical schema; an unlicensed/missing field stores as `unavailable`, never zero.
- [ ] A non-redistributable source is refused for commercial publish ([SPEC §8](../../SPEC.md)).
- [ ] A restatement bumps `as_of_version` and preserves the prior point-in-time record.

### Compliance gate
- [ ] Publishing is refused from a source lacking redistribution rights; the licensing note is documented ([SPEC §8](../../SPEC.md)).
- [ ] Missing/unlicensed metrics are `unavailable`, never guessed ([SPEC §6.2](../../SPEC.md)).

### Acceptance criteria
- [ ] Fundamentals ingest where licensed, normalize, and persist as-of versioned; unavailable data is explicit, not fabricated.

---
## Feature: Valuation bands (descriptive)  `(Mode A)`
**Objective:** Compute valuation multiples and position each as a **descriptive band** — percentile vs the instrument's own history and vs its peer/sector median — with **no fair-value target and no buy/sell trigger**.
**Backend dep:** multiple calculators (P/E, P/B, EV/EBITDA, dividend yield), historical-percentile + peer-median engine, descriptive-band classifier, versioned band config · **Frontend dep:** `ValuationPanel` (band chips + percentile + peer median), used by stock page and peer comparison ([04 §10, §19](../04-feature-modules.md)) · **Data dep:** persisted fundamentals, adjusted price, peer/sector mappings.

### Steps
- [ ] 1. `app/valuation/multiples.py`: compute `pe = price / eps_ttm`, `pb = price / book_value_per_share`, `ev_ebitda`, `dividend_yield` from persisted fundamentals + adjusted price ([01](01-local-mvp-foundation.md)); each result carries its inputs + `as_of_version`. A missing denominator → `unavailable`, never a forced value.
- [ ] 2. `app/valuation/bands.py`: for each multiple compute (a) its **percentile vs the instrument's own N-year history** and (b) its position **vs peer/sector median**; classify into descriptive bands `LOW / BELOW_HISTORICAL / IN_LINE / ABOVE_HISTORICAL / ELEVATED` — **measurement labels, not verdicts**. Thresholds/windows are **versioned config**, mirroring scanner-score governance ([02](02-indicators-and-scanners.md), [SPEC §6.5](../../SPEC.md)).
- [ ] 3. Build descriptive reason strings **only** from facts + band labels, e.g. *"P/E 28 sits in the 82nd percentile of its 5-year range and above its sector median of 19 — historically an elevated band"* — **no** "cheap"/"expensive as a call", no fair-value target, no implied return ([SPEC §5, §3.3](../../SPEC.md)).
- [ ] 4. Emit a facts-only valuation payload `{symbol, asOfDate, multiples, historicalPercentiles, peerMedians, bands, reasons}` consumable by the stock page, peer comparison ([16-scanners-extended.md](16-scanners-extended.md)), and the AI summarizer — **no forward price/target field**.
- [ ] 5. `GET /api/stocks/{symbol}/valuation` per [10](../10-api-contracts.md): multiples + bands + percentiles + peer medians; standard envelope + `data_confidence`; `unavailable` where ungated.

### Tests
- [ ] `tests/valuation/test_multiples.py` (**critical-logic**): P/E, P/B, EV/EBITDA reproduce from fixture fundamentals + adjusted price; a missing denominator yields `unavailable`, not a forced number.
- [ ] `tests/valuation/test_bands.py`: historical percentile + peer-median position + band label correct on a fixture; band thresholds read from versioned config.
- [ ] `tests/valuation/test_valuation_language.py` (**guardrail**): no reason/band/label contains "cheap, buy" / "overvalued, sell" / "undervalued" / a fair-value target / any always-prohibited phrase; the payload exposes **no forward-looking field** ([SPEC §3.3, §5](../../SPEC.md)).

### Compliance gate
- [ ] Valuation is a **descriptive band**, never a buy/sell trigger or fair-value target; bands are measurement labels ([SPEC §4 rows 5.24–5.28](../../SPEC.md), [02 §7](../02-product-roadmap.md)).
- [ ] No band, percentile, or reason implies an action or a return ([SPEC §3.3](../../SPEC.md)).

### Acceptance criteria
- [ ] Each multiple positions descriptively vs history + peers; every number reproducible from persisted inputs; no buy/sell framing anywhere.

---
## Feature: Earnings summaries & stock-page fundamentals  `(Mode A)`
**Objective:** Summarize earnings releases factually (grounded, runtime-verified, source-retained) and render fundamentals + valuation bands + earnings on the stock page beside the technical/risk panels, with a clear "descriptive, not advice" caveat.
**Backend dep:** `earnings_summary_v1` payload builder, summarizer under the payload contract, runtime verifier, blocked-phrase guardrail, audit logger (all from [04](04-ai-explanation-layer.md)/[14 §5](../14-ai-llm-agent-architecture.md)) · **Frontend dep:** stock-page `FundamentalsPanel` + `ValuationPanel` + `EarningsSummaryCard`, data-confidence badge, "descriptive, not advice" caveat ([04 §10](../04-feature-modules.md)) · **Data dep:** fundamentals, valuation payload, results announcement ([17-corporate-announcements.md](17-corporate-announcements.md) `results` category), source metadata.

### Steps
- [ ] 1. Build the `earnings_summary_v1` payload: latest-period financials, YoY/QoQ deltas, the valuation bands, and the linked `results` announcement ([17-corporate-announcements.md](17-corporate-announcements.md)) — the summarizer **may reference nothing else** ([SPEC §6.6](../../SPEC.md)).
- [ ] 2. Implement the summarizer enforcing factual wording: *"Q1 revenue rose 12% YoY; net profit up 8%; P/E sits in an elevated band vs its history"* — classification/measurement language, **no** "results beat — buy", no exaggeration of impact ([18 §8](../18-news-sentiment-and-corporate-actions.md), [SPEC §5](../../SPEC.md)).
- [ ] 3. Runtime-verify every number against the payload (block/regenerate on mismatch), run the blocked-phrase guardrail at output time, retain source + as-of date, and write to the AI audit log ([SPEC §6.6](../../SPEC.md)). On missing critical inputs, **suppress, never guess** ([12 §4.2](../12-data-ingestion-and-market-data.md)).
- [ ] 4. `GET /api/stocks/{symbol}/fundamentals` and `GET /api/stocks/{symbol}/earnings-summary` per [10](../10-api-contracts.md); premium-gated where the roadmap requires; standard envelope + `data_confidence`.
- [ ] 5. Extend the stock page ([04 §10](../04-feature-modules.md), [06](06-frontend-foundation-and-v1-screens.md)): fundamentals table, valuation band chips (percentile + peer median), earnings summary card; **data-confidence badge** and a **"Valuation bands are descriptive context, not investment advice"** caveat; **no** "buy"/"target"/"fair value" CTA.

### Tests
- [ ] `tests/fundamentals/test_earnings_language.py` (**guardrail**): injecting "results beat — buy" / a fair-value target / an exaggeration is caught at output time ([SPEC §3.3](../../SPEC.md)).
- [ ] An earnings summary referencing a figure not in the payload is blocked/regenerated.
- [ ] When fundamentals are unavailable, the panel reads "Fundamentals unavailable for this instrument" and the summary is suppressed, not guessed.
- [ ] Every generation writes an audit-log row (prompt id/version, payload hash, model id, grounding report).

### Compliance gate
- [ ] The earnings summary reports facts + descriptive bands; it never frames results as a buy/sell call or exaggerates impact ([18 §8](../18-news-sentiment-and-corporate-actions.md), [SPEC §5](../../SPEC.md)).
- [ ] The stock page carries the "descriptive, not advice" caveat; no panel contains an always-prohibited phrase ([SPEC §3.3](../../SPEC.md)); passes the Compliance Review Agent before display ([14 §5](../14-ai-llm-agent-architecture.md)).

### Acceptance criteria
- [ ] Fundamentals, descriptive valuation bands, and factual earnings summaries render on the stock page with confidence + caveat; every figure traces to the payload; no buy/sell framing ([04 §10](../04-feature-modules.md)).

---
## Done-when
- [ ] All three features pass their tests, compliance gates, and acceptance criteria; the Exit gate checklist is fully checked.
- [ ] Valuation is **descriptive bands only** (percentile vs history + peers), with **no fair-value target, no buy/sell trigger, no implied return** — proven by a contract test ([SPEC §3.3, §4 rows 5.24–5.28](../../SPEC.md), [02 §7](../02-product-roadmap.md)).
- [ ] Fundamentals ingest only where **licensed/available**; unlicensed/missing metrics read as `unavailable`, never guessed; the licensing note is documented ([SPEC §8, §6.2](../../SPEC.md)).
- [ ] Earnings summaries are grounded, runtime-verified, source-retained, audit-logged, and free of always-prohibited phrases ([SPEC §6.6, §3.3](../../SPEC.md)).
- [ ] Every displayed value is as-of versioned and reproducible from persisted inputs; the stock page carries a data-confidence badge and a "descriptive, not advice" caveat ([SPEC §6.2](../../SPEC.md), [04 §10](../04-feature-modules.md)).
