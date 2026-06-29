# Steps · 19 · Thematic baskets
> Read first: [SPEC.md](../../SPEC.md) (§7.20 thematic baskets — **bucket views, not model portfolios**; §3/§5 Mode-A language; §4) · [Roadmap](../02-product-roadmap.md) (V3 / Phase 3) · [Feature modules](../04-feature-modules.md) (§9) · [Scanner engine](../13-scanner-engine-and-scoring.md) (§4.7 sector strength) · [API contracts](../10-api-contracts.md) · [Screens](../08-screen-by-screen-documentation.md) (§7 theme basket page)

**Maps to:** Roadmap **V3** · SPEC Phase 3 · **Status:** Not started · **Regulatory mode:** A
**Prerequisites:** [02-indicators-and-scanners.md](02-indicators-and-scanners.md) (indicators) · [16-scanners-extended.md](16-scanners-extended.md) (sector-strength scanner / breadth) · [04-ai-explanation-layer.md](04-ai-explanation-layer.md) (grounded AI, guardrails) · [05-api-and-pipeline.md](05-api-and-pipeline.md) · [06-frontend-foundation-and-v1-screens.md](06-frontend-foundation-and-v1-screens.md). News drivers from [07-v2-accounts-watchlist-ai-news.md](07-v2-accounts-watchlist-ai-news.md).

## Overview
Curated thematic baskets give users a **bucket view** into a theme (power, defence, railways, PSU banks, private banks, IT, pharma, realty, capital goods, consumption, renewables, EV, electronics, infra) with aggregate descriptive technicals, theme momentum/breadth, risk context, and AI-summarized news drivers.

**The single non-negotiable rule: a thematic basket is a bucket VIEW, NOT a model portfolio** ([SPEC §7.20, §4](../../SPEC.md), [docs/04 §9](../04-feature-modules.md), [docs/08 §7](../08-screen-by-screen-documentation.md)). It carries **no weights, no allocations, no "recommended portfolio", no returns implying a portfolio recommendation**. Membership is a curated descriptive list; aggregate stats are simple descriptive roll-ups (e.g. "% of constituents above their 50-DMA"), never a weighted basket return presented as a strategy. Every basket page renders a prominent disclaimer banner: *"This is a bucket view for research, not a recommended portfolio."*

This phase adds: **basket definitions + membership** (theme→symbol, versioned, curated), a **theme aggregation engine** (theme momentum, breadth, risk context, news drivers — reusing the sector-strength/indicator layer), a **grounded AI theme summary**, and the **basket list + detail UI** with the disclaimer banner. Membership and aggregates are as-of versioned and reproducible.

## Exit gate (Definition of Done)
- [ ] Baskets are **bucket views**: no per-constituent weight, no allocation, no basket "return" framed as a portfolio outcome; the disclaimer banner is present on every basket surface ([SPEC §7.20](../../SPEC.md), [docs/08 §7](../08-screen-by-screen-documentation.md)).
- [ ] Theme membership is curated, **versioned** (theme→symbol mapping in config), and as-of versioned; constituents pass the eligibility gate or are marked, never silently dropped/fabricated ([docs/13 §3.1](../13-scanner-engine-and-scoring.md)).
- [ ] Aggregate stats (theme momentum, breadth, risk context) are **descriptive roll-ups reproducible** from as-of versioned adjusted inputs; a constituent gap is excluded from breadth, never counted ([SPEC §6.1–6.2](../../SPEC.md)).
- [ ] The AI theme summary references **only** the grounded payload; it describes the theme + news drivers, never "buy the theme"/"allocate"/return claim ([SPEC §3.3, §5](../../SPEC.md), [docs/13 §6](../13-scanner-engine-and-scoring.md)).
- [ ] The basket UI (list + detail) shows constituents + aggregate descriptive stats with **no allocation/weight column, no "invest in this basket" CTA**; disclaimer banner prominent; follow action allowed.
- [ ] An acceptance test asserts **no basket response or surface contains weights/allocations/returns implying a portfolio recommendation** ([docs/08 §7](../08-screen-by-screen-documentation.md)).

