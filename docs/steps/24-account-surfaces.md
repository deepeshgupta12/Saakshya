# Steps · 24 · Account Surfaces
> Read first: [SPEC.md](../../SPEC.md) (esp. [§7 personalization](../../SPEC.md)) · [Roadmap](../02-product-roadmap.md) · [Feature modules](../04-feature-modules.md) · [Personas & journeys](../03-user-personas-and-journeys.md) · [Security & auth](../23-security-auth-and-privacy.md) · [Alerts & notifications](../17-alerts-and-notifications.md) · [API contracts](../10-api-contracts.md) · [Screens](../08-screen-by-screen-documentation.md)

**Maps to:** Roadmap V2 · SPEC Phase 2
**Status:** Not started   |   **Regulatory mode:** A
**Prerequisites:** [07-v2-accounts-watchlist-ai-news.md](07-v2-accounts-watchlist-ai-news.md) (auth, JWT/refresh, RBAC + row-scoping, `consents`, `user_preferences`) · [06-frontend-foundation-and-v1-screens.md](06-frontend-foundation-and-v1-screens.md) (frontend foundation, `(app)` group, compliance wrappers)

## Overview
[07](07-v2-accounts-watchlist-ai-news.md) built the **auth foundation** (signup/login, tokens, RBAC, `consents`, `user_preferences`). This file builds the **account surfaces on top of that foundation**: the **first-run onboarding flow** (`/onboarding` — pick sectors, seed a watchlist, set a risk preference, record acknowledgements), the **profile & settings** area (preferences, the risk preference that defaults scanner filters, notification channel prefs), the **notification center** (the in-app inbox for alerts/news/briefs), and **account management** (password change, active sessions, data export & deletion per [23](../23-security-auth-and-privacy.md)).

**The single non-negotiable for this whole file:** every preference here is **navigation personalization only** ([SPEC §7](../../SPEC.md)). A risk preference defaults *which scanner filters and layout* a user sees — it **never** produces a per-stock behavioural suggestion ("because you view banking, consider HDFC Bank"); that is Investment-Adviser (Mode C) territory and is out. Followed sectors prioritize *layout and navigation*, not recommendations. The line is kept explicit in design review so it cannot creep across releases ([SPEC §7](../../SPEC.md), [03 §1](../03-user-personas-and-journeys.md)).

The notification center is an **inbox surface**, not a content engine — its content inherits the originating service's compliance posture (alerts are event-reporting, briefs are descriptive). Account management is **privacy-by-design**: minimal PII, encrypted, row-scoped, with a working right-to-erasure path ([23 §0, §5](../23-security-auth-and-privacy.md)).

## Exit gate (Definition of Done)
- [ ] First-run `/onboarding` records a risk preference, followed sectors, an optional seed watchlist item, and the not-advice + AI-use acknowledgements; it can be skipped and resumed ([08 §17](../08-screen-by-screen-documentation.md), [SPEC §6.7](../../SPEC.md)).
- [ ] The risk preference sets **default filters/layout only** — a contract test asserts it produces **no** per-stock suggestion ([SPEC §7](../../SPEC.md)).
- [ ] Profile & settings let a user view/edit preferences and notification channels; all writes are row-scoped server-side ([23 §2](../23-security-auth-and-privacy.md)).
- [ ] The notification center shows alerts/news/briefs as an in-app inbox with read/unread; in-app is the **source of truth** even when other channels fail ([17 §6](../17-alerts-and-notifications.md)).
- [ ] Password change enforces the ≥12-char + breach-check policy and re-hashes with Argon2id; changing the password revokes other sessions ([23 §1](../23-security-auth-and-privacy.md)).
- [ ] Active-session management lists sessions and can revoke them (refresh-family revocation); a revoked session cannot refresh ([23 §1](../23-security-auth-and-privacy.md)).
- [ ] Data export returns the user's own data; account deletion runs the right-to-erasure workflow (anonymize-by-reference on immutable compliance records), and erasure is itself logged ([23 §5](../23-security-auth-and-privacy.md)).
- [ ] No surface in this file emits a buy-lean, target/SL, or behaviour-derived per-stock suggestion; personalization is navigation-only ([SPEC §7](../../SPEC.md)).

