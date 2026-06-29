# Steps · 22 · Institutional activity

> Read first: [SPEC.md](../../SPEC.md) (§4 row "Institutional activity" 5.26 Phase 4 — *data-availability dependent*, §3/§5 Mode-A language, §3.3 always-prohibited, §6.2 as-of versioning, §6.6 grounding, §8 licensing) · [Roadmap](../02-product-roadmap.md) (Phase 4 / §8) · [Feature modules](../04-feature-modules.md) (§12 news, §16 risk) · [Data ingestion](../12-data-ingestion-and-market-data.md) (§3 sources, §4 quality, §8 licensing) · [API contracts](../10-api-contracts.md) · [Database](../11-database-architecture.md)

**Maps to:** Roadmap V9 premium depth (Phase 4 portions) · SPEC Phase 4
**Status:** Not started   |   **Regulatory mode:** A
**Prerequisites:** [01-local-mvp-foundation.md](01-local-mvp-foundation.md) (DataSource adapter, as-of-versioned store) · [05-api-and-pipeline.md](05-api-and-pipeline.md) (pipeline + envelope) · [04-ai-explanation-layer.md](04-ai-explanation-layer.md) (payload contract, runtime verifier, guardrails, audit log) · [06-frontend-foundation-and-v1-screens.md](06-frontend-foundation-and-v1-screens.md) (stock/sector pages) · siblings [17-corporate-announcements.md](17-corporate-announcements.md) (shareholding-pattern filings), [21-fundamentals-valuation.md](21-fundamentals-valuation.md)

## Overview
This phase adds **institutional-activity intelligence**: FII/DII net flows (market and, where available, sector level), bulk- and block-deal disclosures, and shareholding-pattern changes (FII/DII/promoter/pledge deltas across quarters). It displays them factually and adds **non-directive AI context** ("FIIs were net buyers for the third straight session") — never a directional call.

**The single hardest gate (non-negotiable): this is data-availability dependent ([SPEC §4 row 5.26](../../SPEC.md)).** Each sub-feature ships **only when its source is licensed and available** — exchange bulk/block-deal disclosures, FII/DII provisional/final flow files, and quarterly shareholding-pattern filings are **distinct procurements** with distinct cadence and reliability. Where a feed is unavailable for an instrument or date, the surface shows it as **unavailable, not estimated** ([SPEC §6.2, §8](../../SPEC.md)). The **data gate** is the first thing every feature below asserts: no institutional-activity surface is built on an unlicensed or guessed feed.

**Mode-A rule:** institutional activity is **factual, non-directive context**, exactly like news sentiment and valuation bands ([SPEC §5](../../SPEC.md)). Permitted: *"FIIs were net sellers of ₹2,400 cr today; a block deal of 1.2 cr shares was disclosed in TATAMOTORS."* Prohibited: *"FIIs are buying — buy"* / *"smart money accumulating, follow"* / any implied return. Bulk/block deals and flows are **disclosures and measurements**, never signals to act ([SPEC §3.3](../../SPEC.md)).

## Exit gate (Definition of Done)
- [ ] Each sub-feature is **gated on its data source**: it activates only when the feed is licensed/available, and a missing feed reads as **unavailable**, never estimated ([SPEC §4 row 5.26, §6.2, §8](../../SPEC.md)).
- [ ] FII/DII flows, bulk/block deals, and shareholding-pattern deltas ingest behind the `DataSource` adapter, normalize to canonical schemas, and persist as-of versioned with `data_confidence`.
- [ ] Every institutional-activity surface and AI context line is **factual and non-directive** — no "follow the smart money", no buy/sell framing, no implied return — asserted by a contract test ([SPEC §3.3](../../SPEC.md)).
- [ ] AI context lines are grounded, runtime-verified (no invented figures), retain source + as-of date, and pass the blocked-phrase guardrail at output time ([SPEC §6.6](../../SPEC.md)).
- [ ] Bulk/block-deal counterparty data, where available, is displayed as the disclosed fact only — never inferred or used to imply intent.

---
## Feature: FII/DII flows  `(Mode A · data-availability gated)`
**Objective:** Ingest and display FII/DII net-flow data (market level; sector/instrument level **where the feed provides it**), with factual trend context — gated on feed availability.
**Backend dep:** `DataSource.fetch_institutional_flows`, flow normalizer, net/trend aggregator, as-of-versioned store, availability gate · **Frontend dep:** `FlowsPanel` on market dashboard + sector page (net buy/sell, multi-session trend) ([04 §1, §8](../04-feature-modules.md)) · **Data dep:** licensed FII/DII flow feed (provisional + final); availability differs by level (market always, sector/instrument feed-dependent).

