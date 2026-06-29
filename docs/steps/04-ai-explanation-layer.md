# Steps · 04 · AI Explanation Layer

> Read first: [SPEC.md](../../SPEC.md) · [Roadmap](../02-product-roadmap.md) · [AI/LLM Agent Architecture](../14-ai-llm-agent-architecture.md) · [API Contracts](../10-api-contracts.md) · [Compliance & Guardrails](../21-compliance-risk-and-guardrails.md)

**Maps to:** Roadmap V2 (AI summary, descriptive) · SPEC Phase 2 · Local milestone M4
**Status:** Not started   |   **Regulatory mode:** A
**Prerequisites:** [00-phase-0-derisk.md](00-phase-0-derisk.md) · [01-local-mvp-foundation.md](01-local-mvp-foundation.md) · [02-indicators-and-scanners.md](02-indicators-and-scanners.md) · [03-scanner-score-validation.md](03-scanner-score-validation.md)

## Overview
Build the **AI explanation layer** that turns a deterministic, computed signal into descriptive, Mode-A-safe plain language — and never lets a fabricated number, target, or buy-lean reach the user. The AI receives **only** a structured payload of computed facts ([SPEC §6.6](../../SPEC.md), [14 §4](../14-ai-llm-agent-architecture.md)); a runtime verification harness extracts every number/named fact from the model output and confirms each traces to the payload, blocking/regenerating on mismatch; a versioned blocked-phrase guardrail runs at **output time**; every generation (published or suppressed) writes an immutable audit record. Default model is **Claude Haiku** (`claude-haiku-4-5-20251001`) behind a provider abstraction, with regenerate-on-change caching keyed by signal category and a hard daily call ceiling ([SPEC §6.8](../../SPEC.md)).

This step is package-local: all code lands under `app/ai/`, tests under `tests/ai/`. It exposes a single callable surface (`explain_stock(...)`, `explain_market(...)`) consumed by the pipeline ([05-api-and-pipeline.md](05-api-and-pipeline.md)). No FastAPI wiring here — that is step 05.

## Exit gate (Definition of Done)
- [ ] `app/ai/payload.py` builds a validated payload containing **only** `computed`/`signalTags`/`riskFlags`/`newsSummaries` + meta; nothing forward-looking can be added (no target/stop/return field exists).
- [ ] `app/ai/explainer.py` generates a descriptive summary via Haiku for a given payload, suppressing (not guessing) when `dataConfidence == LOW` or a critical field is missing.
- [ ] The runtime verification harness blocks any output containing a number/tag/entity not present in the payload (proven by injected-fabrication regression tests).
- [ ] The output-time guardrail blocks the seed blocked-phrase list ([SPEC §6.9](../../SPEC.md)); no directive tail ("before fresh action") survives.
- [ ] Every generation writes an audit record with prompt id+version, payload hash, raw + user-visible output, grounding report, model id, tokens, cost, suppressed flag.
- [ ] Cache serves an unchanged summary when the signal category is unchanged; the daily call ceiling halts further LLM calls and degrades to a non-AI templated fallback.
- [ ] `pytest tests/ai/` green: grounding/number-traceability, blocked-phrase, suppression-on-missing-input, cache-hit, ceiling-degradation.

---

