# Steps · 14 · V9 — Advisory, Technical Levels & Recommendations (RA-GATED)
> Read first: [SPEC.md](../../SPEC.md) (§0 precedence, §2 modes, §3.2 RA-gated prohibitions, §4 rows 5.21/5.22, §6.7 AI-use disclosure, §10 Phase 5) · [Roadmap](../02-product-roadmap.md) (§12 V9, §13 the RA-gated layer) · [Compliance & guardrails](../21-compliance-risk-and-guardrails.md) (§1 modes, §3 prohibited phrases, §7 recommendation rules, §13 SEBI context) · [AI/LLM agent architecture](../14-ai-llm-agent-architecture.md) (§11 AI-use disclosure) · [Security, auth & privacy](../23-security-auth-and-privacy.md)

**Maps to:** Roadmap V9 · SPEC Phase 5 · SPEC §4 rows **5.21** (technical levels) and **5.22** (candidate layer)
**Status:** Not started — GATED (the hardest gate in the product)   |   **Regulatory mode:** **B (RA)** for stock-specific recommendations & technical levels; **C (IA)** for personalized advice / model portfolios
**Gate (must be met before ANY of these features ship — disclaimers do NOT cure substance):**
> **RA registration must be IN FORCE.** Specifically: **NISM Series-XV certification** obtained; **RAASB enlistment via BSE** complete; **FD lien** scaled to client count posted; **record-keeping** system live; a **formal research report behind each recommendation**; **mandatory AI-use disclosure** live in onboarding + terms ([SPEC §6.7](../../SPEC.md)); **counsel sign-off** on the recommendation product. For **personalized allocation / model portfolios**, **IA (Mode C) registration in force** in addition. Until then these features **MUST NOT ship — a "not investment advice" disclaimer does not cure advisory substance** ([SPEC §0](../../SPEC.md), [compliance §8](../21-compliance-risk-and-guardrails.md)).
**Prerequisites:** RA filing track started in [00-phase-0-derisk.md](00-phase-0-derisk.md) and now **completed and in force**; the AI platform ([11-v6-agentic-workflows.md](11-v6-agentic-workflows.md)) with output-time guardrails, grounding, and audit; the admin/compliance console with feature flags and four-eyes ([compliance §10.2](../21-compliance-risk-and-guardrails.md)).

## Overview
This is **the file that unlocks the RA-gated features deferred throughout the product** — the single biggest divergence from the original Saakshya vision ([SPEC §4](../../SPEC.md), [Roadmap §13](../02-product-roadmap.md)):

- **Per-stock technical entry / target / stop-loss / invalidation LEVELS** (SPEC **5.21**) — advisory-in-substance, RA-only.
- **The "candidate" / recommendation layer** (SPEC **5.22**) — a label that functions as a buy-lean is advisory-in-substance, RA-only.
- **Model portfolios** — personalized allocation, **IA (Mode C)**-only.
- **Personalized advisory** ("given your portfolio, do X") — **IA (Mode C)**-only.

These were **deliberately deferred to Phase 5 and re-worded to neutral, descriptive forms throughout v1** ([SPEC §5](../../SPEC.md), [compliance §5](../21-compliance-risk-and-guardrails.md)). **They are not built early "just to see them"** ([SPEC §12](../../SPEC.md)) — building them unregistered creates the exact substance-over-form exposure SEBI examines ([compliance §13 Dec-2025 substance-over-form order](../21-compliance-risk-and-guardrails.md)).

**This file is "what to enable + the controls required once registered," not a license to build early.** Every step below is contingent on the gate above. The deliverable is a registered, controlled, auditable recommendation capability behind a feature flag that **cannot be enabled until RA (and, for personalization, IA) is in force**.

## Exit gate (Definition of Done)
- [ ] **RA registration in force** (NISM Series-XV, RAASB enlistment, FD lien, record-keeping) verified by counsel before the flag can be enabled ([SPEC §2](../../SPEC.md), [compliance §1](../21-compliance-risk-and-guardrails.md)).
- [ ] **Mandatory AI-use disclosure** is live in onboarding + terms; the audit log is the evidence trail ([SPEC §6.7](../../SPEC.md), [docs/14 §11](../14-ai-llm-agent-architecture.md)).
- [ ] Every recommendation is backed by a **formal research report** with **named-analyst sign-off** and is **record-kept** ([compliance §1 Mode B](../21-compliance-risk-and-guardrails.md)).
- [ ] Technical levels (5.21) and the recommendation layer (5.22) ship **only behind a Phase-5 feature flag** that is OFF until RA is confirmed in force ([compliance §1 gating principle](../21-compliance-risk-and-guardrails.md)).
- [ ] **Tier-1 always-prohibited phrases remain blocked** even under RA (guarantee, assured, sure-shot, risk-free, multibagger, "buy now", "best stock for you") ([SPEC §3.3](../../SPEC.md), [compliance §3.1](../21-compliance-risk-and-guardrails.md)).
- [ ] **Model portfolios / personalized advice ship only with IA (Mode C) in force**; otherwise they stay out ([SPEC §4](../../SPEC.md), [Roadmap §12](../02-product-roadmap.md)).
- [ ] **SEBI fee cap (~₹1.51L/yr/family)** respected wherever RA applies ([SPEC §11](../../SPEC.md)).
- [ ] Counsel sign-off + registration status logged ([decision log](../30-decision-log.md)).