---
## Feature: Onboarding (first-run) flow  `(Mode A)`
**Objective:** A guided first-run setup that personalizes **navigation only** — risk preference (default filters), followed sectors (layout), an optional seed watchlist item — and records the mandatory acknowledgements, then drops the user on the dashboard.
**Backend dep:** `POST /me/onboarding`, `PATCH /me/preferences` ([08 §17](../08-screen-by-screen-documentation.md)); writes `user_preferences` + `consents` from [07](07-v2-accounts-watchlist-ai-news.md) · **Frontend dep:** `(app)` group, `OnboardingStepper` (Risk preference → Follow sectors → Seed watchlist → Acknowledge & finish), stepper state in Zustand ([08 §17](../08-screen-by-screen-documentation.md)) · **Data dep:** sector catalog, symbol search, `user_preferences`, `consents`.

### Steps
- [ ] 1. Implement `POST /me/onboarding` and `PATCH /me/preferences` in `app/api/routes/me.py`: persist `risk_preference`, `followed_sectors[]`, and layout into `user_preferences`; record the not-advice + AI-use acknowledgements into `consents` with version + timestamp ([07](07-v2-accounts-watchlist-ai-news.md), [SPEC §6.7](../../SPEC.md)).
- [ ] 2. Build `app/(app)/onboarding/page.tsx` with `OnboardingStepper` per [08 §17](../08-screen-by-screen-documentation.md): **Risk preference → Follow sectors → Seed watchlist → Acknowledge & finish**; stepper state in Zustand; Next/Back/Skip; finish routes to `/dashboard` ([03 §3.1](../03-user-personas-and-journeys.md)).
- [ ] 3. Frame the risk-preference step explicitly as **"sets your default scanner filters"** — never "we'll tell you what to buy"; the copy states it personalizes navigation, not recommendations ([SPEC §7](../../SPEC.md)).
- [ ] 4. The seed-watchlist step reuses the watchlist add flow from [07](07-v2-accounts-watchlist-ai-news.md); it is **optional** and skippable; any "suggested" sectors/symbols shown are filter-based discovery, never per-user buy-leans ([07 watchlist](07-v2-accounts-watchlist-ai-news.md)).
- [ ] 5. Make onboarding **resumable**: a user who skips can complete it later from settings; the acknowledgement step cannot be skipped (signup already gated it, but re-confirm version on change) ([SPEC §6.7](../../SPEC.md)).
- [ ] 6. Animation: step slide/fade transitions, confirmation on finish; all reduce-motion-aware ([07 design](../07-design-system-and-ui-ux.md)).
- [ ] 7. Analytics: `onboarding_start`, `onboarding_step{n}`, `onboarding_skip`, `onboarding_complete` ([08 §17](../08-screen-by-screen-documentation.md)).

### Tests
- [ ] Completing onboarding writes `risk_preference` + `followed_sectors[]` to `user_preferences` and the acknowledgements to `consents`.
- [ ] The risk preference only changes default filters/layout — a contract test asserts **no** per-stock suggestion is produced from it ([SPEC §7](../../SPEC.md)).
- [ ] Skip → later resume restores stepper progress; the dashboard reflects followed sectors.
- [ ] A user cannot write another user's preferences (row-scope, [23 §2](../23-security-auth-and-privacy.md)).

### Compliance gate
- [ ] Risk preference sets **default filters/layout only**, never per-stock suggestions; no behaviour-derived buy-leans ([SPEC §7](../../SPEC.md), [08 §17 acceptance](../08-screen-by-screen-documentation.md)).
- [ ] Acknowledgements (not-advice + AI-use) are recorded with version + timestamp ([SPEC §6.7](../../SPEC.md)).

