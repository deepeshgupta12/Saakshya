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

### D-019 — RSI implementation: pure EWM initialization (not SMA-init Wilder)
- **Date:** 2026-06-30
- **Context:** Two common RSI implementations exist: (a) SMA of first N gains/losses as the seed then Wilder smoothing (the original Wilder 1978 text), and (b) pure EWM with `alpha=1/period` from bar 0 (vectorized pandas `ewm(com=period-1, adjust=False)`). They converge after ~3× the period but diverge in the warmup window.
- **Alternatives considered:** Wilder SMA-init (requires a Python loop or two-pass pandas which is not vectorized); pure EWM from bar 0 (fully vectorized, pandas-native).
- **Final decision:** Use **pure EWM** (`ewm(com=period-1, min_periods=period, adjust=False)`). SPEC §9 mandates vectorized implementations; the divergence from SMA-init is negligible after ~42 bars (3× period=14) and does not affect any scanner decision boundary. Documented in `test_rsi_golden_ewm` with an analytically exact golden value (13 drops + 1 rise → RSI = 100/14). **Not TA-Lib-compatible** — known and acceptable.
- **Owner:** Quant/Engineering
- **Impact:** Indicators module (`app/indicators/core.py`); golden test value is 100/14 ≈ 7.143, not the SMA-init Wilder value. Comparisons with external tools may differ in the first ~42 bars.
- **Status:** Accepted

### D-020 — volume_ratio_20: compare today's volume to the PRIOR 20-day average (shift(1))
- **Date:** 2026-06-30
- **Context:** `rolling(20).mean()` without shift uses the current bar in the denominator, which inflates the average when today is a volume spike — defeating the purpose of the ratio for breakout detection.
- **Alternatives considered:** `rolling(20).mean()` including current bar (standard rolling average — wrong for this use case); `rolling(20).mean().shift(1)` (prior period average — correct semantics).
- **Final decision:** Use **`shift(1)`** — `volume_ratio_20 = volume / rolling(20).mean().shift(1)`. First valid bar is bar 20 (0-indexed). This gives `ratio = 3.0` when today's volume is 3× the prior 20-day average, matching the intended scanner interpretation.
- **Owner:** Quant/Engineering
- **Impact:** `app/indicators/returns.py`; warmup is 20 bars (not 19); golden test is 3000/1000 = 3.0.
- **Status:** Accepted

### D-021 — NEUTRAL sentinel: `float("nan")` for missing scanner sub-scores
- **Date:** 2026-06-30
- **Context:** Missing sub-scores (e.g. sectorStrength not yet computed, delivery data absent) must be excluded from the composite with weight redistributed pro-rata — not penalized as zero.
- **Alternatives considered:** `None` (forces Optional typing everywhere); `-1` sentinel (could collide with valid negative scores); a dedicated enum class (over-engineered for v1).
- **Final decision:** Use **`float("nan")`** as the NEUTRAL sentinel. All sub-score types are `float`, `math.isnan()` checks are clean, and pandas naturally propagates NaN through arithmetic. The `is_neutral()` helper in `normalize.py` is the canonical check.
- **Owner:** Engineering
- **Impact:** `app/scanners/normalize.py`, `composite.py`, every scanner; all sub-scores are `float` (never Optional or int).
- **Status:** Accepted

### D-022 — Schema migration: M2 indicator columns via idempotent ALTER TABLE ADD COLUMN IF NOT EXISTS
- **Date:** 2026-06-30
- **Context:** `technical_indicators` was created in M0/M1 with only base columns. Adding 26 indicator columns in M2 without breaking existing DuckDB installs required a migration strategy.
- **Alternatives considered:** DROP and recreate the table (loses existing M0/M1 data); a Flyway/Alembic migration tool (over-engineered for a local-first DuckDB single-file prototype); idempotent `ALTER TABLE ADD COLUMN IF NOT EXISTS` run after schema.sql (simple, safe, repeatable).
- **Final decision:** Use a `_M2_MIGRATIONS` list of `ALTER TABLE ADD COLUMN IF NOT EXISTS` statements in `duckdb.py`, run in `init_schema()` after the base schema. Idempotent — safe for fresh installs and existing M0/M1 installs.
- **Owner:** Engineering
- **Impact:** `app/storage/duckdb.py`; migration strategy for local-first DuckDB.
- **Status:** Accepted