---
## Feature: Registration & disclosure gate (must clear before anything)  `(Mode B gate)`
**Objective:** Verify RA is in force and the mandatory disclosure + record-keeping obligations are live before any RA-gated feature can be enabled ([SPEC §2, §6.7](../../SPEC.md), [compliance §1](../21-compliance-risk-and-guardrails.md)). · **Backend dep:** feature-flag system, onboarding/terms, audit log · **Frontend dep:** disclosure surfaces · **Data dep:** none.
### Steps
- [ ] 1. **Owner: Founder/Legal.** Confirm and document RA **in force**: NISM Series-XV cert, RAASB enlistment via BSE, FD lien scaled to client count, record-keeping system ([compliance §1 Mode B](../21-compliance-risk-and-guardrails.md)). **Artifact:** counsel-verified registration pack.
- [ ] 2. **Owner: Compliance/Eng.** Make the **AI-use disclosure** live in onboarding + terms — disclosed to clients, with the registered analyst remaining fully responsible for AI-assisted output ([SPEC §6.7](../../SPEC.md), [docs/14 §11](../14-ai-llm-agent-architecture.md)). **Artifact:** disclosure copy + onboarding flow.
- [ ] 3. **Owner: Eng.** Implement the **RA feature flag** governing every 5.21/5.22 surface; it is OFF by default and can only be turned on with a recorded counsel confirmation ([compliance §1 gating principle](../21-compliance-risk-and-guardrails.md)).
- [ ] 4. **Owner: Compliance.** Structure RA-operated tiers to respect the **fee cap (~₹1.51L/yr/family)** ([SPEC §11](../../SPEC.md)).
- [ ] 5. **Owner: Founder.** Log registration status + counsel sign-off ([decision log](../30-decision-log.md)).
### Tests / Compliance gate / Acceptance criteria
- [ ] The RA feature flag **cannot be enabled** without a recorded counsel confirmation that RA is in force (enforced + tested).
- [ ] AI-use disclosure is presented at onboarding and recorded; the audit log captures AI involvement per generation ([docs/14 §7, §11](../14-ai-llm-agent-architecture.md)).
- [ ] **Compliance gate:** with the flag OFF, no 5.21/5.22 surface exists in the router ([compliance §1](../21-compliance-risk-and-guardrails.md)).

---
## Feature: Per-stock technical levels — entry / target / stop-loss / invalidation (5.21)  `(Mode B — RA only)`
**Objective:** Enable per-stock technical **levels** — the directive output deferred throughout v1 — only under RA, each backed by a formal research report and analyst sign-off ([SPEC §4 row 5.21](../../SPEC.md), [Roadmap §13](../02-product-roadmap.md)). · **Backend dep:** RA flag, research-report store, sign-off workflow, output guardrails, audit · **Frontend dep:** level display behind the RA flag · **Data dep:** validated indicators + the research-report record.
### Steps
- [ ] 1. **Gate:** build/enable only with the RA flag ON (registration in force). Until then these levels **do not exist** in the product ([SPEC §3.2](../../SPEC.md), [compliance §3.2](../21-compliance-risk-and-guardrails.md)).
- [ ] 2. Require a **formal research report behind each level set** (entry/target/stop/invalidation), with **named-analyst sign-off** and record-keeping ([compliance §1 Mode B](../21-compliance-risk-and-guardrails.md)).
- [ ] 3. Re-enable the Tier-2 vocabulary **only under RA**: "entry zone / target zone / stop-loss zone / invalidation zone" move from blocked to permitted **in Mode B context only**, still subject to Tier-1 floor ([compliance §3.1–3.2](../21-compliance-risk-and-guardrails.md)).
- [ ] 4. Keep **Tier-1 always-prohibited** language blocked even here (no "guaranteed target", "assured", "sure-shot") ([SPEC §3.3](../../SPEC.md), [compliance §3.1](../21-compliance-risk-and-guardrails.md)).
- [ ] 5. Any AI-assisted level narration still passes **grounding + output-time guardrails + compliance review**, and the AI-use disclosure applies ([docs/14 §6, §11](../14-ai-llm-agent-architecture.md), [compliance §9](../21-compliance-risk-and-guardrails.md)).
- [ ] 6. Record-keep every published level set (report, analyst, timestamp, rationale) for SEBI defensibility ([compliance §10](../21-compliance-risk-and-guardrails.md)).
### Tests / Compliance gate / Acceptance criteria
- [ ] With the RA flag OFF, no entry/target/stop/invalidation surface is reachable (router + guardrail test) ([compliance §1](../21-compliance-risk-and-guardrails.md)).
- [ ] Every published level set has a linked formal research report + analyst sign-off + record-keeping entry ([compliance §1 Mode B](../21-compliance-risk-and-guardrails.md)).
- [ ] Tier-1 phrases remain blocked under RA ([SPEC §3.3](../../SPEC.md)).

