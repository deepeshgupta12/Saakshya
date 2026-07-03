# Saakshya — Canonical Product & Build Specification

**Version:** 1.0 (reconciled) · **Date:** 2026-06-29 · **Status:** Pre-build, Mode-A scope frozen for v1

This document is the single source of truth for Saakshya. It reconciles two prior inputs:

- **The Saakshya product spec** (markdown) — the full, ambitious product vision.
- **The Indian Equity Research Platform Spec v3** (PDF) — the same product after a legal / correctness / economics hardening pass, including a local-first build plan.

It supersedes both. Build from this document; treat the two source docs as historical context only.

---

## 0. How to read this document — the precedence rule

The two source documents **disagree on what is legal to ship**. The Saakshya spec was written in a permissive "research tool with disclaimers" style; the v3 spec rewrote that posture after post-2025 SEBI enforcement. This document resolves every such conflict with one rule:

> **Where the Saakshya vision and the v3 constraints conflict, the v3 constraint wins.** Disclaimers do not cure advisory substance. A feature ships only when the regulatory mode it requires (Section 2) is in force.

Everything in the Saakshya vision is preserved — but re-sequenced and, where necessary, **re-worded or deferred** so that v1 is legal, correct, and economically viable.

---

## 1. What Saakshya is

Saakshya ("evidence") is an AI-powered Indian equity **research, scanning, and portfolio decision-support** platform for NSE/BSE retail investors, swing traders, and analysts. It surfaces momentum, volume, sector strength, technical setups, news sentiment, and risk signals from **end-of-day data**, and uses AI to **explain deterministic, data-grounded signals** in plain language.

**The product philosophy is evidence-first and it doubles as the compliance posture:** every output traces to visible data and explainable logic, and the AI layer *explains* signals — it never *invents* numbers, prices, news, or targets, and never issues a buy/sell instruction in v1. This is what separates Saakshya from a stock-tips app, and it is also what keeps the AI layer out of regulatory trouble.

---

## 2. Foundational decision — Regulatory Operating Mode

