# Steps · 18 · Peer comparison
> Read first: [SPEC.md](../../SPEC.md) (§7.17 peer comparison, §3/§5 Mode-A language, §6.1–6.2 correctness) · [Roadmap](../02-product-roadmap.md) (V3 / Phase 3) · [Feature modules](../04-feature-modules.md) (§19) · [Scanner engine](../13-scanner-engine-and-scoring.md) (peer params, §4.7 sector strength) · [API contracts](../10-api-contracts.md) (`GET /api/stocks/{symbol}/peers`) · [Screens](../08-screen-by-screen-documentation.md)

**Maps to:** Roadmap **V3** · SPEC Phase 3 · **Status:** Not started · **Regulatory mode:** A
**Prerequisites:** [02-indicators-and-scanners.md](02-indicators-and-scanners.md) (indicators, relative strength) · [16-scanners-extended.md](16-scanners-extended.md) (sector-strength scanner) · [04-ai-explanation-layer.md](04-ai-explanation-layer.md) (grounded AI, guardrails) · [05-api-and-pipeline.md](05-api-and-pipeline.md) · [06-frontend-foundation-and-v1-screens.md](06-frontend-foundation-and-v1-screens.md). Sentiment from [07-v2-accounts-watchlist-ai-news.md](07-v2-accounts-watchlist-ai-news.md).

## Overview
Peer comparison lets a user compare one instrument against its same-sector peers across descriptive technical (and, where available, valuation) metrics. **The single non-negotiable rule: comparison is comparative, NOT directive** ([SPEC §7.17](../../SPEC.md), [docs/04 §19](../04-feature-modules.md)). Permitted: *"INFY's 3-month relative strength is higher than TCS's; TCS trades closer to its 52-week high."* Prohibited: *"INFY is the better buy"*, *"switch from TCS to INFY"*, any ranking framed as a recommendation, any target/return claim.

This phase adds: **same-sector peer-set resolution** (from the sector classification master), a **comparison-metrics builder** reusing the indicator layer (performance, momentum, volume, RSI, MA trend, volatility, market cap, valuation-if-available, news sentiment, risk flags), a **comparative AI explanation** under the grounded facts-only contract, the `GET /api/stocks/{symbol}/peers` endpoint ([docs/10](../10-api-contracts.md)), and the **compare UI** (peer table/matrix). Every metric is reproducible from as-of versioned adjusted inputs ([SPEC §6.1–6.2](../../SPEC.md)); a missing metric for a peer is rendered as a gap (`data_confidence` per cell), never fabricated.

## Exit gate (Definition of Done)
- [ ] Peer set resolves to **same-sector** comparable names; the subject symbol is excluded from its own peer list; non-comparable / illiquid names are filtered via the eligibility gate ([docs/13 §3.1](../13-scanner-engine-and-scoring.md)).
- [ ] Every comparison cell is **reproducible** from as-of versioned adjusted inputs; a missing metric renders as a gap with `data_confidence`, never a guessed value ([SPEC §6.1–6.2](../../SPEC.md)).
- [ ] Valuation metrics appear **only when available**, are framed **descriptively** (band/relative), and never as "cheap → buy" ([SPEC §7.17](../../SPEC.md)).
- [ ] The comparative AI explanation references **only** values in the grounded payload; it is comparative, never directive; no "better buy"/"switch"/ranking-as-recommendation/target/return ([SPEC §3.3, §5](../../SPEC.md), [docs/13 §6](../13-scanner-engine-and-scoring.md)).
- [ ] `GET /api/stocks/{symbol}/peers` matches the contract ([docs/10](../10-api-contracts.md)): Bearer/Premium, `eod` cache, 60/min; returns the comparative table.
- [ ] The compare UI presents a comparison matrix with **no "buy"/"switch"/"best" CTA**; valuation cells carry a descriptive caveat; empty state when no peers mapped.

