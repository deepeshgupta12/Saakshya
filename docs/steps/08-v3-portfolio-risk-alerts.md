# Steps · 08 · V3 — Portfolio, Risk & Alerts
> Read first: [SPEC.md](../../SPEC.md) · [Roadmap](../02-product-roadmap.md) · [Portfolio & risk engine](../16-portfolio-and-risk-engine.md) · [Alerts & notifications](../17-alerts-and-notifications.md) · [AI architecture](../14-ai-llm-agent-architecture.md) · [News & sentiment](../18-news-sentiment-and-corporate-actions.md) · [API contracts](../10-api-contracts.md) · [Screens](../08-screen-by-screen-documentation.md)

**Maps to:** Roadmap V3 · SPEC Phase 2–3
**Status:** Complete   |   **Regulatory mode:** A
**Prerequisites:** [04-ai-explanation-layer.md](04-ai-explanation-layer.md) · [05-api-and-pipeline.md](05-api-and-pipeline.md) · [06-frontend-foundation-and-v1-screens.md](06-frontend-foundation-and-v1-screens.md) · [07-v2-accounts-watchlist-ai-news.md](07-v2-accounts-watchlist-ai-news.md)

## Overview
V3 lets a user track holdings and receive **factual, event-reporting** risk signals and alerts. It adds the **portfolio tracker** (manual holdings reconstructed from a transaction ledger, FIFO cost basis, P&L, allocation), the **risk engine** (concentration/sector/volatility/news/technical-breakdown components + a portfolio health score), the **portfolio AI summary** (Mode-A wording, grounded), and the **alerts/notifications system** (event-reporting types, EOD evaluation after the scanner run, in-app/email/push channels, throttling, delivery logs).

**The single hardest rule (non-negotiable):** in Mode A, portfolio risk output is **factual event reporting, never prescription** ([16 §0](../16-portfolio-and-risk-engine.md)). Permitted: *"You hold TATAMOTORS; it closed below its 50-DMA today."* Prohibited: *"Sell TATAMOTORS"* / *"Reduce your position"* / *"Book profit."* **Per-stock stop-loss / target / entry / invalidation zone monitoring is RA-gated (Mode B, Phase 5) and is NOT built or surfaced in v1** — it is documented in the engine/schema only for forward-compatibility, and a contract test asserts no Mode-A response ever contains it ([16 §3.3](../16-portfolio-and-risk-engine.md), [17 §3](../17-alerts-and-notifications.md)).

This phase depends on V2 accounts (row-scoping, RBAC, audit log), the AI explanation layer, and the news/impact outputs from [07](07-v2-accounts-watchlist-ai-news.md). Holdings are **sensitive financial data** treated as PII-class ([23 §5](../23-security-auth-and-privacy.md)).

## Exit gate (Definition of Done)
- [ ] Holdings reconstruct from a transaction ledger; a 1:2 split and 1:1 bonus leave `invested_value` unchanged with correct quantity/avg cost (never reads as a loss) ([16 §1.5](../16-portfolio-and-risk-engine.md)).
- [ ] Realized P&L matches a hand-computed FIFO worked example to the paisa; a missing close yields `data_confidence: LOW` and **suppresses the AI summary, never guesses** ([16 §1.5](../16-portfolio-and-risk-engine.md)).
- [ ] Every risk component returns with its underlying evidence; the portfolio health score is reproducible from components + versioned weights ([16 §3–4](../16-portfolio-and-risk-engine.md)).
- [ ] No Mode-A API response contains `stop_loss_zone`, `target_zone`, or any `ra_gated` field — asserted by a contract test ([16 §8](../16-portfolio-and-risk-engine.md)).
- [ ] Portfolio AI summary passes runtime verification + guardrails; holdings notes are **factual event statements**, never "sell X" ([16 §5](../16-portfolio-and-risk-engine.md)).
- [ ] Alerts evaluate **only after the EOD refresh completes**; are **event-reporting only**; every template passes the blocked-phrase validator at output time ([17 §1–2](../17-alerts-and-notifications.md)).
- [ ] RA-gated SL/target alert types are unreachable in Mode A (contract test); throttling/dedup bound noise; every send writes a delivery-log row ([17 §3, §5–6](../17-alerts-and-notifications.md)).

