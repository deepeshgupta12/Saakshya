# Steps · 12 · V7 — Live Licensed Data & Real-Time
> Read first: [SPEC.md](../../SPEC.md) (§8 data strategy & licensing, §4 "Live / real-time" row, §10 Phase 5) · [Roadmap](../02-product-roadmap.md) (§10 V7) · [Data ingestion](../12-data-ingestion-and-market-data.md) (§3 layered sources, §3.2 future live data) · [Compliance & guardrails](../21-compliance-risk-and-guardrails.md) · [Security, auth & privacy](../23-security-auth-and-privacy.md)

**Maps to:** Roadmap V7 · SPEC Phase 5
**Status:** Not started — GATED   |   **Regulatory mode:** A\* (Mode-A-safe in **content**, but gated on **data licensing**)
**Gate (must be met before ANY build starts):** A **signed licensed live/real-time (intraday) data agreement with explicit commercial redistribution rights** is in force ([SPEC §8](../../SPEC.md), [§4 Live row](../../SPEC.md)). **No unofficial/free or scraped real-time feed may be used in production** — free/unofficial sources are prototype-only and the platform refuses to publish commercially from a source where `supports("redistribution") == False` ([SPEC §8](../../SPEC.md), [docs/12 §3.1](../12-data-ingestion-and-market-data.md)). Until the live-data license is signed, this file is **plan-only**.
**Prerequisites:** Phase 5 reached; the EOD `DataSource` adapter, scanners, alerts, and watchlist already shipped (V1–V3). Data-vendor + redistribution groundwork from [00-phase-0-derisk.md](00-phase-0-derisk.md).

## Overview
V7 adds a **separately-licensed live/intraday tier** behind the **existing `DataSource` adapter** — streaming ingestion over WebSocket, near-real-time scanners/alerts, and a live watchlist — without touching the scanner, indicator, or AI business logic ([SPEC §8](../../SPEC.md), [docs/12 §3.2](../12-data-ingestion-and-market-data.md)). The content is **Mode-A-safe** (descriptive scanners, event-reporting alerts), so the gate here is **commercial, not advisory**: licensed real-time data with redistribution rights. Live data does **not** change what may be *said* — alerts remain event-reporting, never prescriptive ([SPEC §4 Live row](../../SPEC.md), [Roadmap §10](../02-product-roadmap.md)).

**Why the licensing gate is front-and-center:** real-time NSE/BSE data is the most aggressively licensed feed in the stack. Shipping it from an unlicensed source is both a contractual breach and a redistribution violation. These steps describe **what to build once the license is in force** — not a license to wire up an unofficial feed early.

## Exit gate (Definition of Done)
- [ ] **Signed live-data license with commercial redistribution rights** is in force; the live adapter's `supports("redistribution")` is `True` and gates commercial publish ([SPEC §8](../../SPEC.md), [docs/12 §3.1](../12-data-ingestion-and-market-data.md)).
- [ ] Live feed lands **behind the same `DataSource` adapter** with a streaming capability flag; scanners/indicators/AI are unchanged ([docs/12 §3.2](../12-data-ingestion-and-market-data.md)).
- [ ] WebSocket streaming ingestion is in place with backpressure, reconnect, and a defined latency budget ([SPEC §6.8](../../SPEC.md)).
- [ ] Near-real-time scanners + alerts run on live data; **alerts remain event-reporting, never prescriptive** ([SPEC §4 Live row](../../SPEC.md), [compliance §3.2](../21-compliance-risk-and-guardrails.md)).
- [ ] The live tier respects rate limits, AI-spend ceiling, and the security controls for the new streaming surface ([docs/23 §7](../23-security-auth-and-privacy.md)).
- [ ] Licensing decision + redistribution rights logged ([decision log](../30-decision-log.md)).

