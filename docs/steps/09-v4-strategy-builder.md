# Steps · 09 · V4 Strategy / Scanner Builder (Mode-A subset)
> Read first: [SPEC.md](../../SPEC.md) · [Roadmap](../02-product-roadmap.md) · [Backtesting & strategy builder](../19-backtesting-and-strategy-builder.md) · [Scanner engine & scoring](../13-scanner-engine-and-scoring.md) · [AI/LLM agent architecture](../14-ai-llm-agent-architecture.md) · [Compliance & guardrails](../21-compliance-risk-and-guardrails.md)

**Maps to:** Roadmap V4 (Mode-A subset) · SPEC Phase 3–4
**Status:** Not started   |   **Regulatory mode:** A (per-stock entry/target/stop-loss/invalidation **LEVELS are RA-gated and NOT built here** — deferred to step 14 `15-cross-cutting…`/`14-v9-advisory-ra-gated.md`)
**Prerequisites:** [00-phase-0-derisk.md](00-phase-0-derisk.md) (M3b score validation), V1 scanner engine + V2/V3 AI layer (earlier step files: `01-v1-eod-core.md` … `08-v3-portfolio-and-alerts.md`)

## Overview
The custom **no-code strategy / scanner builder**: a typed condition-tree UI and rule engine that compiles to **scanner queries producing LISTS of current matches — never buy/sell calls** ([SPEC.md §4 row 5.17](../../SPEC.md), [19 §1](../19-backtesting-and-strategy-builder.md)). It adds saved strategies, a curated screener library, and a **natural-language → strategy** path via the **Strategy Builder Agent** ([14 §5.6](../14-ai-llm-agent-architecture.md)), which is grounded (emits only known indicator/scanner fields under the payload contract) and outputs a **structured, editable strategy definition** the user confirms.