---
## Feature: Portfolio tracker  `(Mode A)`
**Objective:** Manual holdings reconstructed from a transaction ledger (the source of truth), with FIFO cost basis, EOD valuation, P&L, and allocation views — corp-action-correct through splits/bonuses.
**Backend dep:** transaction ledger, FIFO/WAVG reducer, corp-action transaction synthesizer, as-of price join, aggregation service · **Frontend dep:** `PortfolioSummaryCard`, `PortfolioTable`, `AddHoldingDialog`/`ImportDialog` ([08 §9](../08-screen-by-screen-documentation.md)) · **Data dep:** `corporate_actions` master, as-of-versioned EOD closes, stock master (sector, market-cap band).

### Steps
- [ ] 1. Create the portfolio data model in `app/storage/migrations/`: `portfolios` (id, user_id, `cost_basis_method` FIFO|WEIGHTED_AVG), `transactions` (the source of truth: type BUY/SELL/BONUS/SPLIT/DIVIDEND/RIGHTS/MERGER_IN/MERGER_OUT, qty, price, trade_date, charges, source, `as_of_version`), `positions` (derived), `portfolio_snapshots` (daily valuation) per [16 §1](../16-portfolio-and-risk-engine.md). Encrypt holdings fields (PII-class, [23 §5](../23-security-auth-and-privacy.md)).
- [ ] 2. Implement the position reducer in `app/portfolio/positions.py`: reconstruct `quantity`, `avg_buy_price`, `invested_value`, realized P&L (default **FIFO**) from the ledger; recompute on corp actions ([16 §1.3–1.5](../16-portfolio-and-risk-engine.md)).
- [ ] 3. Implement the corp-action transaction **synthesizer**: synthesize BONUS/SPLIT/DIVIDEND/RIGHTS transactions from the `corporate_actions` master so a 1:1 bonus doubles quantity and halves avg cost (never a 50% loss) ([16 §1.2](../16-portfolio-and-risk-engine.md), [SPEC §6.1](../../SPEC.md)).
- [ ] 4. Value positions against as-of EOD closes; on a missing/quarantined close, mark the position `data_confidence: LOW` and suppress its AI summary — never guess ([16 §1.4](../16-portfolio-and-risk-engine.md)).
- [ ] 5. Build aggregate analytics in `app/portfolio/analytics.py`: totals, day change, and allocation views (stock / sector / market-cap), weights summing to 100% (±0.1) ([16 §2](../16-portfolio-and-risk-engine.md)).
- [ ] 6. Implement the API in `app/api/routes/portfolio.py` per [10 §7](../10-api-contracts.md): `POST /api/portfolio/holdings`, `GET /api/portfolio/summary`, `GET /portfolio/{id}/overview`, `GET /portfolio/{id}/positions`, `POST /portfolio/{id}/transactions` ([16 §8](../16-portfolio-and-risk-engine.md)). Premium-gated.
- [ ] 7. Build the portfolio screen per [08 §9](../08-screen-by-screen-documentation.md): holdings table, sector-allocation (descriptive), import dialog with row-level validation, **no "sell"/"rebalance" CTA**; state P&L is the user's own data, not a return claim; "Saakshya does not compute tax liability" surfaced near realized P&L ([16 §1.5](../16-portfolio-and-risk-engine.md)).

### Tests
- [ ] A 1:2 split and a 1:1 bonus on a test symbol leave `invested_value` unchanged and `quantity`/`avg_buy_price` correct ([16 §1.5](../16-portfolio-and-risk-engine.md)).
- [ ] Realized P&L matches a hand-computed FIFO worked example to the paisa.
- [ ] A missing close yields `data_confidence: LOW` and suppresses the AI summary, never a guessed value.
- [ ] Allocation weights sum to 100% (±0.1); a single-stock portfolio shows 100% concentration in that stock and its sector.
- [ ] A user cannot read another user's portfolio (row-scope/IDOR test, [23 §2](../23-security-auth-and-privacy.md)).

### Compliance gate
- [ ] No portfolio surface contains "sell"/"reduce"/"book profit"/target/SL; copy reviewed against the blocked-phrase list ([16 §0](../16-portfolio-and-risk-engine.md)).
- [ ] Holdings never appear in plaintext logs; PII-class handling enforced ([23 §5–6](../23-security-auth-and-privacy.md)).

### Acceptance criteria
- [ ] P&L is the user's own data, not a return claim; corp actions correct; no target/SL anywhere ([08 §9](../08-screen-by-screen-documentation.md)).

