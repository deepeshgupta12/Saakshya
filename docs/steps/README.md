# Saakshya Implementation Steps — Build Plan

This `/docs/steps` directory is the **executable build plan**: feature-wise, ordered checklists that turn the specs in `/docs` into shipped code. The `/docs` files describe **what** to build; these step files describe **how** and **in what order**, with task checkboxes, file targets, tests, compliance gates, and acceptance criteria.

> Read first: [SPEC.md](../../SPEC.md) (canonical spec, risk-first roadmap, local build plan) · [CLAUDE.md](../../CLAUDE.md) (operating manual) · [docs/02 roadmap](../02-product-roadmap.md)

## How to use these files

1. **Work top-down in order.** The sequence is **risk-first** (per [SPEC.md](../../SPEC.md)): de-risk → local Mode-A core → V1 UI → V2 → V3 → later/gated versions. Don't start a file until its **Prerequisites** are done.
2. **Each file is a checklist.** Tick `- [ ]` tasks as you complete them. Update **Status** in the file header (`Not started` → `In progress` → `Done`).
3. **Respect the gates.** Several files have an **Exit gate** that must pass before the next phase. RA-gated files ([14](14-v9-advisory-ra-gated.md), parts of [09](09-v4-strategy-builder.md)/[12](12-v7-live-data.md)/[13](13-v8-broker-integration.md)) **must not be built** until the regulatory gate is met.
4. **Every task carries its non-negotiables.** Each feature has a **Compliance gate** (Mode-A check) and **Acceptance criteria**. If a task would emit a buy-lean, target, or stop-loss in Mode A — stop (see [CLAUDE.md §3](../../CLAUDE.md)).
5. **Keep docs in sync.** When a step changes behavior, update the matching `/docs` spec in the same change.

## Definition of Done (applies to every feature in every file)

- [ ] Behavior matches the relevant `/docs` spec.
- [ ] **Evidence-first:** every number/label/insight traces to computed inputs; AI output passes the verification harness.
- [ ] **Compliance:** Mode-A language only; banned phrases blocked at output time; no RA-gated output.
- [ ] **Tested:** unit/integration/contract tests added; critical logic (scoring, corp-action adjustment, AI grounding/guardrails) covered.
- [ ] **Docs updated**; decision logged in [docs/30](../30-decision-log.md) if a choice was made.

## Master build sequence

| Step file | Delivers | Roadmap | SPEC phase | Local M | Mode | Status |
|---|---|---|---|---|---|---|
| [00-phase-0-derisk](00-phase-0-derisk.md) | Legal mode, data procurement, score-validation spike plan | pre-V1 | Phase 0 | — | A | Not started |
| [01-local-mvp-foundation](01-local-mvp-foundation.md) | Repo scaffold, config, DuckDB, DataSource adapter, ingestion, corp-actions | V1 | Phase 0–1 | M0–M1 | A | Not started |
| [02-indicators-and-scanners](02-indicators-and-scanners.md) | Vectorized indicators + rule-based momentum/volume/RSI/MA scanners | V1 | Phase 1 | M2–M3 | A | Not started |
| [03-scanner-score-validation](03-scanner-score-validation.md) | **Gate:** prove momentum score carries signal (else redesign) | V1 | Phase 0 spike | M3b | A | Not started |
| [04-ai-explanation-layer](04-ai-explanation-layer.md) | Grounding contract, Haiku explainer, verification harness, guardrails | V1–V2 | Phase 2 | M4 | A | Not started |
| [05-api-and-pipeline](05-api-and-pipeline.md) | Pipeline orchestration + FastAPI endpoints + envelope/caching | V1 | Phase 1–2 | M5 | A | Not started |
| [06-frontend-foundation-and-v1-screens](06-frontend-foundation-and-v1-screens.md) | Next.js + design system + dashboard/scanner/stock/sector screens | V1 | Phase 1 | M6 | A | Not started |
| [07-v2-accounts-watchlist-ai-news](07-v2-accounts-watchlist-ai-news.md) | Accounts, watchlists, AI summaries + daily brief, news sentiment | V2 | Phase 2 | — | A | Not started |
| [08-v3-portfolio-risk-alerts](08-v3-portfolio-risk-alerts.md) | Portfolio tracker, risk engine, portfolio AI summary, alerts | V3 | Phase 2–3 | — | A | Not started |
| [09-v4-strategy-builder](09-v4-strategy-builder.md) | No-code strategy/scanner builder, NL→strategy (tech levels deferred) | V4 | Phase 3–4 | — | A | Not started |
| [10-v5-backtesting-and-ml](10-v5-backtesting-and-ml.md) | Backtesting (integrity-gated) + ML ranking / signal quality | V5 | Phase 4 | — | A | Not started |
| [11-v6-agentic-workflows](11-v6-agentic-workflows.md) | LangGraph agent platform + eval harness + compliance pass | V6 | Phase 2+ | — | A | Not started |
| [12-v7-live-data](12-v7-live-data.md) | Licensed live feed + WebSocket streaming + real-time alerts | V7 | Phase 5 | — | A ⛔ licensing gate | Not started |
| [13-v8-broker-integration](13-v8-broker-integration.md) | Broker portfolio sync → (later) execution | V8 | Phase 5 | — | ⛔ licensing/security gate | Not started |
| [14-v9-advisory-ra-gated](14-v9-advisory-ra-gated.md) | **Unlocks** entry/target/SL levels, candidate layer, advisory, model portfolios | V4(gated)+V9 | Phase 5 | — | ⛔ **B (RA)** / C (IA) | Not started |
| [15-cross-cutting-admin-infra-qa](15-cross-cutting-admin-infra-qa.md) | Admin, compliance ops, testing, infra graduation, analytics, security | all | Phases 0–5 | — | A | Not started |

