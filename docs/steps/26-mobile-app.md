# Steps · 26 · Mobile App
> Read first: [SPEC.md](../../SPEC.md) · [Roadmap](../02-product-roadmap.md) · [Feature modules](../04-feature-modules.md) · [Backend architecture](../09-backend-architecture.md) · [API contracts](../10-api-contracts.md) · [Alerts & notifications](../17-alerts-and-notifications.md) · [Security & auth](../23-security-auth-and-privacy.md) · [Screens](../08-screen-by-screen-documentation.md) · [Decision log](../30-decision-log.md)

**Maps to:** Roadmap V5 (Phase 4) · SPEC Phase 4
**Status:** Not started   |   **Regulatory mode:** A
**Prerequisites:** [07-v2-accounts-watchlist-ai-news.md](07-v2-accounts-watchlist-ai-news.md) (auth, watchlist, AI summary/brief) · [08-v3-portfolio-risk-alerts.md](08-v3-portfolio-risk-alerts.md) (portfolio, alerts) · [24-account-surfaces.md](24-account-surfaces.md) (notification center, account management) · [25-pricing-subscription-billing.md](25-pricing-subscription-billing.md) (entitlements/gating)

## Overview
The native mobile app, landing in **Phase 4 / V5** alongside premium tiers ([02 §2](../02-product-roadmap.md)). Its scope is deliberately **focused** per the brief: **alerts, watchlist, portfolio, the daily brief, and the stock page** — the surfaces a user checks on the go. It is **not** a port of the full web app; deep research, scanner-building, backtesting, and admin stay web-only.

**The app is a thin client over the same backend.** It consumes the **same versioned gateway** (`/api/v1`, JWT auth, plan-gating with `PLAN_REQUIRED`, the standard `data`/`meta`/`error` envelope with `as_of` + `data_confidence`) that the web app uses ([09 §3](../09-backend-architecture.md), [10 §0](../10-api-contracts.md)) — no mobile-specific market/AI logic, no client-side financial computation. Every **Mode-A constraint carries over unchanged**: no entry/target/SL, no buy-leans, no ranked "what to buy"; AI text is display-only, pre-verified, grounding-badged + not-advice; RA-gated slots render the same gated-placeholder; the build-time blocked-phrase guard runs on the mobile codebase too ([SPEC §3](../../SPEC.md), [06 §13](../06-frontend-architecture.md)).

> **Two decisions this file makes explicit (neither is fixed in [09](../09-backend-architecture.md) — log both in [30](../30-decision-log.md)):** (1) the **cross-platform framework** — **React Native or Flutter** — chosen for a single codebase across iOS/Android sharing the one backend; (2) **push** via **FCM** (Firebase Cloud Messaging) as the concrete realization of the abstract "push provider" in the notification service ([09 §2.15](../09-backend-architecture.md), [17 §6](../17-alerts-and-notifications.md)). Pick one framework, confirm FCM (APNs is reached via FCM on iOS), and record the rationale.

## Exit gate (Definition of Done)
- [ ] One cross-platform framework (React Native **or** Flutter) is chosen, with the decision + rationale logged in [30](../30-decision-log.md); a single codebase targets iOS + Android.
- [ ] The app consumes the **same `/api/v1` gateway** with JWT auth, plan-gating (`PLAN_REQUIRED`), and the `data`/`meta`/`error` envelope; **no** mobile-specific market/AI computation exists ([09 §3](../09-backend-architecture.md), [10 §0](../10-api-contracts.md)).
- [ ] The five scoped surfaces render: **alerts inbox, watchlist, portfolio, daily brief, stock page** — each with loading/error/empty/suppressed states and the not-advice banner.
- [ ] Push notifications via **FCM** deliver alerts/briefs; in-app inbox remains the source of truth even if push fails; quiet hours honored ([17 §6](../17-alerts-and-notifications.md)).
- [ ] Tokens are stored in platform **secure storage** (Keychain/Keystore), never plaintext; refresh rotation + reuse detection carry over ([23 §1, §4](../23-security-auth-and-privacy.md)).
- [ ] **No** entry/target/SL, buy-lean, ranked "what to buy", or any always-prohibited phrase appears; AI text is grounding-badged + not-advice; RA-gated slots render the gated placeholder ([SPEC §3](../../SPEC.md)).
- [ ] Plan limits are enforced **server-side** — the app reacts to `PLAN_REQUIRED` with an upgrade prompt, it never grants entitlement client-side ([25-pricing-subscription-billing.md](25-pricing-subscription-billing.md)).
- [ ] Biometric login is deferred behind a flag (later), and its absence does not block the EOD-aligned shipping scope.