---
## Feature: Basket definitions & membership  `(Mode A)`
**Objective:** Curated, versioned theme→symbol definitions (power, defence, railways, PSU/private banks, IT, pharma, realty, capital goods, consumption, renewables, EV, electronics, infra) with as-of versioned membership — a bucket view, not a portfolio. · **Backend dep:** classification master, eligibility gate ([16](16-scanners-extended.md)) · **Frontend dep:** none · **Data dep:** theme→symbol mapping, listing status
### Steps
- [ ] 1. `app/baskets/definitions.py` + versioned config: define each theme with `slug`, display name, description, and curated constituent symbol list (theme→symbol). Mapping lives in **versioned config**, not code; a `definitionVersion` is stamped into every result. **No weight field exists on a constituent** — membership only.
- [ ] 2. `app/baskets/membership.py`: resolve constituents for the as-of date; apply the eligibility gate ([docs/13 §3.1](../13-scanner-engine-and-scoring.md)) — a delisted/quarantined constituent is **marked** (status), never silently dropped or replaced; carry `as_of_version`.
- [ ] 3. Persist basket membership as-of versioned so a basket as-of a past date is reproducible; a constituent leaving/entering the theme is a new `definitionVersion`.
### Tests
- [ ] `tests/baskets/test_membership.py`: each seeded theme resolves its curated constituents; a quarantined/delisted constituent is marked not silently dropped; `definitionVersion` + `as_of_version` stamped; **no weight/allocation field on any constituent** (schema assertion).
### Compliance gate
- [ ] Definitions are bucket views — membership only, no weights/allocations; theme list is curated and versioned, not a "recommended set" ([SPEC §7.20](../../SPEC.md), [docs/04 §9](../04-feature-modules.md)).
### Acceptance criteria
- [ ] Versioned curated membership reproducible as-of; constituents eligibility-marked; no weight field anywhere.

---
## Feature: Theme aggregation engine (momentum, breadth, risk, news drivers)  `(Mode A)`
**Objective:** Compute descriptive aggregate stats for a theme — theme momentum, breadth, risk context, and surfaced news drivers — reusing the sector-strength/indicator layer; never a weighted basket return. · **Backend dep:** indicators ([02](02-indicators-and-scanners.md)), sector-strength/breadth ([16](16-scanners-extended.md)), news sentiment/impact ([07](07-v2-accounts-watchlist-ai-news.md)) · **Frontend dep:** none · **Data dep:** constituent adjusted OHLCV, SMAs, ATR%, news sentiment, corp-action master
### Steps
- [ ] 1. `app/baskets/aggregate.py`: compute descriptive roll-ups — `breadth_pct = count(constituent.close > constituent.sma50) / count(eligible constituents)`; theme momentum as the **median (or mean) of constituent relative strength** (an unweighted descriptive average, explicitly **not** a portfolio return); risk context (share of constituents with `ELEVATED_VOLATILITY`/breakdown flags). Reuse the sector-strength breadth logic from [16](16-scanners-extended.md).
- [ ] 2. A constituent with a data gap is **excluded from the breadth denominator**, never counted as below-MA; mark the aggregate `data_confidence` accordingly ([SPEC §6.2](../../SPEC.md)).
- [ ] 3. `app/baskets/drivers.py`: surface the top **news drivers** for the theme — above-threshold, entity-resolved news on constituents (with source + timestamp), grouped to the theme; no fabricated or unresolved items ([07](07-v2-accounts-watchlist-ai-news.md)).
- [ ] 4. Build the basket aggregate record `{ slug, asOfDate, definitionVersion, breadth_pct, theme_momentum_descriptive, risk_context, constituents:[{symbol, change_pct_20d, rsi_14, above_50dma, riskFlags}], news_drivers:[{symbol, headline, source, ts, sentiment}], data_confidence }`; stamp `as_of_version`. **No weighted return field.**
### Tests
- [ ] `tests/baskets/test_aggregate.py` (**critical-logic, golden**): `breadth_pct`, theme momentum, and risk context reproduce on a committed multi-constituent fixture; a gapped constituent is excluded from breadth, never counted below-MA; **no weighted-return field exists** (assertion).
- [ ] `tests/baskets/test_drivers.py`: only above-threshold, entity-resolved news appears, each with source + timestamp; no unresolved/fabricated driver.
### Compliance gate
- [ ] Aggregates are descriptive roll-ups; theme momentum is an explicit descriptive average, never a portfolio return; no allocation implied ([SPEC §7.20](../../SPEC.md)).
### Acceptance criteria
- [ ] Roll-ups reproducible from as-of versioned inputs; breadth excludes gaps; news drivers resolved + sourced; no weighted return.