---
## Feature: The "candidate" / recommendation layer (5.22)  `(Mode B — RA only)`
**Objective:** Enable the recommendation layer — where "candidate" may legitimately function as a buy-lean — only under RA, replacing the v1 neutral scanner-membership framing ([SPEC §4 row 5.22](../../SPEC.md), [compliance §5.1](../21-compliance-risk-and-guardrails.md)). · **Backend dep:** RA flag, research-report store, sign-off, guardrails, audit · **Frontend dep:** recommendation surfaces behind the RA flag · **Data dep:** research report per recommendation.
### Steps
- [ ] 1. **Gate:** enable only with the RA flag ON. In Mode A, "candidate" stays **scanner-membership-only**; the buy-lean sense is unlocked **only** under RA ([compliance §5.1](../21-compliance-risk-and-guardrails.md)).
- [ ] 2. Each recommendation (and any ranked actionable list / "what to buy" framing) requires a **formal research report + analyst sign-off + record-keeping** ([compliance §1 Mode B, §7](../21-compliance-risk-and-guardrails.md)).
- [ ] 3. Update the **compliance rule manager** so the "candidate"-proximity rule and the Tier-2 list switch to RA-mode behavior **only when the flag is ON** ([compliance §5.1, §9](../21-compliance-risk-and-guardrails.md)).
- [ ] 4. Keep the **descriptive Mode-A path intact** for non-RA contexts/tiers; the recommendation layer is additive, not a replacement of the neutral path ([SPEC §5](../../SPEC.md)).
- [ ] 5. All recommendation text passes grounding + output-time guardrails + compliance review; AI-use disclosure applies ([docs/14 §6, §11](../14-ai-llm-agent-architecture.md)).
### Tests / Compliance gate / Acceptance criteria
- [ ] With the flag OFF, "candidate" near buy-lean signals is still `block`ed (Mode-A behavior preserved) ([compliance §5.1](../21-compliance-risk-and-guardrails.md)).
- [ ] Every recommendation/ranked pick has a linked research report + sign-off + record-keeping ([compliance §1, §7](../21-compliance-risk-and-guardrails.md)).
- [ ] Tier-1 floor still enforced under RA ([compliance §3.1](../21-compliance-risk-and-guardrails.md)).

---
## Feature: Model portfolios  `(Mode C — IA only)`
**Objective:** Enable model portfolios — personalized allocation — **only** with IA (Mode C) registration in force; otherwise out ([SPEC §4](../../SPEC.md), [Roadmap §12](../02-product-roadmap.md)). · **Backend dep:** separate IA flag, IA record-keeping · **Frontend dep:** model-portfolio surfaces behind the IA flag · **Data dep:** per-client/portfolio context (IA scope).
### Steps
- [ ] 1. **Gate:** require **IA (Mode C) registration in force** — RA alone is insufficient for personalized allocation ([SPEC §2, §4](../../SPEC.md), [compliance §1 Mode C](../21-compliance-risk-and-guardrails.md)).
- [ ] 2. Until IA is in force, keep thematic **baskets as bucket views, not model portfolios** ([SPEC §4 thematic row](../../SPEC.md)); the boundary stays explicit in design review ([compliance §12](../21-compliance-risk-and-guardrails.md)).
- [ ] 3. When unblocked: apply IA-specific record-keeping, disclosure, and suitability obligations (counsel-defined) behind a **separate IA feature flag**.
### Tests / Compliance gate / Acceptance criteria
- [ ] With IA not in force, no model-portfolio surface exists; baskets remain bucket views only ([SPEC §4](../../SPEC.md)).
- [ ] Model portfolios require the IA flag, which is gated on counsel-verified IA registration.

