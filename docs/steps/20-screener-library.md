# Steps · 20 · Prebuilt Screener Library

> Read first: [SPEC.md](../../SPEC.md) (§3–§5 Mode-A language, §4 row 5.17 builder, §6.5 validated scores) · [Roadmap](../02-product-roadmap.md) (V3/Phase 3) · [Feature Modules](../04-feature-modules.md) (§2–§7 scanners, §20 strategy/scanner builder) · [Scanner engine & scoring](../13-scanner-engine-and-scoring.md) · [IA & URL Paths](../05-information-architecture-and-url-paths.md) · [API Contracts](../10-api-contracts.md) · [Compliance & guardrails](../21-compliance-risk-and-guardrails.md)

**Maps to:** Roadmap V3 · SPEC Phase 3 · Feature Modules §5.23 (prebuilt screener library)
**Status:** Not started   |   **Regulatory mode:** A
**Prerequisites:** [02-indicators-and-scanners.md](02-indicators-and-scanners.md) (indicator + scanner primitives), [03-scanner-score-validation.md](03-scanner-score-validation.md) (validated scores), [05-api-and-pipeline.md](05-api-and-pipeline.md) (scanner endpoints + envelope), [06-frontend-foundation-and-v1-screens.md](06-frontend-foundation-and-v1-screens.md) (scanner UI components, `ScannerResultsTable`, `EvidenceDrawer`). Links forward to [09-v4-strategy-builder.md](09-v4-strategy-builder.md) (custom no-code builder + field catalog).

## Overview
The **prebuilt screener library** is a catalog of curated, **named** Mode-A filters — e.g. *"Above 50-DMA + RSI 55–70 + 2× volume"*, *"Oversold quality (RSI < 30, above 200-DMA)"*, *"Volume-delivery expansion"* — that a user can **browse, run, save, and re-run**, with **list outputs only** ([04 §2–§7](../04-feature-modules.md), [SPEC §4 row 5.17](../../SPEC.md)). Each library entry is a fixed, server-defined condition spec over the **same validated indicators/scanners V1 already computes** ([13 §3–4](../13-scanner-engine-and-scoring.md)) — it never invents new fields, never carries a forward target/stop, and its results are framed with **membership language** ("matches this filter" / "appears in the scanner"), never as buy-leans ([SPEC §3.2, §5](../../SPEC.md)).

This step is the **bridge between the fixed V1 scanners and the fully custom builder** ([09-v4-strategy-builder.md](09-v4-strategy-builder.md)): the library reuses [09](09-v4-strategy-builder.md)'s field catalog and strategy schema so every library entry is a valid, openable strategy. From any library result, a user can **"Open in builder"** to edit the spec into a custom scanner ([04 §20](../04-feature-modules.md)). Library entries are **seed-data + admin-curated**, versioned, and pass the same compliance review as any Mode-A copy ([21 §9](../21-compliance-risk-and-guardrails.md)). No library entry, name, description, or result row may emit entry/target/SL, a "candidate" buy-lean, or a ranked "what to buy" ([SPEC §3.2, row 5.22](../../SPEC.md)).

## Exit gate (Definition of Done)
- [ ] A curated catalog of named prebuilt screeners persists as **versioned server-side specs** built only on the [09](09-v4-strategy-builder.md) field catalog; no spec references an unknown or RA-gated (target/stop) field.
- [ ] A user can **browse** the library (by category/tag), **run** an entry (list output), **save** it to their saved screeners, and **re-run** a saved entry reproducibly for a given `as_of`.
- [ ] Every library result is a **list** with score + descriptive reasons + risk flags and per-row evidence — membership language only; **no buy-lean / target / SL** anywhere.
- [ ] "Open in builder" hands a library spec to [09-v4-strategy-builder.md](09-v4-strategy-builder.md) as an editable strategy tree; round-trips without losing or inventing fields.
- [ ] Library names/descriptions are guardrail- + compliance-reviewed; the build-time blocked-phrase lint fails on any advisory string ([06 §13 lint](06-frontend-foundation-and-v1-screens.md), [SPEC §6.9](../../SPEC.md)).
- [ ] `pytest` (catalog validation, run determinism, field-allowlist) + frontend component/E2E green.

