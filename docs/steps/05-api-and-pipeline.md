# Steps · 05 · API & Pipeline

> Read first: [SPEC.md](../../SPEC.md) · [Roadmap](../02-product-roadmap.md) · [Backend Architecture](../09-backend-architecture.md) · [API Contracts](../10-api-contracts.md) · [AI/LLM Agent Architecture](../14-ai-llm-agent-architecture.md) · [Compliance & Guardrails](../21-compliance-risk-and-guardrails.md)

**Maps to:** Roadmap V1–V2 · SPEC Phase 1–2 · Local milestone M5
**Status:** Complete (M5 — 2026-06-30)   |   **Regulatory mode:** A
**Prerequisites:** [01-local-mvp-foundation.md](01-local-mvp-foundation.md) · [02-indicators-and-scanners.md](02-indicators-and-scanners.md) · [03-scanner-score-validation.md](03-scanner-score-validation.md) · [04-ai-explanation-layer.md](04-ai-explanation-layer.md)

## Overview
Wire the validated local core into a runnable system: a **pipeline orchestrator** (`scripts/run_pipeline.py`) that runs ingest → compute → scan → explain over the local universe, and a **FastAPI app** (`app/api/`) that serves the M5 endpoints from [10-api-contracts.md](../10-api-contracts.md) under the standard response envelope. Every response carries `data`/`meta` with `as_of` + `data_confidence` (or the standard `error` object); AI summaries are served from cache when signals are unchanged ([SPEC §6.8](../../SPEC.md)); rate limiting protects the AI bucket. Locally, auth/plan-gating may be stubbed, but the **envelope, `as_of`, `data_confidence`, and the AI guardrail/grounding check remain non-negotiable** ([10 §0 local-first note](../10-api-contracts.md)).

Scope is the M5 endpoint set ([SPEC §12 M5](../../SPEC.md)): `GET /market/summary`, `GET /scanners/momentum` (+ sibling scanner reads `/scanners/rsi`, `/scanners/volume-breakout` as available), `GET /stocks/{sym}/overview`, `GET /stocks/{sym}/technicals`, `GET /stocks/{sym}/ai-summary`. Postgres/Timescale/Celery/Redis are **out** locally ([SPEC §12](../../SPEC.md)) — the pipeline is plain scripts over DuckDB.

## Exit gate (Definition of Done)
- [x] `python scripts/run_pipeline.py` runs ingest → compute → scan → explain end-to-end and persists results to DuckDB with an `as_of` version.
- [x] `uvicorn app.main:app --reload` serves all M5 endpoints; every 2xx carries `data` + `meta.as_of` + `meta.data_confidence`; every error uses the standard error object + code ([10 §0.2–0.3](../10-api-contracts.md)).
- [x] `/stocks/{sym}/ai-summary` returns a grounded, guardrail-checked summary with `audit_id` + `model_version`, served from cache when signals are unchanged, and `422 DATA_SUPPRESSED` (not a guess) when inputs are missing.
- [x] Responses match the documented shapes in [10](../10-api-contracts.md) (validated by contract tests).
- [x] Rate limiting returns `429 RATE_LIMITED` with `Retry-After`; the AI bucket is stricter than read endpoints.
- [x] `pytest tests/api/` green: contract, envelope, cache-hit, suppression, rate-limit.

---