### Acceptance criteria
- [ ] First-run setup personalizes navigation only and records acknowledgements; skippable and resumable ([08 §17](../08-screen-by-screen-documentation.md)).

---
## Feature: Profile & settings  `(Mode A)`
**Objective:** A self-serve area where a user views/edits their profile (display name, email), preferences (risk preference, followed sectors, layout, density), and notification channel preferences — transparent and user-editable, with the personalization line held.
**Backend dep:** `GET/PATCH /me`, `PATCH /me/preferences`; `user_preferences` store ([04 §24](../04-feature-modules.md)) · **Frontend dep:** `(app)` settings route, `ProfileForm`, `PreferencesForm`, `NotificationChannelPrefs`, `FollowedSectorsEditor` · **Data dep:** `users`, `user_preferences`, sector catalog, notification channel config ([17 §6](../17-alerts-and-notifications.md)).

### Steps
- [ ] 1. Implement `GET /me` and `PATCH /me` (display name, email-change with re-verification) in `app/api/routes/me.py`; all reads/writes row-scoped to the authenticated user ([23 §2](../23-security-auth-and-privacy.md)).
- [ ] 2. Build the settings area `app/(app)/settings/page.tsx` with tabbed sections: **Profile**, **Preferences**, **Notifications**, **Account & security** (the last delegates to the account-management feature below).
- [ ] 3. `PreferencesForm`: edit `risk_preference` (default-filter level), `followed_sectors[]` (`FollowedSectorsEditor`), layout/density — all written via `PATCH /me/preferences`; copy states each setting personalizes **navigation, not recommendations** ([04 §24](../04-feature-modules.md), [SPEC §7](../../SPEC.md)).
- [ ] 4. `NotificationChannelPrefs`: per-channel (in-app always-on, email, push) toggles + quiet hours, persisted for the notification service to honor ([17 §5–6](../17-alerts-and-notifications.md)).
- [ ] 5. Keep personalization **transparent and reversible**: every applied default shows where it came from ("Filters defaulted from your risk preference") and can be overridden ad-hoc without changing the saved preference ([SPEC §7](../../SPEC.md)).
- [ ] 6. States: optimistic save with toast; validation errors inline; loading skeleton; email-change pending-verification state.
- [ ] 7. Analytics: `settings_view`, `preference_update{key}`, `notification_pref_update{channel}` ([24 analytics](../24-analytics-seo-and-growth.md)).

### Tests
- [ ] Editing `risk_preference` changes default scanner filters only; no per-stock suggestion appears anywhere as a result ([SPEC §7](../../SPEC.md)).
- [ ] Notification channel prefs + quiet hours persist and are honored by the notification service ([17 §5](../17-alerts-and-notifications.md)).
- [ ] A user cannot read/write another user's profile or preferences (IDOR, [23 §2](../23-security-auth-and-privacy.md)).

### Compliance gate
- [ ] All preferences are navigation-only and user-editable; the design-review line (Mode A vs Mode C) is explicit so personalization cannot creep into per-stock advice ([SPEC §7](../../SPEC.md)).

### Acceptance criteria
- [ ] Preferences personalize navigation, never recommendations; transparent and reversible ([04 §24](../04-feature-modules.md), [SPEC §7](../../SPEC.md)).

---
## Feature: Notification center (in-app inbox)  `(Mode A)`
**Objective:** A central in-app inbox for alerts, daily briefs, and system messages with read/unread state — the source-of-truth surface that always receives every notification even when email/push fail.
**Backend dep:** notification service (`notifications` store, [09 §2.15](../09-backend-architecture.md)); alert fired-events ([10 alerts](../10-api-contracts.md), `GET /api/alerts/{id}/events`) · **Frontend dep:** `NotificationCenter` (inbox list, read/unread, filter), `NotificationItem`, `AlertsFeed` on `/dashboard` ([08 §18](../08-screen-by-screen-documentation.md)) · **Data dep:** `notifications` (per-user, source service, read state), alert/brief/news payloads.