---

## Feature: Curated screener catalog (versioned specs)  `(Mode A)`
**Objective:** Define the prebuilt screeners as fixed, versioned condition specs over the validated indicator/scanner layer, each with a descriptive name, "what it measures" blurb, and tags — never a forward field. · **Backend dep:** [09](09-v4-strategy-builder.md) field catalog (`app/strategy/catalog.py`) + strategy schema (`app/strategy/schema.py`); validated scanners ([13](../13-scanner-engine-and-scoring.md)). · **Frontend dep:** none. · **Data dep:** indicator + scanner outputs, validated sub-scores/tags.
### Steps
- [ ] 1. Create `app/screeners/library.py` with a versioned `SCREENER_LIBRARY` registry: each entry is `ScreenerDef(id, slug, name, what_it_measures, category, tags, rule_spec, default_universe, default_sort, version)`. `rule_spec` reuses [09](09-v4-strategy-builder.md)'s `entry_rules` condition tree (`app/strategy/schema.py`) — **entry conditions only**, no exit/stop/target fields.
- [ ] 2. Seed the initial catalog (one concept per entry, all expressible on the field catalog): e.g. `above-50dma-rsi-band-volume` ("trading above the 50-DMA, RSI 55–70, volume ≥ 2× 20-day avg"), `oversold-above-200dma` ("RSI(14) < 30 while above the 200-DMA"), `volume-delivery-expansion` ("volume ≥ 2× 20-day avg with elevated delivery %"), `ma-stack-aligned` ("close > SMA20 > SMA50 > SMA200"), `near-20d-high-on-volume`. Each name/blurb is **descriptive**, never "best buys" ([SPEC §5](../../SPEC.md)).
- [ ] 3. **Validate every spec at load time** against [09](09-v4-strategy-builder.md)'s `app/strategy/validate.py`: reject any entry referencing an unknown field, a malformed operator, or an RA-gated level field (`target`/`stop`/`sl`/`entry`/`invalidation`) — raise `ForbiddenFieldError` ([04 universal rules](../04-feature-modules.md), [SPEC §3.2](../../SPEC.md)). A library entry **cannot** carry a forward price.
- [ ] 4. Each entry maps `category`/`tags` for browse/filter (e.g. `momentum`, `mean-reversion`, `volume`, `trend`) and links a `learn_slug` to its concept explainer ([27-seo-learn-content.md](27-seo-learn-content.md), e.g. RSI entry → `/learn/what-is-rsi`).
- [ ] 5. Stamp `version` per entry; a spec change requires a version bump (no silent edits) — enforced by a test hashing the registry against registered versions (mirrors [04 §6 prompt-version lock pattern](04-ai-explanation-layer.md)).
- [ ] 6. Expose `list_screeners(category=None, tag=None)` and `get_screener(slug)`; admin-curation hooks (add/disable/version) land in the admin layer ([15-cross-cutting-admin-infra-qa.md](15-cross-cutting-admin-infra-qa.md)).
### Tests
- [ ] `test_every_library_spec_validates` — each seeded entry passes [09](09-v4-strategy-builder.md) tree validation.
- [ ] `test_library_rejects_forward_field` — a spec with a `target`/`stop` field raises `ForbiddenFieldError`.
- [ ] `test_screener_version_locked` — editing a spec without bumping its version fails.
### Compliance gate
- [ ] No entry name/blurb/tag is a buy-lean or "best stock" framing; specs reference only validated, non-forward fields ([SPEC §3.2, §5](../../SPEC.md), [13 §0.4](../13-scanner-engine-and-scoring.md)).
### Acceptance criteria
- [ ] The catalog is a versioned set of valid strategy specs reusing the [09](09-v4-strategy-builder.md) field catalog; nothing forward-looking can be encoded.

