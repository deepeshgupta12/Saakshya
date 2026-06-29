# 30 — Decision Log

> One-line purpose: The append-only record of significant product and engineering decisions for Saakshya — what was decided, why, the alternatives weighed, owner, impact, and status — continuing alongside the SPEC's open-decision table.
> Read first: [SPEC.md](../SPEC.md)

Related: [Product Overview](01-product-overview.md) · [Product Roadmap](02-product-roadmap.md) · [Backend Architecture](09-backend-architecture.md) · [AI/LLM Agent Architecture](14-ai-llm-agent-architecture.md) · [Compliance & Guardrails](21-compliance-risk-and-guardrails.md) · [Coding Standards](27-coding-standards.md) · [Glossary](29-glossary.md)

---

## 0. How this log works

- This log is **append-only**. To reverse a decision, add a **new** entry (a "superseded by" pointer) rather than editing history.
- It **continues alongside SPEC §13** (the open-decisions table). SPEC §13 tracks decisions that still *block* downstream work; this log records decisions **as they are made** (including ones SPEC already resolved) with full context. Where this log and SPEC §13 overlap, SPEC remains the canonical source-of-truth for scope; this log carries the rationale.
- **Format / columns:** `ID` · `Date` · `Decision` · `Context` · `Alternatives considered` · `Final decision` · `Owner` · `Impact` · `Status`.
- **Status values:** `Accepted` · `Provisional` (decided but revisit-on-trigger) · `Open` (mirrors a SPEC §13 unresolved item) · `Superseded` (by a later ID).
- New decisions get the next `D-NNN` id and today's date.

---

## 1. Decision entries

Each decision is recorded as a section for readability; the summary table (§2) indexes them.

### D-001 — Product name "Saakshya"
- **Date:** 2026-06-29
- **Context:** The product needed a name that *is* the thesis. The product is evidence-first: every output traces to visible data and explainable logic (SPEC §1).
- **Alternatives considered:** Generic finance-app names; English "Evidence/Proof"-style names; ticker-screener-style names.
- **Final decision:** **Saakshya** (साक्ष्य, "evidence"). The name doubles as the compliance posture and the differentiation.
- **Owner:** Product
- **Impact:** Branding, positioning, public copy; reinforces "best screener + best explanations", never "what to buy".
- **Status:** Accepted

### D-002 — Evidence-first philosophy as both product thesis and compliance posture
- **Date:** 2026-06-29
- **Context:** Disclaimers do not cure advisory substance (SPEC §0). Treating compliance as a disclaimer is a known failure mode in Indian fin-products.
- **Alternatives considered:** "Research tool with disclaimers" posture (the original permissive framing, rejected by the v3 hardening pass).
- **Final decision:** Every output is **data-backed, explainable, traceable**; AI **explains, never invents**; compliance is a **product property**, enforced at output time (SPEC §0, §5, §6.9).
- **Owner:** Product + Compliance
- **Impact:** Governs UI copy, AI behavior, SEO copy, and the entire guardrail layer.
- **Status:** Accepted

### D-003 — v1 operating mode = Mode A, with RA (Mode B) registration in parallel
- **Date:** 2026-06-29
- **Context:** SEBI RA/finfluencer rules make advisory-in-substance features illegal to ship unregistered (SPEC §2). The mode decision gates data use, AI language, and shippable features.
- **Alternatives considered:** Launch under RA from day one (slow, registration lead time); ship advisory features behind disclaimers (rejected — substance over form); IA/Mode C (not needed for v1).
- **Final decision:** Ship **Mode A** (pure analytics); run **RA registration in parallel** as a gating dependency that later unlocks recommendation-flavored features. No feature ships until its mode is in force.
- **Owner:** Founders + Counsel
- **Impact:** Everything. RA-gated routes/fields/copy are absent from the v1 router and flag-only ([05](05-information-architecture-and-url-paths.md)).
- **Status:** Accepted (mirrors SPEC §13 "v1 operating mode")

### D-004 — EOD / T+1 launch strategy
- **Date:** 2026-06-29
- **Context:** Live/real-time data carries licensing cost and a larger compliance surface; the target users (swing traders, researchers, portfolio holders) are well served by EOD (SPEC §8).
- **Alternatives considered:** Live/intraday from launch (cost + licensing + compliance load); delayed-data tier.
- **Final decision:** **EOD-first (T+1)**: ingest previous session → normalize → corp-action adjust → compute → scan → news → AI summaries → morning brief. Live data is a later, separately-licensed premium tier.
- **Owner:** Product + Data
- **Impact:** Pipeline cadence, caching, alert model (EOD-batch), monetization tiers.
- **Status:** Accepted