---
## Feature: Mobile shell, framework & shared API client  `(Mode A)`
**Objective:** Stand up the cross-platform app shell (navigation, theme tokens, providers) and a typed API client that talks to the **same gateway** as web — thin client, no financial computation.
**Backend dep:** existing `/api/v1` gateway, JWT auth, envelope/caching ([09 §3](../09-backend-architecture.md), [10 §0](../10-api-contracts.md)) · **Frontend dep:** framework choice (RN/Flutter), shared query/cache layer, design tokens mirrored from [07](../07-design-system-and-ui-ux.md) · **Data dep:** the same payloads the web client consumes.

### Steps
- [ ] 1. Choose **React Native or Flutter** for a single iOS/Android codebase sharing the one backend; record the decision + rationale in [30](../30-decision-log.md) (neither is pre-fixed in [09](../09-backend-architecture.md)).
- [ ] 2. Scaffold the app with bottom-tab navigation for the five scoped surfaces (Alerts, Watchlist, Portfolio, Brief, Stock/Search), an auth stack, and providers (query cache, theme).
- [ ] 3. Mirror the design tokens + semantic colors from [07](../07-design-system-and-ui-ux.md) (descriptive bullish/bearish, market color always paired with a non-color signal; reduce-motion respected) so the app shares the web visual language.
- [ ] 4. Build a **typed API client** against `/api/v1` ([10](../10-api-contracts.md)): standard envelope (`data`/`meta.as_of`/`meta.data_confidence`/`error`); invalid shapes surface an error state, never render unvalidated data; **no client-side derivation** of indicators/scores ([06 §4–§5](../06-frontend-architecture.md)).
- [ ] 5. Handle the auth lifecycle: login/refresh against `POST /api/auth/login` / `/refresh`; attach the Bearer token; on `PLAN_REQUIRED` show an upgrade prompt (gating stays server-side) ([10 §1, §0.2](../10-api-contracts.md)).
- [ ] 6. Port the compliance wrappers: a persistent `NotAdviceBanner` on data/AI surfaces, a `GroundingBadge` on AI text, an RA-gated placeholder (never an empty target/SL widget) ([06 §3](../06-frontend-architecture.md)).
- [ ] 7. Mirror the **blocked-phrase guard** into the mobile build so any advisory string fails CI, same as web ([06 §13](../06-frontend-architecture.md), [SPEC §6.9](../../SPEC.md)).

### Tests
- [ ] The app renders each scoped surface against fixture payloads; an envelope missing `meta.as_of` surfaces an error state, never unvalidated data.
- [ ] No mobile module computes an indicator/score/signal locally (lint/architecture check).
- [ ] A `PLAN_REQUIRED` response renders an upgrade prompt, not the gated content.
- [ ] The blocked-phrase guard fails the mobile build on an introduced advisory string.

### Compliance gate
- [ ] No client-side financial computation; the app renders API payloads only and traces figures to evidence ([06 §0, §13](../06-frontend-architecture.md)).
- [ ] Compliance wrappers (not-advice, grounding badge, RA-gated placeholder) present on every relevant surface ([SPEC §3](../../SPEC.md)).

### Acceptance criteria
- [ ] A thin cross-platform shell consumes the shared `/api/v1` gateway with the standard envelope, auth, and server-side gating ([09 §3](../09-backend-architecture.md), [10 §0](../10-api-contracts.md)).

---
## Feature: Scoped surfaces — alerts, watchlist, portfolio, brief, stock page  `(Mode A)`
**Objective:** Build the five focused mobile surfaces, each reusing existing backend endpoints and carrying the same Mode-A constraints as their web counterparts.
**Backend dep:** `GET /me/notifications` + alerts ([24-account-surfaces.md](24-account-surfaces.md), [10 alerts](../10-api-contracts.md)); `/api/watchlists` ([07](07-v2-accounts-watchlist-ai-news.md)); `/api/portfolio/*` ([08-v3-portfolio-risk-alerts.md](08-v3-portfolio-risk-alerts.md)); `GET /api/ai/market-brief`; `GET /api/stocks/{symbol}/overview` + `/ai-summary` · **Frontend dep:** mobile lists/cards/sheets, the stock page's evidence drawer as a bottom sheet · **Data dep:** the same EOD/T+1 payloads web uses.

