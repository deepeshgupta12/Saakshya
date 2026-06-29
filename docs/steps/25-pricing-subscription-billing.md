# Steps · 25 · Pricing, Subscription & Billing
> Read first: [SPEC.md](../../SPEC.md) (esp. [§11 monetization](../../SPEC.md)) · [Roadmap](../02-product-roadmap.md) · [Feature modules](../04-feature-modules.md) · [Backend architecture](../09-backend-architecture.md) · [API contracts](../10-api-contracts.md) · [Security & auth](../23-security-auth-and-privacy.md) · [Admin panel](../20-admin-panel.md) · [Screens](../08-screen-by-screen-documentation.md)

**Maps to:** Roadmap (Phase 4 — premium tiers) · SPEC Phase 4
**Status:** Not started   |   **Regulatory mode:** A
**Prerequisites:** [07-v2-accounts-watchlist-ai-news.md](07-v2-accounts-watchlist-ai-news.md) (accounts, JWT scopes, `PLAN_REQUIRED` plumbing) · [05-api-and-pipeline.md](05-api-and-pipeline.md) (envelope/caching) · [15-cross-cutting-admin-infra-qa.md](15-cross-cutting-admin-infra-qa.md) (admin config, AI-spend meter)

## Overview
This phase turns the entitlement plumbing built in [07](07-v2-accounts-watchlist-ai-news.md) into a **revenue surface**: the public **pricing page**, the **subscription lifecycle** (subscribe / upgrade / downgrade / cancel), the **billing service** with a **payment-provider integration**, **server-side feature-gating** (entitlements enforced at the gateway, never in the client), **usage metering** for plan limits + the AI-spend meter, and **invoices/transactions**. Tiers are **Free / Premium / Pro / Enterprise** per [SPEC §11](../../SPEC.md) and [04](../04-feature-modules.md).

**Two economics constraints from [SPEC §11](../../SPEC.md) are first-class here, not afterthoughts:**
1. **Data-licensing and AI-generation are recurring per-user costs.** Each tier must be modelled against its marginal cost *before* a price is fixed — a flat Free tier running full-universe daily AI summaries is loss-making at scale without the caching strategy ([SPEC §6.8](../../SPEC.md)). The AI-spend meter ([09 §2.18](../09-backend-architecture.md)) and the regenerate-on-change cache ([04](04-ai-explanation-layer.md)) are the levers that keep the per-user cost inside the tier's margin.
2. **The SEBI per-client fee cap (~₹1.51L/yr/family) applies to any tier operated under RA (Mode B).** v1 ships **Mode A**, so no tier is RA-operated yet — but the billing service ships a **fee-cap guard** so that when an RA-gated tier later lands ([14-v9-advisory-ra-gated.md](14-v9-advisory-ra-gated.md)), its annual per-family price cannot be configured above the cap. The guard is built now, dormant in Mode A, asserted by test.

Billing is **infrastructure, not a content surface** — it emits no market/AI output, so it carries no buy-lean risk; its compliance gate is about **honest pricing, the fee-cap guard, and PII handling of payment references**, not Mode-A language. Plan changes reflect in **JWT scopes on next refresh** ([09 §2.19](../09-backend-architecture.md)); gating is a gateway authz check, never separate URLs.

## Exit gate (Definition of Done)
- [ ] The four tiers (Free/Premium/Pro/Enterprise) are defined as **versioned entitlement config** with explicit per-tier feature + limit sets matching [SPEC §11](../../SPEC.md) and [04](../04-feature-modules.md).
- [ ] Every gated feature is enforced **server-side at the gateway** via `403 PLAN_REQUIRED` carrying `{ required_plan, current_plan }`; no client flag is the only gate ([10 §0.2/§14](../10-api-contracts.md)).
- [ ] Subscribe/upgrade/downgrade/cancel work end-to-end against the payment provider; a plan change reflects in **JWT scopes on the next refresh** ([09 §2.19](../09-backend-architecture.md)).
- [ ] Payment webhooks are verified, idempotent, and reconcile against `billing_transactions`; a replayed webhook is a no-op ([09 §2.19](../09-backend-architecture.md)).
- [ ] Usage metering tracks per-user plan-limit counters and the AI-spend meter; a user at a limit gets `PLAN_REQUIRED`, and the monthly AI ceiling alerts before breach ([09 §2.18](../09-backend-architecture.md), [SPEC §6.8](../../SPEC.md)).
- [ ] Each tier's per-user cost (data-licensing + AI) is modelled and recorded against its price; the Free tier is not loss-making at projected scale given the caching strategy ([SPEC §11, §6.8](../../SPEC.md)).
- [ ] The **fee-cap guard** rejects configuring any RA-operated tier above ~₹1.51L/yr/family; in Mode A no tier is RA-operated, asserted by a contract test ([SPEC §11](../../SPEC.md), [09 §2.19](../09-backend-architecture.md)).
- [ ] Invoices/transactions are retrievable per user, row-scoped; payment tokens/PII never appear in logs ([23 §5](../23-security-auth-and-privacy.md)).

