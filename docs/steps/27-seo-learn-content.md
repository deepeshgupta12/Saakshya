# Steps · 27 · SEO & Educational Content (Public Surface)

> Read first: [SPEC.md](../../SPEC.md) (§3.3 prohibited phrases, §5 language, §6.2 as-of, §6.9 output-time guardrail) · [Roadmap](../02-product-roadmap.md) (Phase 1+) · [Analytics, SEO & Growth](../24-analytics-seo-and-growth.md) · [IA & URL Paths](../05-information-architecture-and-url-paths.md) · [Feature Modules](../04-feature-modules.md) · [Screen-by-Screen](../08-screen-by-screen-documentation.md) · [API Contracts](../10-api-contracts.md) · [Compliance & guardrails](../21-compliance-risk-and-guardrails.md)

**Maps to:** Roadmap Phase 1+ (public acquisition surface; grows with each phase) · SPEC Phase 1+
**Status:** Not started   |   **Regulatory mode:** A
**Prerequisites:** [06-frontend-foundation-and-v1-screens.md](06-frontend-foundation-and-v1-screens.md) (public `(market)` screens, blocked-phrase build-time lint, design tokens), [05-api-and-pipeline.md](05-api-and-pipeline.md) (EOD-cached public endpoints + envelope). Glossary terms tie to [29 — Glossary](../29-glossary.md). The blocked-phrase guardrail mirrors [04-ai-explanation-layer.md](04-ai-explanation-layer.md)'s `blocked_phrases_export()`.

## Overview
The public, **indexed** surface is Saakshya's acquisition engine and the proof of the evidence-first positioning ([24 §0, §3](../24-analytics-seo-and-growth.md)). This step ships: (1) **indexed entity pages** — `/stocks/[symbol]`, `/sectors/[sector]`, and the **query-shaped scanner SEO pages** `/scanners/momentum-stocks` + `/scanners/volume-breakout-stocks`; (2) the **`/learn` educational library** — `/learn/what-is-rsi`, `/learn/volume-breakout-meaning`, `/learn/how-to-read-moving-averages` — and **market glossary pages** `/learn/glossary/[term]`; (3) the SEO plumbing: **structured data (schema.org)**, **internal linking**, **canonical rules**, split sitemaps, and the **gated-premium vs public-education** split.

The compliance constraint is the whole point: **indexed pages are the highest-leverage compliance surface** — a single buy-lean on a crawlable, archived, regulator-visible page is a public violation ([24 §0.3](../24-analytics-seo-and-growth.md), [SPEC §3.3, §6.9](../../SPEC.md)). **Every** title, H1, meta description, body string, and JSON-LD value on an indexed page uses **Mode-A descriptive language** — no buy-leans, no targets, no stop-losses, no "candidate" language, no return claims — and passes the same guardrail (run over **rendered HTML** in CI) as AI output ([24 §3.2](../24-analytics-seo-and-growth.md), [21 §9](../21-compliance-risk-and-guardrails.md)). Scanner pages say "appears in / matches this filter", never "top stocks to buy". Structured data may **never** emit `Rating`/`Review`/`Recommendation`-shaped types ([24 §3.3](../24-analytics-seo-and-growth.md)). Every indexed analytical page carries a visible **"Not investment advice"** line and the data **`as_of`** date ([SPEC §6.2](../../SPEC.md)).

## Exit gate (Definition of Done)
- [ ] Indexed entity pages (`/stocks/[symbol]`, `/sectors/[sector]`, `/scanners/momentum-stocks`, `/scanners/volume-breakout-stocks`) render meaningful SSR/SSG content from EOD data with descriptive copy, a visible not-advice line, and an `as_of` date.
- [ ] `/learn` library + `/learn/glossary/[term]` pages exist as evergreen SSG explainers, cross-linked to the live scanner/stock pages and to [29 — Glossary](../29-glossary.md).
- [ ] **The blocked-phrase guardrail runs over rendered HTML of all indexed routes in CI and fails the build on any violation** ([24 §5](../24-analytics-seo-and-growth.md), [SPEC §6.9](../../SPEC.md)).
- [ ] Structured data is valid JSON-LD for the **allowed** types only; **no** `Rating`/`Review`/`Recommendation` markup on any Mode-A page.
- [ ] Canonical rules hold: one canonical per concept; scanner SEO-slug ↔ app-path resolves to a single indexable URL; filter/sort/page/as_of params excluded; symbol case 301s to uppercase.
- [ ] Split sitemaps include only `indexed` routes; `noindex`/`disallow` correct for auth/admin/api ([05 §6](../05-information-architecture-and-url-paths.md)).
- [ ] Internal-linking loop (education → live data → education) and indicator-chip → glossary deep-links are wired.

