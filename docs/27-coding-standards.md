# 27 — Coding Standards

> One-line purpose: The enforceable conventions for every layer of Saakshya — frontend (TS/React/Next), backend (Python/FastAPI), data pipelines, AI prompts, Alembic migrations, and tests — including naming, typing, error handling, structured logging, the API response envelope, commit/branch/PR rules, and good-vs-bad examples.
> Read first: [SPEC.md](../SPEC.md)

Related: [Frontend Architecture](06-frontend-architecture.md) · [Backend Architecture](09-backend-architecture.md) · [API Contracts](10-api-contracts.md) · [Database Architecture](11-database-architecture.md) · [AI/LLM Agent Architecture](14-ai-llm-agent-architecture.md) · [QA & Release](25-qa-testing-and-release-process.md) · [Agentic Workflows](28-agentic-development-workflows.md) · [Decision Log](30-decision-log.md)

---

## 0. Principles (read before coding)

1. **Critical logic MUST be documented and covered by tests.** Non-negotiable for: **scanner scoring**, **corporate-action adjustment**, and **AI grounding/guardrails** (SPEC §6.1, §6.5, §6.6, §6.9). A PR that touches any of these without tests + doc update is rejected ([25](25-qa-testing-and-release-process.md), [28](28-agentic-development-workflows.md)).
2. **Evidence-first in code too.** Functions that produce user-facing values carry/propagate the `as_of` of their inputs (SPEC §6.2). AI code may only consume the structured payload (SPEC §6.6) — never reach back to raw data or invent values.
3. **Mode-A is a code constraint.** No symbol, route, field, or string in `main` emits entry/target/SL or buy-lean language (SPEC §3). RA-gated code is flag-guarded and off by default.
4. **Strict typing everywhere.** Strict TS; Python type hints + `mypy --strict`. No `any`, no untyped public function.
5. **Fail loud, never guess.** On missing critical input, **suppress** (fallback) and log — do not fabricate (SPEC §6.2).

---

## 1. Repository & folder conventions

Mirrors the SPEC §12 project structure so local modules lift into services later.

```
saakshya/
  app/
    config.py            # env + settings (pydantic-settings)
    data/                # DataSource adapters (yfinance, nse_bhavcopy), symbol universe
    storage/             # DB connection, schema, repositories
    indicators/          # vectorized RSI, SMA/EMA, ATR, MACD, Bollinger, returns
    scanners/            # scanner scoring: score + reasons + risk flags
    ai/                  # payload contract, prompts, grounding verifier, guardrails
    pipeline/            # ingest -> compute -> scan orchestration
    api/                 # FastAPI routers, schemas, dependencies
  alembic/               # migrations
  tests/                 # mirrors app/ tree
  web/                   # Next.js app (added once core validated)
```

- One responsibility per module; `scanners/` never imports `api/`; `ai/` never imports raw `data/` adapters (only the payload).
- Tests mirror source paths: `app/scanners/momentum.py` → `tests/scanners/test_momentum.py`.

---

## 2. Naming conventions

| Thing | Convention | Example |
|---|---|---|
| Python module/file | `snake_case` | `corp_action_adjuster.py` |
| Python function/var | `snake_case` | `compute_rsi`, `adjusted_close` |
| Python class | `PascalCase` | `MomentumScanner`, `DataSource` |
| Python constant | `UPPER_SNAKE` | `RSI_PERIOD`, `BLOCKED_PHRASES` |
| TS variable/function | `camelCase` | `fetchScannerResults` |
| TS type/interface/component | `PascalCase` | `ScannerResult`, `StockHeader` |
| React component file | `PascalCase.tsx` | `ScannerResultsTable.tsx` |
| TS hook | `useCamelCase` | `useScannerResults` |
| API route (REST) | plural kebab nouns | `/api/v1/scanners/momentum` |
| DB table | `snake_case` plural | `daily_bars`, `corp_actions` |
| DB column | `snake_case` | `adjusted_close`, `as_of_date` |
| Env var | `UPPER_SNAKE` | `ANTHROPIC_API_KEY` |
| Feature flag | `snake_case`, area-prefixed | `ra_levels_enabled` |

---

## 3. Typing rules

### 3.1 TypeScript (frontend)

- `tsconfig`: `strict: true`, `noUncheckedIndexedAccess`, `noImplicitAny`, `exactOptionalPropertyTypes`.
- **No `any`.** Use `unknown` + narrowing. API responses validated with `zod` at the boundary.
- Shared API types generated from the backend OpenAPI ([10](10-api-contracts.md)) — never hand-duplicated.