### D-005 — AI as the explanation layer, not a stock picker
- **Date:** 2026-06-29
- **Context:** Generic AI hallucinates prices/news/targets — both wrong and a regulatory landmine (SPEC §1, §6.6).
- **Alternatives considered:** AI that ranks/recommends "what to buy" (Mode B/C, rejected for v1); free-form AI over raw data (ungrounded, rejected).
- **Final decision:** AI receives a **structured payload only**, **explains** deterministic signals, is **runtime-verified** (every number/fact traced to payload, block/regenerate on mismatch), and is **suppressed when inputs are missing** (SPEC §6.6).
- **Owner:** AI/ML
- **Impact:** AI architecture, payload contract, verification harness, audit log.
- **Status:** Accepted

### D-006 — Rule-based, explainable scanners in v1 (ML later)
- **Date:** 2026-06-29
- **Context:** v1 must be explainable and validatable; ML ranking adds opacity and is a later-phase concern (SPEC §4, §6.5, §10).
- **Alternatives considered:** ML ranking in v1 (opacity, validation burden, Phase 4+ territory).
- **Final decision:** **Rule-based scanners** with transparent score + sub-scores + reasons + risk flags in v1; ML ranking / probability bands deferred to Phase 4+ and framed as measurement.
- **Owner:** Quant/Engineering
- **Impact:** Scanner engine design; M3b validation applies to rule-based scores.
- **Status:** Accepted

### D-007 — Next.js frontend
- **Date:** 2026-06-29
- **Context:** The public surface is the SEO/acquisition engine and needs strong SSR/ISR for indexed pages (SPEC §9, [24](24-analytics-seo-and-growth.md)).
- **Alternatives considered:** SPA-only (poor SEO); other SSR frameworks.
- **Final decision:** **Next.js + React + TypeScript + Tailwind** (production stack); frontend **deferred** in local-first until core is validated (SPEC §9, §12).
- **Owner:** Frontend
- **Impact:** SEO rendering, routing/IA, screen architecture.
- **Status:** Accepted

### D-008 — FastAPI backend
- **Date:** 2026-06-29
- **Context:** Python ecosystem for data/indicators/AI; needs a typed, async, OpenAPI-native API layer (SPEC §9, §12).
- **Alternatives considered:** Node/Express backend (splits the data/AI stack from Python); Django (heavier than needed).
- **Final decision:** **Python FastAPI** (Celery/Redis in production; plain scripts/Makefile locally). Standard response envelope + grounding metadata on AI endpoints ([27 §6](27-coding-standards.md)).
- **Owner:** Backend
- **Impact:** API contracts, async pipeline orchestration, AI integration.
- **Status:** Accepted

### D-009 — Database strategy: PostgreSQL + TimescaleDB in production, DuckDB local-first
- **Date:** 2026-06-29
- **Context:** Time-series-heavy workload; the MVP must run on one laptop to retire risk cheaply (SPEC §9, §12).
- **Alternatives considered:** Postgres/Timescale from day one locally (friction for a one-laptop prototype); ClickHouse early (later concern).
- **Final decision:** **DuckDB (single file)** for local-first M0–M6; **PostgreSQL + TimescaleDB** (Redis, ClickHouse later, S3) in production. **As-of versioning fields** on all time-series/indicator entities; an **AI-generation audit-log** entity (SPEC §9).
- **Owner:** Data/Backend
- **Impact:** Storage schema, repositories, migration strategy.
- **Status:** Provisional (revisit when moving off local-first; mirrors SPEC §13 "Local storage")

### D-010 — AI architecture: LangGraph / LlamaIndex (RAG, provider abstraction)
- **Date:** 2026-06-29
- **Context:** Agentic workflows + grounded retrieval + provider abstraction are needed; local-first uses the Anthropic SDK directly (SPEC §9).
- **Alternatives considered:** Single-call LLM with no orchestration (insufficient for agentic depth); bespoke orchestration.
- **Final decision:** **LangGraph/LlamaIndex** for agents + RAG in production; **provider abstraction** retained (cheap model for repetitive summarization, premium for complex synthesis). Local-first: Anthropic SDK directly.
- **Owner:** AI/ML
- **Impact:** Agent architecture, RAG/payload contract, cost/latency controls.
- **Status:** Accepted

