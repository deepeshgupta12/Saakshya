# Steps · 13 · V8 — Broker Integration & Execution
> Read first: [SPEC.md](../../SPEC.md) (§4 broker row, §10 Phase 5+) · [Roadmap](../02-product-roadmap.md) (§11 V8) · [Security, auth & privacy](../23-security-auth-and-privacy.md) (§3 secrets, §4 encryption, §6 AI logs, §7 broker-token storage) · [Compliance & guardrails](../21-compliance-risk-and-guardrails.md) · [Data ingestion](../12-data-ingestion-and-market-data.md)

**Maps to:** Roadmap V8 · SPEC Phase 5+
**Status:** Not started — GATED   |   **Regulatory mode:** B / C for any advisory-attached execution (read-only sync itself is Mode A; **order placement is a separate, later, licensed capability**)
**Gate (must be met before ANY build starts):** Broker integration is a **separate licensing, security, and operational undertaking** ([SPEC §4 broker row](../../SPEC.md), [Roadmap §11](../02-product-roadmap.md)). Before build: (1) **counsel review** of the regulatory/operational duties broker connectivity creates; (2) a **passed security review** of the broker-token threat surface ([docs/23 §7–8](../23-security-auth-and-privacy.md)); (3) for **order placement**, the relevant execution licensing in force and **no advisory substance attached to execution** unless the relevant registration (RA/IA) is in force ([Roadmap §11 acceptance](../02-product-roadmap.md)). **Read-only portfolio sync ships first; order placement is deferred behind its own gate.**
**Prerequisites:** Phase 5; V1–V3 portfolio tracker shipped; the security foundation (auth, RBAC, secrets, encryption, audit) from [docs/23](../23-security-auth-and-privacy.md). Live-data work ([12-v7-live-data.md](12-v7-live-data.md)) is independent but typically precedes.

## Overview
V8 integrates brokers so users can act on decisions without leaving the platform ([Roadmap §11](../02-product-roadmap.md)). It is sequenced in **two distinct capabilities with separate gates**:

1. **Read-only portfolio sync (first):** pull holdings/positions from the broker to enrich the existing portfolio tracker. This is **Mode A** in content (factual holdings, never "sell X") but introduces a **new high-sensitivity secret class** (broker tokens) and consent obligations.
2. **Order placement / execution (later, separately licensed):** placing orders is a separate undertaking with execution-licensing, elevated security, and operational duties — and **must carry no advisory substance** unless the relevant registration is in force ([SPEC §4](../../SPEC.md), [Roadmap §11](../02-product-roadmap.md)).

**The gate is regulatory + security, front and center.** Broker tokens are the highest-sensitivity secret class in the product ([docs/23 §7](../23-security-auth-and-privacy.md)); execution creates duties counsel must review. These steps describe **what to build once the gates are cleared**, read-only first, not a license to wire order placement early.

## Exit gate (Definition of Done)
- [ ] **Counsel has reviewed** the regulatory/operational duties of broker connectivity; for execution, the **execution licensing is in force** and counsel-confirmed ([Roadmap §11 acceptance](../02-product-roadmap.md)).
- [ ] A **security review of the broker-token surface has passed** ([docs/23 §7–8, §9 checklist](../23-security-auth-and-privacy.md)).
- [ ] **Read-only portfolio sync** ships first; broker tokens are **envelope-encrypted, short-scoped, never logged, revocable per user, isolated from the general user store** ([docs/23 §7](../23-security-auth-and-privacy.md)).
- [ ] **Explicit per-user consent flows** govern linking, scope, and revocation; consent and revocation are logged ([docs/23 §5](../23-security-auth-and-privacy.md)).
- [ ] Order placement, **if** built, is gated separately on execution licensing and carries **no advisory substance** unless RA/IA is in force ([SPEC §4](../../SPEC.md)).
- [ ] Licensing + security-review decisions logged ([decision log](../30-decision-log.md)).