### Steps
- [ ] 1. **Alerts inbox:** render the in-app notification center ([24-account-surfaces.md](24-account-surfaces.md)) with read/unread, type filter, and event-reporting language only ("TCS entered the momentum scanner") — never "buy at open" ([17 §1–2](../17-alerts-and-notifications.md)).
- [ ] 2. **Watchlist:** multiple lists (tier-capped via server gating), per-item EOD change/score/scanner-membership tags/risk flag — membership language, never a per-user buy-lean ([07 watchlist](07-v2-accounts-watchlist-ai-news.md)).
- [ ] 3. **Portfolio:** holdings, P&L (the user's own data, not a return claim), sector allocation, the portfolio health score with its drivers — **factual event reporting only**, no "sell"/"rebalance" CTA; SL/target monitoring is RA-gated and absent ([08-v3-portfolio-risk-alerts.md](08-v3-portfolio-risk-alerts.md), [SPEC §3.2](../../SPEC.md)).
- [ ] 4. **Daily brief:** the descriptive, event-reporting brief (`GET /api/ai/market-brief`) with followed-sectors emphasis (navigation personalization only), evidence drill-in, and not-advice; never a ranked "what to buy" ([07 brief](07-v2-accounts-watchlist-ai-news.md)).
- [ ] 5. **Stock page:** facts, chart, indicators (value + state), scanner memberships, descriptive S/R (historical framing), grounded AI summary with grounding badge + "View evidence" bottom sheet, risk badge — **no entry/target/SL** (gated placeholder); suppressed state on `422 DATA_SUPPRESSED` ([06 stock screen](06-frontend-foundation-and-v1-screens.md), [SPEC §6.6](../../SPEC.md)).
- [ ] 6. Each surface implements loading/error/empty/**suppressed** states and the not-advice banner; charts plot pre-computed API series only ([06 §8](../06-frontend-architecture.md)).
- [ ] 7. Analytics parity: `mobile_alerts_view`, `mobile_watchlist_view`, `mobile_portfolio_view`, `mobile_brief_view`, `mobile_stock_view{symbol}`, `mobile_ai_evidence_open` ([24 analytics](../24-analytics-seo-and-growth.md)).

### Tests
- [ ] Each surface renders its web-equivalent payload correctly with all four states; a suppressed AI payload shows the suppressed state, never a guessed value.
- [ ] The stock surface contains **no** entry/target/SL element in the view tree; the AI summary shows a grounding badge.
- [ ] Portfolio shows factual events only — no "sell"/"reduce"/"book profit" copy (blocked-phrase check).
- [ ] A user sees only their own watchlist/portfolio/alerts (row-scope, [23 §2](../23-security-auth-and-privacy.md)).

### Compliance gate
- [ ] Every surface inherits its web counterpart's Mode-A posture: membership/event-reporting/descriptive language, grounded-or-suppressed AI, no buy-lean/target/SL ([SPEC §3, §5](../../SPEC.md)).
- [ ] Personalization (followed-sector emphasis) is navigation-only, never per-stock suggestions ([SPEC §7](../../SPEC.md)).

### Acceptance criteria
- [ ] The five scoped surfaces render from shared endpoints with full states and Mode-A-safe content; no entry/target/SL anywhere ([SPEC §3.2](../../SPEC.md)).

---
## Feature: Push notifications (FCM)  `(Mode A)`
**Objective:** Deliver alerts and the daily brief to the device via FCM, with the in-app inbox as the source of truth, quiet hours honored, and event-reporting content only.
**Backend dep:** notification service ([09 §2.15](../09-backend-architecture.md)) with FCM as the push provider; device-token registry; per-channel prefs + quiet hours ([17 §5–6](../17-alerts-and-notifications.md)) · **Frontend dep:** FCM SDK integration, permission prompt, deep-link routing · **Data dep:** `notifications` store, device tokens, alert/brief payloads.

### Steps
- [ ] 1. Integrate the **FCM SDK** in the app; request notification permission contextually (after the user creates a first alert, not on cold start); register the **device token** to the backend, scoped to the user.
- [ ] 2. Add a device-token registry + send path in the notification service so push is delivered via **FCM** (the concrete "push provider" behind [09 §2.15](../09-backend-architecture.md)); APNs on iOS is reached through FCM.
- [ ] 3. Keep **in-app as the source of truth**: every alert/brief lands in the inbox even if push fails ([17 §6](../17-alerts-and-notifications.md)); push is best-effort with at-least-once + idempotency at the service ([09 §2.15](../09-backend-architecture.md)).
- [ ] 4. Honor **quiet hours** and per-channel prefs ([24-account-surfaces.md](24-account-surfaces.md), [17 §5](../17-alerts-and-notifications.md)): no push during quiet hours; queue to the next window.
- [ ] 5. Push payloads carry **event-reporting** copy only ("TATAMOTORS closed below its 50-DMA") — the blocked-phrase validator runs on push templates at output time, same as in-app/email ([17 §2](../17-alerts-and-notifications.md), [SPEC §6.9](../../SPEC.md)).
- [ ] 6. Tapping a push **deep-links** to the relevant surface (alert → stock/scanner, brief → brief screen) and marks the inbox item handled.
- [ ] 7. On logout/account deletion, **unregister the device token** so a deleted user receives no push ([23 §5](../23-security-auth-and-privacy.md)).

### Tests
- [ ] An alert/brief delivers via FCM **and** lands in the in-app inbox; with push simulated as failing, the inbox still receives it ([17 §6](../17-alerts-and-notifications.md)).
- [ ] Quiet hours suppress push and queue to the next window ([17 §5](../17-alerts-and-notifications.md)).
- [ ] A push template containing a directive phrase is blocked at output time ([SPEC §6.9](../../SPEC.md)).
- [ ] Logout/deletion unregisters the device token; no further push is sent to it.

### Compliance gate
- [ ] Push content is event-reporting only ("entered the scanner"), never prescriptive ("buy at open"); blocked-phrase validator runs on push templates ([17 §1–2](../17-alerts-and-notifications.md), [SPEC §3.2](../../SPEC.md)).

### Acceptance criteria
- [ ] FCM push delivers alerts/briefs with in-app as source of truth, quiet hours honored, and Mode-A-safe content ([17 §6](../17-alerts-and-notifications.md)).

---
## Feature: Secure storage & biometric login (biometric deferred)  `(Mode A)`
**Objective:** Store tokens in platform secure storage and carry over the web auth security model; ship biometric unlock behind a flag as a **later** enhancement, not a blocker for the EOD scope.
**Backend dep:** auth/token service from [07](07-v2-accounts-watchlist-ai-news.md) (RS256 JWT, rotating refresh, reuse detection) · **Frontend dep:** Keychain (iOS) / Keystore (Android) wrapper, biometric API (Face ID / fingerprint), feature flag · **Data dep:** access/refresh tokens; no portfolio/PII cached in plaintext.

### Steps
- [ ] 1. Store access/refresh tokens in **platform secure storage** (iOS Keychain / Android Keystore), never in plaintext or unencrypted local storage ([23 §4](../23-security-auth-and-privacy.md)).
- [ ] 2. Carry over the token model: short-lived access + rotating refresh with **reuse detection** (a replayed refresh revokes the family); all traffic over TLS ([23 §1, §4](../23-security-auth-and-privacy.md)).
- [ ] 3. Do **not** cache portfolio/PII-class data in plaintext on device; treat any local cache as sensitive, encrypted at rest, and clear it on logout ([23 §5](../23-security-auth-and-privacy.md)).
- [ ] 4. Implement **biometric login behind a flag (later)**: Face ID / fingerprint to unlock the locally-stored refresh token; off by default, opt-in, with a passcode/password fallback. Its absence must not block shipping the scoped surfaces.
- [ ] 5. On logout/deletion, purge tokens + local caches and unregister the push token ([23 §5](../23-security-auth-and-privacy.md)).

### Tests
- [ ] Tokens reside only in secure storage; no token or PII appears in plaintext local storage or logs ([23 §4–5](../23-security-auth-and-privacy.md)).
- [ ] A replayed refresh token revokes the family; an expired/invalid token forces re-login.
- [ ] Logout/deletion purges tokens, local caches, and the device push token.
- [ ] With the biometric flag off, the app ships and authenticates normally (biometric is non-blocking).

### Compliance gate
- [ ] Tokens/PII are never stored or logged in plaintext; secure storage + TLS enforced ([23 §4–5](../23-security-auth-and-privacy.md)).

### Acceptance criteria
- [ ] Tokens are in secure storage with the web security model intact; biometric login is a deferred, flagged enhancement that does not gate the EOD scope ([23 §1, §4](../23-security-auth-and-privacy.md)).

---
## Done-when
- [ ] All four features pass their tests, compliance gates, and acceptance criteria; the Exit gate checklist is fully checked.
- [ ] The framework choice (RN or Flutter) and FCM-as-push-provider are logged in [30](../30-decision-log.md); a single codebase targets iOS + Android over the shared `/api/v1` gateway.
- [ ] The five scoped surfaces (alerts, watchlist, portfolio, brief, stock page) render from shared endpoints with full states; no mobile-specific financial computation exists.
- [ ] Push via FCM delivers alerts/briefs with in-app as source of truth and quiet hours honored; push content is event-reporting only.
- [ ] Tokens live in secure storage with the web auth model intact; biometric login is deferred behind a flag.
- [ ] No mobile surface renders entry/target/SL, a buy-lean, a ranked "what to buy", or any always-prohibited phrase; AI is grounding-badged + not-advice; plan limits are enforced server-side ([SPEC §3](../../SPEC.md), [25-pricing-subscription-billing.md](25-pricing-subscription-billing.md)).