---

## Feature: Indexed entity pages (stock, sector, scanner SEO)  `(Mode A)`
**Objective:** Ship the crawlable, descriptive public pages with Mode-A titles/H1/meta and a not-advice + as-of line, reusing the V1 screens. · **Backend dep:** EOD-cached `GET /stocks/{symbol}/overview`, `/sectors/{id}/summary`, `/scanners/momentum`, `/scanners/volume-breakout` ([10 §3–§5](../10-api-contracts.md)). · **Frontend dep:** V1 stock/sector/scanner components + compliance wrappers from [06-frontend-foundation-and-v1-screens.md](06-frontend-foundation-and-v1-screens.md). · **Data dep:** EOD batch + `as_of` + confidence flags.
### Steps
- [ ] 1. Reuse the V1 `/stocks/[symbol]` and `/sectors/[sector]` SSR/ISR pages ([06](06-frontend-foundation-and-v1-screens.md), [05 §2](../05-information-architecture-and-url-paths.md)); add **per-page SEO metadata** (`generateMetadata`) with **descriptive** title/H1/meta — good: *"RELIANCE Share Analysis — Indicators, Scanners & Risk (EOD) | Saakshya"*; bad/blocked: *"Top Stocks to Buy Today"* ([24 §3.2](../24-analytics-seo-and-growth.md)).
- [ ] 2. Add the **query-shaped scanner SEO pages** `/scanners/momentum-stocks` and `/scanners/volume-breakout-stocks` ([24 §3.1](../24-analytics-seo-and-growth.md)): they render the scanner result **list** (score + reasons + risk flags, membership framing) and **canonicalize to / 301 from** the app paths `/scanners/momentum` and `/scanners/volume-breakout` so exactly **one** URL per scanner is indexable ([24 §3.1 slug note, §3.4](../24-analytics-seo-and-growth.md), [05 §6](../05-information-architecture-and-url-paths.md)).
- [ ] 3. Ensure each indexed analytical page renders, server-side, a visible **"Not investment advice"** line and the data **`as_of`** date ([SPEC §6.2](../../SPEC.md), [24 §3.2](../24-analytics-seo-and-growth.md)); content is genuinely present for crawlers (no cloaking — [24 §3.6](../24-analytics-seo-and-growth.md)).
- [ ] 4. Confirm RA-gated slots stay as `RaGatedPlaceholder` (no entry/target/SL ever rendered or indexed); descriptive S/R uses historical framing ([05 §2 stock row](../05-information-architecture-and-url-paths.md), [06](06-frontend-foundation-and-v1-screens.md)).
- [ ] 5. Scanner SEO pages frame results as "appears in / matches this filter", **never** "candidate / buy / top picks" ([24 §3.2](../24-analytics-seo-and-growth.md), [SPEC §5](../../SPEC.md)).
### Tests
- [ ] `test_indexed_page_has_as_of_and_not_advice` — each indexed entity page renders the as-of date + not-advice line server-side.
- [ ] `test_scanner_seo_slug_canonical` — `/scanners/momentum-stocks` resolves to a single canonical (301 or `<link rel=canonical>`), never both indexed.
- [ ] Visual regression: stock/sector/scanner SEO page (dark + light).
### Compliance gate
- [ ] No indexed title/H1/meta/body string contains a buy-lean, target, SL, "candidate", or return claim; scanner pages use membership language ([24 §3.2](../24-analytics-seo-and-growth.md), [SPEC §3.3](../../SPEC.md)).
### Acceptance criteria
- [ ] Indexed pages render descriptive EOD content with as-of + not-advice, one canonical per scanner concept, and no RA-gated levels ([24 §3, §5](../24-analytics-seo-and-growth.md)).