## Feature: Pipeline orchestration  `(Mode A)`
**Objective:** A single command runs the full EOD-shaped local pipeline (ingest → compute → scan → explain) deterministically, stamping one `as_of` version. · **Backend dep:** DataSource adapter (step 01), indicators + scanners (steps 02/03), AI explainer (step 04). · **Frontend dep:** none. · **Data dep:** local universe (~50 Nifty names, M0); corp-action-adjusted series.
### Steps
- [x] 1. Create `app/pipeline/orchestrator.py` exposing `run(universe, *, as_of=None) -> PipelineResult`. Generate one `as_of_version` (`ds-<ISO timestamp>`) for the run and thread it through every stage so all stored values share a point-in-time stamp ([SPEC §6.2](../../SPEC.md), [09 §0](../09-backend-architecture.md)).
- [x] 2. Stage 1 **ingest**: call the `DataSource` adapter (`app/data/`) to land/refresh adjusted OHLCV in DuckDB; record per-symbol ingest status + a data-confidence flag (missing candle / abnormal jump → MEDIUM/LOW per [SPEC §6.2](../../SPEC.md)).
- [x] 3. Stage 2 **compute**: run `app/indicators/` (RSI, SMA 20/50/200, EMA, ATR, MACD, Bollinger, returns, volume ratio) over the adjusted series; persist to an `indicators` table keyed by (`symbol`, `date`, `as_of_version`).
- [x] 4. Stage 3 **scan**: run `app/scanners/` (momentum + available scanners) producing score, sub-scores, descriptive reasons, risk flags; persist to a `scanner_results` table; mark missing sub-scores neutral ([SPEC §12 M3](../../SPEC.md)).
- [x] 5. Stage 4 **explain**: for each scanner member, build the payload (`app/ai/payload.py`) and call `explain_stock` (step 04) — cache-aware, ceiling-aware; persist to `ai_summary_cache` + write audit. Suppress (don't guess) on missing inputs.
- [x] 6. Make stages idempotent and independently re-runnable (`run(..., stages=["compute","scan"])`); a corrected symbol re-emits dependent indicators → scanners → AI summaries ([SPEC §6.2 correction workflow](../../SPEC.md)).
- [x] 7. Create `scripts/run_pipeline.py` as the CLI entrypoint: parse `--universe`, `--as-of`, `--stages`; call the orchestrator; print a stage summary (counts, suppressions, AI calls, cache hits, cost).
- [x] 8. Add structured logging per stage (rows in/out, duration) — the local stand-in for the overnight-window latency budget ([SPEC §6.8](../../SPEC.md)).
### Tests
- [x] `test_pipeline_runs_end_to_end` — on a fixture universe, all four stages complete and write rows under one `as_of_version`.
- [x] `test_pipeline_reemit_after_correction` — correcting one symbol re-emits its indicators, scanner result, and AI summary only.
- [x] `test_pipeline_suppresses_missing_inputs` — a thin-data symbol yields a suppressed AI summary, not a fabricated one.
### Compliance gate
- [x] No stage emits entry/target/SL or buy-leans; scanner reasons are descriptive; AI stage passes verify+guardrail ([SPEC §3.2](../../SPEC.md), [§6.6](../../SPEC.md)).
### Acceptance criteria
- [x] `python scripts/run_pipeline.py` reproduces the same outputs for the same `as_of` (deterministic, reproducible — [SPEC §6.2](../../SPEC.md)).

---

## Feature: FastAPI app + standard envelope  `(Mode A)`
**Objective:** Stand up the FastAPI app with a single response envelope, error model, and shared dependencies, so every endpoint is consistent and reproducible. · **Backend dep:** DuckDB store, pipeline outputs. · **Frontend dep:** typed client mirrors these shapes (step 06). · **Data dep:** `as_of` + `data_confidence` on every stored value.
### Steps
- [x] 1. Create `app/main.py` constructing the FastAPI app, mounting routers under `/api/v1`, and registering middleware (request id, envelope wrapper, rate limiter, error handler).
- [x] 2. Create `app/api/envelope.py` with `Envelope[T]` (Pydantic generic): `data`, `meta` (`as_of`, `data_confidence`, `source`, `is_adjusted`, `generated_at`, `request_id`, optional `page`), `error`. Add `ok(data, *, as_of, data_confidence, ...)` and `fail(code, message, details=None, http_status=...)` helpers matching [10 §0.1–0.2](../10-api-contracts.md).
- [x] 3. Create `app/api/errors.py` with the standard error codes ([10 §0.3](../10-api-contracts.md)): `VALIDATION_ERROR` 400, `UNAUTHENTICATED` 401, `FORBIDDEN`/`PLAN_REQUIRED`/`MODE_GATED` 403, `NOT_FOUND` 404, `DATA_SUPPRESSED` 422, `RATE_LIMITED` 429, `INTERNAL` 500, `PIPELINE_UNAVAILABLE` 503. A custom exception → handler maps to the error envelope.
- [x] 4. Create `app/api/deps.py`: a DuckDB session dependency, an `as_of` resolver (`?date=`/`?as_of=` → latest published if absent, else the stored version), and a **stubbed** auth/plan dependency that is no-op locally but present so production can swap it in ([10 §0 local-first note](../10-api-contracts.md)).
- [x] 5. Add a global exception handler returning `INTERNAL` (never a stack trace) and a `503 PIPELINE_UNAVAILABLE` when EOD data for the requested date is not yet published.
- [x] 6. Enforce the **Mode-A guarantee at the API boundary**: no router exposes entry/target/SL or ranked picks; a request for an RA-gated field returns `403 MODE_GATED` (the `/levels` route, if added later, is descriptive-only) ([10 §14](../10-api-contracts.md), [05 §5.8](../05-information-architecture-and-url-paths.md)).
### Tests
- [x] `test_envelope_present_on_2xx` — every endpoint's 2xx carries `data` + `meta.as_of` + `meta.data_confidence`.
- [x] `test_error_envelope_shape` — a forced error returns `data:null`, `meta.request_id`, and a standard `error` object with a known code.
- [x] `test_mode_gated_field_rejected` — requesting a target/SL-style field → `403 MODE_GATED`.
### Compliance gate
- [x] No endpoint returns advisory fields; `MODE_GATED` guards RA-only fields ([SPEC §3.2](../../SPEC.md), [10 §0, §14](../10-api-contracts.md)).
### Acceptance criteria
- [x] All M5 endpoints share one envelope + error model; any value is reconstructable from stored series for its `as_of` ([10 §14](../10-api-contracts.md)).

---

## Feature: Market & scanner endpoints  `(Mode A)`
**Objective:** Serve the EOD market snapshot and scanner reads exactly per [10 §2, §5](../10-api-contracts.md), descriptive only. · **Backend dep:** pipeline `scanner_results` + index/breadth, AI market summary (step 04). · **Frontend dep:** market dashboard + scanner screens (step 06). · **Data dep:** index/breadth EOD, validated scanner scores.
### Steps
- [x] 1. Create `app/api/routers/market.py`: `GET /market/summary` returning `session_date`, `indices[]` (symbol, close, change, change_pct), `breadth` (advances/declines/unchanged), and a **descriptive, guardrail-checked** `headline` ([10 §2](../10-api-contracts.md)). The headline is produced via `explain_market` (step 04) or a templated fallback; it is grounded and never directive.
- [x] 2. Create `app/api/routers/scanners.py`: `GET /scanners/momentum` returning `symbol`, `score`, `sub_scores`, `reasons[]` (descriptive: "trading above its 50-DMA", "volume expanded 1.9x vs its 20-day average"), `risk_flags[]`; support `date?`, `universe?`, `limit?`, `offset?`, `min_score?`, `sort?`; include `meta.page` ([10 §5](../10-api-contracts.md)).
- [x] 3. Add sibling scanner reads that exist locally (`GET /scanners/rsi`, `GET /scanners/volume-breakout`) using the same row family; gate Premium-only scanners behind the stubbed plan dependency (local: open) — false-breakout surfaces as a **risk flag**, never "buy the breakout" ([10 §5](../10-api-contracts.md)).
- [x] 4. Add `GET /scanners` catalog (id, name, plan) so the scanner directory has data ([10 §5](../10-api-contracts.md)).
- [x] 5. Set EOD cache headers (`ETag`, `Cache-Control` keyed by `as_of`) per [05 §5](../05-information-architecture-and-url-paths.md).
### Tests
- [x] `test_market_summary_contract` — response matches the [10 §2](../10-api-contracts.md) shape; `headline` passes the guardrail.
- [x] `test_momentum_scanner_contract` — rows carry score+sub_scores+reasons+risk_flags; pagination meta present.
- [x] `test_scanner_reasons_descriptive` — no reason/headline string contains a blocked phrase or directive pattern.
### Compliance gate
- [x] Membership framing ("appears in the momentum scanner"); scores are the validated ones from step 03 ([SPEC §6.5](../../SPEC.md)); no buy-leans ([10 §5 mode notes](../10-api-contracts.md)).
### Acceptance criteria
- [x] Endpoints return validated, descriptive data with correct envelopes and EOD cache behavior.

---

## Feature: Stock endpoints (overview, technicals, ai-summary)  `(Mode A)`
**Objective:** Serve the stock detail data per [10 §4](../10-api-contracts.md) — facts, full indicator set, and the grounded AI summary — with no entry/target/SL anywhere. · **Backend dep:** indicators, scanner memberships, risk score, AI explainer + cache + audit (step 04). · **Frontend dep:** stock detail page + evidence drawer (step 06). · **Data dep:** corp-action-adjusted series, validated scores, grounded AI.
### Steps
- [x] 1. Create `app/api/routers/stocks.py`: `GET /stocks/{symbol}/overview` returning last OHLCV (+ `delivery_pct` when available), key `indicators` (`rsi_14`, `sma_50`, `sma_200`, `above_50dma`, `volume_ratio_20`), `scanner_memberships[]` (neutral language), and `risk_score` (`value`, `band`) ([10 §4](../10-api-contracts.md)). `404 NOT_FOUND` for unknown symbol; `422 DATA_SUPPRESSED` for thin data.
- [x] 2. `GET /stocks/{symbol}/technicals` returning `latest` (full indicator set) + optional `series[]` honoring `range?` (`1m|3m|6m|1y|max`) and `adjusted?` (default true); descriptive support/resistance lives only on the (descriptive) `/levels` route — technicals carry **no** trade instruction ([10 §4](../10-api-contracts.md)).
- [x] 3. `GET /stocks/{symbol}/ai-summary` returning `summary`, `evidence[]` (each `claim`→`field`→`value`), `model_version`, `audit_id`, `disclaimer:"Not investment advice."`; `meta.data_confidence`. Serve from the step-04 cache when signals are unchanged; on missing critical inputs return `422 DATA_SUPPRESSED` (suppressed, not guessed) ([10 §4](../10-api-contracts.md), [SPEC §6.2](../../SPEC.md)).
- [x] 4. Add the `GET /api/ai/stock-summary/{symbol}` alias mapping to the same handler/contract ([10 §9](../10-api-contracts.md)).
- [x] 5. Build `evidence[]` from the explainer's `cited_facts` + payload values so each rendered figure traces to a source field (powers the UI evidence drawer in step 06).
### Tests
- [x] `test_overview_contract` — shape per [10 §4](../10-api-contracts.md); `scanner_memberships` use neutral language; no entry/target/SL key present.
- [x] `test_ai_summary_grounded_and_audited` — `summary` passes verify+guardrail; response carries `audit_id` + `model_version`; every `evidence.field` exists in the payload.
- [x] `test_ai_summary_suppressed_on_missing_input` — thin-data symbol → `422 DATA_SUPPRESSED`, no fabricated text.
### Compliance gate
- [x] No entry/target/SL on any stock endpoint; AI numbers trace to payload; banned phrases blocked at output ([SPEC §6.6](../../SPEC.md), [§6.9](../../SPEC.md), [10 §4 mode notes](../10-api-contracts.md)).
### Acceptance criteria
- [x] Stock endpoints return adjusted, validated, grounded data matching [10 §4](../10-api-contracts.md).

---

## Feature: AI-summary caching (serve-on-unchanged-signals)  `(Mode A)`
**Objective:** Make `/stocks/{sym}/ai-summary` serve the cached summary when the stock's signal category is unchanged, regenerating only on category change ([SPEC §6.8](../../SPEC.md), [10 §4](../10-api-contracts.md)). · **Backend dep:** step-04 cache (`ai_summary_cache`) + `signal_category`. · **Frontend dep:** Query caches by symbol + signal-version ([06 §4](../06-frontend-architecture.md)). · **Data dep:** per-symbol signal category from the latest pipeline run.
### Steps
- [x] 1. In the ai-summary handler, compute `signal_category(payload)` and call `get_cached(symbol, category)`; on hit, return the cached summary + its `audit_id` without an LLM call.
- [x] 2. On miss, generate via the explainer, `put_cached(...)`, and return; honor the daily ceiling (degrade to templated fallback when exhausted).
- [x] 3. Expose a cache marker in `meta` (e.g. `meta.cache="hit"|"miss"|"degraded"`) for observability and frontend signal-version keying.
- [x] 4. Set `Cache-Control`/`ETag` keyed by (`symbol`, `as_of`, `signal_category`) so gateway/CDN caching aligns with regenerate-on-change.
### Tests
- [x] `test_ai_summary_cache_hit` — two requests with unchanged signals → second is a cache hit, provider mock called once, identical `summary`.
- [x] `test_ai_summary_regenerates_on_category_change` — changed risk flag → new generation + new `audit_id`.
### Compliance gate
- [x] Cached and degraded summaries are still grounded, guardrail-clean, and audited ([SPEC §6.6](../../SPEC.md), [§6.8](../../SPEC.md)).
### Acceptance criteria
- [x] Unchanged signals are never re-summarized; cost is bounded; `meta.cache` reflects the path taken.

---

## Feature: Rate limiting  `(Mode A)`
**Objective:** Protect endpoints with a per-client token bucket, stricter for the AI bucket, returning `429 RATE_LIMITED` with `Retry-After` ([10 §0, §4, §9](../10-api-contracts.md)). · **Backend dep:** FastAPI middleware; in-memory/DuckDB counter locally. · **Frontend dep:** client backs off on 429 ([06 §6](../06-frontend-architecture.md)). · **Data dep:** none.
### Steps
- [x] 1. Create `app/api/ratelimit.py` with a token-bucket limiter keyed by client (local: IP/stub user); separate buckets per category — read endpoints (e.g. 60–120/min) vs **AI bucket** (e.g. 30/min for ai-summary, stricter per [10 §4, §9](../10-api-contracts.md)).
- [x] 2. Register as middleware; on exhaustion return the standard error envelope with `RATE_LIMITED` + a `Retry-After` header.
- [x] 3. Make limits config-driven in `app/config.py` so production can tighten per-plan without code changes.
### Tests
- [x] `test_rate_limit_returns_429` — exceeding the AI bucket → `429 RATE_LIMITED` with `Retry-After`.
- [x] `test_read_bucket_separate_from_ai_bucket` — read endpoints unaffected by AI-bucket exhaustion.
### Compliance gate
- [x] Rate-limit responses use the standard error object ([10 §0.2](../10-api-contracts.md)).
### Acceptance criteria
- [x] AI endpoints are rate-limited more strictly than reads; limits are configurable.

---

## Done-when
- [x] `scripts/run_pipeline.py` runs ingest → compute → scan → explain over the local universe under one `as_of` version, idempotent and re-emit-capable.
- [x] FastAPI serves `GET /market/summary`, `GET /scanners/momentum` (+ siblings + catalog), `GET /stocks/{sym}/overview`, `/technicals`, `/ai-summary` (+ alias) under the standard envelope with `as_of` + `data_confidence`.
- [x] AI summaries are grounded, guardrail-clean, audited, cached on unchanged signals, and suppressed (not guessed) on missing inputs.
- [x] No endpoint exposes entry/target/SL, buy-leans, or ranked picks; RA-gated fields return `MODE_GATED` ([10 §14](../10-api-contracts.md)).
- [x] Rate limiting enforces a stricter AI bucket; `pytest tests/api/` (contract, envelope, cache-hit, suppression, rate-limit) is green.
- [x] End-to-end ready for the thin UI in [06-frontend-foundation-and-v1-screens.md](06-frontend-foundation-and-v1-screens.md): pick a stock → indicators, scanner score, grounded explanation ([SPEC §12 M6](../../SPEC.md)).
