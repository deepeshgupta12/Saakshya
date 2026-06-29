# Steps · 28 · Personalization
> Read first: [SPEC.md](../../SPEC.md) (esp. [§7 personalization vs compliance](../../SPEC.md)) · [Roadmap](../02-product-roadmap.md) (V3+) · [Feature modules](../04-feature-modules.md) · [Backend architecture](../09-backend-architecture.md) (Account & Preferences) · [Compliance, risk & guardrails](../21-compliance-risk-and-guardrails.md) · [Account surfaces](24-account-surfaces.md) · [V9 advisory (RA-gated)](14-v9-advisory-ra-gated.md)

**Maps to:** Roadmap **V3+** · SPEC Phase 3 (+ Phase 5 gated)
**Status:** Not started   |   **Regulatory mode:** A (+ C gated)
**Prerequisites:** [07-v2-accounts-watchlist-ai-news.md](07-v2-accounts-watchlist-ai-news.md) (auth, RBAC + row-scoping, `consents`, `user_preferences`, follows/watchlist) · [24-account-surfaces.md](24-account-surfaces.md) (preferences UI, followed sectors/instruments, risk preference, consent surfaces)

## Overview
Personalization on Saakshya splits into **two clearly separated tiers**, and the line between them is the **single non-negotiable compliance boundary** of this step ([SPEC §7](../../SPEC.md), [docs/04 §1](../04-feature-modules.md), [docs/09](../09-backend-architecture.md)):

- **Tier 1 — Mode A navigation personalization (build now).** Personalize the **navigation** experience: layout, which followed sectors/instruments surface first, default scanner filters seeded from the user's **stated** risk preference, and prioritization of relevant **educational** content. This personalizes **how the user moves through the product**, **not what they should buy**. It is **transparent and user-editable**, and stores **no per-stock behavioural buy-leans** ([SPEC §7 "Allowed in Mode A"](../../SPEC.md), [docs/09](../09-backend-architecture.md)).
- **Tier 2 — Mode C advisory personalization (GATED — do NOT build until IA registration is in force).** Per-stock behavioural nudges ("because you view banking, consider HDFC Bank") and personalized allocation / model portfolios. Nudging a specific user toward specific securities based on behaviour is **Investment Adviser (Mode C)** territory ([SPEC §7 "Not allowed in Mode A"](../../SPEC.md), [SPEC 5.30](../../SPEC.md), [SPEC §2 Mode C](../../SPEC.md)). **Not built, not surfaced, not stubbed in a reachable path** until IA registration is live.

> **The one rule.** Personalize **navigation, not recommendations.** Behaviour-derived per-stock suggestions are Mode C and are out until IA is in force. Keep the line **explicit in design review** so it does not creep across releases ([SPEC §7](../../SPEC.md), [docs/21 compliance](../21-compliance-risk-and-guardrails.md), [14-v9-advisory-ra-gated.md](14-v9-advisory-ra-gated.md)).

## Exit gate (Definition of Done)
- [ ] Tier 1 personalizes **layout, followed sectors/instruments ordering, default scanner filters (from stated risk preference), and educational-content priority** — and nothing else ([SPEC §7](../../SPEC.md)).
- [ ] Every personalization input is **user-visible and user-editable**; the user can see "why am I seeing this" and reset it ([SPEC §7](../../SPEC.md), [docs/04 §1](../04-feature-modules.md)).
- [ ] `user_preferences` stores **no per-stock behavioural buy-lean**; a contract test asserts the personalization payload exposes no security-level recommendation field ([docs/09](../09-backend-architecture.md), [SPEC §7](../../SPEC.md)).
- [ ] **Tier 2 (Mode C) is unreachable in Mode A:** behaviour-derived per-stock suggestions and personalized allocation are behind an `iaRegistered` mode flag that is **off**, hard-excludes any such object from every response, and is covered by a contract test ([SPEC §2](../../SPEC.md), [SPEC §7](../../SPEC.md), [docs/21](../21-compliance-risk-and-guardrails.md), [14-v9-advisory-ra-gated.md](14-v9-advisory-ra-gated.md)).

