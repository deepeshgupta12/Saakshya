# 25 — QA, Testing & Release Process

> One-line purpose: The full test pyramid (unit → E2E → load → security), the correctness-critical layers unique to Saakshya (scanner-logic golden series, data-quality, AI grounding, guardrail enforcement), the test-data strategy, and the release pipeline with the SPEC validation gates baked in.
> Read first: [SPEC.md](../SPEC.md)

Related: [Scanner Engine & Scoring](13-scanner-engine-and-scoring.md) · [AI/LLM Agent Architecture](14-ai-llm-agent-architecture.md) · [Data Ingestion & Market Data](12-data-ingestion-and-market-data.md) · [Compliance & Guardrails](21-compliance-risk-and-guardrails.md) · [Coding Standards](27-coding-standards.md) · [Infrastructure & Observability](22-infrastructure-devops-and-observability.md) · [Decision Log](30-decision-log.md)

---

## 0. Principles (read before testing)

1. **Correctness is testable, not aspirational.** SPEC §6 promotes correctness, compliance, economics, and trust to **first-class, hard requirements**. Each maps to a **test layer and a release gate** (§6). "All critical logic MUST be documented and covered by tests" — scanner scoring, corporate-action adjustment, AI grounding/guardrails ([27](27-coding-standards.md)).
2. **A compliance violation is a release blocker, not a warning.** Blocked-phrase enforcement is tested **at output time** (SPEC §6.9), not just in prompts. A guardrail-test failure fails the build.
3. **An inflated backtest is a compliance failure.** Backtesting integrity tests (survivorship / look-ahead / point-in-time) are correctness *and* compliance tests (SPEC §6.3).
4. **AI tests assert grounding, not vibes.** Every number/named fact in AI output must trace to its payload (SPEC §6.6). The verification harness must be **green** to release.
5. **EOD/T+1 shapes testing too.** Data-quality and pipeline tests run against the overnight batch cadence and `as_of` semantics (SPEC §6.2, §8).

---

## 1. Test layers

| Layer | Scope | Tooling | Runs in CI | Gate |
|---|---|---|---|---|
| **Unit** | Pure functions: indicators, scoring math, adjusters, utils | `pytest` (py), `vitest` (ts) | every PR | required |
| **Integration** | Module boundaries: repo↔DB, pipeline stages, adapter↔storage | `pytest` + ephemeral DuckDB/Postgres | every PR | required |
| **API contract** | Request/response shapes match [10-api-contracts.md](10-api-contracts.md) | `schemathesis` / OpenAPI diff | every PR | required |
| **Scanner-logic (golden series)** | Scanner score + reasons + risk flags vs locked golden outputs | `pytest` + fixture series | every PR | required (critical) |
| **Data-quality** | Missing candles, abnormal jumps, duplicates, delisted, volume sanity | `pytest` + Great-Expectations-style checks | every PR + nightly | required (critical) |
| **AI-output (grounding/number-traceability)** | Every number/fact in AI output traces to payload; suppression when inputs missing | verification harness + golden dataset | every PR touching AI + nightly | required (critical) |
| **Guardrail (blocked-phrase at output time)** | No blocked phrase escapes any user-visible surface (AI, copy, SEO HTML) | guardrail engine over rendered output | every PR | **blocker** |
| **Visual regression** | Key screens pixel/DOM diff | Playwright + snapshot | every PR (UI) | required |
| **E2E** | User journeys end-to-end | **Playwright** | every PR (smoke) + nightly (full) | required |
| **Load** | EOD pipeline window; API P95 under tier load | `k6` / `locust` | nightly + pre-release | required pre-release |
| **Security** | Authz, injection, secrets, dependency CVEs, prompt-injection | SAST + `pip-audit`/`npm audit` + DAST | PR (SAST) + pre-release (DAST) | required pre-release |

### 1.1 Scanner-logic tests (golden series)

The riskiest logic in the product. Scanner score + sub-scores + reasons + risk flags are deterministic given an input series — so we **lock golden outputs**.

- **Golden series fixtures**: hand-built and real (corp-action-adjusted) OHLCV windows with known expected outcomes (e.g., a clean uptrend that must score high momentum; a post-split series that must NOT register a false breakdown).
- Assert: numeric sub-scores within tolerance, **exact** reason strings (Mode-A phrasing), exact risk-flag set.
- **Missing-sub-score** cases assert the sub-score is marked **neutral**, not guessed (SPEC §6.2, M3 gate).
- Cross-link the **M3b score-validation** evidence ([13](13-scanner-engine-and-scoring.md)): golden tests prove *stability*; M3b proves the score *carries signal* (SPEC §6.5).

### 1.2 Data-quality tests

Run as code (CI) and as runtime monitors ([22](22-infrastructure-devops-and-observability.md)):