### D-023 — VWAP deferred to V7 (intraday only); column exists but is always NULL in EOD mode
- **Date:** 2026-06-30
- **Context:** VWAP is computed from intraday tick/OHLCV data. With one EOD bar per day, VWAP would simply equal the adjusted close — meaningless. The `technical_indicators.vwap` column exists in the schema for forward compatibility.
- **Alternatives considered:** Remove the column entirely (breaks schema forward-compat); compute a synthetic VWAP from OHLC (misleading — not how VWAP is used); defer to V7 intraday milestone (chosen).
- **Final decision:** The `vwap` column is **always NULL in EOD mode**. No scanner/payload/AI may reference VWAP until V7. Documented in schema comments and `compute.py`.
- **Owner:** Quant/Engineering
- **Impact:** `app/indicators/compute.py`; V7 intraday milestone; any AI prompt that mentions VWAP must be blocked until then.
- **Status:** Accepted

### D-024 — Scanner weights stamped `weights-v1-hypothesis`, `validationStatus=PENDING_M3B`
- **Date:** 2026-06-30
- **Context:** The v1 composite weights (priceMomentum 25%, volumeExpansion 20%, maTrend 15%, sectorStrength 15%, rsiHealth 10%, newsSentiment 10%, riskAdjustment 5%) are a reasonable starting hypothesis but are NOT validated. Wiring the composite to any UI before validation risks shipping a "horoscope" (SPEC §6.5, D-013).
- **Alternatives considered:** Ship equal weights (also unvalidated but less misleading); defer the whole composite until M3b (loses the M3 deliverable); ship with a clear "hypothesis" stamp and gate the UI on M3b.
- **Final decision:** Stamp every scanner result with `weightsVersion="weights-v1-hypothesis"` and `validationStatus="PENDING_M3B"`. The blended composite is computed and stored but **not wired to any UI** until M3b validation ([03-scanner-score-validation.md](03-scanner-score-validation.md)) passes.
- **Owner:** Quant/Engineering + Product
- **Impact:** All four scanners; UI integration gate; M3b validation workstream.
- **Status:** Accepted (PENDING_M3B — revisit after D-013 spike completes)