---
## Feature: Regulatory + security gate (pre-build)  `(gate — Mode B/C scope)`
**Objective:** Clear the regulatory and security prerequisites before any broker code, separating read-only sync from order placement ([SPEC §4](../../SPEC.md), [docs/23 §7–8](../23-security-auth-and-privacy.md)). · **Backend dep:** none (gate) · **Frontend dep:** none · **Data dep:** none.
### Steps
- [ ] 1. **Owner: Founder/Legal.** Obtain **counsel review** distinguishing the duties of (a) read-only holdings sync vs (b) order placement/execution, including any broker-partner, intermediary, or execution-licensing obligations ([Roadmap §11](../02-product-roadmap.md)). **Artifact:** counsel memo.
- [ ] 2. **Owner: Legal/Compliance.** Confirm that **no advisory substance** may attach to execution unless RA (Mode B) / IA (Mode C) is in force — execution UI must not become a backdoor for buy-leans or per-stock levels ([SPEC §3.2, §4](../../SPEC.md), [compliance §1.1](../21-compliance-risk-and-guardrails.md)). **Artifact:** scope boundary memo.
- [ ] 3. **Owner: Security.** Run a **dedicated security review** of the broker-token threat surface (token theft, scope creep, replay, isolation) against the threat model ([docs/23 §8](../23-security-auth-and-privacy.md)). **Artifact:** passed security review.
- [ ] 4. **Owner: Founder.** Log decisions: read-only-first sequencing, execution deferral until licensing, security sign-off ([decision log](../30-decision-log.md)).
### Tests / Compliance gate / Acceptance criteria
- [ ] N/A (gate). Verification = counsel memo + scope boundary memo + passed security review on file.
- [ ] **Compliance gate:** no broker code starts until these artifacts exist; order placement remains deferred behind its own gate.

---
## Feature: Read-only portfolio sync  `(Mode A content; broker-token security)`
**Objective:** Pull holdings/positions read-only from the broker to enrich the existing portfolio tracker, with factual (non-advisory) presentation ([SPEC §4 portfolio row](../../SPEC.md), [Roadmap §6 V3](../02-product-roadmap.md)). · **Backend dep:** secure broker connector, portfolio store, token vault · **Frontend dep:** broker-link UI, synced holdings view · **Data dep:** broker holdings/positions API (read scope only).
### Steps
- [ ] 1. Build a **secure broker connector** requesting the **minimum read-only scope** (holdings/positions); never request order/trade scopes for this capability ([docs/23 §2 least-privilege](../23-security-auth-and-privacy.md)).
- [ ] 2. Map synced holdings into the existing portfolio model; treat holdings as **sensitive financial PII** — encrypted, row-scoped, redacted from logs ([docs/23 §5](../23-security-auth-and-privacy.md)).
- [ ] 3. Reconcile synced positions against user-entered holdings; surface differences **factually**, never as a prescription.
- [ ] 4. Reuse the existing portfolio AI/risk notes under guardrails — "X broke its 50-DMA" is factual; **never** "sell X" ([compliance §1.1](../21-compliance-risk-and-guardrails.md), [SPEC §4 portfolio row](../../SPEC.md)).
- [ ] 5. Handle sync lifecycle: scheduled refresh, error/expiry handling, and a clear "last synced" timestamp.
### Tests / Compliance gate / Acceptance criteria
- [ ] A user cannot read another user's synced holdings (IDOR test); holdings never appear in plaintext logs ([docs/23 §2, §5](../23-security-auth-and-privacy.md)).
- [ ] The connector requests **read-only** scope; any order/trade scope is rejected at config time.
- [ ] **Compliance gate:** synced-holdings presentation is factual; no "sell/reduce/rebalance" output ([compliance §1.1](../21-compliance-risk-and-guardrails.md)).

---
## Feature: Secure broker-token storage  `(security-critical)`
**Objective:** Store and manage broker tokens as the highest-sensitivity secret class, per [docs/23 §7](../23-security-auth-and-privacy.md). · **Backend dep:** KMS/envelope encryption, Secrets Manager, isolated token store · **Frontend dep:** none directly · **Data dep:** broker OAuth/token material.
### Steps
- [ ] 1. **Envelope-encrypt** broker tokens (KMS-managed keys), stored in a **store isolated from the general user store** ([docs/23 §4, §7](../23-security-auth-and-privacy.md)).
- [ ] 2. Keep tokens **short-scoped and revocable per user**; support rotation/refresh; **never log** tokens (redaction at write) ([docs/23 §6, §7](../23-security-auth-and-privacy.md)).
- [ ] 3. Load any vendor/app secrets from **Secrets Manager only** — never in code, images, or env files ([docs/23 §3](../23-security-auth-and-privacy.md)).
- [ ] 4. Gate token access by **least-privilege service IAM**; the general API path cannot read raw tokens ([docs/23 §2](../23-security-auth-and-privacy.md)).
- [ ] 5. Ensure tokens are covered by **right-to-erasure** and revoked on account deletion ([docs/23 §5](../23-security-auth-and-privacy.md)).
### Tests / Compliance gate / Acceptance criteria
- [ ] CI secret-scan: no token/secret in source, images, or logs ([docs/23 §3, §9](../23-security-auth-and-privacy.md)).
- [ ] Tokens are envelope-encrypted, scoped, revocable, and isolated (security checklist item 12) ([docs/23 §9](../23-security-auth-and-privacy.md)).
- [ ] Revoking a link or deleting the account invalidates the token; erasure removes it ([docs/23 §5](../23-security-auth-and-privacy.md)).