```ts
// good — validated at boundary, typed envelope
const Result = z.object({ symbol: z.string(), momentumScore: z.number(), asOf: z.string() });
type ScannerRow = z.infer<typeof Result>;
async function getMomentum(): Promise<ScannerRow[]> {
  const res = await api.get("/scanners/momentum");
  return z.array(Result).parse(res.data.data); // envelope.data (§6)
}
```

```ts
// bad — any, no validation, trusts the wire
async function getMomentum(): Promise<any> {
  const res = await fetch("/scanners/momentum");
  return (await res.json()).data; // shape unchecked
}
```

### 3.2 Python (backend / pipeline / AI)

- Type hints on **every** public function; `mypy --strict` in CI. Pydantic v2 models for all I/O.
- No bare `dict` across module boundaries — use typed models.

```python
# good
def compute_rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    """RSI over adjusted closes. Returns NaN for the warm-up window (never 0)."""
    ...

class AiPayload(BaseModel):  # the ONLY thing the LLM may reference (SPEC §6.6)
    symbol: str
    as_of: date
    metrics: dict[str, float]
    scanner_tags: list[str]
    risk_markers: list[str]
```

```python
# bad — untyped, leaks raw frame into AI, no as_of
def summarize(stock):                 # no types
    raw = db.read_raw(stock)          # AI must NOT see raw data
    return llm(f"summarize {raw}")    # ungrounded, unverified
```

---

## 4. Error handling

- **Backend**: raise typed domain exceptions (`DataMissingError`, `GuardrailViolation`, `GroundingFailure`); a FastAPI exception handler maps them to the error envelope (§6). Never `except: pass`.
- **AI grounding/guardrails fail closed**: on `GroundingFailure` or `GuardrailViolation`, return the **non-AI fallback** (SPEC §6.8), log the audit record, never the raw fabrication.
- **Missing critical input → suppress, don't guess** (SPEC §6.2): return a "data unavailable" state with the `as_of`, not a fabricated value.
- **Frontend**: error boundaries per route segment; user-facing messages are neutral and never advisory.

```python
# good — fail closed, audited
result = verify_grounding(output, payload)        # SPEC §6.6
if not result.ok:
    log_audit(audit_id, status="grounding_failed", detail=result.mismatches)
    return non_ai_fallback(payload)               # never the fabricated text
```

---

## 5. Structured logging

- **JSON structured logs only.** No `print`. Every log line carries: `ts`, `level`, `service`, `module`, `request_id`, and for data/AI surfaces `as_of` and (AI) `model_version` + `audit_id`.
- **No PII / no secrets** in logs (SPEC §6, [23](23-security-auth-and-privacy.md)). No API keys, no email, no portfolio amounts.
- AI generations write a full **audit log** (prompt, input payload, model version, output) to the audit store, not the app log (SPEC §6.6).

```python
# good
log.info("scanner_run", scanner="momentum", as_of=str(d), n=len(rows), request_id=rid)
# bad
print(f"ran momentum for {user.email} key={ANTHROPIC_API_KEY}")  # PII + secret + print
```

---

## 6. Standard API response envelope

All FastAPI business endpoints return one envelope ([10](10-api-contracts.md), [05 §5](05-information-architecture-and-url-paths.md)).

```jsonc
// success
{
  "data": { /* payload */ },
  "meta": {
    "as_of": "2026-06-26",        // trading date of the data (SPEC §6.2)
    "request_id": "req_...",
    "cached": true
  },
  "error": null
}
// AI success additionally carries grounding metadata (SPEC §6.6, §6.8)
{ "data": { "output": "...", "grounded": true, "model_version": "claude-haiku-4-5",
            "audit_id": "aud_...", "payload_ref": "pl_..." }, "meta": {...}, "error": null }
// error
{ "data": null, "meta": { "request_id": "req_..." },
  "error": { "code": "DATA_MISSING", "message": "No EOD data for symbol on as_of date",
             "field": "symbol" } }
```

- **AI endpoints always include grounding metadata.** If grounding fails, return the non-AI fallback in `data` with `grounded: false` — never a fabricated answer (SPEC §6.8).
- Error `code` is a stable machine string; `message` is human, neutral, non-advisory.

---

## 7. Layer-specific standards