## Feature: Structured payload contract  `(Mode A)`
**Objective:** Construct the single validated object the model is allowed to see — computed facts only, with versioned permitted vocabulary and a mode context — so the model literally cannot reference an ungrounded value. · **Backend dep:** indicator + scanner outputs (steps 02/03), `as_of` versioning. · **Frontend dep:** none. · **Data dep:** corp-action-adjusted indicators, validated scanner sub-scores, risk flags, (Phase 2) entity-resolved news.
### Steps
- [ ] 1. Create `app/ai/payload.py` with frozen dataclasses / Pydantic models mirroring [14 §4](../14-ai-llm-agent-architecture.md): `Subject`, `ComputedBlock` (`scanner`, `compositeScore`, `subScores: dict`, `facts: dict[str, float|bool]`), `NewsSummary`, and `Payload` (`intent`, `asOfDate`, `asOfVersion`, `subject`, `computed`, `signalTags: list[str]`, `riskFlags: list[str]`, `newsSummaries: list`, `dataConfidence`, `permittedVocabulary`, `modeContext="A"`).
- [ ] 2. Enforce **contract invariants** at construction: reject any key under `facts` whose name matches a forbidden semantic (`target`, `stop`, `sl`, `entry`, `invalidation`, `return_forecast`, `price_target`); raise `ForbiddenFieldError`. There is no field for a forward price — none exists upstream.
- [ ] 3. Add `build_stock_payload(symbol, indicators, scanner_result, risk_flags, news=None, *, as_of, as_of_version) -> Payload` and `build_market_payload(...)`. Each computes `dataConfidence` (HIGH/MEDIUM/LOW/SUPPRESSED) from input completeness + the data-confidence flag from storage ([SPEC §6.2](../../SPEC.md)).
- [ ] 4. Add `permitted_vocabulary()` returning the versioned tag→descriptive-phrase map (e.g. `MOMENTUM_STRONG → "appears in the momentum scanner"`, `ABOVE_50DMA → "trading above its 50-DMA"`, `ELEVATED_VOLATILITY → "short-term volatility is elevated"`). Load from `app/ai/vocab.py` with a `VOCAB_VERSION` constant; **no** tag maps to a buy-lean.
- [ ] 5. Add `payload.hash()` (sha256 of canonical JSON) and `payload.to_model_json()` — the exact bytes the model receives — used by the audit log and harness as the single source of truth.
- [ ] 6. Add `is_suppressed(payload) -> bool` returning True when `dataConfidence in {LOW, SUPPRESSED}` or any critical field (`facts.close`, the scanner `compositeScore`) is missing.
### Tests
- [ ] `test_payload_rejects_forward_fields` — adding `facts["target"]` raises `ForbiddenFieldError`.
- [ ] `test_payload_hash_stable` — same inputs → same hash; reordered dicts → same hash (canonicalized).
- [ ] `test_data_confidence_low_marks_suppressed` — missing close → `is_suppressed` True.
### Compliance gate
- [ ] No payload field can carry entry/target/SL/return; vocabulary maps only to descriptive phrases ([SPEC §3.1–3.2](../../SPEC.md), [§5](../../SPEC.md)).
### Acceptance criteria
- [ ] The model receives exactly `payload.to_model_json()` and nothing else; the harness (below) validates against this same object ([14 §4 invariants](../14-ai-llm-agent-architecture.md)).

---

## Feature: System prompt + Haiku explainer  `(Mode A)`
**Objective:** Generate a descriptive, traceable summary restricted to Mode-A language, via a provider-abstracted Claude Haiku call, suppressing on missing inputs. · **Backend dep:** payload contract (above), provider adapter. · **Frontend dep:** none (display-only later in step 06). · **Data dep:** `ANTHROPIC_API_KEY` via env ([SPEC §9](../../SPEC.md)).
### Steps
- [ ] 1. Create `app/ai/provider.py` with the `LLMProvider` protocol from [14 §3](../14-ai-llm-agent-architecture.md): `complete(*, prompt_id, prompt_version, system, payload_json, model_tier) -> LLMResult` (`text`, `model_id`, `tokens_in`, `tokens_out`, `cost_usd`). Implement `AnthropicProvider` mapping `model_tier="cheap" → claude-haiku-4-5-20251001`, `"premium" → premium Claude model` (reserved). Use prompt caching of the static system/contract prefix where supported.
- [ ] 2. Create `app/ai/prompts/` with versioned prompt files: `stock_summary.v1.txt`, `market_brief.v1.txt`, `scanner_explain.v1.txt`. The system prompt states the iron rules: explain only the supplied facts; never invent numbers/prices/news/targets; never issue buy/sell; use the supplied permitted vocabulary; cite only fields present; emit the worked-example register from [SPEC §5](../../SPEC.md); append "Not investment advice."
- [ ] 3. Create `app/ai/registry.py`: a prompt registry mapping `prompt_id -> (version, path, model_tier)`; `get_prompt(prompt_id)` loads template + stamps `prompt_version`. A change to a template requires a version bump (no silent edits) — enforced by a test hashing the file against the registered version.
- [ ] 4. Create `app/ai/explainer.py`:
  - `explain_stock(payload, *, provider, ...) -> Explanation` — short-circuits to a `SUPPRESSED` Explanation (`"Summary unavailable — required inputs missing."`) when `is_suppressed(payload)`, **never calling the model** ([SPEC §6.2](../../SPEC.md)).
  - Otherwise renders the system prompt + `payload.to_model_json()`, calls `provider.complete(model_tier="cheap")`, then runs verify → guardrail → (optional local compliance check) before returning.
  - `Explanation` carries `summary`, `cited_facts: list[str]`, `risk_notes: list[str]`, `model_version`, `audit_id`, `suppressed: bool`, `grounding_report`.