---
## Feature: Peer-set resolution  `(Mode A)`
**Objective:** Resolve the subject symbol's comparable same-sector peer set deterministically, filtered for liquidity/data quality. · **Backend dep:** sector classification master, eligibility gate ([16](16-scanners-extended.md)), market-cap band · **Frontend dep:** none · **Data dep:** sector/industry classification, market-cap band, listing status
### Steps
- [ ] 1. `app/peers/resolve.py`: resolve peers as **same sector (and, where available, same industry / market-cap band)** from the classification master; exclude the subject symbol itself; cap to a configurable top-N by liquidity. Mapping rules in **versioned config**, not constants.
- [ ] 2. Apply the shared eligibility gate ([docs/13 §3.1](../13-scanner-engine-and-scoring.md)) to candidate peers — drop penny/illiquid/quarantined/unreconciled names with a logged reason.
- [ ] 3. Carry `as_of_version` of the classification + price inputs into the resolved set; on no comparable peers, return an **empty** peer set (UI shows the empty state), never an unrelated fallback.
### Tests
- [ ] `tests/peers/test_resolve.py`: peers are same-sector; subject excluded from its own list; illiquid/quarantined peers dropped with logged reason; no-peer case returns empty (not a fabricated set).
### Compliance gate
- [ ] Peer set is a comparable cohort, not a "recommended alternatives" list; no ranking-as-recommendation in resolution ([docs/04 §19](../04-feature-modules.md)).
### Acceptance criteria
- [ ] Deterministic same-sector cohort, subject excluded, eligibility-filtered, as-of versioned; empty when none.