---

## Feature: `/learn` educational library + glossary  `(Mode A)`
**Objective:** Build the evergreen, indexed education hub and one-concept-per-page glossary, cross-linked to live data and to the canonical glossary source. · **Backend dep:** `GET /learn`, `GET /learn/{slug}` (CMS/MDX) ([05 §2](../05-information-architecture-and-url-paths.md)). · **Frontend dep:** `ArticleRenderer`, `Toc`, `RelatedArticles`, `LearnIndexGrid` ([05 §2](../05-information-architecture-and-url-paths.md)). · **Data dep:** MDX/CMS content; [29 — Glossary](../29-glossary.md) term definitions.
### Steps
- [ ] 1. Build `/learn` index (`LearnIndexGrid`) and `/learn/[slug]` article pages (SSG) with the seed explainers: `what-is-rsi`, `volume-breakout-meaning`, `how-to-read-moving-averages` — each **defines the concept** and links to the **live** scanner/stock that demonstrates it ([24 §3.1, §3.5](../24-analytics-seo-and-growth.md), [05 §2](../05-information-architecture-and-url-paths.md)).
- [ ] 2. Build **market glossary pages** `/learn/glossary/[term]` (one concept per page, e.g. `rsi`, `delivery-percentage`, `relative-strength`, `50-dma`), each cross-linking to its [29 — Glossary](../29-glossary.md) source-of-truth definition ([24 §3.1, §3.3](../24-analytics-seo-and-growth.md)).
- [ ] 3. Education copy is **educational, never directive**: explains "RSI above 70 indicates elevated short-term conditions" — **never** "buy when RSI is oversold" ([SPEC §5](../../SPEC.md), [04 §4 RSI mode](../04-feature-modules.md)). All copy passes the blocked-phrase guardrail.
- [ ] 4. Carry the not-advice line on any page that references live signals; education pages need no `as_of` (evergreen) but live-data callouts label their as-of.
- [ ] 5. Wire `RelatedArticles` + concept→scanner→stock links to form the **education → live data → education** loop ([24 §3.5](../24-analytics-seo-and-growth.md)).
### Tests
- [ ] `test_learn_pages_render_ssg` — each seed explainer + glossary page builds statically with valid metadata.
- [ ] `test_learn_links_to_live` — each explainer links to its live scanner/stock and to its glossary term.
- [ ] `test_glossary_ties_to_source` — glossary page references the [29](../29-glossary.md) definition.
### Compliance gate
- [ ] Education/glossary copy defines concepts descriptively; no "buy oversold"/"sell overbought" directive framing; no blocked phrases ([SPEC §5](../../SPEC.md), [24 §3.2](../24-analytics-seo-and-growth.md)).
### Acceptance criteria
- [ ] `/learn` + glossary are indexed, evergreen, cross-linked to live pages and the glossary source, and Mode-A clean ([24 §3.1, §3.5](../24-analytics-seo-and-growth.md)).

---