| Check | Asserts | On failure |
|---|---|---|
| Missing candles | No gaps in trading-day calendar per symbol | quarantine + alert |
| Abnormal jumps | Day-over-day move beyond threshold is a **corp action**, not bad data | flag for corp-action reconcile |
| Duplicate symbols | One row per (symbol, trading_date) | dedup + alert |
| Delisted / merged | Series ends cleanly; not silently nulled | mark delisted |
| Volume sanity | Non-negative; delivery% ≤ 100% | quarantine |
| Reconciliation | EOD series reconciles vs a 2nd source on a sample (SPEC §6.1) | block publish |

These implement the **detect → quarantine → correct → re-emit** workflow (SPEC §6.2). A correction must re-emit dependent indicators **and** AI summaries.

### 1.3 AI-output tests (grounding & number-traceability)

The **verification harness** (SPEC §6.6) is the gate:

- **Payload-contract test**: AI receives only the structured payload; any reference to a number/name not in the payload → **fail** (block/regenerate).
- **Number-traceability test**: extract every numeric and named entity from output; assert each maps to a payload field.
- **Suppression test**: when a critical input is missing, the summary is **suppressed** (non-AI fallback), never guessed.
- **Golden dataset + regression**: a fixed set of payloads with approved outputs; runs on **every prompt/model change** (SPEC §6.6, [27](27-coding-standards.md) AI-prompt rules). A regression (new fabrication, drifted phrasing into directive language) fails CI.
- **Audit-log test**: every generation writes prompt + input data + model version + output (SPEC §6.6).

### 1.4 Guardrail tests (blocked-phrase, output-time)

- A versioned blocked-phrase/pattern list (SPEC §6.9) is asserted to **block at output time** across AI output, UI copy, and **rendered SEO HTML** ([24 §3.2](24-analytics-seo-and-growth.md)).
- Adversarial cases: paraphrases of "buy now", leetspeak, split tokens, multilingual variants — must still block.
- Mode-A neutralization swaps (SPEC §5) are asserted: "candidate" → "appears in the scanner", no entry/target/SL on Mode-A surfaces.
- **This layer is a hard blocker** — any escape fails the build.

---

## 2. Test data strategy

| Fixture set | Purpose |
|---|---|
| **Split/bonus/rights names** | Corporate-action correctness (SPEC §6.1): each fixture is a real or synthetic series spanning a 1:1 bonus, 1:2 split, rights issue, symbol change. Tests assert adjusted series has **no false crash** and indicators stay continuous. |
| **Delisted/merged names** | Survivorship-bias control for backtesting (SPEC §6.3): series that end mid-window must be includable. |
| **Golden indicator series** | Known RSI/MA/ATR/MACD outputs vs a reference for unit tests (M2 gate). |
| **Missing/dirty data** | Gaps, duplicates, negative volume, >100% delivery — drives §1.2 checks. |
| **AI golden payloads** | Approved payload→output pairs for the verification harness (§1.3). |
| **Blocked-phrase corpus** | Positive (must block) + adversarial paraphrases + negative (must NOT over-block legitimate descriptive copy). |

- Fixtures are **point-in-time / as-of stamped** (SPEC §6.2) so reproducibility is testable.
- Never test against live vendor data in CI (licensing, flakiness); use frozen, committed fixtures.

---

## 3. Environments & staging sign-off

| Env | Data | AI | Purpose |
|---|---|---|---|
| **Local** | DuckDB fixtures (SPEC §12) | Claude Haiku, key via env | dev + M0–M6 milestones |
| **CI** | Frozen fixtures only | mocked/replayed AI + harness | gate every PR |
| **Staging** | Recent EOD snapshot (licensed feed) | real AI, real guardrails | **staging sign-off** before prod |
| **Production** | Licensed feed | real AI + audit log | live |

**Staging sign-off checklist** (must pass before promotion):
- Full E2E suite green; visual regression reviewed.
- Verification harness green on staging payloads.
- Guardrail suite green over staging-rendered output + SEO HTML.
- Data-quality + reconciliation green on the staging EOD snapshot.
- **Compliance design-review** sign-off recorded (SPEC §3, §5, §7).
- Load test meets P95 + EOD-window targets.

---

## 4. Release pipeline

```mermaid
flowchart TB
  PR[Pull request] --> LINT[Lint + type-check\nmypy / tsc strict]
  LINT --> UNIT[Unit + integration + API contract]
  UNIT --> CRIT[Critical-logic gates:\nscanner golden · data-quality ·\nAI grounding harness · guardrails]
  CRIT --> VIS[Visual regression + E2E smoke]
  VIS --> SEC[SAST + dependency audit]
  SEC --> REVIEW{PR checklist + code review\n(incl. compliance review if user-facing)}
  REVIEW -- approved --> MERGE[Merge to main]
  MERGE --> STAGE[Deploy to staging]
  STAGE --> SGATE{Staging sign-off:\nE2E full · load · DAST ·\ncompliance design-review ·\nharness GREEN}
  SGATE -- pass --> CANARY[Canary / progressive prod]
  CANARY --> MON[Prod monitoring:\ndata health · AI grounding ·\nguardrail blocks · AI-spend]
  MON -- regression --> RB[Rollback / feature-flag off]
  MON -- healthy --> DONE[Release complete]
  SGATE -- fail --> FIX[Fix → re-run]
```