---
## Feature: Risk engine + portfolio health score  `(Mode A)`
**Objective:** Compute per-position and portfolio-level risk **components** (concentration, sector, market-cap, volatility, news, technical-breakdown), each with its underlying evidence, plus a single 0–100 portfolio **health score** — a diagnostic measurement, never advice. **Stop-loss/target-zone monitoring is RA-gated and NOT built in v1.**
**Backend dep:** risk-component calculators sharing the indicator layer, entropy/tilt helpers, versioned weight config, RA-gating feature flag that hard-excludes SL/target objects · **Frontend dep:** per-position `RiskPanel` (components + evidence), `HealthGauge` + driver list ([08 §9](../08-screen-by-screen-documentation.md)) · **Data dep:** indicators, breakdown scanner, news sentiment/impact (from [07](07-v2-accounts-watchlist-ai-news.md)), allocation weights.

### Steps
- [ ] 1. Implement per-position risk components in `app/risk/components.py` per [16 §3.1–3.2](../16-portfolio-and-risk-engine.md): concentration (`weight/SINGLE_STOCK_SOFT_CAP × 50`, clamp 0–100), sector concentration, market-cap exposure, volatility (ATR%-percentile), news (max negative impact 7d, above-threshold links only), technical-breakdown (sum of breached conditions: <SMA50, <SMA200, breakdown-scanner hit, <swing low). Each ships with the data points that produced it.
- [ ] 2. Store all thresholds/windows/weights (`SINGLE_STOCK_SOFT_CAP`, etc.) as **versioned admin config**, mirroring scanner-score governance ([16 §3.2](../16-portfolio-and-risk-engine.md), [SPEC §6.5](../../SPEC.md)).
- [ ] 3. Implement the portfolio **health score** in `app/risk/health.py` per [16 §4](../16-portfolio-and-risk-engine.md): weighted sub-health (diversification 25%, sector balance 15%, volatility 20%, technical 20%, news 10%, cap balance 10%), descriptive bands (Resilient/Balanced/Elevated/High), and a **drivers** list where each line names its data point.
- [ ] 4. **RA-GATED / Mode B — do NOT build or surface in v1:** stop-loss / target / entry / invalidation zone computation and monitoring. Define the schema (`ra_gated`, `mode_required: "B"`, `stop_loss_zone`, `target_zone`) for forward-compatibility only; gate behind a feature flag that **hard-excludes these objects from every Mode-A response** ([16 §3.3](../16-portfolio-and-risk-engine.md)). The Mode-A factual equivalent is the technical-breakdown flag ("closed below its 50-DMA") — the event, not a level to act on.
- [ ] 5. Implement `GET /api/portfolio/risk`, `GET /portfolio/{id}/health`, `GET /portfolio/{id}/risk/{symbol}` per [10 §7](../10-api-contracts.md) / [16 §8](../16-portfolio-and-risk-engine.md); flags are **events** ("broke below its 50-DMA"), never "sell X".
- [ ] 6. Build the risk panel + health gauge per [08 §9](../08-screen-by-screen-documentation.md): components with evidence, drivers each traceable, "diagnostic measurement, not a grade / not advice" stated; **no SL/target UI**.

### Tests
- [ ] Every component returns with its underlying evidence (e.g. "ATR% = 4.1, 88th percentile").
- [ ] In Mode A, **no** API response contains `stop_loss_zone` / `target_zone` / any `ra_gated` field — contract test asserts absence ([16 §3.3, §8](../16-portfolio-and-risk-engine.md)).
- [ ] The health score is reproducible from its components and versioned weights; a concentrated single-sector portfolio scores materially lower on diversification + sector balance.
- [ ] Every driver line names the data point behind it; no band label or driver contains prescriptive language.
- [ ] Technical-breakdown flags are phrased as events and pass the blocked-phrase validator at output time.

### Compliance gate
- [ ] RA-gated SL/target objects are unreachable in Mode A (feature flag + contract test); building them locally is explicitly out of scope ([SPEC §12](../../SPEC.md)).
- [ ] No risk flag, band, or driver contains "sell"/"reduce"/"buy" or any always-prohibited phrase ([SPEC §3.3](../../SPEC.md)).

### Acceptance criteria
- [ ] Risk surfaced as events/facts, never "sell X"; no target/SL anywhere; every flag traces to inputs ([02 §6](../02-product-roadmap.md), [08 §9](../08-screen-by-screen-documentation.md)).

---
## Feature: Portfolio AI summary  `(Mode A)`
**Objective:** A grounded, runtime-verified, factual portfolio summary that reports events and what to monitor — never prescribes — under the Portfolio Risk Agent and structured payload contract.
**Backend dep:** payload builder, Portfolio Risk Agent (cheap model; premium for multi-factor synthesis), runtime verifier, guardrail filter, audit logger (all from [04](04-ai-explanation-layer.md)/[14 §5.3](../14-ai-llm-agent-architecture.md)) · **Frontend dep:** summary card with as-of stamp + confidence badge + "Not investment advice" footer ([16 §5](../16-portfolio-and-risk-engine.md)) · **Data dep:** aggregate metrics, allocation, per-position risk components + evidence, health score + drivers, surfaced news.