### Steps
- [ ] 1. Extend the adapter: `fetch_institutional_flows(self, session_date)` + `supports("institutional_flows")`; **availability gate** — if unsupported/unlicensed, the feature renders "unavailable", never an estimate ([12 §3.1](../12-data-ingestion-and-market-data.md), [SPEC §8](../../SPEC.md)).
- [ ] 2. `app/institutional/flows_models.py`: canonical flow record (`session_date`, `level` MARKET|SECTOR|SYMBOL, `entity` FII|DII, `gross_buy`, `gross_sell`, `net`, `provisional` bool, `source`, `as_of_version`); provisional flows are flagged and superseded by final on `as_of_version` bump ([12 §4.1](../12-data-ingestion-and-market-data.md)).
- [ ] 3. `app/institutional/flows.py`: aggregate net flow + multi-session trend (e.g. "net buyers N of last M sessions") as **facts**; no directional inference.
- [ ] 4. `GET /api/institutional/flows` and `GET /api/sectors/{sector}/flows` per [10](../10-api-contracts.md); standard envelope + `data_confidence`; `unavailable` where ungated. Build `FlowsPanel`: net buy/sell + trend, "provisional" badge, "factual disclosure, not advice" caveat; **no** "follow flows" CTA.

### Tests
- [ ] `tests/institutional/test_flows.py`: net + multi-session trend reproduce from a fixture; a provisional record is flagged and superseded by final via `as_of_version`.
- [ ] When the flow feed is unavailable, the panel reads "unavailable" and no number is estimated ([SPEC §6.2](../../SPEC.md)).
- [ ] A non-redistributable source is refused for commercial publish ([SPEC §8](../../SPEC.md)).

### Compliance gate
- [ ] Flows are **factual disclosures**, non-directive; no "follow the smart money" / buy-sell framing ([SPEC §3.3, §5](../../SPEC.md)).
- [ ] The feature is gated on feed availability; missing data is `unavailable`, not estimated ([SPEC §4 row 5.26, §6.2](../../SPEC.md)).

### Acceptance criteria
- [ ] FII/DII net flows + trend display factually where the feed exists; provisional vs final handled; no directional call.

---
## Feature: Bulk & block deals  `(Mode A · data-availability gated)`
**Objective:** Ingest exchange bulk- and block-deal disclosures, map each to its symbol, and display the disclosed deal (quantity, price, counterparty where disclosed) factually — gated on feed availability.
**Backend dep:** `DataSource.fetch_deals` (bulk/block), normalizer, symbol mapping (reused from ingestion [12 §1](../12-data-ingestion-and-market-data.md)), as-of-versioned store, availability gate · **Frontend dep:** `DealsPanel` on stock page + a market deals feed ([04 §10](../04-feature-modules.md)) · **Data dep:** NSE/BSE bulk/block-deal disclosure feed (EOD); symbol-alias map.

### Steps
- [ ] 1. Extend the adapter: `fetch_deals(self, session_date)` + `supports("bulk_block_deals")`; availability gate as above ([SPEC §8](../../SPEC.md)).
- [ ] 2. `app/institutional/deals_models.py`: canonical deal record (`session_date`, `deal_type` BULK|BLOCK, `symbol`, `client_name` *as disclosed*, `side` BUY|SELL, `quantity`, `weighted_avg_price`, `source`, `as_of_version`); map to `stock_id` ([12 §1](../12-data-ingestion-and-market-data.md)).
- [ ] 3. `app/institutional/deals.py`: surface the disclosed deal as a **fact** — display counterparty **only as disclosed**, never infer intent ("accumulating"/"exiting") from a single disclosure.
- [ ] 4. `GET /api/stocks/{symbol}/deals` and `GET /api/institutional/deals` per [10](../10-api-contracts.md); envelope + `data_confidence`. Build `DealsPanel`: deal list with type/side/qty/price/counterparty + source + as-of date; **no** intent inference, **no** "follow" CTA.

### Tests
- [ ] `tests/institutional/test_deals.py`: a sample bulk/block disclosure normalizes, maps to the right symbol, and renders the disclosed fields only.
- [ ] No deal surface infers intent or direction from the disclosure (guardrail assertion).
- [ ] When the deals feed is unavailable, the panel reads "unavailable", not estimated.

### Compliance gate
- [ ] Deals are **disclosed facts**; counterparty/intent is never inferred; no buy/sell or "follow" framing ([SPEC §3.3, §5](../../SPEC.md)).
- [ ] Gated on feed availability; missing data is `unavailable` ([SPEC §4 row 5.26](../../SPEC.md)).

### Acceptance criteria
- [ ] Bulk/block deals display factually with disclosed fields + source where the feed exists; no intent inference, no directive.