### 4.1 Rollback plan

- **Feature-flag first**: every user-facing change ships behind a flag; the fastest rollback is a flag flip (no redeploy). RA-gated paths are flag-only and absent from the v1 router ([05](05-information-architecture-and-url-paths.md)).
- **Versioned artifacts**: previous container image + DB migration are retained; rollback redeploys the prior image.
- **Migrations are reversible**: every Alembic migration has a tested `downgrade` ([27](27-coding-standards.md)); destructive migrations are two-phase (expand → contract).
- **Data corrections** use the detect→quarantine→correct→re-emit workflow, not a code rollback (SPEC §6.2).
- **AI rollback**: prompt/model versions are pinned; revert to the last harness-green prompt version via the admin prompt registry ([20 — Admin Panel], [05 §4](05-information-architecture-and-url-paths.md)).

### 4.2 Production monitoring (release-relevant signals)

- **Data health**: missing candles, jumps, reconciliation status, data-confidence ([22](22-infrastructure-devops-and-observability.md)).
- **AI quality**: grounding rate, fallback rate, **disagree-with-AI** rate ([24 §2](24-analytics-seo-and-growth.md)) — a spike is a release-quality alert.
- **Guardrail blocks**: count of blocked outputs; a sudden rise post-release ⇒ investigate.
- **AI-spend meter**: against the monthly ceiling (SPEC §6.8); breach ⇒ graceful degradation + alert.
- **Trust KPI T1/T4** drift ⇒ stop-the-line.

---

## 5. Release checklist (per release)

- [ ] All required CI layers green (unit → security).
- [ ] **Scanner golden-series** tests green; M3b validation evidence current ([13](13-scanner-engine-and-scoring.md)).
- [ ] **Data-quality + reconciliation** green on staging EOD snapshot.
- [ ] **AI verification harness GREEN** (grounding + number-traceability + suppression) on any AI/prompt/model change.
- [ ] **Guardrail suite GREEN** over AI output, UI copy, and rendered SEO HTML.
- [ ] **Backtesting integrity** tests green if backtesting touched (survivorship/look-ahead/point-in-time, SPEC §6.3).
- [ ] **Compliance design-review gate** signed off for user-facing changes (Mode-A language, no buy-leans, no RA-gated content leaking — SPEC §3, §5, §7).
- [ ] Docs updated for any behavior change ([28 — Agentic Workflows](28-agentic-development-workflows.md), [27](27-coding-standards.md)).
- [ ] Migrations have tested `downgrade`; rollout is flag-gated.
- [ ] Load + P95 + EOD-window targets met.
- [ ] Monitoring dashboards + alerts confirmed for new surfaces.

---

## 6. Mapping to SPEC validation gates

| SPEC gate | What proves it | Test layers | Release gate |
|---|---|---|---|
| **Correctness** (SPEC §6.1–6.5) | Indicators reconcile; corp actions correct; scores carry signal | unit, integration, scanner-golden, data-quality, M3b evidence | block on fail |
| **Compliance** (SPEC §3, §5, §6.9) | No blocked phrase at output; Mode-A language; no RA-gated leak | guardrail tests, compliance design-review | **hard blocker** |
| **Economics** (SPEC §6.8, §11) | AI spend within ceiling; latency within EOD window | load tests, AI-spend monitor | block pre-release |
| **Trust** (SPEC §6.2, §6.6) | Grounding ~100%; suppression on missing input; T1↓/T2↑ | AI grounding harness, data-quality, trust KPIs | harness GREEN |

---

## 7. Related documents

- [12 — Data Ingestion & Market Data](12-data-ingestion-and-market-data.md)
- [13 — Scanner Engine & Scoring](13-scanner-engine-and-scoring.md)
- [14 — AI/LLM Agent Architecture](14-ai-llm-agent-architecture.md)
- [19 — Backtesting & Strategy Builder](19-backtesting-and-strategy-builder.md)
- [21 — Compliance, Risk & Guardrails](21-compliance-risk-and-guardrails.md)
- [22 — Infrastructure, DevOps & Observability](22-infrastructure-devops-and-observability.md)
- [27 — Coding Standards](27-coding-standards.md)
- [28 — Agentic Development Workflows](28-agentic-development-workflows.md)
- [30 — Decision Log](30-decision-log.md)