### Steps
- [ ] 1. Build the `portfolio_summary_v1` payload per [16 §5.1](../16-portfolio-and-risk-engine.md): aggregate, health (score/band/drivers), concentration (top stock/sector), events (breakdowns, negative news with source + ts); the agent may reference nothing else.
- [ ] 2. Implement `GET /api/portfolio/{id}/ai-summary` (cached, regenerate-on-change) via the Portfolio Risk Agent ([14 §5.3](../14-ai-llm-agent-architecture.md), [16 §8](../16-portfolio-and-risk-engine.md)).
- [ ] 3. Enforce Mode-A wording rules ([16 §5.2](../16-portfolio-and-risk-engine.md)): "2 of your 11 holdings closed below their 50-DMA" (allowed) vs "Sell the holdings below their 50-DMA" (prohibited); "is a level to watch" not "…before fresh action".
- [ ] 4. Suppress per-holding notes whose facts are missing / `data_confidence: LOW`; never guess ([14 §12](../14-ai-llm-agent-architecture.md)).
- [ ] 5. Runtime-verify every number against the payload (block/regenerate on mismatch), run the blocked-phrase guardrail at output time, and write the generation to the AI audit log ([16 §5.1](../16-portfolio-and-risk-engine.md)).

### Tests
- [ ] A fabricated figure in a regression prompt is blocked by the verifier ([16 §5.3](../16-portfolio-and-risk-engine.md)).
- [ ] Injecting "sell"/"target" into model output is caught by the guardrail filter.
- [ ] When any holding has `data_confidence: LOW`, its note is suppressed, not guessed.
- [ ] Every generation has an audit-log row (prompt id/version, payload hash, model id, grounding report).

### Compliance gate
- [ ] The summary reports events + what to monitor only; passes the Compliance Review Agent before display ([14 §5.8](../14-ai-llm-agent-architecture.md)).
- [ ] No "sell"/"reduce"/"rebalance" or always-prohibited phrase, in any mode ([16 §5.2](../16-portfolio-and-risk-engine.md), [SPEC §3.3](../../SPEC.md)).

### Acceptance criteria
- [ ] Portfolio AI summary passes runtime verification; every figure traces to the payload; carries an `audit_id` + as-of date ([16 §5](../16-portfolio-and-risk-engine.md)).

---
## Feature: Alerts & notifications  `(Mode A)`
**Objective:** Event-reporting alert types evaluated **after the EOD refresh**, with debounce/dedup/throttle, in-app/email/push delivery, and delivery logging. RA-gated stop-loss/target alerts are **not generated in Mode A**.
**Backend dep:** post-refresh alert evaluator, per-type evaluators reading engine outputs, dedup store keyed on `dedup_key`, prior-state snapshots, per-alert + per-user rate limiter, template renderer, channel adapters, delivery-log writer · **Frontend dep:** `AlertRuleList`/`AlertRuleEditor`/`AlertHistory`, channel selection, alert feed ([08 §10](../08-screen-by-screen-documentation.md)) · **Data dep:** indicators, scanner-membership deltas, sector scores, breadth, news sentiment/impact, corp-action master, portfolio risk events.