---
## Feature: Tier 1 — Navigation personalization (layout + follows)  `(Mode A)`
**Objective:** Personalize the home/dashboard layout and surface the sectors/instruments the user already **follows**, ordered by their stated preferences — navigation only, never a per-stock buy-lean. · **Backend dep:** Account & Preferences service (`user_preferences`, follows/watchlist from [07](07-v2-accounts-watchlist-ai-news.md)), row-scoping/RBAC · **Frontend dep:** personalized dashboard / `(app)` home, preferences UI from [24](24-account-surfaces.md) · **Data dep:** followed sectors/instruments, watchlist, stock/sector master.
### Steps
- [ ] 1. Extend `user_preferences` (from [07](07-v2-accounts-watchlist-ai-news.md)) with **navigation-only** personalization fields: `dashboard_layout`, `pinned_sections`, `followed_sectors[]`, `followed_instruments[]` ordering — **no security-level recommendation field** ([docs/09](../09-backend-architecture.md), [SPEC §7](../../SPEC.md)).
- [ ] 2. Personalize the dashboard server-side: order modules/sections by the user's pins + follows; surface followed sectors/instruments first. The output is a **layout/ordering**, not a ranked "what to buy".
- [ ] 3. Provide a "why am I seeing this" affordance per personalized section (e.g. "because you follow Banking") and a one-click **reset to default**; every personalization input is editable from the preferences screen ([24](24-account-surfaces.md)).
- [ ] 4. `GET /api/personalization/dashboard` returns the personalized **layout descriptor** (section order + follows), never a per-stock suggestion list; premium-gated as applicable.
### Tests
- [ ] A user who follows Banking sees the Banking sector surfaced first; a user with no follows gets the default layout.
- [ ] The personalization response contains **no** security-level recommendation/buy-lean field (contract test).
- [ ] A user cannot read another user's preferences/layout (row-scope/IDOR test).
### Compliance gate
- [ ] Personalizes **navigation, not recommendations**; no "because you view X, consider Y" anywhere; copy reviewed against the blocked-phrase list ([SPEC §7](../../SPEC.md), [docs/21](../21-compliance-risk-and-guardrails.md)).
### Acceptance criteria
- [ ] Layout + follows are personalized, transparent, and user-editable; nothing implies a per-stock action ([SPEC §7](../../SPEC.md)).

---
## Feature: Tier 1 — Default scanner filters from stated risk preference  `(Mode A)`
**Objective:** Seed scanner/screener default filters from the user's **explicitly stated** risk preference (e.g. conservative → large-cap, lower-volatility defaults) — a default the user can change, not a recommendation. · **Backend dep:** Account & Preferences (`risk_preference`), scanner/screener engine · **Frontend dep:** scanner screen default-filter state, preferences UI · **Data dep:** stated `risk_preference`, scanner filter schema.
### Steps
- [ ] 1. Read the **stated** `risk_preference` (set by the user in preferences, never inferred from behaviour) and map it to **default** scanner filter values (market-cap band, volatility caps) via versioned config.
- [ ] 2. Apply the mapping as the **initial** filter state only; the user can override every filter freely — the preference is a starting point, not a lock.
- [ ] 3. Show "defaults from your risk preference (editable)" so the basis is transparent; changing filters does not silently rewrite the stored preference.
### Tests
- [ ] A conservative stated preference seeds the documented default filters; a user override is honored and persists for the session.
- [ ] `risk_preference` is sourced from the user's stated value, not derived from view/click behaviour (asserted: no behavioural inference writes it).
### Compliance gate
- [ ] Defaults are a transparent, user-editable **filter seed**, never a per-stock recommendation; output is a **list**, not a call ([SPEC §7](../../SPEC.md), [SPEC §2 Mode A](../../SPEC.md)).
### Acceptance criteria
- [ ] Scanner defaults reflect the stated risk preference and remain fully editable; no buy-lean introduced.

---
## Feature: Tier 1 — Educational-content prioritization  `(Mode A)`
**Objective:** Prioritize relevant **educational** content (learn/SEO articles, explainers) based on followed sectors and stated interests — educational relevance, not security advice. · **Backend dep:** content catalog + tagging, Account & Preferences · **Frontend dep:** learn/home content rails · **Data dep:** content tags, followed sectors/topics.
### Steps
- [ ] 1. Tag educational content by sector/topic and rank it for the user by overlap with followed sectors / stated interests.
- [ ] 2. Surface prioritized **educational** items in the learn rails; keep content descriptive/educational — never a per-stock call dressed as an article.
- [ ] 3. Keep prioritization transparent ("relevant to sectors you follow") and resettable.
### Tests
- [ ] Educational items matching followed sectors rank higher; with no follows, default ordering applies.
- [ ] Prioritized content carries no per-stock buy/sell directive (guardrail-style assertion).
### Compliance gate
- [ ] Prioritizes **educational** content only; no behaviour-derived security suggestion ([SPEC §7](../../SPEC.md), [docs/21](../21-compliance-risk-and-guardrails.md)).
### Acceptance criteria
- [ ] Education is personalized by relevance, transparent and editable; no recommendation surface introduced.