---

## Feature: Run & save prebuilt screeners (list outputs)  `(Mode A)`
**Objective:** Execute a library entry against the EOD universe to produce a reproducible **list** with score + reasons + risk flags + evidence, and let users save it to their screeners. · **Backend dep:** [09](09-v4-strategy-builder.md) condition-tree evaluator (`app/strategy/engine.py`) / scanner-rule compiler; saved-screener store ([11 — database architecture](../11-database-architecture.md)); envelope + `as_of` caching ([05-api-and-pipeline.md](05-api-and-pipeline.md), [10 §0.1](../10-api-contracts.md)). · **Frontend dep:** scanner result components from [06](06-frontend-foundation-and-v1-screens.md). · **Data dep:** EOD indicators/scanner sub-scores, validated scores, risk flags, as-of version.
### Steps
- [ ] 1. Implement `app/screeners/run.py` `run_screener(slug, *, universe, as_of, limit, offset, sort, filters) -> ScreenerResult` — compiles the entry's `rule_spec` via [09](09-v4-strategy-builder.md)'s compiler to a **live scanner rule (entry conditions only)** and returns a **list** of matches, each row carrying `symbol`, validated `score`/`sub_scores`, descriptive `reasons`, `risk_flags`, and per-row `evidence` ([10 §5 scanner shape](../10-api-contracts.md)). Exit/stop/target are structurally absent.
- [ ] 2. Add API endpoints under the scanner family ([10 §5](../10-api-contracts.md), [05 §0](../05-information-architecture-and-url-paths.md)): `GET /api/scanners/library` (catalog) and `GET /api/scanners/library/{slug}` (run; same params/shape as `GET /api/scanners/momentum` — `date?`, `universe?`, `limit?`, `offset?`, `min_score?`, `sort?`). Reuse the standard envelope with `meta.as_of` + `meta.data_confidence`.
- [ ] 3. Add a **saved-screener store**: `POST /api/me/screeners` (save a library entry, optionally with the user's filter overrides), `GET /api/me/screeners`, `DELETE /api/me/screeners/{id}`. A saved entry stores the `slug` + `version` + overrides so re-runs are reproducible and version-pinned ([SPEC §6.2](../../SPEC.md)).
- [ ] 4. Caching: library runs are `eod`-cacheable keyed by (`slug`, `version`, `universe`, `as_of`, filter hash); identical inputs serve cache, no recomputation ([10 §0](../10-api-contracts.md)).
- [ ] 5. Suppression/low-confidence: if a required input is missing for the date, return `data_confidence: low`/`suppressed` per row or surface the date-unavailable state — never fabricate a match ([SPEC §6.2](../../SPEC.md), [04 §2 states](../04-feature-modules.md)).
### Tests
- [ ] `test_run_screener_returns_list_only` — output is a list of rows; no row carries entry/target/SL/exit fields.
- [ ] `test_run_screener_reproducible` — same (`slug`,`version`,`universe`,`as_of`) → identical result set.
- [ ] `test_saved_screener_version_pinned` — a saved entry re-runs against its pinned spec version.
### Compliance gate
- [ ] Results are **lists, not calls**; reasons use membership language; every score/reason/flag traces to the row's evidence ([SPEC §4, §5](../../SPEC.md), [13 §0.4](../13-scanner-engine-and-scoring.md)).
### Acceptance criteria
- [ ] A library entry runs to a reproducible, evidence-backed **list**; saving + re-running preserves the exact spec version ([10 §5, §14](../10-api-contracts.md)).

---

## Feature: Library UI — browse, run, save, "Open in builder"  `(Mode A)`
**Objective:** A browsable library surface and a per-screener results view that reuse the V1 scanner UI, plus a hand-off into the custom builder. · **Backend dep:** library catalog + run + saved-screener endpoints (above). · **Frontend dep:** `(market)`/`(app)` route groups, `ScannerResultsTable`, `ScoreBadge`, `ReasonChips`, `RiskFlagChip`, `EvidenceDrawer`, `RaGatedPlaceholder`, `NotAdviceBanner` from [06-frontend-foundation-and-v1-screens.md](06-frontend-foundation-and-v1-screens.md). · **Data dep:** catalog + result payloads.
### Steps
- [ ] 1. Build `app/(market)/scanners/library/page.tsx` → `ScreenerLibraryGrid` of `ScreenerLibraryCard`s (name, "what it measures" blurb, category/tags, last-run/result count) sourced from `GET /api/scanners/library`. Each card states what the filter measures — **never** "best buys" / "top picks" ([04 §20](../04-feature-modules.md), [08 §global overlay](../08-screen-by-screen-documentation.md)).
- [ ] 2. Build `app/(market)/scanners/library/[slug]/page.tsx` reusing `ScannerHeader` (name, what it measures, last-run, validation note from [SPEC §6.5](../../SPEC.md)), `ScannerFilters` (sector/index/score-band/risk-flag — **no "buy" preset**), `ScannerResultsTable`, and the per-row `EvidenceDrawer` from [06](06-frontend-foundation-and-v1-screens.md). Virtualized + paginated; loading/error/empty states.
- [ ] 3. Add **Save** (to `/api/me/screeners`, auth-gated with an upgrade gate inside the route per [05 §3](../05-information-architecture-and-url-paths.md)) and **"Open in builder"** that routes to `/strategy-builder` ([09-v4-strategy-builder.md](09-v4-strategy-builder.md)) with the spec preloaded as an editable strategy tree.
- [ ] 4. Wrap the surface in `NotAdviceBanner`; render any RA-gated slot as `RaGatedPlaceholder` (none should appear — list outputs only). Tags deep-link to their `/learn/...` concept page ([27-seo-learn-content.md](27-seo-learn-content.md)).
- [ ] 5. Analytics ([24 §1.2](../24-analytics-seo-and-growth.md)): `scanner_view{scanner="library:<slug>"}` on run, plus `screener_library_view`, `screener_card_open`, `screener_save`, `screener_open_in_builder`, `scanner_row_evidence_open`.
### Tests
- [ ] Component: `ScreenerLibraryCard` renders the descriptive blurb; `ScannerResultsTable` renders score/reasons/risk flags; "Open in builder" routes with the spec.
- [ ] E2E: browse library → open an entry → see a list with score + reasons + evidence; assert **no** entry/target/SL element in the DOM.
### Compliance gate
- [ ] No card/blurb/result uses buy-lean/target/SL language; filters offer **no** "best stocks" preset; `NotAdviceBanner` present ([08 global overlay](../08-screen-by-screen-documentation.md), [SPEC §3.2](../../SPEC.md)).
### Acceptance criteria
- [ ] The library is browsable, runnable, saveable, and hands a valid editable spec to [09-v4-strategy-builder.md](09-v4-strategy-builder.md); all outputs are evidence-backed lists.

---

## Done-when
- [ ] A versioned, compliance-reviewed catalog of named prebuilt screeners exists, built only on the [09](09-v4-strategy-builder.md) field catalog; no spec carries a forward/RA-gated field.
- [ ] Users browse, run (list outputs), save, and reproducibly re-run library entries; saved entries are spec-version-pinned.
- [ ] Every result is an evidence-backed list with membership language; "Open in builder" round-trips a valid editable strategy into [09-v4-strategy-builder.md](09-v4-strategy-builder.md).
- [ ] No library name, description, filter, or result row emits a buy-lean, target, stop-loss, or ranked "what to buy"; blocked-phrase lint + compliance review pass ([SPEC §3.2, §6.9](../../SPEC.md)).
- [ ] Backend + frontend tests green; analytics events fire per [24](../24-analytics-seo-and-growth.md).