### Steps
- [ ] 1. Define the alert schema in `app/alerts/models.py` per [17 §4](../17-alerts-and-notifications.md): alert definition (type, scope, condition, `cadence: EOD`, channels, `throttle{max_per_day, cooldown_minutes}`, `ra_gated`, enabled) and the fired-alert instance (`dedup_key`, `rendered_text`, `guardrail_status`, `delivery[]`). Carry the `cadence` field so live alerts forward-port without redesign.
- [ ] 2. Implement per-type evaluators for the Mode-A alert table ([17 §2](../17-alerts-and-notifications.md)): price above/below, % movement, volume breakout, RSI threshold, MA crossover, scanner entry/exit, watchlist positive/negative news, portfolio risk, news sentiment shift, corporate action, descriptive resistance/support, daily brief, sector weakness, market breadth. Every template is **past-tense, event-reporting** ("closed above ₹X", not "is crossing now").
- [ ] 3. Hook the evaluator to run **only after the EOD pipeline completes** (ingestion → adjustment → indicators → scanners → news → portfolio risk); deliver in the morning-brief window — no intraday/"buy at open" semantics ([17 §1.1](../17-alerts-and-notifications.md)).
- [ ] 4. **RA-GATED — do NOT generate in Mode A:** stop-loss / target zone alerts. Carry the `ra_gated` flag; disable these evaluators in Mode A; the Mode-A factual equivalent is the portfolio-risk / MA-crossover alert ("You hold TATAMOTORS; it closed below its 50-DMA today") ([17 §3](../17-alerts-and-notifications.md)).
- [ ] 5. Implement dedup/debounce/throttle ([17 §5](../17-alerts-and-notifications.md)): drop if `dedup_key` (`{type}:{symbol|sector|market}:{discriminator}:{as_of_date}`) already fired this window; debounce oscillating conditions to **newly-true** transitions via prior-state snapshots; per-alert `max_per_day` + cooldown; per-user global cap with priority ordering (portfolio-risk + negative-news > scanner > breadth); quiet hours; channel collapse.
- [ ] 6. Render each template, run the **blocked-phrase check at output time**; on fail, **suppress + log for compliance** (never silently drop) ([17 §7](../17-alerts-and-notifications.md)).
- [ ] 7. Implement channel adapters (in-app always; email batched into the morning window; push respecting quiet hours; WhatsApp future/gated) and the delivery-log writer recording `delivered`|`failed`|`suppressed` with timestamp + reason; retry with backoff on transient failure ([17 §6](../17-alerts-and-notifications.md)).
- [ ] 8. Implement the alert API per [10 §8](../10-api-contracts.md): `GET/POST /api/alerts`, `PUT/DELETE /api/alerts/{id}`, `GET /api/alerts/{id}/events`. Premium-gated; EOD-batch, event-reporting only.
- [ ] 9. Build the alerts screen + notification center per [08 §10](../08-screen-by-screen-documentation.md): condition builder ("enters momentum scanner", "crosses 50-DMA", "risk flag appears"), channel choice, history, "Alert set (EOD)" confirmation; cadence indicator shows "EOD" everywhere.

### Tests
- [ ] Every alert type renders a past-tense, event-reporting template that passes the blocked-phrase validator (contract test over all templates) ([17 §2](../17-alerts-and-notifications.md)).
- [ ] RA-gated SL/target evaluators emit **nothing** in Mode A (contract test) ([17 §3](../17-alerts-and-notifications.md)).
- [ ] The same event on the same as-of date fires at most once; a price oscillating around a level fires only on the first crossing.
- [ ] A flooding scenario respects the per-user cap with correct priority ordering.
- [ ] A failed email still shows the alert in-app; a guardrail-suppressed alert is logged (with the failing phrase/rule), not silently dropped; every send writes a delivery-log row.
- [ ] No v1 alert implies an intraday action; each states its as-of date.

### Compliance gate
- [ ] Every emitted alert maps to a non-prescriptive, event-reporting template; "buy at open"/"sell"/"book profit" never appear ([17 §0](../17-alerts-and-notifications.md)).
- [ ] Nothing reaches a channel without passing the output-time guardrail; RA-gated types are dropped in Mode A ([17 §7](../17-alerts-and-notifications.md)).

### Acceptance criteria
- [ ] Alerts are event-reporting only ("entered the scanner"), EOD-batch, never "buy at open"; delivery logged; throttling bounds noise ([02 §6](../02-product-roadmap.md), [08 §10](../08-screen-by-screen-documentation.md)).

---
## Done-when
- [ ] All four features pass their tests, compliance gates, and acceptance criteria; the Exit gate checklist is fully checked.
- [ ] A contract test proves **no** Mode-A response (portfolio, risk, or alert) contains `stop_loss_zone`, `target_zone`, or any `ra_gated` field, and no RA-gated alert is generated ([16 §8](../16-portfolio-and-risk-engine.md), [17 §3](../17-alerts-and-notifications.md)).
- [ ] Corp actions are correct on the split/bonus test set; realized P&L matches the FIFO worked example to the paisa ([16 §1.5](../16-portfolio-and-risk-engine.md)).
- [ ] All portfolio/risk/alert AI and template output is factual event-reporting, runtime-verified where AI-generated, and free of always-prohibited phrases ([SPEC §3.3, §6.6, §6.9](../../SPEC.md)).
- [ ] Holdings are treated as PII-class throughout (encrypted, row-scoped, redacted from logs) ([23 §5–6](../23-security-auth-and-privacy.md)).
- [ ] **Stop-loss/target-zone monitoring remains explicitly deferred to Phase 5 (RA-gated, Mode B)** and is documented in schema only, not built or surfaced.