This step builds **only the Mode-A surface**: condition blocks over the same indicators/scanners V1 already computes ([13 §3–4](../13-scanner-engine-and-scoring.md)), AND/OR composition, save/load, a screener library, and NL→strategy. Exit/stop/target fields are permitted **only as backtest-simulation parameters** (they configure step 10's historical engine) and are **dropped from any live scanner form** ([19 §1.1, §2.1](../19-backtesting-and-strategy-builder.md)). The backtesting *engine* itself ships in [10-v5-backtesting-and-ml.md](10-v5-backtesting-and-ml.md).

### NON-NEGOTIABLE boundaries
- Builder outputs are **lists, not calls** ([SPEC.md §4 5.17](../../SPEC.md)). No field, label, or prose may function as a buy/sell instruction or a "candidate" buy-lean ([SPEC.md row 5.22](../../SPEC.md)).
- The word "buy" in a user's NL phrasing maps to an **entry rule of a backtest/scanner definition**, never a recommendation ([19 §2](../19-backtesting-and-strategy-builder.md)).
- Stop-loss / target / trailing-stop blocks are labelled **"backtest parameters"** and are **never surfaced as live per-stock levels** for a current holding — that is the RA-gated divergence ([SPEC.md row 5.21](../../SPEC.md), see DEFERRED section below).
- The Strategy Builder Agent may reference **only** the versioned field catalog; an unknown field is **rejected, not invented** ([SPEC.md §6.6](../../SPEC.md), [14 §5.6](../14-ai-llm-agent-architecture.md)).

## Exit gate (Definition of Done)
- [ ] A user can build a multi-condition strategy in the UI, it round-trips to JSON and back ([19 §7](../19-backtesting-and-strategy-builder.md)), and an invalid tree (e.g. exit with no entry) is rejected with a clear error.
- [ ] The strategy's **entry conditions** compile to a **live scanner rule** that returns a **list** of current matches; exit/stop/target are **dropped** from the live scanner form.
- [ ] Saved strategies and the screener library persist, version, and reload correctly.
- [ ] NL→strategy produces editable typed blocks the user confirms; directive phrasing in the prompt does **not** produce a recommendation; unknown fields are rejected.
- [ ] No live builder/scanner output contains entry/target/stop-loss/invalidation **levels**; guardrail + compliance review pass on all agent prose ([14 §5.6, §5.8](../14-ai-llm-agent-architecture.md)).
- [ ] DEFERRED/RA-GATED section is honored: no per-stock technical levels are implemented in this phase.

---
## Feature: No-code condition builder + rule engine  `(Mode A)`
**Objective:** Compose typed condition blocks (AND/OR) over V1 indicators/scanners into a validated strategy tree that compiles to a scanner query (list output). · **Backend dep:** condition-tree evaluator over the indicator/scanner layer ([13](../13-scanner-engine-and-scoring.md)); universe resolver with point-in-time membership ([19 §1](../19-backtesting-and-strategy-builder.md)); scanner-rule compiler. · **Frontend dep:** drag-and-drop block builder, AND/OR grouping, parameter forms. · **Data dep:** adjusted historical OHLCV, computed indicators, scanner sub-scores/tags, point-in-time index membership.

### Steps
- [ ] 1. Define the **versioned field/block catalog** in `app/strategy/catalog.py` — the allow-list of referenceable fields: indicator conditions (`RSI(14)`, `close > SMA(50)`, `MACD_hist crosses_above 0`), price/volume (`close > prior_high(20)`, `volume > 2 × avg_vol(20)`), scanner membership (`in_scanner('momentum')`, `score('momentum') > 70`), universe filters (market-cap band, sector, point-in-time index membership), and Phase-3+ descriptive fundamental bands (`pe_band == 'below_sector_median'`). Mirror the block table in [19 §1](../19-backtesting-and-strategy-builder.md). All thresholds/operators in versioned config, no magic constants.
- [ ] 2. Implement the **strategy schema** in `app/strategy/schema.py` matching the JSON in [19 §7](../19-backtesting-and-strategy-builder.md): `universe` (with `membership_mode: point_in_time`, `include_delisted`), `entry_rules` (AND/OR condition tree), `exit_rules` (indicator/cross/`stop_loss`/`target`/`trailing_stop`/`time`), `execution`, `backtest`, `integrity`, `disclaimer`, plus `strategy_id`/`name`/`version`.
- [ ] 3. Implement the **condition-tree evaluator** in `app/strategy/engine.py` over the indicator layer; resolve the **point-in-time universe** (index/cap band as-of date) via the universe resolver. Reuse V1 indicator + scanner outputs; never recompute differently.
- [ ] 4. Implement the **scanner-rule compiler** in `app/strategy/compiler.py`: from a strategy, emit a **live scanner rule** that uses **only `entry_rules`** and produces a **list** of current matches ([19 §2.1](../19-backtesting-and-strategy-builder.md)). Explicitly **strip `exit_rules`/`stop_loss`/`target`/`trailing_stop`** from the live form.
- [ ] 5. Implement **tree validation** in `app/strategy/validate.py`: reject invalid trees (exit with no entry, unknown field, malformed operator, RA-gated level fields) with structured errors.
- [ ] 6. Frontend: drag-and-drop block builder with AND/OR grouping and per-block parameter forms (`web/app/strategy/builder/…`). Label any stop/target/trailing block **"backtest parameter"** with an inline note that it is simulation-only, not a live level.
- [ ] 7. API: `POST /strategy/validate`, `POST /strategy/compile-scanner` (returns the list-producing rule), per [10 — API contracts](../10-api-contracts.md).

### Tests
- [ ] A built strategy round-trips to JSON and back byte-equivalent on the canonical fields ([19 §1.1, §7](../19-backtesting-and-strategy-builder.md)).
- [ ] An invalid tree (exit without entry; unknown field; RA-gated level field) is rejected with a clear, structured error.
- [ ] The compiled **live scanner rule contains no `exit`/`stop`/`target`/`trailing` fields** and returns a list given a fixture universe.
- [ ] Point-in-time universe resolution selects the correct membership for a historical date (no current-membership leakage).

### Compliance gate
- [ ] No builder field or compiled output can be reworded into a buy/sell call or a "candidate" buy-lean ([SPEC.md §3.2, row 5.22](../../SPEC.md)).
- [ ] Stop/target/trailing blocks render with the **"backtest parameter / simulation-only"** label and never as a live per-stock level ([SPEC.md row 5.21](../../SPEC.md), [19 §1.1](../19-backtesting-and-strategy-builder.md)).
- [ ] Live scanner output uses descriptive membership language ("matches this filter" / "appears in the scanner") only ([13 §0.4](../13-scanner-engine-and-scoring.md)).

### Acceptance criteria
- [ ] Builder outputs are **lists, not calls** ([19 §1, §2.1](../19-backtesting-and-strategy-builder.md)).
- [ ] Invalid tree rejected with a clear error ([19 §1.1](../19-backtesting-and-strategy-builder.md)).
- [ ] The live scanner form contains **no exit/stop/target** ([19 §2.1](../19-backtesting-and-strategy-builder.md)).

---
## Feature: Saved strategies + screener library  `(Mode A)`
**Objective:** Persist, version, share (read-only), and reload user strategies; ship a curated **screener library** of prebuilt Mode-A filters. · **Backend dep:** saved-strategy store + versioning ([11 — database architecture](../11-database-architecture.md)); strategy schema (above). · **Frontend dep:** strategy list/detail, save/clone, library browse. · **Data dep:** strategy JSON; library seed definitions.

### Steps
- [ ] 1. Persist strategies in a `strategies` entity (id, owner, name, version, JSON, created/updated, `validationStatus`) per [11](../11-database-architecture.md); bump `version` on edit (immutable prior versions for audit).
- [ ] 2. Seed a **curated screener library** (`app/strategy/library/…`): prebuilt Mode-A filters (e.g. "oversold large-cap 50-DMA reclaim" as a **scanner**, momentum + volume confirmation, sector-leader breadth). Each library entry is a list-producing scanner, descriptively named — **no** "top picks"/"buy" naming.
- [ ] 3. API: `GET/POST/PUT /strategy`, `POST /strategy/{id}/clone`, `GET /strategy/library`, per [10](../10-api-contracts.md). Sharing is **read-only** (no per-user actionable distribution).
- [ ] 4. Frontend: strategy list, save/clone/rename, library browse + "use as scanner".

### Tests
- [ ] Save → reload yields an identical strategy; editing creates a new version and preserves the prior.
- [ ] Library entries each validate against the schema and compile to a list-producing scanner.
- [ ] Cloning a library entry produces an editable user-owned copy.

### Compliance gate
- [ ] Library and shared-strategy naming/prose is descriptive, never directive ("top picks", "buy list" are blocked); guardrail list applies ([21 §3](../21-compliance-risk-and-guardrails.md)).
- [ ] Shared strategies are **filter definitions / lists**, not per-user actionable distributions ([SPEC.md §7](../../SPEC.md)).

### Acceptance criteria
- [ ] Strategies persist, version, and reload correctly.
- [ ] The screener library is browsable and each entry produces a list.

---
## Feature: Natural-language → strategy (Strategy Builder Agent)  `(Mode A)`
**Objective:** Convert a user's NL filter idea into a **structured strategy JSON of typed blocks**, shown back as **editable blocks for confirmation** — grounded on the field catalog, never inventing data sources ([19 §2](../19-backtesting-and-strategy-builder.md), [14 §5.6](../14-ai-llm-agent-architecture.md)). · **Backend dep:** Strategy Builder Agent under the payload contract; NL→blocks validator; field catalog; the standard verification → guardrail → compliance-review pipeline ([14 §2, §6, §5.8](../14-ai-llm-agent-architecture.md)). · **Frontend dep:** NL input, agent-proposed editable blocks, explicit confirm step. · **Data dep:** the versioned indicator/scanner field catalog the agent may reference.

### Steps
- [ ] 1. Implement the **Strategy Builder Agent** per [14 §5.6](../14-ai-llm-agent-architecture.md): premium model tier; tools `get_field_catalog`, `validate_rule_spec`; output schema `{ ruleSpec, outputType:"list", explanation, disclaimer:"Outputs a list, not recommendations." }`.
- [ ] 2. Implement the **NL→blocks validator**: every emitted block must reference a **known catalog field**; an unknown field is **rejected with a clarify-request**, never fabricated ([19 §2.1 acc.](../19-backtesting-and-strategy-builder.md)).
- [ ] 3. Map directive verbs ("buy oversold large-caps…") to **entry rules of a backtest/scanner definition**; the guardrail **strips any directive framing** from agent prose ([19 §2](../19-backtesting-and-strategy-builder.md)).
- [ ] 4. Route every agent output through verification → guardrail → **Compliance Review Agent** ([14 §6, §5.8](../14-ai-llm-agent-architecture.md)); write an audit record ([14 §7](../14-ai-llm-agent-architecture.md)).
- [ ] 5. Frontend: NL prompt → proposed editable blocks → **explicit user confirm** before any compile/run; the AI proposes structure, it **does not auto-run** ([19 §2](../19-backtesting-and-strategy-builder.md)).
- [ ] 6. API: `POST /strategy/from-nl` returning proposed blocks + grounding/compliance status.

### Tests
- [ ] The agent **only emits known fields**; an unknown field is rejected, not invented ([19 §2.1(a)](../19-backtesting-and-strategy-builder.md)).
- [ ] Directive language in the user prompt **does not produce a recommendation** — output remains a list-producing filter ([19 §2.1(b)](../19-backtesting-and-strategy-builder.md)).
- [ ] The compiled **live scanner form contains no exit/stop/target** ([19 §2.1(c)](../19-backtesting-and-strategy-builder.md)).
- [ ] Golden-dataset regression: a request for target/stop fields is **rejected as RA-gated** ([14 §5.6, §8](../14-ai-llm-agent-architecture.md)).

### Compliance gate
- [ ] Agent output passes runtime verification (no ungrounded field), guardrail (no blocked phrase), and compliance review (Mode-A safe) before display ([14 §2](../14-ai-llm-agent-architecture.md)).
- [ ] The `disclaimer` "Outputs a list, not recommendations." is present on every NL-derived strategy ([14 §5.6](../14-ai-llm-agent-architecture.md)).
- [ ] Agent **rejects requests for target/stop/entry-level fields** (RA-gated) rather than emitting them ([14 §5.6](../14-ai-llm-agent-architecture.md)).

### Acceptance criteria
- [ ] Agent emits only known fields; unknown → clarify, not fabricate.
- [ ] Directive prompt → list-producing filter, never a call.
- [ ] User confirms editable blocks before any run.

---
## DEFERRED / RA-GATED — per-stock technical LEVELS are NOT built here
> **This is the single biggest divergence from the original Saakshya spec** ([SPEC.md §4 rows 5.21/5.22](../../SPEC.md), [02 §7, §13](../02-product-roadmap.md)).

The following are **NOT implemented in this step** and **must not appear** in any V4 Mode-A surface:

- **Per-stock entry levels, target levels, stop-loss levels, invalidation levels** ("Saakshya V4 technical levels") — advisory-in-substance; require **RA registration (Mode B) in force** ([SPEC.md row 5.21](../../SPEC.md)).
- **"Candidate" buy-lean labels** — a label functioning as a buy-lean is advisory-in-substance ([SPEC.md row 5.22](../../SPEC.md)).

**Gating note:** These are deferred to **Phase 5 / step `14-v9-advisory-ra-gated.md`** and ship **only when RA registration is in force**. Until then:
- The Mode-A part of V4 is the **strategy/scanner builder only** (this step).
- Stop/target/trailing fields exist **solely** as **backtest-simulation parameters** for step 10 — never as live per-stock levels for a current holding ([19 §1.1](../19-backtesting-and-strategy-builder.md), [16 §3.3 portfolio](../16-portfolio-and-risk-engine.md)).
- Descriptive support/resistance ("historically a resistance zone") is the only level-like language allowed in Mode A ([SPEC.md §5](../../SPEC.md), [21 §1.1](../21-compliance-risk-and-guardrails.md)).
- RA-gated routes/widgets **do not exist in the v1 router**; they are added behind a feature flag in Phase 5 ([21 §1](../21-compliance-risk-and-guardrails.md)).

---
## Done-when
- [ ] No-code builder + rule engine ships: validated condition trees compile to **list-producing** scanner rules; exit/stop/target stripped from live form.
- [ ] Saved strategies + curated screener library persist, version, and reload.
- [ ] NL→strategy (Strategy Builder Agent) produces grounded, editable, confirmable blocks; unknown fields rejected; directive prompts yield lists, not calls.
- [ ] Every agent output passes verification → guardrail → compliance review and is audited.
- [ ] **No per-stock entry/target/stop-loss/invalidation levels and no "candidate" buy-leans exist anywhere in this step** — deferred to step 14, RA-gated.