### D-025 — M3b validation harness: versioned GateConfig thresholds + scipy Spearman IC
- **Date:** 2026-06-30
- **Context:** SPEC §6.5 requires proving the momentum score tracks realized forward relative strength before the composite drives any UI. The gate thresholds must be fixed in advance (not cherry-picked after seeing results) and version-stamped so any future redesign uses a new config version.
- **Alternatives considered:** Hard-coded thresholds in gate.py (not reproducible/auditable); ML-tuned thresholds (circular — can't tune until score is validated); no thresholds (just qualitative review — violates the "objective decision gate" requirement).
- **Final decision:** `app/validation/config.py` holds a `GateConfig` dataclass registry. v1 thresholds: Spearman ρ ≥ 0.6, top-bottom spread > 0, mean IC > 0, IC t-stat ≥ 1.5, no regime inversion. Gate verdict is always tagged with the config version. scipy 1.14.1 added to requirements for `spearmanr`. **Actual run verdict (`VALIDATED` / `FAILED_VALIDATION`) is logged here after `scripts/run_m3b_validation.py` executes on real NSE data.**
- **Owner:** Quant/Engineering
- **Impact:** Unblocks composite UI once verdict is `VALIDATED`; triggers redesign loop if `FAILED_VALIDATION`.
- **Status:** Accepted (harness complete; real-data verdict pending `run_m3b_validation.py` execution)

### D-026 — DuckDB reserved keyword: `pivot` column must be double-quoted in all SQL
- **Date:** 2026-06-30
- **Context:** `PIVOT` is a reserved keyword in DuckDB 1.1.3+. The `technical_indicators.pivot` column was named before this was caught. All M2 tests were pure-function tests with no DB; the conflict only surfaced in the first DB-exercising test (`test_apply_validated_verdict_sets_db_flag` in test_gate.py).
- **Alternatives considered:** Rename the column to `pivot_pp` (cleaner, but a breaking migration on existing DBs); add `"pivot"` quoting everywhere in SQL (backward-compatible).
- **Final decision:** Double-quote `pivot` in all SQL: `ALTER TABLE ... ADD COLUMN IF NOT EXISTS "pivot"`, SELECT `ti."pivot"`, INSERT/UPDATE `"pivot"=excluded."pivot"`. Affects `duckdb.py`, `compute.py`, `repository.py`.
- **Owner:** Engineering
- **Impact:** Storage layer + pipeline; no change to indicator semantics.
- **Status:** Accepted

### D-027 — Default AI provider: Ollama (`qwen2.5:7b-instruct`) replaces Claude Haiku for local-first MVP
- **Date:** 2026-06-30
- **Context:** SPEC §12 mandates local-first validation on one M1 Mac before any cloud spend. CLAUDE.md §7 names Claude Haiku (`claude-haiku-4-5-20251001`) as the default repetitive-summarization model. The dev machine has no network access to Anthropic's API (network block); it does have Ollama 0.20.6 with `qwen2.5:7b-instruct` (4.7 GB) locally installed. Using the cloud API in local-first phase would also incur per-call cost, contrary to the "zero cloud spend to validate" thesis.
- **Alternatives considered:** Keep Claude Haiku as default (network-blocked, incurs cost, violates local-first); use OpenAI (same network/cost objection); add a mock provider (no real grounding verification signal); use Ollama (local, zero cost, same OpenAI-compatible REST interface, production code path exercised).
- **Final decision:** `OllamaProvider` becomes the default provider in `app/ai/provider.py`. `Settings.ai_provider` defaults to `"ollama"`, `ai_ollama_base_url` to `http://localhost:11434`, `ai_ollama_model_cheap` and `ai_ollama_model_premium` both to `qwen2.5:7b-instruct`. The `LLMProvider` protocol abstraction means switching to Claude Haiku in production (Mode B or cloud staging) is a single env-var change (`SAAKSHYA_AI_PROVIDER=anthropic`); no business-logic code changes. The verification harness and guardrail are applied identically regardless of provider — their criticality is **higher** with a local model (higher hallucination risk), making the suppress-not-guess default essential.
- **Owner:** AI/ML + Engineering
- **Impact:** `app/ai/provider.py`, `app/config.py`; zero impact on `explainer.py`, `verify.py`, `guardrail.py` (fully provider-agnostic). Cost is 0.0 USD per call locally. Provider can be swapped at deploy time.
- **Status:** Accepted (supersedes the "Claude Haiku default" aspect of D-011; Ollama remains the local-first default until cloud staging begins)

### D-028 — M5 rate-limiter: in-process token bucket (no Redis) for local-first
- **Date:** 2026-06-30
- **Context:** SPEC §12 local-first mandate excludes Redis and all cloud infrastructure until Mode A core is validated.  The API needs rate limiting to enforce the AI bucket (30 req/min) and read-endpoint bucket (60 req/min) per docs/10 §0.4.
- **Alternatives considered:** Redis-backed rate limiter (violates local-first, adds ops overhead); middleware-library (Slow API / limits-aware deps — adds a dependency for a simple feature); in-process token bucket (no deps, deterministic in tests, swappable for production).
- **Final decision:** `app/api/ratelimit.py` implements a thread-safe in-process token bucket keyed by `(client_ip, bucket_name)`. Config-driven via `Settings.api_read_rate_limit` / `api_ai_rate_limit`. Exposed as FastAPI dependency functions (`read_rate_limit_dep`, `ai_rate_limit_dep`). Replace with Redis-backed implementation when moving to multi-worker production.
- **Owner:** Engineering
- **Impact:** `app/api/ratelimit.py`, `app/config.py`; no impact on scanner/AI business logic.
- **Status:** Accepted (local-first only; Redis swap-in is tracked in step 06 → cloud phase)

### D-029 — `do` is a reserved keyword in DuckDB — all daily_ohlc JOINs use alias `ohlc`
- **Date:** 2026-06-30
- **Context:** DuckDB treats `DO` as a reserved keyword (like `BEGIN`/`END`). Using `daily_ohlc do` as a table alias raises `Parser Error: syntax error at or near "do"`. Discovered during M5 API testing when `get_latest_ohlc_for_symbol` joined `daily_ohlc` with `stock_master`.
- **Alternatives considered:** Use `d` as alias (too short, confusing); use `daily` (confusable with a column); use `ohlc` (clearly names the table's content, zero collision risk).
- **Final decision:** All JOIN queries over `daily_ohlc` use the `ohlc` alias. Additionally, when `_OHLC_COLS` (unqualified column list) is used in a JOIN, each column is prefixed as `ohlc.{col}` to avoid ambiguity (both `daily_ohlc` and `stock_master` have `stock_id`).
- **Owner:** Engineering
- **Impact:** `app/storage/repository.py` — `get_latest_ohlc_for_symbol`, `get_universe_for_scanner`; all new JOIN queries must follow this convention.
- **Status:** Accepted

---

### D-030 — Tailwind v4: `@theme inline` CSS-variable mapping replaces `tailwind.config.ts`
- **Date:** 2026-06-30
- **Context:** M6 frontend uses Tailwind v4 (4.x). Tailwind v4 deprecated `tailwind.config.ts` in favour of a CSS-first config model. Theme values must be declared via `@theme` or `@theme inline` inside `globals.css`.
- **Alternatives considered:** Downgrade to Tailwind v3 (stable `tailwind.config.ts`); use `@theme` with inlined raw hex values; use `@theme inline` with CSS variable references.
- **Final decision:** Use `@theme inline { --color-*: var(--*) }` so that Tailwind utility classes (`bg-surface-1`, `text-bullish`, etc.) reference the CSS custom properties at runtime. This enables instant dark/light switching via `data-theme` attribute without JS recompilation. All semantic token names from `docs/07 §1` are preserved.
- **Owner:** Frontend
- **Impact:** `web/app/globals.css`, `web/src/styles/tokens.css` — all component authors use semantic Tailwind utilities only, never raw hex.
- **Status:** Accepted

### D-031 — Zod v4 breaking changes: `z.record()` 2-arg, `z.enum()` removed, `z.string()` for enum fields
- **Date:** 2026-06-30
- **Context:** Zod v4 (4.x) has two breaking API changes relevant to M6 schemas: (1) `z.record(valueSchema)` is no longer valid — `z.record(z.string(), valueSchema)` is required; (2) `z.enum(["A","B"])` requires a tuple literal or the Zod v4 `z.enum([...] as const, ...)` overload, which doesn't match the TS overload signatures cleanly in strict mode.
- **Alternatives considered:** Pin Zod to v3; use `z.enum()` with `as const` tuple — hits type inference issues in strict TS; replace with `z.string()` and cast in the client layer.
- **Final decision:** (1) All `z.record()` calls use 2 arguments; (2) all API enum fields (`data_confidence`, `cache`) use `z.string()`, with explicit `as SomeType["field"]` casts in `client.ts` where the TypeScript type constrains the string. No runtime behavior change; type safety is maintained end-to-end via the client mapping layer.
- **Owner:** Frontend
- **Impact:** `web/src/lib/api/schemas.ts`, `web/src/lib/api/client.ts`, `web/src/types/index.ts`.
- **Status:** Accepted

### D-032 — Lightweight Charts v5: `chart.addSeries(SeriesType, opts)` replaces named series methods
- **Date:** 2026-06-30
- **Context:** TradingView Lightweight Charts v5 (5.x) removed `chart.addCandlestickSeries()`, `chart.addLineSeries()`, and `chart.addHistogramSeries()`. The v5 API uses a generic `chart.addSeries(SeriesType, options)` with named series type imports (`CandlestickSeries`, `LineSeries`, `HistogramSeries`) from the package root.
- **Alternatives considered:** Pin to lightweight-charts v4 (stable named methods); upgrade and migrate (1–2 call sites).
- **Final decision:** Use v5 with the `addSeries(SeriesType, opts)` pattern throughout `PriceChartImpl.tsx`. Since we're already on v5 in `package.json`, migrating is correct; locking to v4 would be technical debt immediately.
- **Owner:** Frontend
- **Impact:** `web/src/components/charts/PriceChartImpl.tsx` — all series creation uses the v5 API.
- **Status:** Accepted

### D-033 — ui-ux-pro-max design system: Modern Dark Cinema style, JetBrains Mono, spring physics, stagger animations
- **Date:** 2026-06-30
- **Context:** The M6 frontend was initially built without invoking the `ui-ux-pro-max` design skill. All components were functional but lacked the premium, evidence-led aesthetic required by docs/07. A dedicated design-upgrade pass was performed using the skill's "Modern Dark Cinema" style (glassmorphism, radial gradients, depth layering) with the Saakshya design system persisted to `design-system/saakshya/MASTER.md`.
- **Alternatives considered:** Keep basic Tailwind styling; use a different style (Neumorphic, Claymorphic); use an existing component library (shadcn-ui default theme).
- **Final decision:** Adopt the ui-ux-pro-max "Modern Dark Cinema" style palette with the following binding decisions:
  - **JetBrains Mono** (via `next/font/google`) for all prices, scores, metrics, and data values; wired as `--font-mono-code` CSS variable.
  - **Spring physics** for all interactive transitions: `damping: 32, stiffness: 300, mass: 0.85` (drawers); `damping: 24, stiffness: 260` (tiles); `damping: 28, stiffness: 400` (snappy actions).
  - **Expo-out easing** `[0.16, 1, 0.3, 1]` for content reveals; exit at ~65% of enter duration.
  - **Stagger sequences**: 30–40ms per item, capped ~300ms total; `staggerContainer` + `staggerRow`/`staggerTile` variants.
  - **AI violet accent** (`--ai: #9A7BFF`): left-border rule `[3px]` + radial gradient glow overlay on all AI cards.
  - **`useReducedMotion()` respected** throughout — all count-up, stagger, and spring animations skip or show final state when reduced-motion is active.
  - **Min touch targets 44px** (`min-h-[44px]`, `cursor-pointer`, `touch-action: manipulation`) on all interactive elements.
  - **Skip-link** + `aria-current="page"` + `aria-live="polite"` on `NotAdviceBanner` for accessibility.
- **Owner:** Frontend
- **Impact:** All files in `web/src/components/` (ui, layout, market, scanner, stock, compliance, charts); `web/src/lib/motion/variants.ts`; `web/app/layout.tsx`; `design-system/saakshya/MASTER.md`.
- **Status:** Accepted

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
| D-011 | 2026-06-29 | Default model Claude Haiku (production target; superseded locally by D-027) | AI/ML | Cost/latency | Provisional |
| D-012 | 2026-06-29 | Corp-action adjustment as first-class workstream | Data Eng | Indicators/backtest | Accepted |
| D-013 | 2026-06-29 | Scanner-score validation (M3b) gating spike | Quant | Whole product | Open |
| D-014 | 2026-06-29 | GitNexus knowledge-graph adoption | Eng/Tooling | Agentic workflow | Accepted |
| D-015 | 2026-06-29 | Build-vs-buy corp-action adjustment → BUILD in-house | Data Eng | Indicators/backtest/ingestion | Decided |
| D-016 | 2026-06-29 | Build-vs-buy news/sentiment feed → BUILD in-house | AI/ML + Data Eng | News-sentiment/entity resolution | Decided |
| D-017 | 2026-06-29 | Personalization line: complete scope, advisory tier IA-gated | Product + Compliance | Personalization/preferences/Mode-C gating | Decided |
| D-018 | 2026-06-29 | Data vendor + redistribution rights → DEFERRED (prototype on yfinance + NSE Bhavcopy) | Product + Data + Counsel | Ingestion source / data-licensing | Deferred |
| D-019 | 2026-06-30 | RSI: pure EWM initialization (vectorized, not SMA-init Wilder) | Quant/Eng | Indicators/tests | Accepted |
| D-020 | 2026-06-30 | volume_ratio_20: compare to PRIOR 20-day average (shift(1)) | Quant/Eng | Indicators/scanners | Accepted |
| D-021 | 2026-06-30 | NEUTRAL sentinel = float("nan") for missing sub-scores | Engineering | All scanners / normalize | Accepted |
| D-022 | 2026-06-30 | M2 migration: idempotent ALTER TABLE ADD COLUMN IF NOT EXISTS | Engineering | duckdb.py / storage | Accepted |
| D-023 | 2026-06-30 | VWAP deferred to V7 (intraday only); column always NULL in EOD | Quant/Eng | indicators/schema | Accepted |
| D-024 | 2026-06-30 | Weights stamped weights-v1-hypothesis / PENDING_M3B; composite not wired to UI | Quant/Eng + Product | All scanners / UI gate | Accepted |
| D-025 | 2026-06-30 | M3b: GateConfig v1 thresholds (ρ≥0.6, IC t-stat≥1.5); scipy 1.14.1 added | Quant/Eng | Composite UI gate | Accepted (verdict pending — yfinance network-blocked on dev machine) |
| D-026 | 2026-06-30 | DuckDB reserved keyword: `pivot` must be double-quoted in all SQL | Engineering | Storage/pipeline | Accepted |
| D-027 | 2026-06-30 | Default AI provider: Ollama (`qwen2.5:7b-instruct`) replaces Claude Haiku for local-first MVP | AI/ML | Provider abstraction / cost | Accepted |
| D-028 | 2026-06-30 | M5 rate-limiter: in-process token bucket (no Redis) for local-first | Engineering | API / ops | Accepted |
| D-029 | 2026-06-30 | `do` reserved in DuckDB — use `ohlc` alias in all daily_ohlc JOINs | Engineering | Storage / all JOIN queries | Accepted |
| D-030 | 2026-06-30 | Tailwind v4 theming: `@theme inline` CSS-var references (no `tailwind.config.ts`) | Frontend | Design tokens / runtime switching | Accepted |
| D-031 | 2026-06-30 | Zod v4 API changes: `z.record()` requires 2 args (key+value); `z.enum()` requires tuple; all API schemas use `z.string()` + explicit casts | Frontend | API client / Zod schemas | Accepted |
| D-032 | 2026-06-30 | Lightweight Charts v5: series created via `chart.addSeries(SeriesType, opts)` — `addCandlestickSeries` / `addLineSeries` etc. removed | Frontend | PriceChartImpl | Accepted |
| D-033 | 2026-06-30 | ui-ux-pro-max design adoption: Modern Dark Cinema, JetBrains Mono, spring physics, stagger, AI violet accent, a11y (skip-link, aria-current, reduced-motion) | Frontend | All web components, motion variants, layout | Accepted |
| D-034 | 2026-06-30 | Tailwind v4 CSS variable syntax: `[--var]` bracket syntax is invalid in v4 (outputs literal string, not `var()`); all 191 occurrences migrated to `(--var)` paren syntax | Frontend | All web components (bulk sed replacement) | Accepted |
| D-035 | 2026-06-30 | Scanner enrichment: JOIN via `stock_master.primary_symbol` (not `exchange_symbols.symbol` which carries `.NS` suffix); fixes null name/sector/price in scanner results | Backend | `app/api/routers/scanners.py` enrichment query | Accepted |
| D-036 | 2026-06-30 | Sector constituents: use `sm.primary_symbol` (not `es.symbol`) so constituent links route to `/stocks/RELIANCE` not `/stocks/RELIANCE.NS` | Backend | `app/api/routers/sectors.py` | Accepted |
| D-037 | 2026-06-30 | Market breadth (advance/decline): compute from actual OHLC close-vs-prev-close, not from momentum scanner count (which is 0 when momentum has no results) | Backend | `app/api/routers/market.py` | Accepted |
| D-038 | 2026-06-30 | Scanner slug normalisation: URL slugs use hyphens (`moving-average`) but backend keys use underscores (`moving_average`); normalise with `.replace(/-/g, "_")` in the API client | Frontend | `web/src/lib/api/client.ts` | Accepted |
| D-039 | 2026-06-30 | AI payload critical-key names corrected: `ret_3m_pct`→`ret_21d`, `sma50`→`sma_50` to match `technical_indicators` column names; fixes universal AI summary suppression | Backend | `app/ai/payload.py` | Accepted |
| D-040 | 2026-06-30 | Named static scanner pages (`/scanners/momentum/page.tsx` etc.) deleted; they redirected to themselves (infinite loop), shadowing the working `[slug]/page.tsx` dynamic route | Frontend | `web/app/(market)/scanners/` | Accepted |
| D-041 | 2026-07-01 | M7 auth: HS256 JWT (not RS256) for local-first MVP; 15-min access tokens in-memory only, 30-day rotating refresh tokens in localStorage; RS256 upgrade gated on cloud deploy | Auth | `app/auth/tokens.py` | Accepted |
| D-042 | 2026-07-01 | Argon2id with `time_cost=3, memory_cost=65536` (64MB) chosen for local-first M1 Mac; meets OWASP recommendation without causing memory pressure | Auth | `app/auth/passwords.py` | Accepted |
| D-043 | 2026-07-01 | Refresh-token replay detection: replayed token (already `revoked=TRUE`) triggers full-family revoke, not just that one token — defends against stolen token + partial race | Auth | `app/api/routers/auth.py` | Accepted |
| D-044 | 2026-07-01 | Market brief: single `GET /api/ai/market-brief` endpoint; cached per `brief_date` in `market_brief_cache`; Ollama `cheap` tier (now `gemma4:4b` per D-051); no external call if suppressed/degraded | AI | `app/ai/market_brief.py` + `app/api/routers/ai.py` | Accepted |
| D-045 | 2026-07-01 | Signup requires both `consent_not_advice=true` + `consent_ai_use=true` as explicit body fields; server-side gate (not just client-side checkbox) — blocked with 422 if missing | Compliance | `app/api/routers/auth.py` | Accepted |
| D-046 | 2026-07-01 | `daily_ohlc` joined via `stock_id` FK (not `symbol` column); alias must be `ohlc` not `do` (DuckDB reserved keyword per D-029); use `close_adj` not `close` | Correctness | `app/api/routers/watchlists.py` | Accepted |
| D-047 | 2026-07-01 | OAuth social sign-in (Google OIDC) implemented as `POST /api/auth/oauth/google`; validates ID token via Google JWKS (python-jose RS256), maps to `oauth_identities`; requires `GOOGLE_CLIENT_ID` env var — returns 503 if unconfigured | Auth | `app/auth/oauth.py`, `app/api/routers/auth.py` | Accepted |
| D-048 | 2026-07-01 | News pipeline MVP uses heuristic keyword-based sentiment (v0.1-heuristic) as a deterministic, auditable baseline; finance-tuned ML classifier deferred to step 15; low-confidence result (< 0.55) suppressed to "neutral" (suppress-not-guess rule) | AI/Correctness | `app/news/sentiment.py` | Accepted |
| D-049 | 2026-07-01 | News surfacing threshold `SURFACING_THRESHOLD=0.75` (versioned in `resolver.py`); below-threshold links stored in `news_stock_links` with `is_surfaced=FALSE` and never returned by API; above-threshold links carry `link_confidence` for display | Compliance | `app/news/resolver.py`, `app/api/routers/news.py` | Accepted |
| D-050 | 2026-07-01 | Watchlist `/watchlist` route placed under `(market)` route group (shares TopNav + Footer); auth guard is client-side redirect; free tier limited to 1 watchlist (enforced in `WatchlistClient`); Watchlist nav item shown only when authenticated | Frontend | `web/app/(market)/watchlist/`, `web/src/components/layout/TopNav.tsx` | Accepted |
| D-051 | 2026-07-01 | Default local Ollama models switched from `qwen2.5:7b-instruct` to **Gemma 4** (`gemma4:4b` cheap / `gemma4:12b` premium, requires Ollama ≥ 0.31); cloud path unchanged (Claude Haiku / premium Claude); provider abstraction requires no code change — config defaults only | AI/ML | `app/config.py`, `app/ai/provider.py`, `docs/14` | Accepted |

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
| Indicators: vectorized/pandas-ta vs TA-Lib | Local M2 | **D-019/D-020 — Decided: pure vectorized pandas/NumPy; no TA-Lib** (RSI: EWM init; volume_ratio: shift(1)) |
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