---
## Feature: License the live feed + plan the integration  `(Mode A* — licensing gate)`
**Objective:** Secure the signed live/intraday data agreement with redistribution rights before any code, and confirm scope (instruments, exchanges, depth, latency, cost) ([SPEC §8](../../SPEC.md)). · **Backend dep:** none (procurement) · **Frontend dep:** none · **Data dep:** the entire feature gates on this.
### Steps
- [ ] 1. **Owner: Founder/Legal.** Negotiate and sign the **live/real-time data license** (e.g. TrueData / Global Datafeeds live tier or peer) with explicit **commercial redistribution rights**, corp-action handling, symbol mapping, and latency SLAs ([SPEC §8](../../SPEC.md), [docs/12 §3](../12-data-ingestion-and-market-data.md)). **Artifact:** signed live-data contract.
- [ ] 2. **Owner: Legal.** Confirm redistribution scope: what the license permits showing to which tier of users, and any exchange display-fee obligations. **Artifact:** redistribution scope memo.
- [ ] 3. **Owner: Eng.** Confirm the live source will drop behind the **existing `DataSource` adapter** with a streaming capability (`supports("streaming")`), touching no scanner/indicator/AI code ([docs/12 §3.1–3.2](../12-data-ingestion-and-market-data.md)). **Artifact:** integration design referencing the adapter interface.
- [ ] 4. **Owner: Founder.** Log the decision and rights in the [decision log](../30-decision-log.md).
### Tests / Compliance gate / Acceptance criteria
- [ ] N/A (procurement). Verification = signed contract + redistribution scope memo on file.
- [ ] **Compliance gate:** no live-feed code is written until the signed license is in hand; the platform refuses to publish from a non-redistributable source ([SPEC §8](../../SPEC.md)).

---
## Feature: Live adapter behind the existing `DataSource` interface  `(Mode A*)`
**Objective:** Implement the live source as an adapter conforming to the existing `DataSource` interface plus a streaming capability, so business logic stays vendor-agnostic ([docs/12 §3.1–3.2](../12-data-ingestion-and-market-data.md)). · **Backend dep:** existing adapter + capability flags · **Frontend dep:** none · **Data dep:** licensed live feed.
### Steps
- [ ] 1. Add a **streaming capability** to the adapter contract (`supports("streaming")`) and a `subscribe(symbols) -> stream[Tick]` method alongside the existing `fetch_eod` / `fetch_delivery` ([docs/12 §3.1](../12-data-ingestion-and-market-data.md)).
- [ ] 2. Implement the live adapter; set `supports("redistribution") == True` only because the signed license permits it ([docs/12 §3.1](../12-data-ingestion-and-market-data.md)).
- [ ] 3. Normalize live ticks into the **canonical schema** and apply **as-of versioning + data-confidence** the same way EOD does ([docs/12 §0, §4.2](../12-data-ingestion-and-market-data.md), [SPEC §6.2](../../SPEC.md)).
- [ ] 4. Keep EOD as the system of record; live data is an **additive tier**, not a replacement for the authoritative EOD reconciliation ([docs/12 §0](../12-data-ingestion-and-market-data.md)).
### Tests / Compliance gate / Acceptance criteria
- [ ] The live source swaps in **without touching scanners/indicators/AI** (vendor-swap test) ([SPEC §8](../../SPEC.md), [docs/12 acceptance](../12-data-ingestion-and-market-data.md)).
- [ ] Commercial publish is refused if `supports("redistribution") == False` (regression test).
- [ ] Live ticks carry `data_confidence`; missing/stale → degraded confidence, not a guess ([SPEC §6.2](../../SPEC.md)).

---
## Feature: WebSocket streaming ingestion  `(Mode A*)`
**Objective:** Stand up the WebSocket streaming tier with reliable, observable ingestion under a latency budget ([docs/12 §3.2](../12-data-ingestion-and-market-data.md), [SPEC §6.8](../../SPEC.md)). · **Backend dep:** streaming adapter, message broker/buffer · **Frontend dep:** live data channel to the client · **Data dep:** licensed live stream.
### Steps
- [ ] 1. Build the **streaming ingestion service**: subscribe via the live adapter, buffer ticks, apply backpressure, and fan out to consumers (scanners, watchlist, client channel).
- [ ] 2. Handle **connection lifecycle**: authenticated connect (vendor creds from Secrets Manager — never in code/logs, [docs/23 §3](../23-security-auth-and-privacy.md)), heartbeat, reconnect with replay/gap-fill, and graceful degradation to EOD on outage.
- [ ] 3. Enforce a **latency budget** with observability (ingest → scanner → alert → client P95) ([SPEC §6.8](../../SPEC.md)).
- [ ] 4. Apply **rate limiting + WAF** to the new streaming/API surface; live endpoints are stricter (cost + abuse) ([docs/23 §7](../23-security-auth-and-privacy.md)).
### Tests / Compliance gate / Acceptance criteria
- [ ] Reconnect + gap-fill recover cleanly after a simulated outage; on sustained outage the system degrades to EOD ([docs/12 §0](../12-data-ingestion-and-market-data.md)).
- [ ] Latency P95 within budget under load; backpressure prevents unbounded buffering.
- [ ] Vendor credentials are loaded from Secrets Manager and never appear in code/images/logs ([docs/23 §3](../23-security-auth-and-privacy.md)).