---
## Feature: Tier 2 — Advisory personalization  `(Mode C — GATED, do NOT build until IA registration is in force)`
**Objective:** Per-stock behavioural nudges and personalized allocation / model portfolios. **This is Investment-Adviser (Mode C) territory and MUST NOT be built, surfaced, or placed in any reachable Mode-A path until IA registration is live.** Documented here for forward-compatibility and to keep the boundary explicit. · **Backend dep:** (gated) `iaRegistered` mode flag hard-excluding all Mode-C objects · **Frontend dep:** none in Mode A · **Data dep:** none consumed in Mode A.

> **🚫 GATE — UNMISSABLE.** Behaviour-derived per-stock suggestions ("because you view banking, **consider HDFC Bank**") and personalized allocation / model portfolios are **Mode C (Registered Investment Adviser)** ([SPEC §2 Mode C](../../SPEC.md), [SPEC 5.30](../../SPEC.md), [SPEC §7 "Not allowed in Mode A"](../../SPEC.md)). **Disclaimers do not cure advisory substance** — a feature ships **only when the regulatory mode it requires is in force** ([SPEC §0 mode-wins rule](../../SPEC.md)). **Do NOT build, stub-in-a-reachable-path, or surface this until IA registration is live.** See [docs/09 §9 (preferences MUST NOT store per-stock behavioural buy-leans)](../09-backend-architecture.md), [docs/21 compliance](../21-compliance-risk-and-guardrails.md), [docs/04](../04-feature-modules.md), and the advisory build itself in [14-v9-advisory-ra-gated.md](14-v9-advisory-ra-gated.md).

### Steps
- [ ] 1. **Do NOT implement in this phase.** Define only the **gate**: an `iaRegistered` mode flag (default **off**) that **hard-excludes** any per-stock behavioural suggestion or personalized-allocation object from **every** response. Persisting per-stock behavioural buy-leans in `user_preferences` is explicitly prohibited ([docs/09](../09-backend-architecture.md), [SPEC §7](../../SPEC.md)).
- [ ] 2. Behaviour signals (views/clicks) may inform **navigation** ordering only (Tier 1) — they may **never** be turned into a per-security suggestion in Mode A.
- [ ] 3. When IA registration is later in force, this feature is built under the advisory step ([14-v9-advisory-ra-gated.md](14-v9-advisory-ra-gated.md)) with the full Mode-C controls — **not here**.
### Tests
- [ ] In Mode A (`iaRegistered` off), **no** response contains a per-stock behavioural suggestion or personalized-allocation object — contract test asserts absence ([SPEC §7](../../SPEC.md), [14-v9-advisory-ra-gated.md](14-v9-advisory-ra-gated.md)).
- [ ] `user_preferences` rejects/omits any per-stock behavioural buy-lean field ([docs/09](../09-backend-architecture.md)).
### Compliance gate
- [ ] Mode-C personalization is **unreachable** in Mode A (flag off + contract test); building it locally before IA is explicitly out of scope ([SPEC §2](../../SPEC.md), [SPEC §7](../../SPEC.md), [docs/21](../21-compliance-risk-and-guardrails.md)).
### Acceptance criteria
- [ ] No behaviour-derived per-stock suggestion or personalized allocation exists in any Mode-A surface; the gate is enforced by flag + contract test.

---
## Done-when
- [ ] Tier 1 personalizes **layout, followed sectors/instruments, default scanner filters (from stated risk preference), and educational content** — transparent and user-editable throughout ([SPEC §7](../../SPEC.md)).
- [ ] No personalization surface or stored preference contains a per-stock behavioural buy-lean; a contract test proves the personalization payload exposes no security-level recommendation field ([docs/09](../09-backend-architecture.md), [SPEC §7](../../SPEC.md)).
- [ ] **Tier 2 (Mode C) advisory personalization remains explicitly deferred until IA registration is in force**, is gated `off`, hard-excluded from every Mode-A response, and built only under [14-v9-advisory-ra-gated.md](14-v9-advisory-ra-gated.md) ([SPEC §2](../../SPEC.md), [SPEC §7](../../SPEC.md), [docs/21](../21-compliance-risk-and-guardrails.md), [docs/04](../04-feature-modules.md)).
- [ ] The Mode-A / Mode-C personalization line is documented and kept **explicit in design review** so it does not creep across releases ([SPEC §7](../../SPEC.md)).