## Feature: Structured data, canonical, sitemaps & internal linking  `(Mode A)`
**Objective:** Emit only allowed JSON-LD, enforce one-canonical-per-concept, split sitemaps to indexed routes, and build dense internal linking. · **Backend dep:** route registry + indexed-route list ([05 §6](../05-information-architecture-and-url-paths.md)). · **Frontend dep:** metadata + JSON-LD components, sitemap generators. · **Data dep:** entity/route catalog.
### Steps
- [ ] 1. **Structured data** ([24 §3.3](../24-analytics-seo-and-growth.md)): stock page → `BreadcrumbList` (+ optional `Dataset` for the EOD series, `Organization` for the issuer); learn/glossary → `Article`/`DefinedTerm` + `DefinedTermSet`, `FAQPage` for Q&A, `BreadcrumbList`; scanner page → `CollectionPage` + `ItemList` (names/links only, neutral membership) + `BreadcrumbList`; sector page → `CollectionPage` + `BreadcrumbList`; site-wide → `WebSite` + `SearchAction`. **Prohibit** `Rating`/`Review`/`AggregateRating`/`Recommendation` and any `price` markup implying a target ([24 §3.3](../24-analytics-seo-and-growth.md)).
- [ ] 2. **Canonical rules** ([24 §3.4](../24-analytics-seo-and-growth.md), [05 §6](../05-information-architecture-and-url-paths.md)): one canonical per concept; scanner SEO-slug vs app-path → pick one, 301 the other; exclude `?sort`/`?filter`/`?page`/`?as_of` from canonical; symbol case/suffix variants 301 to uppercase (`/stocks/tcs` → `/stocks/TCS`); `noindex` on `/login`,`/signup`, all auth/admin; `disallow` `/api/`,`/admin/`.
- [ ] 3. **Split sitemaps** ([05 §6](../05-information-architecture-and-url-paths.md)): `sitemap-static.xml`, `sitemap-stocks.xml`, `sitemap-sectors.xml`, `sitemap-scanners.xml`, `sitemap-learn.xml` indexed by `sitemap.xml`; include **only** `indexed` routes.
- [ ] 4. **Internal linking** ([24 §3.5](../24-analytics-seo-and-growth.md)): every indicator chip on a stock/scanner page deep-links to its glossary page (`RSI` chip → `/learn/glossary/rsi`); stock pages link to their sector page; sector pages link to relevant scanners; explainers link to the live page that demonstrates the concept.
- [ ] 5. **Gated vs public split** ([24 §3.6](../24-analytics-seo-and-growth.md)): public education + today's scanner list + one rate-limited grounded AI summary are crawlable; full filters/history/export and backtesting/strategy-builder are gated **in-route** (no URL split, no cloaking).
- [ ] 6. **CI guardrail over rendered HTML** ([24 §5](../24-analytics-seo-and-growth.md), [25 — QA & release](../25-qa-testing-and-release-process.md)): render each indexed route and run the mirrored blocked-phrase guardrail ([04 `blocked_phrases_export()`](04-ai-explanation-layer.md)); build fails on any hit.
### Tests
- [ ] `test_no_prohibited_jsonld_types` — no `Rating`/`Review`/`Recommendation` JSON-LD on any Mode-A page; allowed types validate.
- [ ] `test_canonical_strips_params` — canonical excludes sort/filter/page/as_of; symbol case 301s to uppercase.
- [ ] `test_sitemaps_indexed_only` — sitemaps contain only `indexed` routes; auth/admin/api absent.
- [ ] `test_html_guardrail_fails_build` — an introduced buy-lean in rendered HTML fails the CI guardrail.
- [ ] `test_indicator_chip_deeplinks_glossary` — an `RSI` chip links to `/learn/glossary/rsi`.
### Compliance gate
- [ ] No prohibited structured-data type; the rendered-HTML guardrail blocks any buy-lean/target/SL/return claim on indexed routes; gating is in-route, not cloaked ([24 §3.3, §3.6, §5](../24-analytics-seo-and-growth.md), [SPEC §6.9](../../SPEC.md)).
### Acceptance criteria
- [ ] Valid allowed JSON-LD, one canonical per concept, indexed-only sitemaps, dense internal linking, and a CI blocked-phrase gate over rendered HTML ([24 §5](../24-analytics-seo-and-growth.md)).

---

## Done-when
- [ ] Indexed entity pages (stock, sector, scanner SEO slugs) render descriptive EOD content with a visible not-advice line + as-of date, and resolve to one canonical per concept ([24 §3, §5](../24-analytics-seo-and-growth.md)).
- [ ] `/learn` + glossary pages are indexed, evergreen, Mode-A-clean, and cross-linked to live data and the [29](../29-glossary.md) source ([24 §3.1, §3.5](../24-analytics-seo-and-growth.md)).
- [ ] Structured data emits only allowed schema.org types (no `Rating`/`Review`/`Recommendation`); canonicals strip params; sitemaps are indexed-only; gating is in-route ([24 §3.3–3.6](../24-analytics-seo-and-growth.md)).
- [ ] The blocked-phrase guardrail runs over rendered HTML of all indexed routes in CI and fails the build on any buy-lean/target/SL/return claim ([24 §5](../24-analytics-seo-and-growth.md), [SPEC §3.3, §6.9](../../SPEC.md)).
- [ ] Internal-linking loops + indicator-chip → glossary deep-links wired; SEO/analytics consistent with [24](../24-analytics-seo-and-growth.md).