---
## Feature: Near-real-time scanners & alerts  `(Mode A*)`
**Objective:** Run the existing (Mode-A) scanners and alerting on live data with a near-real-time cadence, keeping alerts **event-reporting only** ([SPEC §4 Live row](../../SPEC.md), [compliance §3.2](../21-compliance-risk-and-guardrails.md)). · **Backend dep:** scanner engine, alert evaluation, streaming fan-out · **Frontend dep:** real-time alert delivery · **Data dep:** live ticks + computed indicators.
### Steps
- [ ] 1. Run scanners on a **near-real-time cadence** (incremental recompute on tick batches) reusing the same scoring logic — no new scanner semantics, no buy-lean language ([SPEC §4](../../SPEC.md)).
- [ ] 2. Evaluate **alerts in near-real-time**: alerts report **events** ("entered the momentum scanner", "broke its 50-DMA intraday"), never "buy at open" or any prescription ([SPEC §4 Live row](../../SPEC.md), [compliance §3.2, §4](../21-compliance-risk-and-guardrails.md)).
- [ ] 3. Route any AI-generated alert text through the **output-time guardrail pipeline** (regex + grounding + compliance-review) ([compliance §9](../21-compliance-risk-and-guardrails.md)).
- [ ] 4. Add **noise controls**: debounce/dedupe so live alerts don't spam on chop; user-configurable thresholds.
### Tests / Compliance gate / Acceptance criteria
- [ ] **Compliance gate:** real-time alerts are event-reporting only; a directive phrasing in a live alert is blocked at output time ([compliance §9, §3.2](../21-compliance-risk-and-guardrails.md)).
- [ ] Scanner scores on live data match the validated EOD semantics; no new directive output paths introduced.
- [ ] Alert debounce/dedupe prevents duplicate/chop spam (test).

---
## Feature: Live watchlist  `(Mode A*)`
**Objective:** Add a real-time watchlist view that streams live prices/scanner membership for the user's tracked instruments, as filter-based discovery — not per-user buy-leans ([SPEC §4 Watchlist/Live rows](../../SPEC.md)). · **Backend dep:** streaming fan-out, watchlist store, entitlement check · **Frontend dep:** live watchlist UI + client streaming channel · **Data dep:** live ticks for subscribed symbols.
### Steps
- [ ] 1. Stream live updates for a user's watchlist symbols (price, scanner-membership changes), row-scoped to the authenticated user ([docs/23 §2](../23-security-auth-and-privacy.md)).
- [ ] 2. Gate the live watchlist behind the appropriate **premium tier entitlement** (authz check, not a separate URL) ([docs/23 §2](../23-security-auth-and-privacy.md)).
- [ ] 3. Keep watchlist content **descriptive** — membership and events, never "candidate" buy-leans or per-stock levels ([compliance §4, §5.1](../21-compliance-risk-and-guardrails.md), [SPEC §4](../../SPEC.md)).
- [ ] 4. Respect per-user subscription limits on live symbol count (cost control) ([docs/23 §7](../23-security-auth-and-privacy.md), [SPEC §6.8](../../SPEC.md)).
### Tests / Compliance gate / Acceptance criteria
- [ ] A user cannot stream another user's watchlist (IDOR test) ([docs/23 §2](../23-security-auth-and-privacy.md)).
- [ ] Live watchlist shows only descriptive membership/events; no buy-lean "candidate" labels ([compliance §5.1](../21-compliance-risk-and-guardrails.md)).
- [ ] Subscription/symbol-count limits enforced.

---
## Done-when
- [ ] A **signed live-data license with redistribution rights is in force**; the live adapter gates commercial publish on it ([SPEC §8](../../SPEC.md)).
- [ ] Live data lands behind the existing `DataSource` adapter via a streaming capability; scanners/indicators/AI unchanged ([docs/12 §3.2](../12-data-ingestion-and-market-data.md)).
- [ ] WebSocket ingestion runs within a latency budget with reconnect/gap-fill and stricter rate-limiting/WAF ([SPEC §6.8](../../SPEC.md), [docs/23 §7](../23-security-auth-and-privacy.md)).
- [ ] Near-real-time scanners + alerts and a live watchlist ship as **Mode-A-safe, event-reporting** features — never prescriptive ([SPEC §4 Live row](../../SPEC.md), [compliance §3.2](../21-compliance-risk-and-guardrails.md)).
- [ ] Licensing + redistribution decision logged ([decision log](../30-decision-log.md)).