### D-011 — Default model: Claude Haiku
- **Date:** 2026-06-29
- **Context:** Full-universe daily AI passes threaten freemium economics; a cheap, fast model is the default with a premium model reserved for complex synthesis (SPEC §6.8, §9).
- **Alternatives considered:** A premium model as default (cost-prohibitive at scale); no provider abstraction (locks in one tier).
- **Final decision:** **Claude Haiku** (`claude-haiku-4-5-20251001`) as the default explainer; premium Claude model reserved for complex synthesis behind the provider abstraction; hard monthly AI-spend ceiling with graceful degradation.
- **Owner:** AI/ML
- **Impact:** Cost model, caching/regenerate-on-change, latency budget.
- **Status:** Provisional (revisit on cost/quality data; mirrors SPEC §13 "AI cost ceiling")

### D-012 — Corporate-action adjustment as a first-class workstream
- **Date:** 2026-06-29
- **Context:** An unadjusted split/bonus silently corrupts RSI, MAs, breakouts, and every backtest — the item that decides whether indicators are real (SPEC §6.1).
- **Alternatives considered:** Rely on yfinance auto-adjustment (prototype convenience only, not production); treat adjustment as a pipeline bullet (rejected — too consequential).
- **Final decision:** Maintain a **corporate-action master**; store **both raw and adjusted** series; back-adjust consistently across full history; **reconcile against a second source** before publishing. Its own engineering workstream with dedicated split/bonus test fixtures ([25 §2](25-qa-testing-and-release-process.md)).
- **Owner:** Data Engineering
- **Impact:** Ingestion, indicators, backtesting integrity, test strategy.
- **Status:** Accepted (build-vs-buy mirrors SPEC §13 "corp-action adjustment")

### D-013 — Scanner-score validation (M3b) as a gating spike
- **Date:** 2026-06-29
- **Context:** Scoring weights are reasonable-sounding but arbitrary; building UI on unvalidated scores risks shipping a "horoscope" (SPEC §6.5, §12 M3b).
- **Alternatives considered:** Ship scores unvalidated (rejected — product-killing risk); skip scoring entirely (loses the core value).
- **Final decision:** Before building UI on scores, **prove on historical adjusted data that ≥1 score (start with momentum) measures what it claims** (tracks realized relative strength). This is measurement validation, not a performance claim; if it's noise, redesign scoring now. Gates the whole product.
- **Owner:** Quant
- **Impact:** Scanner engine credibility; release gate ([25 §6](25-qa-testing-and-release-process.md)).
- **Status:** Open (gating spike; mirrors SPEC §13 "Score-validation outcome (M3b)")

### D-014 — GitNexus knowledge-graph adoption
- **Date:** 2026-06-29
- **Context:** Agentic development needs grounded impact analysis (affected modules, dependency graph, call chains, impact radius) before editing (SPEC-aligned correctness discipline, [28](28-agentic-development-workflows.md)).
- **Alternatives considered:** Ad-hoc grep/search (misses transitive impact); no impact step (risky for critical logic).
- **Final decision:** Adopt **GitNexus** as the repo knowledge graph; the agent workflow queries it at step 2 (context/impact) before any change ([26](26-gitnexus-knowledge-graph.md), [28](28-agentic-development-workflows.md)).
- **Owner:** Engineering / Tooling
- **Impact:** Agentic workflow, code-review/impact-analysis, refactoring safety.
- **Status:** Accepted

### D-015 — Build-vs-buy: corporate-action adjustment → BUILD in-house
- **Date:** 2026-06-29
- **Context:** SPEC §13 carried corp-action adjustment as an open build-vs-buy item; D-012 already made it a first-class workstream. Adjustment quality decides whether every indicator, scanner, and backtest is real (SPEC §6.1). Buying a black-box adjusted feed surrenders the most consequential correctness surface and hides reconciliation failures.
- **Alternatives considered:** Buy a pre-adjusted vendor feed (opaque adjustment logic, no raw series, hard to reconcile/audit); rely on yfinance auto-adjustment (prototype convenience only); hybrid (buy with in-house reconciliation — still inherits vendor adjustment semantics).
- **Final decision:** **BUILD in-house** as a first-class engineering workstream — maintain the corporate-action master, **store both raw and adjusted** series, back-adjust consistently across full history, and **reconcile against a second source** before publishing. Confirms and resolves the D-012 build-vs-buy question.
- **Owner:** Data Engineering
- **Impact:** Ingestion, indicators, backtesting integrity, test fixtures; closes SPEC §13 "Build vs buy: corp-action adjustment".
- **Status:** Decided (resolves SPEC §13 "Build vs buy: corp-action adjustment"; extends D-012)