- [ ] 5. Implement the regenerate loop: on verification/guardrail failure, regenerate up to `N=2` (config), then **suppress** with the safe fallback ([14 §6](../14-ai-llm-agent-architecture.md)).
- [ ] 6. Add `explain_market(payload, ...)` (premium tier reserved; defaults to cheap locally) producing the descriptive, event-framed brief (no ranked "what to buy").
### Tests
- [ ] `test_suppression_on_missing_input` — `dataConfidence=LOW` payload returns suppressed Explanation with **zero** provider calls (provider mock asserts not called).
- [ ] `test_explainer_returns_grounded_summary` — stub provider returns a payload-faithful summary → passes verify+guardrail, `suppressed=False`, every cited fact in payload.
- [ ] `test_prompt_version_locked` — editing a prompt file without bumping the registry version fails.
### Compliance gate
- [ ] System prompt forbids entry/target/SL/buy-leans/directive tails; output ends with "Not investment advice." ([SPEC §3.2–3.3](../../SPEC.md), [§5](../../SPEC.md)).
### Acceptance criteria
- [ ] Default path uses `claude-haiku-4-5-20251001` via the provider abstraction; swapping providers touches no business logic ([SPEC §9](../../SPEC.md), [14 §3](../14-ai-llm-agent-architecture.md)).

---

## Feature: Runtime verification harness  `(Mode A)`
**Objective:** On every generation, extract each number/percentage/price/symbol/tag/named fact and confirm it traces to the payload; block or regenerate on any mismatch — the hallucination firewall. · **Backend dep:** payload contract. · **Frontend dep:** none. · **Data dep:** none.
### Steps
- [ ] 1. Create `app/ai/verify.py` with `extract_facts(text) -> ExtractedFacts`: regex for numeric tokens (ints/floats/percent/₹ prices), uppercase NSE-style symbols, scanner tags (`MOMENTUM_STRONG`, `ABOVE_50DMA`…), and risk flags. Normalize numbers (strip `%`, `₹`, commas).
- [ ] 2. Implement `verify(text, payload) -> GroundingReport`:
  - each numeric must equal a value under `payload.computed.facts`/`subScores`/`compositeScore` within float tolerance (`abs_tol=0.05`, `rel_tol=0.005`);
  - each tag must be in `signalTags`; each risk flag in `riskFlags`; each named entity in `newsSummaries`;
  - any unmatched item → `matched=False`, recorded in `unmatched` ([14 §6 algorithm](../14-ai-llm-agent-architecture.md)).
- [ ] 3. Return a `GroundingReport(matched: bool, matched_items, unmatched_items)`; the explainer treats `matched=False` as a regenerate trigger, then suppression.
- [ ] 4. Guard against false negatives: maintain a small allowlist of non-fact tokens (years like "20-day", "50-DMA", "200-DMA" treated as window labels, not figures) so legitimate descriptive phrasing isn't flagged. Window labels resolve against payload facts (`sma50`, `sma200`) rather than being treated as free numbers.
- [ ] 5. Record the full grounding report into the audit log (below) for both pass and fail.
### Tests
- [ ] `test_harness_blocks_injected_number` — output claims `ret_3m_pct +35.0` while payload has `21.4` → `matched=False`.
- [ ] `test_harness_blocks_unknown_tag` — output asserts a tag absent from `signalTags` → fail.
- [ ] `test_harness_passes_grounded_text` — the [SPEC §5 worked example](../../SPEC.md) over a matching payload → `matched=True`.
- [ ] `test_window_labels_not_flagged` — "trading above its 50-DMA" with `sma50` present → pass.
### Compliance gate
- [ ] No output with an unmatched number/tag/entity ever returns from `explain_*` (regenerate→suppress) ([SPEC §6.6](../../SPEC.md)).
### Acceptance criteria
- [ ] Golden-dataset regression proves the harness blocks fabricated numbers/targets and does not over-suppress grounded text ([14 §6 acceptance](../14-ai-llm-agent-architecture.md)).

---