⛔ = gated; do not build until the named regulatory/licensing prerequisite is in force.

## Feature-module step files (16–28)

These cover modules that **slot into the phases of the primary track above** — they do not run after it. Build each when its phase arrives (see the coverage matrix below).

| Step file | Delivers | Slots into |
|---|---|---|
| [16-scanners-extended](16-scanners-extended.md) | Breakout, breakdown, sector-strength, low-risk-momentum, high-risk, 52-wk-high, 200-DMA-reclaim, oversold-recovery, portfolio-risk scanners | Phase 1–3 (after 02–03) |
| [17-corporate-announcements](17-corporate-announcements.md) | Exchange-announcement ingestion + AI summary; feeds the corp-action master | Phase 2–3 |
| [18-peer-comparison](18-peer-comparison.md) | Same-sector peer comparison (comparative, not directive) | Phase 3 |
| [19-thematic-baskets](19-thematic-baskets.md) | Curated theme baskets (bucket views, not model portfolios) | Phase 3 |
| [20-screener-library](20-screener-library.md) | Prebuilt named screeners (list outputs) | Phase 3 |
| [21-fundamentals-valuation](21-fundamentals-valuation.md) | Descriptive valuation bands + earnings summaries | Phase 3 |
| [22-institutional-activity](22-institutional-activity.md) | FII/DII flows, bulk/block deals (data-gated) | Phase 4 |
| [23-ai-assistant](23-ai-assistant.md) | Conversational grounded AI dock with evidence cards | Phase 2+ |
| [24-account-surfaces](24-account-surfaces.md) | Profile/settings, notification center, onboarding | Phase 2 |
| [25-pricing-subscription-billing](25-pricing-subscription-billing.md) | Tiers, billing, server-side entitlements | Phase 4 |
| [26-mobile-app](26-mobile-app.md) | Mobile app (alerts/watchlist/portfolio/brief/stock) | Phase 4 |
| [27-seo-learn-content](27-seo-learn-content.md) | Public SEO pages + /learn + glossary (Mode-A language) | Phase 1+ |
| [28-personalization](28-personalization.md) | Navigation personalization (Mode A, now) + advisory personalization (⛔ IA / Mode-C gated) | Phase 3 / Phase 5 ⛔ |

## Full coverage matrix — every module → step file

Confirms the entire roadmap/module scope ([docs/04](../04-feature-modules.md), [docs/02](../02-product-roadmap.md)) is covered by a step file.

| Module / feature | Step file |
|---|---|
| Data ingestion, stock master, corporate-action adjustment | [01](01-local-mvp-foundation.md) |
| Technical indicators | [02](02-indicators-and-scanners.md) |
| Momentum / volume-breakout / RSI / moving-average scanners | [02](02-indicators-and-scanners.md) |
| Breakout / breakdown / sector-strength / 52-wk / oversold / portfolio-risk scanners | [16](16-scanners-extended.md) |
| Scanner-score validation (gate) | [03](03-scanner-score-validation.md) |
| AI stock summary / explanation layer | [04](04-ai-explanation-layer.md) |
| API + EOD pipeline | [05](05-api-and-pipeline.md) |
| Market dashboard, stock detail, sector dashboard, scanner UI | [06](06-frontend-foundation-and-v1-screens.md) |
| Accounts/auth, watchlist, AI daily brief, news sentiment | [07](07-v2-accounts-watchlist-ai-news.md) |
| Corporate announcements | [17](17-corporate-announcements.md) |
| Portfolio tracker, risk engine, alerts/notifications | [08](08-v3-portfolio-risk-alerts.md) |
| Peer comparison | [18](18-peer-comparison.md) |
| Thematic baskets | [19](19-thematic-baskets.md) |
| Screener library | [20](20-screener-library.md) |
| Fundamentals / valuation / earnings | [21](21-fundamentals-valuation.md) |
| Institutional activity | [22](22-institutional-activity.md) |
| AI assistant (conversational) | [23](23-ai-assistant.md) |
| User profile, notification center, onboarding | [24](24-account-surfaces.md) |
| Strategy / custom-scanner builder | [09](09-v4-strategy-builder.md) |
| Backtesting + ML ranking / signal quality | [10](10-v5-backtesting-and-ml.md) |
| Agentic AI workflows | [11](11-v6-agentic-workflows.md) |
| Pricing / subscription / billing | [25](25-pricing-subscription-billing.md) |
| Mobile app | [26](26-mobile-app.md) |
| SEO public pages + /learn education + glossary | [27](27-seo-learn-content.md) |
| Live data / real-time ⛔ | [12](12-v7-live-data.md) |
| Broker integration ⛔ | [13](13-v8-broker-integration.md) |
| RA-gated: entry/target/SL levels, candidate layer, model portfolios, advisory ⛔ | [14](14-v9-advisory-ra-gated.md) |
| Admin, compliance ops, QA, infra, analytics, security | [15](15-cross-cutting-admin-infra-qa.md) |
| Personalization (navigation Mode A / advisory ⛔ IA-gated) | [28](28-personalization.md) |

## The recommended starting point

Begin at **[00-phase-0-derisk](00-phase-0-derisk.md)** (the non-code gates), then **[01-local-mvp-foundation](01-local-mvp-foundation.md)** → milestone **M0** (pull ~50 Nifty names via yfinance into DuckDB). That is the first running code and exercises the three riskiest assumptions — legal posture, data correctness, and whether the scores carry signal — with the least surface. See [SPEC.md §12](../../SPEC.md).