### Steps
- [ ] 1. Confirm the `notifications` store + delivery from the notification service ([09 §2.15](../09-backend-architecture.md)): every alert/brief/system message lands in the **in-app feed as source of truth**, with at-least-once delivery + idempotency key ([17 §6](../17-alerts-and-notifications.md)).
- [ ] 2. Implement the inbox API in `app/api/routes/notifications.py`: `GET /me/notifications` (paginated, row-scoped), `POST /me/notifications/{id}/read`, `POST /me/notifications/read-all`, unread-count; envelope per [10 §0.1](../10-api-contracts.md).
- [ ] 3. Build `NotificationCenter` (inbox list with read/unread, type filter — alert / news / brief / system) and the dashboard `AlertsFeed` snapshot ([08 §18](../08-screen-by-screen-documentation.md)); a header bell shows the unread count.
- [ ] 4. Render each `NotificationItem` with its **originating compliance posture intact**: alerts as event-reporting ("TCS entered the momentum scanner"), briefs as descriptive, news as classification — never re-written into a directive ([17 §1–2](../17-alerts-and-notifications.md), [SPEC §5](../../SPEC.md)).
- [ ] 5. Link each item to its source (alert event → stock/scanner, brief → brief page, news → article) for evidence drill-in; below-threshold news links never appear ([07 news](07-v2-accounts-watchlist-ai-news.md)).
- [ ] 6. States: empty ("No notifications yet"), loading skeleton, error; reduce-motion-aware unread→read transition.
- [ ] 7. Analytics: `notification_center_open`, `notification_item_click{type}`, `notification_mark_read`, `notification_mark_all_read` ([24 analytics](../24-analytics-seo-and-growth.md)).

### Tests
- [ ] An alert/brief/news message lands in the in-app inbox even when email/push are simulated as failing (in-app is source of truth, [17 §6](../17-alerts-and-notifications.md)).
- [ ] Mark-read / mark-all-read updates state and the unread count; a user sees only their own notifications (row-scope, [23 §2](../23-security-auth-and-privacy.md)).
- [ ] An alert item renders event-reporting language, never "buy at open"; copy passes the blocked-phrase validator ([17 §2](../17-alerts-and-notifications.md)).

### Compliance gate
- [ ] Inbox content inherits the originating service's posture: event-reporting alerts, descriptive briefs, classification news — never prescriptive ([17 §1–2](../17-alerts-and-notifications.md), [SPEC §3.2](../../SPEC.md)).
- [ ] Below-threshold news→symbol links are never surfaced in the inbox ([07 news](07-v2-accounts-watchlist-ai-news.md)).

### Acceptance criteria
- [ ] The in-app inbox is the source of truth for all notifications, with read/unread, row-scoped, and Mode-A-safe content ([17 §6](../17-alerts-and-notifications.md)).

---
## Feature: Account management — password, sessions, export & deletion  `(Mode A)`
**Objective:** Self-serve security & privacy controls: change password (policy-enforced), view/revoke active sessions, export own data, and delete the account via the right-to-erasure workflow — minimal PII, encrypted, row-scoped, logged.
**Backend dep:** auth/password service + token store from [07](07-v2-accounts-watchlist-ai-news.md); session listing over `refresh_tokens` families; data-export assembler; right-to-erasure workflow ([23 §5](../23-security-auth-and-privacy.md), [20 admin](../20-admin-panel.md)) · **Frontend dep:** `ChangePasswordForm`, `ActiveSessionsList`, `DataExportButton`, `DeleteAccountDialog` · **Data dep:** `users`, `refresh_tokens`, `consents`, `user_preferences`, watchlists/portfolios/alerts owned by the user.