### 7.1 Frontend (TS/React/Next)
- App Router; Server Components by default, Client Components only when interactive.
- Data fetching server-side for indexed pages (SSR/ISR, EOD cadence — [24](24-analytics-seo-and-growth.md)).
- No business logic in components; call typed API clients. No inline blocked-phrase risk in copy (lint rule).

### 7.2 Backend (Python/FastAPI)
- Routers thin; logic in `scanners/`, `indicators/`, `ai/`, services. Dependencies via FastAPI `Depends`.
- Pydantic models for every request/response; OpenAPI is the contract source.

### 7.3 Data pipelines
- **Vectorized pandas/NumPy or pandas-ta — avoid TA-Lib** (M1 friction, SPEC §9, §12).
- Every stage is idempotent and `as_of`-stamped. Corp-action adjustment is a first-class, separately-tested stage (SPEC §6.1) — store **both raw and adjusted** series.
- Implement detect→quarantine→correct→re-emit for corrections (SPEC §6.2).

### 7.4 AI prompts
- Prompts are **versioned files** in `ai/prompts/`, referenced by id; never inline string-built from user data.
- The LLM may reference **only** the `AiPayload` (SPEC §6.6). Output passes the grounding verifier **and** the guardrail engine before display.
- Default model **Claude Haiku** (`claude-haiku-4-5-20251001`); premium model reserved for complex synthesis via the provider abstraction (SPEC §9). Any prompt/model change re-runs the verification harness ([25 §1.3](25-qa-testing-and-release-process.md)).
- No directive tails ("before fresh action"); Mode-A neutralization (SPEC §5) enforced.

### 7.5 Database migrations (Alembic)
- Every schema change is an Alembic migration with a **tested `downgrade`**.
- **Destructive changes are two-phase**: expand (add nullable/new) → backfill → contract (drop) in a later release, so rollback is always safe ([25 §4.1](25-qa-testing-and-release-process.md)).
- New time-series/indicator tables include **as-of versioning fields** and AI tables the **audit-log** linkage (SPEC §9).
- One logical change per migration; descriptive slug; never edit a merged migration.

### 7.6 Tests
- Mirror source tree; name `test_*`. Critical logic has golden/grounding tests ([25](25-qa-testing-and-release-process.md)).
- No network in unit tests; use committed fixtures (split/bonus/delisted, golden series, golden payloads).

---

## 8. Commit, branch & PR standards

### 8.1 Conventional Commits
`type(scope): summary` — types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`.

```
feat(scanners): add delivery-% sub-score to volume-breakout scanner
fix(ai): block paraphrased "buy now" in guardrail engine
docs(13): document M3b score-validation evidence
```

### 8.2 Branches
- `main` is protected; no direct pushes.
- Branch per change: `feat/<scope>-<slug>`, `fix/<scope>-<slug>`, `docs/<n>-<slug>`.
- Small, single-purpose PRs; rebase before merge.

### 8.3 PR checklist
- [ ] Conventional-commit title; scope correct.
- [ ] Strict types pass (`tsc` / `mypy --strict`); lint clean.
- [ ] Tests added/updated; **critical logic (scoring / corp-action / AI grounding+guardrails) has tests** if touched.
- [ ] AI/prompt/model change → **verification harness GREEN** + golden dataset updated ([25 §1.3](25-qa-testing-and-release-process.md)).
- [ ] No blocked phrases / buy-leans / RA-gated content introduced (Mode-A) — guardrail suite green.
- [ ] Migration has tested `downgrade`; two-phase if destructive.
- [ ] **Docs updated** for any behavior change (the relevant `docs/NN-*.md`).
- [ ] `as_of` propagation preserved for user-facing values.
- [ ] No PII/secrets in logs.

---

## 9. Related documents

- [06 — Frontend Architecture](06-frontend-architecture.md)
- [09 — Backend Architecture](09-backend-architecture.md)
- [10 — API Contracts](10-api-contracts.md)
- [11 — Database Architecture](11-database-architecture.md)
- [13 — Scanner Engine & Scoring](13-scanner-engine-and-scoring.md)
- [14 — AI/LLM Agent Architecture](14-ai-llm-agent-architecture.md)
- [25 — QA, Testing & Release Process](25-qa-testing-and-release-process.md)
- [28 — Agentic Development Workflows](28-agentic-development-workflows.md)
- [30 — Decision Log](30-decision-log.md)