---
## Feature: AI theme summary  `(Mode A)`
**Objective:** A grounded, runtime-verified summary describing the theme's recent technical character and news drivers — descriptive, never "buy the theme"/"allocate". · **Backend dep:** grounded payload builder, theme summary agent ([04](04-ai-explanation-layer.md)), runtime verifier, guardrail filter, audit log · **Frontend dep:** theme summary card on the basket detail page · **Data dep:** the basket aggregate record (facts only)
### Steps
- [ ] 1. `app/baskets/summary_payload.py`: build the facts-only payload from the aggregate record — breadth, theme momentum (descriptive), risk context, and the surfaced news drivers (source + ts). The agent may reference **nothing else** ([docs/13 §6](../13-scanner-engine-and-scoring.md)).
- [ ] 2. Generate via the theme summary agent ([04](04-ai-explanation-layer.md)): descriptive only — "the power theme shows broad participation, with 68% of constituents above their 50-DMA; recent drivers include …". Prohibited: "buy the theme", "allocate", "this basket is a good portfolio", any return claim.
- [ ] 3. Runtime-verify every number against the payload (block/regenerate on mismatch); run the blocked-phrase guardrail at output time; write the generation to the AI audit log; suppress the summary when aggregate `data_confidence: LOW`.
### Tests
- [ ] `tests/baskets/test_summary.py`: a fabricated figure is blocked by the verifier; injecting "buy the theme"/"allocate"/"portfolio" is caught by the guardrail; LOW-confidence aggregate suppresses the summary; every generation writes an audit row.
### Compliance gate
- [ ] Descriptive theme summary only; passes the Compliance Review path before display; no "buy the theme"/"allocate"/portfolio framing / always-prohibited phrase ([SPEC §3.3, §5](../../SPEC.md)).
### Acceptance criteria
- [ ] Every figure traces to the payload; descriptive not directive; carries an `audit_id` + as-of date.

---
## Feature: Basket API + UI (list, detail, disclaimer)  `(Mode A)`
**Objective:** Serve baskets and render the list + detail with the prominent bucket-view disclaimer and no portfolio affordance. · **Backend dep:** definitions, aggregation, theme summary · **Frontend dep:** `ThemeBasketList`, `ThemeHeader`, `ThemeDisclaimerBanner`, `ThemeConstituentTable`, aggregate stats card ([docs/08 §7](../08-screen-by-screen-documentation.md)) · **Data dep:** basket aggregate record
### Steps
- [ ] 1. Implement `GET /api/themes` (list) and `GET /api/themes/{slug}` + `GET /api/themes/{slug}/constituents` in `app/api/routes/themes.py` per [docs/10](../10-api-contracts.md) (group `thematic` per the dashboard params). Responses carry membership + descriptive aggregates + drivers; **no weight/allocation field**.
- [ ] 2. Build the basket **list** page and the **detail** page (`/themes/[theme-slug]`, public/ISR per [docs/08 §7](../08-screen-by-screen-documentation.md)): `ThemeHeader`, prominent `ThemeDisclaimerBanner` ("This is a bucket view for research, not a recommended portfolio"), `ThemeConstituentTable` (constituents + per-constituent descriptive stats, **no weight/allocation column**), aggregate descriptive stats, the AI theme summary. CTAs: open constituent, add constituent(s) to watchlist, **follow theme** — **no "invest in this basket"/"buy the basket" CTA**.
- [ ] 3. Emit analytics `basket_view`/`theme_view{slug}`, `basket_follow`, `theme_constituent_open`, `theme_watchlist_add` ([docs/04 §9](../04-feature-modules.md), [docs/08 §7](../08-screen-by-screen-documentation.md)); show as-of date + confidence badge.
### Tests
- [ ] `tests/api/test_themes_contract.py`: list/detail/constituents endpoints match the documented shapes; **no response contains a weight/allocation/portfolio-return field** (contract assertion).
- [ ] `tests/baskets/test_ui_disclaimer.py` (or component test): the disclaimer banner is present on every basket surface; no weight/allocation column; no "invest in this basket"/"buy" CTA; follow + watchlist-add CTAs present.
### Compliance gate
- [ ] Disclaimer banner present everywhere; no weights/allocations/returns implying a portfolio recommendation; no "invest in"/"buy the basket" affordance ([docs/08 §7](../08-screen-by-screen-documentation.md), [SPEC §7.20](../../SPEC.md)).
### Acceptance criteria
- [ ] List + detail render constituents + descriptive aggregates with the disclaimer; no portfolio affordance; follow/watchlist actions work.

---
## Done-when
- [ ] Baskets are bucket views: versioned curated membership, no weights/allocations, no portfolio-return framing; the disclaimer banner is present on every surface ([SPEC §7.20](../../SPEC.md), [docs/08 §7](../08-screen-by-screen-documentation.md)).
- [ ] Aggregate stats (momentum, breadth, risk, news drivers) reproduce from as-of versioned adjusted inputs; breadth excludes gapped constituents; drivers are resolved + sourced ([SPEC §6.1–6.2](../../SPEC.md)).
- [ ] The AI theme summary is grounded, runtime-verified, descriptive not directive, audit-logged ([docs/13 §6](../13-scanner-engine-and-scoring.md)).
- [ ] No basket API response or UI surface contains weights/allocations/returns implying a portfolio recommendation, or any always-prohibited phrase — asserted by tests ([SPEC §3.3, §7.20](../../SPEC.md)).