## Feature: Banned-phrase output-time guardrail  `(Mode A)`
**Objective:** Enforce the versioned blocked-phrase/pattern list on the **generated text**, not just in the prompt ([SPEC §6.9](../../SPEC.md)). · **Backend dep:** none. · **Frontend dep:** mirror list for build-time JSX lint (step 06). · **Data dep:** none.
### Steps
- [ ] 1. Create `app/ai/guardrail.py` with a versioned list in `app/ai/blocked_phrases.py` seeded from [SPEC §3.3 / §6.9](../../SPEC.md) and [14 §10](../14-ai-llm-agent-architecture.md): `guaranteed`, `assured/confirmed target`, `risk-free`, `sure-shot`, `multibagger`, `buy now`, `best stock for you`, `target confirmed`, plus directive patterns (`\bbuy\b`, `\bsell\b`, `stop[- ]?loss`, `entry zone`, `target zone`, `before fresh action`). Carry `GUARDRAIL_VERSION`.
- [ ] 2. Implement `check(text) -> GuardrailReport(clean: bool, blocked_phrases, directive_hits)` using compiled case-insensitive regex with word boundaries (avoid matching inside benign words).
- [ ] 3. Wire into `explainer.py` after verification: a non-clean report triggers regenerate→suppress ([14 §12](../14-ai-llm-agent-architecture.md)).
- [ ] 4. Add the safe-alternative map ([SPEC §5](../../SPEC.md), [14 §10](../14-ai-llm-agent-architecture.md)) as documentation/reference only (the guardrail blocks; it does not auto-rewrite — rewriting risks re-introducing advice).
- [ ] 5. Expose `blocked_phrases_export()` so the frontend can mirror the list into `src/constants/blocked-phrases.ts` ([06 §13](../06-frontend-architecture.md), referenced in step 06).
### Tests
- [ ] `test_guardrail_blocks_seed_phrases` — each seed phrase in text → `clean=False`.
- [ ] `test_guardrail_blocks_directive_tail` — "...should be monitored before fresh action" → blocked.
- [ ] `test_guardrail_allows_descriptive` — the [SPEC §5 worked example](../../SPEC.md) → `clean=True`.
### Compliance gate
- [ ] Enforcement is at output time on generated text; list is versioned and exportable to admin/frontend ([SPEC §6.9](../../SPEC.md)).
### Acceptance criteria
- [ ] No blocked phrase or directive pattern can survive `explain_*` output.

---

## Feature: AI generation audit log  `(Mode A)`
**Objective:** Write an immutable record of **every** generation (published or suppressed) for incident replay, cost attribution, and SEBI Mode-B accountability. · **Backend dep:** DuckDB store ([01-local-mvp-foundation.md](01-local-mvp-foundation.md)). · **Frontend dep:** admin audit search (later). · **Data dep:** as-of version.
### Steps
- [ ] 1. Add an `ai_audit_log` table to the DuckDB schema (`app/storage/schema.py`): columns per [14 §7](../14-ai-llm-agent-architecture.md) — `audit_id`, `timestamp`, `intent`, `agent`, `prompt_id`, `prompt_version`, `model_tier`, `model_id`, `payload_hash`, `payload_json`, `raw_output`, `grounding_report_json`, `guardrail_report_json`, `compliance_decision`, `user_visible_output`, `suppressed`, `as_of_version`, `tokens_in`, `tokens_out`, `cost_usd`.
- [ ] 2. Create `app/ai/audit.py` with `write_audit(record) -> audit_id` (sha-prefixed `gen-...`); records are append-only (no update/delete API).
- [ ] 3. Call `write_audit` from `explainer.py` on **every** terminal outcome — pass, regenerate-exhausted-suppress, missing-input-suppress, provider error — so suppression is auditable too.
- [ ] 4. Surface `audit_id` on the returned `Explanation` (the API returns it per [10 §4 ai-summary](../10-api-contracts.md)).
### Tests
- [ ] `test_audit_written_on_publish` — successful generation writes one row with `suppressed=False` and a non-empty grounding report.
- [ ] `test_audit_written_on_suppress` — missing-input path writes a row with `suppressed=True` and `raw_output` empty/null.
### Compliance gate
- [ ] Stored fields include prompt id+version, input payload, model version, raw + user-visible output ([SPEC §6.6](../../SPEC.md)); records immutable.
### Acceptance criteria
- [ ] Any generation is fully reconstructable from its audit row (replayable).

---