---
## Feature: Comparison-metrics builder  `(Mode A)`
**Objective:** Compute the comparable descriptive metrics for the subject + each peer, reusing the indicator layer; mark missing metrics as gaps, never guessed. · **Backend dep:** indicators ([02](02-indicators-and-scanners.md)), relative strength, news sentiment ([07](07-v2-accounts-watchlist-ai-news.md)), valuation source (if available) · **Frontend dep:** none · **Data dep:** adjusted OHLCV, RSI, SMAs, ATR%, volume ratio, market cap, valuation bands, sentiment
### Steps
- [ ] 1. `app/peers/metrics.py`: per symbol, compute the comparison row — **performance** (`change_pct_20d` and multi-window returns), **momentum** (relative strength vs sector/Nifty, `rs_3m`), **volume** (`vol_ratio`), **RSI** (`rsi_14` + band), **MA trend** (`above_50/200`, stacked), **volatility** (`atr_pct`), **market cap**, **valuation-if-available** (descriptive band, e.g. P/E vs sector range), **news sentiment** (resolved score), **risk** (the symbol's risk flags). Reuse the indicator functions; do not re-derive.
- [ ] 2. Each cell carries a per-cell `data_confidence`; a missing input → **gap** (rendered blank), never zero/guessed ([SPEC §6.2](../../SPEC.md)). Valuation is **omitted** entirely when no source is available — no placeholder.
- [ ] 3. Build the comparison record `{ subject, asOfDate, peers:[{ symbol, change_pct_20d, rsi_14, relative_strength, atr_pct, above_50dma, market_cap, valuation_band?, sentiment, riskFlags, data_confidence }] }` per [docs/10](../10-api-contracts.md); stamp `as_of_version`.
### Tests
- [ ] `tests/peers/test_metrics.py` (**critical-logic, golden**): every cell reproduces from a committed fixture vs hand-computed values; a peer missing valuation omits that cell (no placeholder); a missing close → cell gap with `data_confidence`, never zero.
### Compliance gate
- [ ] Metrics are descriptive facts; valuation framed as a band/relative, never "cheap → buy"; no composite "peer score" presented as a ranking ([SPEC §7.17](../../SPEC.md)).
### Acceptance criteria
- [ ] All cells reproducible from as-of versioned inputs; gaps marked not guessed; valuation only-if-available and descriptive.

---
## Feature: Comparative AI explanation  `(Mode A)`
**Objective:** A grounded, runtime-verified comparative summary that contrasts the subject with peers on facts — comparative, never directive. · **Backend dep:** grounded payload builder, comparison agent (cheap model), runtime verifier, guardrail filter, audit log ([04](04-ai-explanation-layer.md)) · **Frontend dep:** comparison summary text on the compare screen · **Data dep:** the comparison record (facts only)
### Steps
- [ ] 1. `app/peers/explanation_payload.py`: build the facts-only payload from the comparison record — subject row + peer rows, with the comparative deltas already computed (e.g. `rs_3m` differences, distance-from-52w-high). The agent may reference **nothing else** ([docs/13 §6](../13-scanner-engine-and-scoring.md)).
- [ ] 2. Generate via the comparison agent ([04](04-ai-explanation-layer.md)): output must be **comparative phrasing only** — "INFY's 3-month relative strength is higher than TCS's; TCS trades closer to its 52-week high". Prohibited: "the better buy", "switch", any ranking-as-recommendation, any target/return.
- [ ] 3. Runtime-verify every number against the payload (block/regenerate on mismatch); run the blocked-phrase guardrail at output time; write the generation to the AI audit log; suppress the summary when subject or a referenced peer has `data_confidence: LOW`.
### Tests
- [ ] `tests/peers/test_explanation.py`: a fabricated figure is blocked by the verifier; injecting "better buy"/"switch"/"target" is caught by the guardrail; LOW-confidence input suppresses the summary; every generation writes an audit row.
### Compliance gate
- [ ] Comparative only; passes the Compliance Review path before display; no "better buy"/"switch"/ranking-as-recommendation/always-prohibited phrase ([SPEC §3.3, §5](../../SPEC.md)).
### Acceptance criteria
- [ ] Every figure traces to the payload; comparative not directive; carries an `audit_id` + as-of date.

---
## Feature: Peers API + compare UI  `(Mode A)`
**Objective:** Serve the comparative table via the documented endpoint and render the compare matrix with no directive affordance. · **Backend dep:** peer resolution, metrics builder, comparison agent · **Frontend dep:** `PeerCompareTable`/`PeerCompareMatrix`, peer-strip entry from stock detail ([docs/04 §10](../04-feature-modules.md)) · **Data dep:** comparison record
### Steps
- [ ] 1. Implement `GET /api/stocks/{symbol}/peers` in `app/api/routes/stocks.py` per [docs/10](../10-api-contracts.md): Bearer (Premium), `eod` cache, 60/min; response `{ data:{ symbol, peers:[{ symbol, change_pct_20d, rsi_14, relative_strength, … }] } }`; empty `peers` when none mapped.
- [ ] 2. Build the compare screen per [docs/04 §19](../04-feature-modules.md) / [docs/08](../08-screen-by-screen-documentation.md): a comparison matrix (subject pinned, peers in columns/rows), per-cell gap rendering, a descriptive valuation caveat near valuation cells, the comparative AI summary, and an **empty state** when no peers mapped. **No "buy"/"switch"/"best"/ranking CTA.** Emit `peer_compare_view` analytics.
- [ ] 3. Premium-gating per the contract; show as-of date + confidence badges; "comparative, not advice" footer.
### Tests
- [ ] `tests/api/test_peers_contract.py`: endpoint matches the documented shape, auth, cache, and rate limit; empty `peers` returns cleanly; a non-Premium caller is gated.
- [ ] `tests/peers/test_ui_language.py` (or component test): no "buy"/"switch"/"best" CTA or copy; valuation caveat present; empty state renders when no peers.
### Compliance gate
- [ ] No directive CTA or ranking-as-recommendation on the surface; valuation descriptive; "comparative, not advice" present ([SPEC §7.17](../../SPEC.md), [docs/04 §19](../04-feature-modules.md)).
### Acceptance criteria
- [ ] Endpoint matches contract; matrix is comparative with gaps marked; no directive affordance; empty state handled.

---
## Done-when
- [ ] Peer set is a deterministic same-sector cohort (subject excluded, eligibility-filtered, as-of versioned); empty when none.
- [ ] Every comparison cell reproduces from as-of versioned adjusted inputs; gaps marked not guessed; valuation only-if-available and descriptive ([SPEC §6.1–6.2, §7.17](../../SPEC.md)).
- [ ] The comparative AI explanation is grounded, runtime-verified, comparative not directive, audit-logged ([docs/13 §6](../13-scanner-engine-and-scoring.md)).
- [ ] `GET /api/stocks/{symbol}/peers` matches the contract; the compare UI has no "buy"/"switch"/"best"/ranking affordance and no always-prohibited phrase ([docs/10](../10-api-contracts.md), [SPEC §3.3](../../SPEC.md)).