---
## Feature: Consent flows  `(Mode A content; privacy)`
**Objective:** Explicit, revocable per-user consent for broker linking — scope shown, granted deliberately, revocable any time, fully logged ([docs/23 §5](../23-security-auth-and-privacy.md)). · **Backend dep:** consent store, audit log · **Frontend dep:** consent + link/unlink UI · **Data dep:** none.
### Steps
- [ ] 1. Show the **exact scope** requested (read-only holdings; later, separately, order placement) and require **deliberate consent** before any broker connection.
- [ ] 2. Provide a one-click **unlink/revoke** that invalidates the token and stops sync ([docs/23 §7](../23-security-auth-and-privacy.md)).
- [ ] 3. **Log consent and revocation** (who/what scope/when) immutably; never auto-escalate scope without fresh consent.
- [ ] 4. For any future **order-placement** scope, require a **separate, explicit consent step** — never bundled with read-only linking.
### Tests / Compliance gate / Acceptance criteria
- [ ] Linking is impossible without explicit scoped consent; scope escalation requires fresh consent (test).
- [ ] Unlink/revoke invalidates the token immediately; consent + revocation are logged ([docs/23 §5](../23-security-auth-and-privacy.md)).

---
## Feature: Order placement / execution (deferred, separately gated)  `(Mode B/C — separate licensing)`
**Objective:** **Deferred.** Placing orders is a separate, later capability with its own execution-licensing, elevated security, and operational duties; documented here only to keep the boundary explicit ([SPEC §4](../../SPEC.md), [Roadmap §11](../02-product-roadmap.md)). · **Backend dep:** order lifecycle, elevated audit, write-scope tokens · **Frontend dep:** order UI · **Data dep:** broker order API.
### Steps
- [ ] 1. **Do not build until** execution licensing is in force and counsel-reviewed ([Roadmap §11 acceptance](../02-product-roadmap.md)).
- [ ] 2. When unblocked: implement the **order lifecycle** (place/modify/cancel/status) with **elevated security + audit**, write-scoped tokens, and idempotency ([docs/23 §7](../23-security-auth-and-privacy.md)).
- [ ] 3. Ensure execution carries **no advisory substance** — the platform may execute a user's own instruction but must not recommend, rank-for-action, or attach per-stock levels unless RA/IA is in force ([SPEC §3.2, §4](../../SPEC.md), [compliance §1.1](../21-compliance-risk-and-guardrails.md)).
### Tests / Compliance gate / Acceptance criteria
- [ ] **Gate:** the order path is unreachable (no route/flag) until execution licensing is confirmed in force ([SPEC §4](../../SPEC.md)).
- [ ] When enabled: order actions are fully audited; tokens are write-scoped + isolated; no advisory substance attaches to execution ([compliance §1.1](../21-compliance-risk-and-guardrails.md)).

---
## Done-when
- [ ] Counsel-reviewed duties + a **passed broker-token security review** are on file; read-only-first sequencing is logged ([docs/23 §7–8](../23-security-auth-and-privacy.md), [decision log](../30-decision-log.md)).
- [ ] **Read-only portfolio sync** ships, presenting holdings factually (never "sell X"); broker tokens are envelope-encrypted, scoped, revocable, isolated, and never logged ([docs/23 §7](../23-security-auth-and-privacy.md), [compliance §1.1](../21-compliance-risk-and-guardrails.md)).
- [ ] Explicit, scoped, revocable, logged **consent flows** govern every broker link ([docs/23 §5](../23-security-auth-and-privacy.md)).
- [ ] **Order placement remains deferred** behind its own execution-licensing gate and carries no advisory substance unless RA/IA is in force ([SPEC §4](../../SPEC.md), [Roadmap §11](../02-product-roadmap.md)).