### D-016 — Build-vs-buy: news / sentiment feed → BUILD in-house
- **Date:** 2026-06-29
- **Context:** SPEC §13 carried news/sentiment as an open build-vs-buy item (SPEC §6.4). Generic sentiment vendors are tuned on Western/general-news corpora and miss Indian-market entity resolution (symbol aliases, corporate hierarchies, group structures); exaggerated or mis-attributed sentiment is both wrong and a compliance hazard.
- **Alternatives considered:** Buy a third-party sentiment API (poor Indian-equity entity resolution, opaque scoring, no labelled-set evaluation); buy news but score in-house (loses control of source provenance/timestamps); no sentiment in v1 (loses a core pillar).
- **Final decision:** **BUILD in-house** — a **finance-tuned sentiment classifier** evaluated against a labelled Indian-market set, plus **entity resolution** over a curated symbol-alias + corporate-hierarchy map with confidence scores and a surfacing threshold; retain source links + timestamps.
- **Owner:** AI/ML + Data Engineering
- **Impact:** News-sentiment module, entity-resolution map, classifier eval harness; closes SPEC §13 "Build vs buy: news/sentiment feed".
- **Status:** Decided (resolves SPEC §13 "Build vs buy: news/sentiment feed")

### D-017 — Personalization line (A vs C) → build COMPLETE scope; advisory tier IA-gated
- **Date:** 2026-06-29
- **Context:** The spec's "personalize toward what the user looks at" quietly contradicts compliance: behaviour-derived per-stock nudges are Investment-Adviser (Mode C) territory (SPEC §7, [09 §user-profile](09-backend-architecture.md)). The line must be explicit so it does not creep across releases.
- **Alternatives considered:** Build only navigation personalization and drop the advisory tier entirely (loses future value); build the full personalization including behavioural nudges in Mode A (illegal — Mode C substance under a Mode A licence); leave the line undocumented (creep risk).
- **Final decision:** **Build the COMPLETE personalization scope**, split by tier: **navigation/layout personalization in Mode A now** (layout, followed sectors, default scanner filters to stated risk preference, prioritized educational content — navigation, not recommendations); **per-stock behavioural / advisory personalization GATED behind IA (Mode C) registration** — designed but **not shipped** in Mode A. The line is kept explicit in design review.
- **Owner:** Product + Compliance
- **Impact:** Personalization module ([04 §29](04-feature-modules.md)), preferences store, Mode-C gating; closes SPEC §13 "Personalization line (A vs C)".
- **Status:** Decided (resolves SPEC §13 "Personalization line (A vs C)")

### D-018 — Data vendor + redistribution rights → DEFERRED (prototype on yfinance + NSE Bhavcopy)
- **Date:** 2026-06-29
- **Context:** Licensed market-data selection carries legality (redistribution rights) and recurring cost implications (SPEC §13), but does not block local-first prototyping. Committing to a vendor before the product is validated is premature procurement risk.
- **Alternatives considered:** Sign a licensed vendor now (premature cost + lock-in before validation); build entirely on free sources permanently (redistribution-rights and reliability risk at scale); defer with a prototype data path (chosen).
- **Final decision:** **DEFERRED — decide later.** Prototype on **yfinance + NSE Bhavcopy (CM-UDiFF + delivery files)** meanwhile; **licensed-vendor selection + redistribution rights remain a tracked open procurement item** to be resolved before production redistribution.
- **Owner:** Product + Data + Counsel
- **Impact:** Ingestion source path (prototype), production data-licensing/cost; redistribution-rights remains an open procurement gate for production launch.
- **Status:** Deferred (intentional; SPEC §13 "Data vendor + redistribution rights" remains a tracked open procurement item)

---

## 2. Decision index