## Feature: Prompt versioning & golden-dataset evaluation  `(Mode A)`
**Objective:** Make every prompt/model change gated by a golden suite covering grounding, guardrail, suppression, and Mode-A language ([14 §8](../14-ai-llm-agent-architecture.md)). · **Backend dep:** explainer + harness + guardrail. · **Frontend dep:** none. · **Data dep:** curated payload→expected-property fixtures.
### Steps
- [ ] 1. Create `tests/ai/golden/` with payload fixtures + expected properties: grounded facts present, fabricated facts blocked, directive phrasing rejected, suppression on missing inputs.
- [ ] 2. Create `app/ai/eval.py` `run_golden(provider) -> EvalReport` computing grounding pass-rate, fabrication block-rate, false-suppression rate, directive-leak rate.
- [ ] 3. Add `tests/ai/test_golden_eval.py` asserting thresholds (fabrication block-rate = 100%, directive-leak = 0%); a failing prompt/model version cannot ship.
- [ ] 4. Stamp `prompt_id`+`prompt_version` from the registry into every audit record so eval results attribute to a version.
### Tests
- [ ] `test_golden_suite_passes_for_v1_prompts` — current registered prompts pass all gates.
- [ ] `test_directive_leak_rate_zero` — no golden case yields directive language.
### Compliance gate
- [ ] A prompt or model version is blocked from promotion unless the golden suite passes all gates ([SPEC §6.6](../../SPEC.md)).
### Acceptance criteria
- [ ] Regression runs on every prompt/model change; metrics reported per [14 §8](../14-ai-llm-agent-architecture.md).

---

## Feature: Local cost controls (cache + daily ceiling)  `(Mode A)`
**Objective:** Make the AI layer economical locally: regenerate-on-change caching keyed by signal category, and a hard daily call ceiling with graceful non-AI degradation ([SPEC §6.8](../../SPEC.md), [14 §3](../14-ai-llm-agent-architecture.md)). · **Backend dep:** explainer, audit log, DuckDB. · **Frontend dep:** none. · **Data dep:** signal-category tags per symbol/day.
### Steps
- [ ] 1. Create `app/ai/cache.py` with a `signal_category(payload) -> str` key = hash of (`signalTags` sorted + `riskFlags` sorted + scanner + rounded `compositeScore` band). Same category since last run → serve cached summary, **no model call** ([SPEC §6.8 regenerate-on-change](../../SPEC.md)).
- [ ] 2. Back the cache with an `ai_summary_cache` DuckDB table (`symbol`, `signal_category`, `summary`, `audit_id`, `as_of`, `model_version`); `get_cached(symbol, category)` / `put_cached(...)`.
- [ ] 3. Create `app/ai/budget.py` with `DAILY_CALL_CEILING` (config/env) and a per-day counter persisted in DuckDB; `allow_call() -> bool`. When exhausted, `explain_*` returns a **non-AI templated fact** fallback (assembled from the payload's descriptive vocabulary) and logs `degraded=True` to audit ([SPEC §6.8 graceful degradation](../../SPEC.md)).
- [ ] 4. Add config keys to `app/config.py`: `AI_DAILY_CALL_CEILING`, `AI_MAX_REGEN`, `AI_MODEL_TIER_DEFAULT="cheap"`.
- [ ] 5. Emit a structured log line when the ceiling is hit (local stand-in for the production AI-spend meter).
### Tests
- [ ] `test_cache_hit_unchanged_signals` — second call with the same signal category serves cache; provider mock asserts called **once**.
- [ ] `test_cache_miss_on_category_change` — changed `riskFlags` → new model call.
- [ ] `test_ceiling_degrades_to_templated_fallback` — over ceiling → non-AI templated fallback, `degraded=True` in audit, provider not called.
### Compliance gate
- [ ] The templated fallback uses only descriptive vocabulary from the payload (still grounded, still Mode-A) ([SPEC §6.8](../../SPEC.md)).
### Acceptance criteria
- [ ] A full local pass over the M0 ~50-name universe stays within the daily ceiling; unchanged signals are not re-summarized.

---

## Done-when
- [ ] `app/ai/` provides `payload.py`, `provider.py`, `registry.py`, `prompts/`, `explainer.py`, `verify.py`, `guardrail.py`, `blocked_phrases.py`, `vocab.py`, `audit.py`, `cache.py`, `budget.py`, `eval.py`.
- [ ] Every `explain_*` outcome (publish/suppress/degrade) writes an audit row; no ungrounded number, blocked phrase, or directive tail can reach a caller.
- [ ] Suppression (never guessing) on missing critical inputs is the default failure mode ([SPEC §6.2](../../SPEC.md)).
- [ ] Caching + daily ceiling keep local cost bounded; the layer is consumed by [05-api-and-pipeline.md](05-api-and-pipeline.md) with no provider lock-in.
- [ ] `pytest tests/ai/` and the golden-eval suite are green; the explainer is ready for the `/stocks/{sym}/ai-summary` and `/market/summary` endpoints in step 05.