---
## Feature: Shareholding-pattern changes & non-directive AI context  `(Mode A · data-availability gated)`
**Objective:** Track quarterly shareholding-pattern deltas (FII/DII/promoter holding, promoter pledge) and add **factual, non-directive AI context** across the institutional-activity surfaces — gated on feed availability.
**Backend dep:** `DataSource.fetch_shareholding_pattern`, quarter-over-quarter delta engine, as-of-versioned store, availability gate, `institutional_context_v1` payload builder + summarizer/verifier/guardrail/audit (from [04](04-ai-explanation-layer.md)/[14 §5](../14-ai-llm-agent-architecture.md)) · **Frontend dep:** `ShareholdingPanel` (QoQ deltas, pledge trend) on stock page + context line on flows/deals panels ([04 §10, §16](../04-feature-modules.md)) · **Data dep:** quarterly shareholding-pattern filings (links to [17-corporate-announcements.md](17-corporate-announcements.md) `shareholding_change`/`pledging`); flows + deals payloads.

### Steps
- [ ] 1. Extend the adapter: `fetch_shareholding_pattern(self, symbols, quarter)` + `supports("shareholding_pattern")`; availability gate ([SPEC §8](../../SPEC.md)). Source overlaps with [17](17-corporate-announcements.md) `shareholding_change`/`pledging` filings — reuse, don't duplicate.
- [ ] 2. `app/institutional/shareholding_models.py`: canonical record (`symbol`, `quarter`, `fii_pct`, `dii_pct`, `promoter_pct`, `promoter_pledge_pct`, `public_pct`, `source`, `as_of_version`); compute **QoQ deltas** as facts.
- [ ] 3. Flag a **rising promoter pledge** as a factual risk marker (feeds the risk engine [16 §3](../16-portfolio-and-risk-engine.md), mirroring its "promoter pledges shares → governance/risk signal" treatment, [18 §7.1](../18-news-sentiment-and-corporate-actions.md)) — a **fact/flag**, never "sell".
- [ ] 4. Build the `institutional_context_v1` payload (flows trend, recent deals, shareholding deltas, pledge trend — facts only) and the summarizer enforcing **non-directive** wording: *"FIIs raised their stake 1.8 pts QoQ; promoter pledge rose to 22%"* — never "smart money is buying — follow". The summarizer **may reference nothing else** ([SPEC §6.6](../../SPEC.md)).
- [ ] 5. Runtime-verify every figure against the payload (block/regenerate on mismatch), run the blocked-phrase guardrail at output time, retain source + as-of date, write to the AI audit log; **suppress on missing input, never guess** ([12 §4.2](../12-data-ingestion-and-market-data.md), [SPEC §6.6](../../SPEC.md)).
- [ ] 6. `GET /api/stocks/{symbol}/shareholding` and `GET /api/stocks/{symbol}/institutional-context` per [10](../10-api-contracts.md). Build `ShareholdingPanel` (QoQ deltas, pledge trend) + context line; "factual context, not advice" caveat; **no** directive.

### Tests
- [ ] `tests/institutional/test_shareholding.py`: QoQ deltas reproduce from two quarters; a rising-pledge case sets the factual risk marker.
- [ ] `tests/institutional/test_institutional_language.py` (**guardrail, contract**): across flows/deals/shareholding context, **no** "follow the smart money" / "buy"/"sell"/"accumulate" / implied return / any always-prohibited phrase; payload exposes no forward-looking field ([SPEC §3.3, §5](../../SPEC.md)).
- [ ] A context line referencing a figure not in the payload is blocked/regenerated; every generation writes an audit-log row.
- [ ] When the shareholding feed is unavailable, the panel reads "unavailable" and the context is suppressed, not guessed.

### Compliance gate
- [ ] All institutional context is **factual and non-directive**; a rising pledge is a fact/flag, never "sell" ([SPEC §3.3, §5](../../SPEC.md)).
- [ ] Gated on feed availability; passes the Compliance Review Agent before display ([14 §5](../14-ai-llm-agent-architecture.md)); no always-prohibited phrase anywhere.

### Acceptance criteria
- [ ] Shareholding deltas + pledge trend display factually; AI context is non-directive, grounded, verified, and audit-logged; all gated on feed availability ([SPEC §4 row 5.26](../../SPEC.md)).

---
## Done-when
- [ ] All three features pass their tests, compliance gates, and acceptance criteria; the Exit gate checklist is fully checked.
- [ ] Every sub-feature is **gated on its data source**: it activates only on a licensed/available feed, and missing data reads as **unavailable**, never estimated ([SPEC §4 row 5.26, §6.2, §8](../../SPEC.md)).
- [ ] All institutional-activity display and AI context is **factual and non-directive** — no "follow the smart money", no buy/sell framing, no inferred intent, no implied return — proven by a contract test ([SPEC §3.3, §5](../../SPEC.md)).
- [ ] AI context is grounded, runtime-verified, source-retained, and audit-logged; suppressed (not guessed) on missing input ([SPEC §6.6](../../SPEC.md)).
- [ ] Shareholding/pledge facts feed the risk engine as factual markers ([16 §3](../16-portfolio-and-risk-engine.md)); shareholding-pattern ingestion reuses [17-corporate-announcements.md](17-corporate-announcements.md) filings rather than duplicating them.