| ID | Date | Decision | Owner | Impact | Status |
|---|---|---|---|---|---|
| D-001 | 2026-06-29 | Product name "Saakshya" | Product | Branding/positioning | Accepted |
| D-002 | 2026-06-29 | Evidence-first = thesis + compliance posture | Product + Compliance | UI/AI/SEO/guardrails | Accepted |
| D-003 | 2026-06-29 | v1 = Mode A; RA (Mode B) in parallel | Founders + Counsel | Everything | Accepted |
| D-004 | 2026-06-29 | EOD / T+1 launch strategy | Product + Data | Pipeline/tiers/alerts | Accepted |
| D-005 | 2026-06-29 | AI = explanation layer, not picker | AI/ML | AI architecture | Accepted |
| D-006 | 2026-06-29 | Rule-based explainable scanners in v1 (ML later) | Quant/Eng | Scanner engine | Accepted |
| D-007 | 2026-06-29 | Next.js frontend | Frontend | SEO/IA/screens | Accepted |
| D-008 | 2026-06-29 | FastAPI backend | Backend | API/orchestration | Accepted |
| D-009 | 2026-06-29 | Postgres+TimescaleDB prod / DuckDB local | Data/Backend | Storage/migrations | Provisional |
| D-010 | 2026-06-29 | LangGraph/LlamaIndex AI architecture | AI/ML | Agents/RAG | Accepted |
| D-011 | 2026-06-29 | Default model Claude Haiku | AI/ML | Cost/latency | Provisional |
| D-012 | 2026-06-29 | Corp-action adjustment as first-class workstream | Data Eng | Indicators/backtest | Accepted |
| D-013 | 2026-06-29 | Scanner-score validation (M3b) gating spike | Quant | Whole product | Open |
| D-014 | 2026-06-29 | GitNexus knowledge-graph adoption | Eng/Tooling | Agentic workflow | Accepted |
| D-015 | 2026-06-29 | Build-vs-buy corp-action adjustment → BUILD in-house | Data Eng | Indicators/backtest/ingestion | Decided |
| D-016 | 2026-06-29 | Build-vs-buy news/sentiment feed → BUILD in-house | AI/ML + Data Eng | News-sentiment/entity resolution | Decided |
| D-017 | 2026-06-29 | Personalization line: complete scope, advisory tier IA-gated | Product + Compliance | Personalization/preferences/Mode-C gating | Decided |
| D-018 | 2026-06-29 | Data vendor + redistribution rights → DEFERRED (prototype on yfinance + NSE Bhavcopy) | Product + Data + Counsel | Ingestion source / data-licensing | Deferred |

---

## 3. Open decisions mirrored from SPEC §13

Items still **Open** block specific downstream work (tracked canonically in SPEC §13); resolved items are surfaced here with their decision pointer for continuity:

| SPEC §13 item | Blocks | This log |
|---|---|---|
| Data vendor + redistribution rights | Phase 1 onward | **D-018 — Deferred** (prototype on yfinance + NSE Bhavcopy; redistribution-rights remains a tracked open procurement gate) |
| Build vs buy: corp-action adjustment | Phase 1 | **D-015 — Decided: BUILD in-house** (extends D-012) |
| Build vs buy: news/sentiment feed | Phase 2 | **D-016 — Decided: BUILD in-house** |
| Scanner scoring weights + validation method | Phase 1 scanners | D-013 (Open) |
| AI cost ceiling + caching policy | Phase 2 AI | D-011 (Provisional) |
| Indicators: vectorized/pandas-ta vs TA-Lib | Local M2 | (resolved: avoid TA-Lib — record on adoption) |
| Personalization line (A vs C) | Phase 3+ | **D-017 — Decided** (complete scope; navigation-only in Mode A, advisory tier IA-gated/Mode C, SPEC §7) |

---

## 4. Related documents

- [SPEC.md §13](../SPEC.md) — canonical open-decisions table
- [01 — Product Overview](01-product-overview.md)
- [02 — Product Roadmap](02-product-roadmap.md)
- [14 — AI/LLM Agent Architecture](14-ai-llm-agent-architecture.md)
- [21 — Compliance, Risk & Guardrails](21-compliance-risk-and-guardrails.md)
- [26 — GitNexus Knowledge Graph](26-gitnexus-knowledge-graph.md)
- [27 — Coding Standards](27-coding-standards.md)
- [29 — Glossary](29-glossary.md)