This is the decision that gates data use, AI language, shippable features, and legal exposure. It must be confirmed with an Indian securities lawyer **before architecture is frozen**. (Not legal advice; SEBI's RA / finfluencer rules changed repeatedly through 2024–2026 and continue to evolve.)

| Mode | What it permits | What it costs |
|---|---|---|
| **A — Pure analytics tool** | Display data, indicators, charts, scanners (score + reasons), sector/news/risk analytics; user draws their own conclusions. **No** per-stock entry/target/stop-loss, **no** "candidate" buy-leans, **no** ranked "what to buy" briefs. | Lowest legal risk. Value proposition is "best screener + best explanations," not "tells me what to buy." |
| **B — Registered Research Analyst (RA)** | Publish stock-specific research and recommendations — the full vision, legally. Unlocks entry/target/SL levels and "candidate" layers. | NISM Series-XV cert; RAASB enlistment (via BSE); FD lien scaled to client count; a formal research report behind each recommendation; record-keeping; per-client fee caps (~₹1.51L/yr/family); **mandatory disclosure that AI is used in producing research**. |
| **C — Registered Investment Adviser (IA)** | Personalized, client-specific advice ("given your portfolio, do X"). | Strictest regime. Only needed for true per-user advice. Not for v1. |

**Decision for v1:** Ship in **Mode A**. Run **RA registration (Mode B) in parallel** as a gating dependency that later unlocks the recommendation-flavored features. This launches legally and fast on the strongest defensible ground (data quality + scanner breadth + explanation quality) while registration proceeds on its own track.

**Gating principle for the whole document:** no feature ships until the mode it requires is in force.

---

## 3. Positioning & hard boundaries

**Positioning (Mode-A safe):** "An AI-powered Indian stock research and market scanner that helps users discover technically strong setups, understand sector momentum, analyse news sentiment, and track portfolios — so they can make their own, better-informed decisions."

**Do not position as:** "AI stock tips," "guaranteed buy/sell calls," "assured target/stop-loss engine," "AI advisor that tells users where to invest."

### 3.1 Permitted language (descriptive, non-directive)
"appearing in the momentum scanner" · "trading above its 50-DMA" · "volume expanded 2× versus its 20-day average" · "news sentiment classified positive" · "historically a resistance zone" · "elevated short-term volatility" · "risk is elevated" · "evidence suggests" · "should be monitored" · "not investment advice".

### 3.2 Prohibited in Mode A (unlocked only under RA)
- Per-stock **entry / target / stop-loss** levels.
- **"Candidate" labels that function as buy-leans.**
- Daily briefs framed as **"what to buy/sell next session"** or ranked actionable picks.
- Behaviour-derived per-stock suggestions ("because you view banking, consider HDFC Bank") — that is Mode C.

### 3.3 Prohibited in **every** mode, always
Any guarantee, assured/confirmed target, "risk-free," "multibagger," "sure-shot," "buy now," "best stock for you," or implied/explicit return claim. Enforced at **output time**, not just in the prompt (see 7.4 / 6.4).

---

## 4. The reconciliation — feature-by-feature mode mapping

This is the heart of the document. Every Saakshya module is tagged with the mode it requires and when it ships. `A` = Mode-A safe · `A+RA` = needs RA before the directive parts · `B` = RA-only · `C` = IA-only · `N/A` = mode-neutral infrastructure.

| Feature | Saakshya ref | v3 ref | Mode | Ships in | Reconciliation note |
|---|---|---|---|---|---|
| Market dashboard, indices, breadth | §7.1 | 5.1 | A | v1 / Phase 1 | AI market summary must be **descriptive, not directive**. |
| Momentum / volume / RSI / MA scanners | §7.2–7.5 | 5.2–5.5 | A | v1 / Phase 1 | Show **score + reasons**. Scores must be **validated** (6.5). Replace "momentum candidate" with "appears in the momentum scanner". |
| Breakout / breakdown scanner | §7.6–7.7 | 5.6 | A | v1 / Phase 1 | False-breakout / breakdown **risk flag** is fine; **no "buy the breakout"** phrasing. |
| Sector strength dashboard | §7.8 | 5.7 | A | v1 / Phase 1 | Index/sector technical analysis is explicitly **lower-risk**. |
| Stock detail page | §7.9 | 5.11 | A | v1 / Phase 1 | Keep facts, scores, **descriptive** support/resistance. **Remove** entry/target/SL/invalidation "zones" — those are RA-gated (see below). |
| AI stock research summary | §7.10 | 5.10 | A | v1 / Phase 1–2 | Grounded in structured signals only; **runtime-verified** (7.1). Drop directive tails like "before fresh action". |
| News sentiment | §7.11 | 5.8 | A | Phase 2 | Hard entity-resolution + finance-tuned sentiment required (6.4). |
| Corporate announcements | §7.12 | 5.9 | A | Phase 2–3 | Simplify, **do not exaggerate impact**. |
| Portfolio tracker + risk flags | §7.13 | 5.13 | A | Phase 2 | "You hold X; it broke its 50-DMA" is **factual**. "Sell X" is **not** — never prescribe. |
| Watchlist | §7.14 | 5.14 | A | Phase 2 | "AI suggested watchlist" must be filter-based discovery, not per-user buy-leans. |
| Alerts | §7.15 | 5.15 | A | Phase 2 | **Event-reporting only** ("entered the scanner"), never prescriptive ("buy at open"). EOD-batch in v1. |
| AI daily market brief | §7.16 | 5.16 | A | Phase 2 | Reports events and what to **monitor**; never a ranked "what to buy". |
| Peer comparison | §7.17 | 5.12 | A | Phase 3 | **Comparative, not directive**. |
| Strategy builder | §7.18 | 5.17 | A | Phase 4 | No-code scanner builder; outputs are **lists**, not calls. |
| Backtesting engine | §7.19 | 5.18–5.19 | A | Phase 4 | Ships **only** with integrity controls (6.3). An inflated backtest is an implied-performance claim. |
| Thematic baskets | §7.20 | 5.29 | A | Phase 3 | **Bucket views, not model portfolios.** |
| Risk engine / risk model | §13.4 | 5.20 | A | v1 / Phase 1 | Risk scoring is **defensible and differentiating**. |
| Fundamentals / valuation / earnings | §7.17, §13 | 5.24–5.28 | A | Phase 3 | **Descriptive valuation bands**, not buy/sell triggers. |
| Institutional activity | §7.17 | 5.26 | A | Phase 4 | Data-availability dependent; strong premium feature. |
| ML ranking / probability bands | §6.5, §13.7–13.8 | — | A | Phase 4–5 | Predict **probability bands**, never exact price; frame as measurement, **never a return promise**. |
| Agentic AI workflows | §6.6, §12.4 | — | A / N/A | Phase 2+ | Each agent's **output** must pass Mode-A guardrails + grounding. Compliance-review agent is **infrastructure, required**. |
| Personalization | §6, §9.9 | 5.30 | A / C | Phase 3 (limited) | **Navigation** personalization only in Mode A (layout, followed sectors, default filters). **Per-stock** behavioural suggestions are Mode C — out. See §8. |
| Community / expert layer | §6.9 | 5.32 | A | Phase 5 | Heavy moderation against tips / pump-and-dump. |
| **Technical entry / target / SL / invalidation zones** | §4.2, §6.4, §7.9 | **5.21** | **B** | **Phase 5 (RA only)** | **Advisory-in-substance. Cannot ship unregistered.** This is the single biggest divergence from the Saakshya spec. |
| **"Candidate" recommendation layer** | §5 (philosophy) | **5.22** | **B** | **Phase 5 (RA only)** | A "candidate" label that functions as a buy-lean is advisory-in-substance. Use neutral scanner-membership language instead. |
| Live / real-time data + intraday alerts | §6.7, §14.3 | — | A* | Phase 5 | Separately **licensed**; WebSocket tier. *Mode-A-safe in content but gated on data licensing. |
| Broker integration / execution | §6.8 | 5.31 | B / C | Phase 5+ | Separate licensing, security, and operational duties. Late phase only. |
| Advisory / model portfolios | §6.9 | — | C | Out (until IA) | Requires Investment Adviser registration. |

---

## 5. Language neutralization guide

The Saakshya spec uses several phrasings that cross the Mode-A line. Build these swaps into the guardrail layer (6.4) and the design review. Left = as written in the Saakshya spec; right = the Mode-A-safe form.

| Saakshya wording (as written) | Mode-A-safe replacement | Why |
|---|---|---|
| "momentum candidate" / "watchlist candidate" (buy-lean) | "appears in the momentum scanner" / "matches this filter" | "Candidate" label = 5.22, RA-gated. |
| "stop-loss zone" / "target zone" / "entry zone" / "invalidation zone" | **Not shown in Mode A** (RA-gated, Phase 5) | Per-stock levels = 5.21, advisory-in-substance. |
| "support zone" / "resistance zone" | "historically a resistance zone" / "a level that has acted as support" | Descriptive/historical framing is permitted. |
| "Sell X" / "exit this holding" | "X broke below its 50-DMA" (state the event) | Factual event reporting vs. a prescriptive call. |
| Daily brief "what to buy/sell next session" | "stocks that entered/exited the momentum scanner today" | Event report, not actionable picks. |
| AI summary: "…should be monitored **before fresh action**" | "…is a level to watch" | Drop the implied trade decision; keep the observation. |
| "best stock for you" / "must invest" / "guaranteed" / "sure-shot" / "risk-free" / "multibagger" | **Blocked in every mode** | Always prohibited; enforce at output time. |

**Worked example — the AI stock summary from Saakshya §7.10, neutralized:**
> "This stock is currently showing positive short-term momentum because it is trading above its 20-DMA and 50-DMA, and recent volume is higher than its 20-day average. Sector strength is supportive. However, RSI is elevated, so the risk of a short-term pullback is higher. The nearest resistance level is one to watch." *(Not investment advice.)*

Only the original's trailing "…should be monitored **before fresh action**" was changed — everything else was already evidence-backed and Mode-A safe.

---

## 6. Correctness & AI constraints (first-class)

The Saakshya spec treated these as secondary; v3 promotes them to hard requirements because they decide whether the product is *accurate* and whether its *economics* work. They are first-class here.

### 6.1 Corporate-action adjustment — the item that decides whether every indicator is real
A 1:1 bonus or 1:2 split looks like a price crash to an unadjusted series and silently corrupts RSI, MAs, breakout detection, and every backtest. Maintain a **corporate-action master** (splits, bonuses, dividends, rights, mergers, symbol changes); store **both raw and adjusted** series; back-adjust consistently across the full history used by any indicator or backtest; **reconcile against a second source** before publishing. This is its own engineering workstream, not a pipeline bullet. *(yfinance's auto-adjustment is a prototyping convenience — see §9 — not the production engine.)*

### 6.2 Data quality, as-of versioning, correction workflow
Point-in-time / as-of versioning so any displayed value is reproducible for the date it was shown; a documented correction workflow (**detect → quarantine → correct → re-emit** dependent indicators and AI summaries); automated checks for missing candles, abnormal jumps, duplicate symbols, delisted securities, inconsistent volume; a user-visible **data-confidence indicator**. **AI summaries are suppressed, not guessed, when critical inputs are missing.**

### 6.3 Backtesting integrity (mandatory before backtesting ships — Phase 4)
Survivorship-bias control (include delisted/merged names for the period) · look-ahead control (only data available at each simulated decision point, including corp-action-adjusted prices as of that date) · point-in-time index membership · realistic fills (slippage + liquidity caps for small/mid-caps) · honest framing ("past performance does not indicate future results", assumptions exposed). An inflated backtest is also an implied-performance claim → a compliance risk.

### 6.4 News-to-symbol resolution & financial sentiment
Curated **symbol-alias + corporate-hierarchy** map; **confidence scores** on every news→symbol link with a surfacing threshold; a **finance-tuned** sentiment/impact classifier evaluated against a labelled Indian-market set (a general model fails on "misses estimates, stock rallies"); retained source links + timestamps so a user sees *why* a sentiment was assigned.

### 6.5 Scanner-score validation — the M3b spike that de-risks the whole product
The scoring weights (25% momentum, 20% volume, …) are reasonable-sounding but arbitrary. Before building UI on top of them, **prove on historical adjusted data that at least one score (start with momentum) measures what it claims** (e.g. that the momentum score tracks realized relative strength). This is measurement validation, **not** a performance claim — it separates a credible scanner from a horoscope. If it's noise, redesign the scoring **now**.

### 6.6 AI grounding & output verification
A **structured payload contract**: the AI receives only computed metrics, scanner tags, news summaries, and risk markers, and may reference nothing else. A **runtime validator** checks every number and named fact in the AI output against the payload and **blocks or regenerates on mismatch**. An **evaluation harness** with a golden dataset + regression tests runs on every prompt/model change. An **audit log** of prompt, input data, model version, and user-visible output for every generation.

### 6.7 Mandatory AI-use disclosure (SEBI, Mode B)
If/when operating under RA, the registered analyst **must disclose AI use to clients** and remains fully responsible for AI-assisted output. Build this into onboarding + terms. (Missing from the Saakshya §18 compliance list — added here.)

### 6.8 Cost / latency / caching budget — the missing economics
A full-universe daily LLM pass over ~2,000+ NSE names is a real token bill and latency window that threatens freemium economics. Levers: **regenerate-on-change** (only re-summarize when a stock's signals change category) · **tiering** (full daily coverage for a watched subset; on-demand + cached for the long tail) · a hard **monthly AI-spend ceiling** with alerting and graceful degradation · a **latency budget** (EOD generation finishes inside the overnight window; on-demand has a P95 target + non-AI fallback) · **provider abstraction** (cheap model for repetitive summarization, premium model for complex synthesis).

### 6.9 Guardrail language enforcement
A versioned blocked-phrase / pattern list (guarantee, assured, sure-shot, risk-free, target confirmed, buy now, …) enforced **at output time**, not just in the prompt, and versioned in the admin console alongside the compliance rules. The Saakshya §12.7 list is the seed; the change is *where* it runs.

---

## 7. Personalization vs compliance — reconciliation

The Saakshya spec's personalization (personalize toward what the user looks at) quietly contradicts compliance. Nudging a specific user toward specific securities based on behaviour is **Investment Adviser (Mode C)** territory.

- **Allowed in Mode A:** personalize layout; surface sectors/instruments the user already follows; default scanner filters to a stated risk preference; prioritize relevant educational content. This personalizes **navigation, not recommendations**.
- **Not allowed in Mode A:** behaviour-derived per-stock suggestions ("because you view banking, consider HDFC Bank").
- Keep personalization transparent and user-editable, and **keep the line explicit in design review** so it doesn't creep across releases.

---

## 8. Data strategy & ingestion sources

**EOD-first (T+1).** Ingest the previous session after close → normalize → corp-action adjust → compute indicators + sector scores → run scanners → process news → generate AI summaries → deliver the morning brief. This suits swing trading, research, and portfolio monitoring, and avoids both live-data licensing cost and a large slice of compliance exposure. Live data is a later, separately-licensed premium tier.

**Licensing reality:** Kite Connect data is licensed for the authenticated user. Commercial redistribution of NSE/BSE data stays blocked (`supports("redistribution") == False`) until a redistribution licence is in force. Historical adjusted depth (years, including delisted names) is a separate procurement item and a gating dependency for scanners and backtesting.

**Single `DataSource` adapter — Zerodha Kite Connect is the sole source (D-058)** (business logic never depends on the vendor; the seam is kept for a future vendor swap):

| Source | Provides | Stage | Caveat |
|---|---|---|---|
| **Zerodha Kite Connect** | Daily OHLCV via `historical_data`; NSE/BSE instrument master | **Sole source (local + production)** | Paid API. Candles **unadjusted**; **no delivery %**; **no corporate-action API**. Daily `access_token` (expires ~07:30 IST), auto-refreshed by `app/data/kite_auth.py` (TOTP login + browser-callback fallback). Not licensed for commercial redistribution. |

**Config:** `SAAKSHYA_ACTIVE_DATA_SOURCE=kite`; `KITE_API_KEY`/`KITE_API_SECRET`/`KITE_ACCESS_TOKEN` from `.env`. Adapter: `app/data/kite_source.py`. **Known gaps** (documented, not silent — see docs/12 §3.4): no corp-action adjustment (series stored unadjusted), no delivery %. *(yfinance, NSE Bhavcopy and the TrueData/Global-Datafeeds layering were removed in the 2026-07-02 reset.)*

---

## 9. Architecture

Two stacks: the **production** target (both source docs agree) and the **local-first** stack that the v3 plan uses to build the MVP on one laptop.

| Layer | Production stack | Local-first stack (M1 Mac) |
|---|---|---|
| Frontend | Next.js, React, TS, Tailwind, Framer Motion; TradingView Lightweight Charts / ECharts | **Deferred** (API + notebook first; add Next.js once core is validated) |
| Backend | Python FastAPI, Celery, Redis | FastAPI + Uvicorn; **plain scripts / Makefile** (defer Celery+Redis) |
| Data processing | Polars/Pandas, NumPy, pandas-ta; Dagster/Airflow | Vectorized pandas/NumPy or pandas-ta — **avoid TA-Lib** (M1 C-lib friction) |
| Databases | **TimescaleDB (analytics core) + MongoDB (user/app docs)** — polyglot (D-059); Redis/ClickHouse/S3 later | **TimescaleDB + MongoDB via docker-compose** (DuckDB retired, D-059) |
| Search / vector | OpenSearch/Elasticsearch; pgvector | Deferred |
| AI/ML | LangGraph/LlamaIndex, RAG, classifiers, ranking; provider abstraction | Anthropic SDK → **Claude Haiku** (`claude-haiku-4-5-20251001`), key via env var |
| Infra/DevOps | Cloud (AWS/GCP), Docker, K8s, Terraform, GitHub Actions, observability + **AI-spend meter** | Docker Desktop for the two local DBs (`docker-compose.yml`); otherwise one laptop, plain scripts |
| Compliance | Admin console: blocked-words, prompts, source reliability, audit logs | Prototype-grade guardrail + grounding check in the AI module |

**Two architectural additions over the originals** (both stacks): **as-of versioning fields** on all time-series and indicator entities, and an **AI-generation audit-log** entity. Keep the **provider abstraction** from the Saakshya stack — default to Claude Haiku locally, reserve a premium Claude model for complex synthesis later.

---

## 10. Reconciled risk-first roadmap

The Saakshya roadmap (V1–V9) is **feature-sequenced**; v3's is **risk-sequenced**. The reconciled roadmap below is risk-first — it retires the assumptions that can kill the product *before* broad feature work — while preserving the Saakshya feature content. Note the key correction: **Saakshya V4 (technical levels) is RA-gated and moves to the end (Phase 5), not the middle.**

| Phase | Focus | Maps to Saakshya | Exit gate |
|---|---|---|---|
| **0 — De-risk** | Legal mode decision; data-vendor + adjusted-history procurement; scanner-score validation spike | (precedes V1) | Counsel confirms Mode-A scope & starts RA filing; signed data contract; evidence ≥1 scanner score carries signal |
| **1 — EOD core** | Ingestion + corp-action adjustment; stock master; market dashboard; momentum/RSI/volume scanners; sector dashboard; stock page; risk engine | V1 | Indicators reconcile vs a 2nd source; corp actions correct on a split/bonus test set |
| **2 — Personalize** | Accounts, watchlists; portfolio tracker; AI stock summary + daily brief (event-reporting); news sentiment; alerts | V2 + V3 | AI verification harness blocks fabricated numbers in regression tests; AI cost within ceiling at projected scale |
| **3 — Breadth** | Custom scanner builder; peer comparison; thematic baskets; corp announcements; fundamentals/valuation bands; limited (navigation) personalization | (part V4, descriptive only) | News-to-symbol precision above target; valuation framed descriptively |
| **4 — Quant** | Backtesting + strategy builder (integrity controls); advanced risk engine; institutional activity; ML ranking / probability bands; mobile; premium tiers | V5 + parts of V4/V6 | Backtests pass survivorship / look-ahead / point-in-time audits; freemium unit economics validated |
| **5 — RA-gated & live** | **RA-gated recommendation layer (5.21/5.22 — Saakshya V4 technical levels)**; live licensed data + intraday; broker integration; community; agentic depth | V4 (gated) + V6–V9 | RA registration **in force**; execution licensing + moderation reviewed by counsel |

*Agentic AI (Saakshya V6) is not a single phase — each agent lands when its underlying data + guardrails exist (market-brief & stock-research agents in Phase 2, etc.), with every output passing Mode-A verification.*

---

## 11. Monetization

Freemium retained: **Free** (EOD dashboard, limited scanners, limited watchlist, basic AI market summary) · **Premium** (full scanners, unlimited watchlists, portfolio, AI summaries, news sentiment, alerts, sector, peer) · **Pro** (strategy builder, backtesting, thematic baskets, portfolio risk engine, exports, premium briefs) · **Enterprise/API**. Two constraints the Saakshya spec omitted:

- If any tier operates under **RA** for individual clients, the **SEBI fee cap (~₹1.51L/yr/family)** applies — structure premium tiers with that ceiling in mind.
- **Data-licensing and AI-generation are recurring per-user costs.** Model them into each tier *before* fixing prices; a flat freemium tier with full-universe daily AI summaries is loss-making at scale without the caching strategy in 6.8.

---

## 12. Local-first build plan (the immediate execution track)

Build and run the Phase 0–1 MVP core entirely on one Apple-Silicon Mac, to retire the three riskiest assumptions — **legal-safe Mode-A output, data correctness, and whether scanner scores carry signal** — for the cost of an API key. Strictly **Mode A**; no RA-gated feature is built locally (building them "just to see them" would create the exact substance-over-form exposure §2 warns against).

**Project structure** (mirrors production so modules lift into services later):
```
saakshya/
  app/
    config.py          # env + settings
    data/              # DataSource adapters (yfinance, nse_bhavcopy), symbol universe
    storage/           # DuckDB connection, schema, repository
    indicators/        # vectorized RSI, SMA/EMA, ATR, MACD, Bollinger, returns
    scanners/          # momentum scanner: score + reasons + risk flags
    ai/                # Haiku explainer: payload contract, prompt, verification
    pipeline/          # ingest -> compute -> scan orchestration
    api/               # FastAPI routes
  scripts/run_pipeline.py
  tests/               # indicator correctness, verification logic
  requirements.txt  .env.example  docker-compose.yml (for later)
```

**Milestones** (each has one deliverable + a gate; do not advance until the gate passes):

| M | Deliverable | Gate |
|---|---|---|
| M0 | Env + data spike: venv, deps, pull ~50 Nifty names via yfinance | Adjusted OHLCV lands in DuckDB for the full history window |
| M1 | DataSource adapter (yfinance primary; bhavcopy + delivery stub) | Same symbol consistent via either adapter; vendor swap touches no business logic |
| M2 | Indicators (RSI, SMA 20/50/200, EMA, ATR, MACD, Bollinger, returns, volume ratio) | Unit tests pass vs known series; reconcile vs a 2nd source on a sample |
| M3 | Momentum scanner: 0–100 score, sub-scores, plain-language reasons, risk flags | Output is descriptive (Mode A); no buy-lean language; missing sub-scores marked neutral |
| **M3b** | **Score-validation: does momentum score track realized relative strength?** | **Evidence the score is signal not noise (6.5) — or redesign scoring now** |
| M4 | Haiku explanation layer: grounding contract + runtime verification | Every number traces to the payload; banned phrases blocked; flagged on mismatch |
| M5 | FastAPI endpoints: `/market/summary`, `/scanner/momentum`, `/stocks/{sym}/overview`, `/stocks/{sym}/ai-summary` | Endpoints return validated data; AI summary served from cache when signals unchanged |
| M6 | Optional thin UI (Next.js) or stay on API + notebook | End-to-end: pick a stock → indicators, scanner score, grounded explanation |

**Run (target commands):**
```
pyenv local 3.11.9
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # all arm64 wheels, no TA-Lib
cp .env.example .env                    # then set ANTHROPIC_API_KEY
python scripts/run_pipeline.py          # ingest -> compute -> scan
pytest                                  # indicator + verification tests
uvicorn app.main:app --reload           # API at :8000
```

**Out of local-first:** live/real-time data, the full Postgres+Timescale+Redis+Celery stack, broker integration, and every RA-gated recommendation feature (5.21/5.22).

**What it proves:** by end of M5 you've retired the three product-killing assumptions on one laptop. Only then is cloud build and the RA track worth the spend.

---

## 13. Open decisions / decision log

Track explicitly; each blocks specific downstream work.

| Decision | Why it matters | Blocks |
|---|---|---|
| v1 operating mode (A vs A+RA) | Governs data use, AI language, shippable features, liability | Everything |
| Data vendor + redistribution rights | Legality + recurring cost of the core feed | Phase 1 onward |
| Build vs buy: corp-action adjustment | Deep problem (6.1), not your differentiation | Phase 1 |
| Build vs buy: news/sentiment feed | Entity-resolution + finance sentiment are hard (6.4) | Phase 2 |
| Scanner scoring weights + validation method | Whether scores carry signal | Phase 1 scanners |
| AI cost ceiling + caching policy | Freemium economics (6.8) | Phase 2 AI |
| Local storage: DuckDB now vs Postgres/Timescale later | Lowest-friction M1 prototype vs production fit | Local M0–M5 |
| Indicators: vectorized/pandas-ta vs TA-Lib | Avoids M1 C-library friction | Local M2 |
| **Score-validation outcome (M3b)** | **Whether scanner scores carry signal** | **Whole product** |
| Personalization line (A vs C) | Keeps personalization non-advisory | Phase 3+ |

---

## 14. Source-document cross-reference

| Topic | Saakshya spec | v3 PDF | This doc |
|---|---|---|---|
| Regulatory mode | §18 (partial) | §3 | §2 |
| Positioning / language | §2, §12.7, §18 | §4 | §3, §5 |
| Feature scope | §6, §7 | §6 | §4 |
| Correctness constraints | §10–11 (light) | §7 | §6.1–6.5 |
| AI constraints | §12 | §8 | §6.6–6.9 |
| Personalization | §6, §9.9 | §9 | §7 |
| Data strategy | §14 | §10 | §8 |
| Architecture | §10, §11, §15 | §11 | §9 |
| Roadmap | §6 | §12 | §10 |
| Monetization | §19 | §15 | §11 |
| Local build plan | (—) | §14 | §12 |
| Decision log | (—) | §16 | §13 |

> **Regulatory note:** This document summarizes publicly reported SEBI positions as of mid-2026 and is not legal advice. Confirm the current regime, registration requirements, and permitted product language with qualified Indian securities counsel before building or launching.