### Steps
- [ ] 1. Implement `POST /me/password` in `app/api/routes/me.py`: require the current password, enforce ≥12-char + HaveIBeenPwned breach-check, re-hash with Argon2id; on success **revoke all other refresh-token families** (keep the current session) ([23 §1](../23-security-auth-and-privacy.md)).
- [ ] 2. Implement `GET /me/sessions` (list active refresh-token families: device/UA, created, last-seen) and `DELETE /me/sessions/{id}` (revoke a family); a revoked family **cannot refresh** (reuse detection, [23 §1](../23-security-auth-and-privacy.md)).
- [ ] 3. Implement **data export** `POST /me/export` → an async job assembling the user's own data (profile, preferences, watchlists, portfolio, alerts, consents) into a downloadable archive; row-scoped; PII handled as sensitive ([23 §5](../23-security-auth-and-privacy.md)). *(Note: [23 §5](../23-security-auth-and-privacy.md) specifies the erasure path; this adds the self-serve export companion — log the decision in [30](../30-decision-log.md).)*
- [ ] 4. Implement **account deletion** `POST /me/delete` running the right-to-erasure workflow ([23 §5](../23-security-auth-and-privacy.md), [20 user-management](../20-admin-panel.md)): remove/anonymize PII while retaining legally-minimal records (immutable compliance/audit entries **anonymized-by-reference, not destroyed**); the erasure itself is logged (who/what/why retained), completing within the policy SLA.
- [ ] 5. Build `app/(app)/settings` → **Account & security** section: `ChangePasswordForm`, `ActiveSessionsList` (revoke buttons), `DataExportButton`, `DeleteAccountDialog` (typed confirmation + consequence summary).
- [ ] 6. Ensure portfolio holdings and other PII-class fields are encrypted, row-scoped, and **redacted from logs** throughout export/deletion ([23 §5–6](../23-security-auth-and-privacy.md)).
- [ ] 7. Analytics: `password_change`, `session_revoke`, `data_export_request`, `account_delete_request` (no PII in event payloads).

### Tests
- [ ] A breached/short password is rejected; a valid change re-hashes (Argon2id) and revokes other sessions; the changed-from password no longer logs in ([23 §1](../23-security-auth-and-privacy.md)).
- [ ] Revoking a session prevents its refresh token from minting a new access token (reuse detection, [23 §1](../23-security-auth-and-privacy.md)).
- [ ] Export returns only the requesting user's data; deletion anonymizes PII while immutable compliance records remain anonymized-by-reference; erasure is logged ([23 §5](../23-security-auth-and-privacy.md)).
- [ ] Portfolio/PII never appears in plaintext logs during export/deletion ([23 §5–6](../23-security-auth-and-privacy.md)).

### Compliance gate
- [ ] Right-to-erasure completes within the policy SLA; post-erasure no PII is retrievable except the minimal anonymized compliance record ([23 §5](../23-security-auth-and-privacy.md)).
- [ ] Passwords are Argon2id-hashed + breach-checked; no plaintext/reversible storage; sessions are revocable ([23 §1](../23-security-auth-and-privacy.md)).

### Acceptance criteria
- [ ] Users can change passwords, manage/revoke sessions, export their own data, and delete their account via the logged erasure workflow ([23 §1, §5](../23-security-auth-and-privacy.md)).

---
## Done-when
- [ ] All four features pass their tests, compliance gates, and acceptance criteria; the Exit gate checklist is fully checked.
- [ ] Onboarding personalizes **navigation only** and records acknowledgements; a contract test proves the risk preference yields no per-stock suggestion ([SPEC §7](../../SPEC.md)).
- [ ] Profile/settings/notification-center are row-scoped and Mode-A-safe; the in-app inbox is the source of truth for all notifications ([17 §6](../17-alerts-and-notifications.md)).
- [ ] Account management enforces the password policy, revocable sessions, data export, and a logged right-to-erasure deletion; PII never appears in plaintext logs ([23 §1, §5–6](../23-security-auth-and-privacy.md)).
- [ ] No account surface emits a buy-lean, target/SL, or behaviour-derived per-stock suggestion; the Mode A ↔ Mode C personalization line is held in design review ([SPEC §7](../../SPEC.md)).