---
## Feature: Tier & entitlement model  `(Mode A)`
**Objective:** Define Free/Premium/Pro/Enterprise as a single, versioned source of truth mapping each tier → the features and numeric limits it unlocks, so both the gateway gate and the pricing page render from one config — never divergent hardcoded lists.
**Backend dep:** entitlement config (versioned, admin-governed like scanner weights), plan→scopes mapping in JWT ([09 §2.19, §3](../09-backend-architecture.md)) · **Frontend dep:** pricing page reads the same config · **Data dep:** `subscriptions` table (current plan/status per user), per-resource `plan` tags ([10 §5](../10-api-contracts.md)).

### Steps
- [ ] 1. Define the entitlement config in `app/billing/entitlements.py` (versioned, mirrored into admin config per [20 §1](../20-admin-panel.md)): for each tier a feature set + numeric limits — **Free** (EOD dashboard, limited scanners, **1** watchlist with item cap, basic AI market summary), **Premium** (full scanners, **unlimited** watchlists, portfolio, AI stock summaries, news sentiment, alerts, sector, peer), **Pro** (Premium + strategy builder, backtesting, thematic baskets, portfolio risk engine, exports, premium briefs), **Enterprise/API** (Pro + API access/keys, seats) — exactly per [SPEC §11](../../SPEC.md) and [04 monetization](../04-feature-modules.md).
- [ ] 2. Map each tier → JWT scopes; on plan change, new scopes take effect on the **next token refresh** (atomic plan change, [09 §2.19](../09-backend-architecture.md)). Access tokens stay short-lived ([23 §1](../23-security-auth-and-privacy.md)) so the lag is bounded.
- [ ] 3. Surface per-resource plan tags so existing list endpoints advertise their required plan (e.g. `GET /api/scanners` returns `plan: "premium"` per item, [10 §5](../10-api-contracts.md)); the client uses these to render upgrade affordances, **never** to enforce.
- [ ] 4. Define the limit-counter contract (watchlists, alerts, AI on-demand calls, exports, API requests) keyed per user per billing window, owned by the `analytics` usage-metering service ([09 §2.18](../09-backend-architecture.md)).
- [ ] 5. Record the **per-user cost model** alongside each tier in the config (data-licensing share + projected AI tokens at the tier's coverage level) so a price change can be checked against margin — the [SPEC §11](../../SPEC.md) "model cost into each tier" requirement made concrete ([SPEC §6.8](../../SPEC.md)).

### Tests
- [ ] Each documented [SPEC §11](../../SPEC.md) feature resolves to exactly one tier in the config; no feature is unreachable or double-mapped.
- [ ] A Free user's JWT carries only Free scopes; after an upgrade + refresh, Premium scopes are present.
- [ ] The pricing page and the gateway gate derive from the **same** config (a config change moves both).

### Compliance gate
- [ ] Pricing copy is descriptive and non-directive — no tier is sold as "AI tells you what to buy"; the value prop is screener/explanation quality ([SPEC §3](../../SPEC.md)).
- [ ] No RA-gated feature (entry/target/SL, candidate layer) is listed as purchasable in any Mode-A tier ([SPEC §4](../../SPEC.md)).

### Acceptance criteria
- [ ] One versioned entitlement config drives both gating and pricing display; plan changes flow to JWT scopes on refresh ([09 §2.19](../09-backend-architecture.md)).

---
## Feature: Pricing page  `(Mode A)`
**Objective:** A public, conversion-oriented pricing page that renders the four tiers, their feature matrix, and current-plan state for signed-in users — honest, non-directive, and driven by the entitlement config.
**Backend dep:** entitlement config read endpoint; `GET /api/billing/subscription` for current plan ([10 §13](../10-api-contracts.md)) · **Frontend dep:** `(marketing)` route group, `PricingTable`, `TierCard`, `FeatureMatrix`, `CurrentPlanBadge`, `UpgradeCta` · **Data dep:** entitlement config + the user's current subscription.

### Steps
- [ ] 1. Build `app/(marketing)/pricing/page.tsx` (SSR, SEO-indexed) composing `src/components/pricing/`: `PricingTable` (four `TierCard`s), `FeatureMatrix` (feature × tier grid from the config), monthly/annual toggle, INR `₹` formatting via `en-IN` ([06 frontend](../06-frontend-architecture.md)).
- [ ] 2. For signed-in users, fetch `GET /api/billing/subscription` and show `CurrentPlanBadge` + contextual CTA (Upgrade / Downgrade / Manage), preserving `?next=` into the auth flow for signed-out visitors.
- [ ] 3. Render the feature matrix from the **shared entitlement config** (single source) so it can never drift from what the gateway actually enforces.
- [ ] 4. Add a clear note that **data-licensing tiers / live data are separately licensed** where relevant ([SPEC §4 live-data row](../../SPEC.md)); do not advertise RA-gated capabilities.
- [ ] 5. States: loading skeleton matching the grid; error fallback; "You're on this plan" disabled state on the current tier.
- [ ] 6. Analytics: `pricing_view`, `tier_card_cta_click{plan}`, `billing_cycle_toggle` ([24 analytics](../24-analytics-seo-and-growth.md)).

### Tests
- [ ] Component: `FeatureMatrix` renders every tier/feature from config; a config edit changes the rendered grid.
- [ ] A signed-in Premium user sees the Premium card as current and Pro as upgradeable.
- [ ] Visual regression: pricing page (dark + light).

### Compliance gate
- [ ] No guarantee/return/urgency copy ("multibagger", "sure-shot", "limited-time guaranteed gains"); blocked-phrase lint passes ([SPEC §3.3](../../SPEC.md), [06 §13](../06-frontend-architecture.md)).
- [ ] Tiers are framed as access to analytics/explanations, never as advice or buy signals ([SPEC §3](../../SPEC.md)).

### Acceptance criteria
- [ ] Pricing renders the four tiers from config with honest, non-directive copy and correct current-plan state.

---
## Feature: Billing service & payment-provider integration  `(Mode A)`
**Objective:** The subscription lifecycle backend — subscribe/cancel, payment-provider integration behind an adapter, verified idempotent webhooks, invoices/transactions — with the SEBI fee-cap guard wired in (dormant in Mode A).
**Backend dep:** `billing` service ([09 §2.19](../09-backend-architecture.md)), payment-provider adapter, webhook verifier, `subscriptions` + `billing_transactions` stores, Secrets-Manager-held provider keys · **Frontend dep:** checkout/manage screens, `PaymentForm` (provider SDK), `BillingSettings` · **Data dep:** `subscriptions` (plan, status, renews_at), `billing_transactions` (amount, currency, status, at).

### Steps
- [ ] 1. Create the billing data model in `app/storage/migrations/`: `subscriptions` (user_id, plan, status `active|canceled`, `renews_at`, `active_until`, provider_ref) and `billing_transactions` (id, user_id, amount, currency `INR`, status `paid|failed`, provider_txn_ref, `at`) per [09 §2.19](../09-backend-architecture.md), [10 §13](../10-api-contracts.md).
- [ ] 2. Build a **payment-provider adapter** in `app/billing/provider.py` (the provider is abstracted in [09 §2.19](../09-backend-architecture.md)/[10 §13](../10-api-contracts.md) — a `tok_…` payment token, no vendor named; pick one with INR + UPI/cards support and log the choice in [30 decision log](../30-decision-log.md)). Business logic never depends on the vendor — same pattern as the `DataSource` adapter ([SPEC §8](../../SPEC.md)).
- [ ] 3. Implement the Billing API in `app/api/routes/billing.py` **exactly** per [10 §13](../10-api-contracts.md): `GET /api/billing/subscription`, `POST /api/billing/subscribe` (`{ plan, payment_token }` → `402-style PAYMENT_FAILED` on decline, `409` on conflict), `POST /api/billing/cancel` (returns `status: "canceled"`, `active_until`), `GET /api/billing/transactions`. All Bearer-auth, row-scoped.
- [ ] 4. Implement the **webhook handler** for asynchronous provider events (payment succeeded/failed, renewal, chargeback): **signature-verified**, **idempotent** (provider event id dedup), reconciling into `billing_transactions`; a replayed webhook is a no-op ([09 §2.19 acceptance](../09-backend-architecture.md)).
- [ ] 5. On a successful subscribe/upgrade/cancel, update `subscriptions` **atomically** and invalidate cached plan state so the **next JWT refresh** carries the new scopes ([09 §2.19](../09-backend-architecture.md)).
- [ ] 6. Implement the **fee-cap guard** in `app/billing/fee_cap.py`: any tier flagged RA-operated (Mode B) **cannot** be configured with an annual per-family price above the SEBI cap (~₹1.51L/yr/family). In Mode A no tier is RA-operated, so the guard is dormant but present and tested ([SPEC §11, §2](../../SPEC.md)).
- [ ] 7. Hold all provider secrets (API key, webhook signing secret) in Secrets Manager, never in code/images/logs; redact `payment_token`/PII at log-write ([23 §3, §5](../23-security-auth-and-privacy.md)).
- [ ] 8. Generate retrievable **invoices** from `billing_transactions` (downloadable PDF/line items) for the billing settings screen; local-first this service is a **no-op (single user)** per [09 §6](../09-backend-architecture.md).

### Tests
- [ ] `POST /api/billing/subscribe` with a declining token returns `PAYMENT_FAILED`; no `subscriptions` row is flipped to active.
- [ ] A duplicate (replayed) provider webhook does not double-charge or double-credit — idempotency-key dedup holds.
- [ ] Cancel sets `status: "canceled"` + `active_until` = end of paid period; access persists until `active_until`, then downgrades.
- [ ] Fee-cap guard rejects an RA-operated tier priced above ~₹1.51L/yr/family; in Mode A, a contract test asserts **no** tier is RA-operated.
- [ ] A user cannot read another user's `subscription`/`transactions` (row-scope/IDOR, [23 §2](../23-security-auth-and-privacy.md)).
- [ ] No payment token or PII appears in application logs (log-redaction test, [23 §5](../23-security-auth-and-privacy.md)).

### Compliance gate
- [ ] The fee-cap guard exists and is enforced for any RA-operated tier; v1 ships Mode A with no RA-operated tier ([SPEC §11, §2](../../SPEC.md)).
- [ ] Payment references are PII-class: encrypted/row-scoped, never logged in plaintext ([23 §5–6](../23-security-auth-and-privacy.md)).

### Acceptance criteria
- [ ] Subscription lifecycle is atomic and provider-reconciled; webhooks are verified + idempotent; fee-cap guard is wired and tested ([09 §2.19](../09-backend-architecture.md)).

---
## Feature: Server-side feature-gating (entitlement enforcement)  `(Mode A)`
**Objective:** Enforce every plan limit at the gateway — returning `PLAN_REQUIRED` with an upgrade hint — so no entitlement is bypassable from the client. This is the non-negotiable from the brief: **feature-gating/entitlements enforced server-side.**
**Backend dep:** gateway plan-gate ([09 §3 "Plan-based access"](../09-backend-architecture.md)), `can(actor, action, resource)` authz with plan check ([23 §2](../23-security-auth-and-privacy.md)), entitlement config · **Frontend dep:** `UpgradeGate` component that catches `PLAN_REQUIRED` and renders an upgrade prompt · **Data dep:** JWT plan/scopes + limit counters.

### Steps
- [ ] 1. Implement the gateway plan-gate per [09 §3](../09-backend-architecture.md): resolve the feature's required plan from the entitlement config, compare against the JWT `plan`/scopes, and return `403 PLAN_REQUIRED` with `details: { required_plan, current_plan }` on a miss ([10 §0.2](../10-api-contracts.md)). Gating is **inside routes**, never separate URLs ([23 §2](../23-security-auth-and-privacy.md)).
- [ ] 2. Enforce **numeric limits** (watchlist count, alert count, on-demand AI calls, exports, API rate) by reading the per-user plan-limit counters ([09 §2.18](../09-backend-architecture.md)); at-limit returns `PLAN_REQUIRED`, not a silent allow.
- [ ] 3. Make the gate **fail-closed**: an unknown/absent plan resolves to Free; a config lookup failure denies the higher-tier feature rather than leaking it.
- [ ] 4. Build the frontend `UpgradeGate` (in `src/components/billing/`): catch `PLAN_REQUIRED` envelopes, render a muted upgrade card with the `required_plan`, deep-link to `/pricing?next=…`. The client **never** decides entitlement — it only reacts to the server's answer.
- [ ] 5. Add a contract test asserting that for every gated endpoint, a Free token receives `PLAN_REQUIRED` and a correctly-scoped token receives `200` — driven from the entitlement config so new gated features are auto-covered.

### Tests
- [ ] Free user hitting a Premium scanner / a 2nd watchlist / a Pro export gets `PLAN_REQUIRED` (not a silent allow); Premium/Pro do not ([10 §14](../10-api-contracts.md)).
- [ ] Tampering with a client flag does not unlock a gated endpoint — the gateway still returns `PLAN_REQUIRED` (no client-side bypass).
- [ ] Fail-closed: a forced entitlement-config lookup error denies the higher-tier feature.
- [ ] Hitting a numeric limit (e.g. alert cap) returns `PLAN_REQUIRED` with the right `required_plan`.

### Compliance gate
- [ ] Gating is an authz check, not URL-based; no gated market/AI content leaks to an under-entitled user ([23 §2](../23-security-auth-and-privacy.md)).

### Acceptance criteria
- [ ] All plan limits are enforced server-side at the gateway with `PLAN_REQUIRED`; the client cannot bypass any entitlement ([10 §14](../10-api-contracts.md)).

---
## Feature: Usage metering & AI-spend meter  `(Mode A)`
**Objective:** Meter per-user usage for plan-limit enforcement and feed the AI-spend meter, so plan counters are accurate within the billing window and the monthly AI ceiling alerts before breach with graceful degradation.
**Backend dep:** `analytics` usage-metering service ([09 §2.18](../09-backend-architecture.md)), `usage_events` store, Redis counters, AI-spend meter ([SPEC §6.8](../../SPEC.md)) · **Frontend dep:** `UsageMeter` in billing settings (e.g. "watchlists 1/1", "on-demand AI 18/20") · **Data dep:** `usage_events`, AI token telemetry from the AI layer.

### Steps
- [ ] 1. Emit `usage_events` from gated actions (watchlist create, alert create, on-demand AI summary, export, API call) into the `analytics` service ([09 §2.18](../09-backend-architecture.md)).
- [ ] 2. Maintain **per-user plan-limit counters** in Redis keyed to the billing window; the gateway gate reads these for numeric-limit enforcement ([09 §2.18 acceptance](../09-backend-architecture.md)).
- [ ] 3. Wire the **AI-spend meter**: record AI token usage per generation; aggregate to a monthly spend metric; **alert before the monthly ceiling** and trigger documented graceful degradation (serve cache / non-AI fallback) per [SPEC §6.8](../../SPEC.md) and [04 AI cost](04-ai-explanation-layer.md).
- [ ] 4. Tie per-tier AI coverage to the cost model: full daily coverage for watched subsets vs on-demand+cached for the long tail, so a tier's projected AI spend stays inside its margin ([SPEC §6.8, §11](../../SPEC.md)).
- [ ] 5. Build `UsageMeter` in billing settings showing the user their counters vs limits with an upgrade affordance when near a cap.

### Tests
- [ ] Plan-limit counters are accurate within the billing window (create N watchlists → counter reads N; cap hit blocks the N+1).
- [ ] The AI-spend meter alerts **before** the monthly ceiling; degradation serves cache/non-AI fallback, never a fabricated AI output ([04](04-ai-explanation-layer.md)).
- [ ] Per-tier projected AI cost is recorded and the Free tier is not loss-making at projected scale given caching ([SPEC §11, §6.8](../../SPEC.md)).

### Compliance gate
- [ ] Degradation never substitutes a guessed/fabricated AI value — it serves cache or the non-AI fallback (suppress-don't-guess, [SPEC §6.2](../../SPEC.md)).
- [ ] Usage telemetry is privacy-respecting; no portfolio/PII leaks into analytics beyond product need ([23 §5](../23-security-auth-and-privacy.md)).

### Acceptance criteria
- [ ] Plan counters accurate within the billing window; AI-spend meter alerts before the ceiling with documented graceful degradation ([09 §2.18](../09-backend-architecture.md), [SPEC §6.8](../../SPEC.md)).

---
## Feature: Upgrade / downgrade & invoices (billing settings)  `(Mode A)`
**Objective:** Self-serve plan changes (with proration semantics) and an invoice/transaction history in account settings, row-scoped and PII-safe.
**Backend dep:** billing service (subscribe/cancel), proration logic, invoice generation · **Frontend dep:** `BillingSettings`, `PlanChangeDialog`, `InvoiceList` (in the account surfaces from [24-account-surfaces.md](24-account-surfaces.md)) · **Data dep:** `subscriptions`, `billing_transactions`.

### Steps
- [ ] 1. Implement upgrade/downgrade through the billing service: upgrade takes effect immediately (new scopes on next refresh); downgrade at period end (`active_until`), with documented proration ([09 §2.19](../09-backend-architecture.md)).
- [ ] 2. Render `BillingSettings` in the account area ([24-account-surfaces.md](24-account-surfaces.md)): current plan, renewal date, payment method (provider-managed, no PAN/card stored locally), `PlanChangeDialog`, `InvoiceList` from `GET /api/billing/transactions`.
- [ ] 3. Make invoices downloadable (line items, GST-aware where applicable — confirm tax handling, not computed as advice); link each to its `billing_transactions` row.
- [ ] 4. On downgrade, enforce that over-limit resources (e.g. extra watchlists on Free) are handled gracefully — read-only/archived, never silently deleted; surface the consequence in `PlanChangeDialog`.
- [ ] 5. Analytics: `upgrade_start{from,to}`, `downgrade_confirm`, `invoice_download` ([24 analytics](../24-analytics-seo-and-growth.md)).

### Tests
- [ ] Upgrade reflects on next refresh; downgrade applies at `active_until` and over-limit resources are archived, not destroyed.
- [ ] `InvoiceList` renders the user's own transactions only (row-scope, [23 §2](../23-security-auth-and-privacy.md)).
- [ ] No card/PAN data is stored locally; only a provider reference (PII handling, [23 §5](../23-security-auth-and-privacy.md)).

### Compliance gate
- [ ] No card/sensitive payment data stored beyond the provider reference; invoices/PII row-scoped and redacted from logs ([23 §5–6](../23-security-auth-and-privacy.md)).

### Acceptance criteria
- [ ] Users can self-serve upgrade/downgrade with correct proration and retrieve their own invoices; downgrades never destroy data silently.

---
## Done-when
- [ ] All six features pass their tests, compliance gates, and acceptance criteria; the Exit gate checklist is fully checked.
- [ ] The four tiers are driven by one versioned entitlement config; every gated feature is enforced **server-side at the gateway** with `PLAN_REQUIRED`; no client bypass exists.
- [ ] Subscribe/upgrade/downgrade/cancel are atomic and provider-reconciled; webhooks are verified + idempotent; plan changes flow to JWT scopes on refresh.
- [ ] Each tier's per-user cost (data-licensing + AI) is modelled into its price; the Free tier is not loss-making at projected scale given the caching strategy ([SPEC §11, §6.8](../../SPEC.md)).
- [ ] The SEBI fee-cap guard (~₹1.51L/yr/family) is wired and tested for any RA-operated tier; v1 ships Mode A with no RA-operated tier ([SPEC §11, §2](../../SPEC.md)).
- [ ] Payment references/invoices are PII-class — encrypted, row-scoped, never logged in plaintext ([23 §5–6](../23-security-auth-and-privacy.md)).