---
## Feature: Personalized advisory  `(Mode C — IA only)`
**Objective:** Enable per-user, client-specific advice ("given your portfolio, do X") **only** under IA; until then, personalization stays navigation-only ([SPEC §7](../../SPEC.md), [compliance §1.1](../21-compliance-risk-and-guardrails.md)). · **Backend dep:** IA flag, suitability/record-keeping · **Frontend dep:** advisory surfaces behind IA flag · **Data dep:** per-user portfolio + suitability profile (IA scope).
### Steps
- [ ] 1. **Gate:** require **IA (Mode C) in force**. Behaviour-derived per-stock suggestions ("because you view banking, consider HDFC Bank") are Mode C and **out** until then ([SPEC §3.2, §7](../../SPEC.md), [compliance §1.1](../21-compliance-risk-and-guardrails.md)).
- [ ] 2. Until IA is in force, keep personalization **navigation-only** (layout, followed sectors, default filters) — never per-stock behaviour-derived suggestions ([SPEC §7](../../SPEC.md), [compliance §1.1](../21-compliance-risk-and-guardrails.md)).
- [ ] 3. When unblocked: apply IA suitability assessment, disclosure, and record-keeping (counsel-defined).
### Tests / Compliance gate / Acceptance criteria
- [ ] With IA not in force, no per-stock personalized suggestion is produced; personalization is navigation-only (design-review item 8) ([compliance §12](../21-compliance-risk-and-guardrails.md)).
- [ ] Personalized advice requires the IA flag, gated on counsel-verified IA registration.

---
## Feature: RA/IA record-keeping, disclosure & four-eyes controls  `(Mode B/C infrastructure)`
**Objective:** The controls that must be live once registered — formal research reports, analyst sign-off, record-keeping, AI-use disclosure, fee-cap structuring, four-eyes on recommendation changes ([compliance §1, §10](../21-compliance-risk-and-guardrails.md), [SPEC §6.7](../../SPEC.md)). · **Backend dep:** research-report store, audit log, four-eyes workflow · **Frontend dep:** disclosure + report surfaces · **Data dep:** none.
### Steps
- [ ] 1. **Formal research report** stored and linked to every recommendation/level set, with **named-analyst sign-off** ([compliance §1 Mode B](../21-compliance-risk-and-guardrails.md)).
- [ ] 2. **Record-keeping**: immutable, exportable trail of every recommendation, report, analyst, and disclosure for SEBI review ([compliance §10](../21-compliance-risk-and-guardrails.md)).
- [ ] 3. **AI-use disclosure** maintained and versioned; the AI audit log is the evidence trail ([SPEC §6.7](../../SPEC.md), [docs/14 §7, §11](../14-ai-llm-agent-architecture.md)).
- [ ] 4. **Four-eyes** on recommendation/level/prompt changes (author ≠ approver; self-approval rejected) ([compliance §10.2](../21-compliance-risk-and-guardrails.md)).
- [ ] 5. **Fee-cap** structuring (~₹1.51L/yr/family) for RA-operated tiers ([SPEC §11](../../SPEC.md)).
### Tests / Compliance gate / Acceptance criteria
- [ ] No recommendation/level publishes without a linked signed-off research report + record-keeping entry ([compliance §1](../21-compliance-risk-and-guardrails.md)).
- [ ] Author == approver rejected on recommendation/level/prompt publish (`self_approval_forbidden`) ([compliance §10.2](../21-compliance-risk-and-guardrails.md)).
- [ ] AI-use disclosure present and audited; fee-cap respected where RA applies ([SPEC §6.7, §11](../../SPEC.md)).

---
## Done-when
- [ ] **RA registration verified in force by counsel**, the RA feature flag is enableable only on that recorded confirmation, and **AI-use disclosure is live** ([SPEC §2, §6.7](../../SPEC.md), [compliance §1](../21-compliance-risk-and-guardrails.md)).
- [ ] Per-stock technical levels (5.21) and the recommendation/"candidate" layer (5.22) ship **only** behind that flag, each backed by a **formal signed-off research report** and record-kept ([SPEC §4](../../SPEC.md), [compliance §1, §7](../21-compliance-risk-and-guardrails.md)).
- [ ] **Tier-1 always-prohibited phrases stay blocked even under RA**; disclaimers are never treated as curing substance ([SPEC §3.3, §0](../../SPEC.md), [compliance §3.1, §8](../21-compliance-risk-and-guardrails.md)).
- [ ] **Model portfolios and personalized advice ship only with IA (Mode C) in force**; otherwise they remain out and personalization stays navigation-only ([SPEC §4, §7](../../SPEC.md)).
- [ ] Record-keeping, four-eyes, and fee-cap controls are live; registration status + counsel sign-off logged ([compliance §10](../21-compliance-risk-and-guardrails.md), [decision log](../30-decision-log.md)).
