# 23 — Security, Auth & Privacy

> One-line purpose: Authentication, authorization, secrets, encryption, PII protection, AI-log security, the threat model, and a security checklist — the controls that protect Saakshya's users, financial data, and AI audit trail.
> Read first: [SPEC.md](../SPEC.md)

Related: [Admin Panel](20-admin-panel.md) · [Compliance & Guardrails](21-compliance-risk-and-guardrails.md) · [Infrastructure, DevOps & Observability](22-infrastructure-devops-and-observability.md) · [AI/LLM Agent Architecture](14-ai-llm-agent-architecture.md) · [Information Architecture](05-information-architecture-and-url-paths.md)

---

## 0. Principles

1. **Least privilege everywhere** — users, admin roles ([Admin RBAC](20-admin-panel.md)), service IAM, DB grants.
2. **Defense in depth** — WAF → API Gateway throttling → app authz → row-level scoping → encrypted storage. No single control is the only line.
3. **The AI audit trail is sensitive *and* immutable** (SPEC §6.6). It must be protected (it may contain PII in payloads) and tamper-evident (it's the compliance forensic record, [Compliance §10](21-compliance-risk-and-guardrails.md)).
4. **Privacy by design** — collect minimal PII; encrypt it; support **right to erasure**; redact PII from logs/AI records.
5. **Secrets never in code or images** — Secrets Manager only, rotated ([Infra](22-infrastructure-devops-and-observability.md)).

---

## 1. Authentication

- **JWT** access tokens (short-lived, ~15 min) + **refresh tokens** (longer-lived, rotating, revocable). Signed (RS256/asymmetric) so services verify without the signing key.
- **OAuth 2.0 / OIDC** social sign-in (Google etc.) alongside email/password.
- **MFA**: TOTP for users (optional), **hardware-MFA enforced for super-admin** ([Admin §1](20-admin-panel.md)).
- **Session expiry**: idle timeout + absolute max lifetime; refresh-token rotation with reuse detection (a replayed refresh token revokes the family).
- **Password policy**: minimum length (≥12), breach-list check (HaveIBeenPwned k-anonymity), Argon2id hashing with per-user salt; no plaintext, no reversible storage; rate-limited login with lockout/backoff.

**Acceptance criteria.** Tokens are short-lived + revocable; a stolen refresh token is detectable and self-revoking; no endpoint accepts an unsigned/expired JWT; passwords are Argon2id-hashed and breach-checked.

---

## 2. Authorization (RBAC)

- **User scope:** every data read is row-scoped to the authenticated user (watchlists, portfolios, alerts) — no IDOR; ownership checked server-side on every object access.
- **Admin RBAC:** the five-role matrix (super-admin, data-admin, compliance-officer, support, read-only) from [Admin §1](20-admin-panel.md) is enforced by `can(actor, action, resource)` middleware, with **four-eyes** (author ≠ approver) on compliance/prompt/scanner publishes.
- **Tier entitlements:** Premium/Pro gating is an authz check inside `auth` routes, not separate URLs ([IA](05-information-architecture-and-url-paths.md)).
- **Service-to-service:** scoped IAM roles per task; least-privilege DB users (the API cannot write audit logs except append; workers cannot read user passwords).

**Acceptance criteria.** A user cannot access another user's objects (IDOR test suite); admin actions resolve through the RBAC matrix at runtime; self-approval is rejected (`409 self_approval_forbidden`).

---

## 3. Secrets & key management

- **AWS Secrets Manager** holds DB creds, `ANTHROPIC_API_KEY`, data-vendor keys, OAuth client secrets, and (future) broker tokens. Loaded at runtime via IAM; **never** in env files committed, images, or logs.
- **API key rotation**: scheduled rotation for vendor/LLM keys and DB creds; rotation runbook; dual-key window so rotation is zero-downtime. Super-admin-only rotation trigger ([Admin §1](20-admin-panel.md)).
- **Encryption keys**: KMS-managed; envelope encryption for application-level PII fields.

**Acceptance criteria.** No secret appears in source, images, or logs (CI secret-scan, [Infra §4](22-infrastructure-devops-and-observability.md)); key rotation completes without downtime; rotation is logged in the admin activity log.

---

## 4. Encryption

| State | Control |
|---|---|
| **In transit** | TLS 1.2+ everywhere (client↔edge, edge↔service, service↔DB); HSTS; no plaintext internal hops. |
| **At rest** | KMS-encrypted RDS/Timescale/Redis/S3/EBS; **application-level field encryption** for sensitive PII and (future) broker tokens (envelope encryption). |
| **Backups** | Encrypted snapshots; cross-region copies remain encrypted ([Infra §7](22-infrastructure-devops-and-observability.md)). |

---

## 5. PII protection & privacy

- **Minimal collection**: email, auth, subscription/billing references, and user-created content (watchlists/portfolios). No collection beyond product need.
- **Portfolio holdings are sensitive financial data** — treated as PII-class: encrypted, row-scoped, redacted from logs, and never sent to the LLM beyond the structured payload required for a *factual, non-advisory* note ("X broke its 50-DMA"), which is itself guardrailed ([Compliance](21-compliance-risk-and-guardrails.md)).
- **Right to erasure**: the [Admin user-management](20-admin-panel.md) deletion workflow removes/anonymizes PII while retaining the legally-minimal records (e.g. immutable compliance/audit entries are anonymized-by-reference, not destroyed). Erasure is itself logged (who/what/why retained).
- **Data residency**: prefer India/region-appropriate storage for Indian-user PII; confirm with counsel alongside the SEBI regime (SPEC §2, §14).

**Acceptance criteria.** An erasure request completes within the policy SLA; post-erasure, no PII is retrievable except the minimal anonymized compliance record; portfolio data never appears in plaintext logs.

---

## 6. Security of AI logs & financial data

The AI audit log (SPEC §6.6) is both **forensically required** ([Compliance §10](21-compliance-risk-and-guardrails.md)) and **PII-bearing** (payloads can include portfolio context). It needs special handling:

- **Retention policy**: prompt/input-payload/output retained per a defined window for compliance defensibility; **redaction** of PII within payloads where it isn't needed for grounding verification.
- **Access control**: full view (input payloads, raw prompts) restricted to `compliance-officer` + `super-admin`; `support`/`read-only` see redacted views ([Admin §2.7](20-admin-panel.md)).
- **Immutability**: append-only, S3 object-lock / WORM backing ([Infra §7](22-infrastructure-devops-and-observability.md)); no role can edit or hard-delete an entry (retention-expiry only, logged).
- **Redaction at write**: structured logging redacts secrets and unnecessary PII before persistence (SPEC §6.6).

**Acceptance criteria.** Raw AI prompts/payloads are visible only to authorized roles; the log is provably append-only and tamper-evident; redaction runs at write time, not just on display.

---

## 7. Network & application hardening

- **WAF** on CloudFront/API Gateway: OWASP managed rules, rate-based rules, and a strict rule set for `/admin/*` and `/api/*` (SPEC §9; [Infra §1](22-infrastructure-devops-and-observability.md)).
- **Rate limiting**: per-IP and per-user at API Gateway + app level; stricter on auth and AI endpoints (cost + abuse protection, ties to the AI-spend meter, SPEC §6.8).
- **Input validation**: schema validation on every endpoint; parameterized queries (no string-built SQL); output encoding (XSS); CSRF protection on state-changing browser requests.
- **Admin activity logs**: every state-changing admin action logged immutably ([Admin §3](20-admin-panel.md)); admin surface is `disallow` in robots and WAF-restricted.
- **(Future) broker-token storage**: when broker integration lands (Phase 5+, Mode B/C), tokens are envelope-encrypted, short-scoped, never logged, revocable per user, and isolated from the general user store — treated as the highest-sensitivity secret class.

---

## 8. Threat model summary

| Threat | Vector | Primary controls |
|---|---|---|
| **Account takeover** | Credential stuffing, phishing, token theft | Breach-list passwords, MFA, refresh-token rotation + reuse detection, rate limiting |
| **IDOR / data exposure** | Guessing another user's object IDs | Server-side ownership checks, row-scoping, IDOR test suite |
| **Privilege escalation (admin)** | Support user reaching rule/prompt edit | RBAC matrix + four-eyes; deny-by-default; admin activity logging |
| **Secret leakage** | Secrets in code/images/logs | Secrets Manager only, CI secret-scan, log redaction |
| **AI log tampering / leakage** | Editing/exfiltrating the compliance record | Append-only WORM, role-gated redacted views, encryption |
| **Prompt injection via news/text** | Malicious text steering AI output | Payload-contract grounding + output-time guardrails (SPEC §6.6, §6.9) — AI references only structured fields; injected directives can't ground |
| **Compliance bypass** | Directive output reaching users | Output-time guardrail pipeline (regex + grounding + review agent), [Compliance §9](21-compliance-risk-and-guardrails.md) |
| **Data exfiltration / abuse** | Scraping, API abuse, cost attacks | WAF, rate limiting, tier limits, AI-spend ceiling (SPEC §6.8) |
| **Supply chain** | Vulnerable deps / base images | SCA + image scan in CI, pinned digests, distroless base ([Infra §4](22-infrastructure-devops-and-observability.md)) |

**Note on prompt injection (SPEC §6.6):** because the AI may reference **only** the structured payload and every number/fact is grounding-verified at output time, injected instructions in news text cannot introduce ungrounded claims or directive language — the grounding contract is itself a security control, not only a correctness one.

---

## 9. Security checklist (run per change)

```text
[ ] 1. AuthN: endpoints require a valid, unexpired, signed JWT; no auth bypass.
[ ] 2. AuthZ: object access is ownership-checked server-side (no IDOR); admin
       actions resolve through the RBAC matrix; four-eyes on rule/prompt publish.
[ ] 3. Secrets: nothing sensitive in code/images/logs; only Secrets Manager.
[ ] 4. Encryption: TLS in transit; KMS at rest; PII fields envelope-encrypted.
[ ] 5. Input: schema-validated; parameterized queries; XSS/CSRF handled.
[ ] 6. PII: minimal collection; portfolio data treated as sensitive; redacted
       from logs; right-to-erasure path intact.
[ ] 7. AI logs: append-only/WORM; redaction at write; raw view role-gated.
[ ] 8. Rate limiting / WAF applied; admin & AI endpoints stricter.
[ ] 9. Admin actions write an immutable activity-log entry.
[ ] 10. Prompt-injection safe: AI references only the structured payload;
        output-time grounding + guardrails enforced. (SPEC §6.6/§6.9)
[ ] 11. Deps/images scanned; no new high/critical CVEs introduced.
[ ] 12. (If broker tokens) envelope-encrypted, scoped, revocable, never logged.
```

---

## 10. Related documents

- [14 — AI/LLM Agent Architecture](14-ai-llm-agent-architecture.md)
- [20 — Admin Panel](20-admin-panel.md)
- [21 — Compliance, Risk & Guardrails](21-compliance-risk-and-guardrails.md)
- [22 — Infrastructure, DevOps & Observability](22-infrastructure-devops-and-observability.md)
- [05 — Information Architecture & URL Paths](05-information-architecture-and-url-paths.md)
- [30 — Decision Log](30-decision-log.md)
