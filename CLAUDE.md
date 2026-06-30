# CLAUDE.md — Saakshya Operating Manual

**This file is the core operating manual for every Claude Code session and every AI coding session in this repository. Read it first, every time, before doing anything else.**

Saakshya (Sanskrit: **"evidence"**) is an AI-powered, **evidence-first** Indian equity research, market-intelligence, scanner, portfolio-intelligence and decision-support platform for NSE/BSE markets. The product is **research, analytics, scanning and decision support — not advice, not tips, not guaranteed returns.**

> **Canonical source of truth:** [SPEC.md](SPEC.md). It reconciles the full product vision with the legal / correctness / economics constraints. **Where any doc conflicts with SPEC.md, SPEC.md wins.** Where SPEC.md is silent, the `/docs` files govern.

---

## 1. Product vision (one paragraph)

Saakshya surfaces momentum, volume, sector strength, technical setups, news sentiment and risk signals across NSE/BSE equities from **end-of-day (EOD/T+1)** data, and uses AI to **explain deterministic, data-grounded signals** in plain language. The name means *evidence*, and that is the product: every output traces to visible data and explainable logic. Saakshya improves user judgment — it does not replace it, and it never tells a user what to buy or sell.

---

## 2. Non-negotiable product principles

1. **Evidence-first.** Every scanner result, score, AI insight, recommendation-like label, risk note, stock summary, portfolio summary, support/resistance zone and alert MUST be **explainable, data-backed and traceable** to the computed inputs that produced it. If it cannot be traced, it does not ship.
2. **AI explains evidence; AI does not invent it.** The AI layer MUST NOT invent or fabricate prices, numbers, financial facts, news, targets, returns, predictions-as-promises, or recommendations. It may only describe and explain the structured data it is given (see §5).
3. **Deterministic core, AI veneer.** Scanner scoring, indicators and risk logic are **rule-based and explainable** in v1. AI sits *on top* of verified data and never alters the numbers. ML ranking is a later phase and is always measurement-validated, never a return promise.
4. **Compliance is substance, not disclaimers.** SEBI reads *substance over form*. A disclaimer does not convert advisory output into education. See §3 and [docs/21](docs/21-compliance-risk-and-guardrails.md).
5. **Correctness is a feature.** A confidently-wrong stock product is worse than none. Corporate-action adjustment, as-of versioning, and scanner-score validation are first-class, not optional. See [docs/12](docs/12-data-ingestion-and-market-data.md), [docs/13](docs/13-scanner-engine-and-scoring.md).
6. **Suppress, don't guess.** When critical inputs are missing or low-confidence, suppress the AI summary / downgrade the data-confidence indicator. Never fill gaps with invention.

---

## 3. Compliance rules (read before writing any user-facing output)

Saakshya v1 operates in **Mode A (pure analytics tool)**. RA registration (Mode B) runs in parallel and is the gating dependency that later unlocks recommendation-flavored features. Full detail: [SPEC.md §2–§5](SPEC.md) and [docs/21](docs/21-compliance-risk-and-guardrails.md).

**Permitted (descriptive, non-directive):** "appears in the momentum scanner" · "trading above its 50-DMA" · "volume expanded 2× vs its 20-day average" · "news sentiment classified positive" · "historically a resistance zone" · "risk is elevated" · "evidence suggests" · "should be monitored" · always pair with "not investment advice."

**Prohibited in Mode A (RA-gated — do NOT build or emit until RA is in force):**
- Per-stock **entry / target / stop-loss / invalidation** levels.
- **"Candidate" labels that function as buy-leans**, ranked "what to buy" briefs, "what to buy/sell next session."
- Behaviour-derived per-stock suggestions ("because you view banking, consider HDFC Bank") — that is Mode C / IA.

**Prohibited in EVERY mode, always (block at output time):** "buy now," "sell now," guarantee, assured/confirmed target, "sure-shot," "risk-free," "multibagger," "best stock for you," "must invest," or any implied/explicit return claim.

**If a requested feature or output crosses these lines, STOP and flag it. Do not implement it under a disclaimer.**

---

## 4. AI output boundaries

- The AI receives a **structured payload of computed facts only** (metrics, scanner tags, news summaries, risk markers) and may reference nothing else.
- A **runtime verification harness** checks every number and named fact in AI output against the payload and **blocks or regenerates on mismatch**. Never ship an AI path without it.
- Every generation is **audit-logged** (prompt, input payload, model + prompt version, output, guardrail result).
- The **blocked-phrase/pattern list is enforced at output time**, not just in the prompt, and is versioned in the admin console.
- Default model is **Claude Haiku** (`claude-haiku-4-5-20251001`) for repetitive summarization, behind a provider abstraction; reserve a premium Claude model for complex synthesis. Under Mode B, **disclose AI use** to clients.

Details: [docs/14](docs/14-ai-llm-agent-architecture.md), [docs/21](docs/21-compliance-risk-and-guardrails.md).

---

## 5. MANDATORY reading map — read these BEFORE making any change

**No code may be generated before reading the relevant documentation below.** Always start with [SPEC.md](SPEC.md), then read the rows that match your change.

| If you are changing… | Read first (in order) |
|---|---|
| **Product / scope / features** | [SPEC.md](SPEC.md) → [docs/01 product overview](docs/01-product-overview.md) → [docs/02 roadmap](docs/02-product-roadmap.md) → [docs/04 feature modules](docs/04-feature-modules.md) (the relevant module PRD) |
| **Frontend (UI/screens/routes)** | [docs/07 design system](docs/07-design-system-and-ui-ux.md) → [docs/08 screen-by-screen](docs/08-screen-by-screen-documentation.md) → [docs/05 IA & URL routes](docs/05-information-architecture-and-url-paths.md) → [docs/06 frontend architecture](docs/06-frontend-architecture.md) |
| **Backend (services/logic)** | [docs/09 backend architecture](docs/09-backend-architecture.md) → [docs/10 API contracts](docs/10-api-contracts.md) → [docs/11 database architecture](docs/11-database-architecture.md) |
| **AI / LLM / agents / prompts** | [docs/14 AI/LLM/agent architecture](docs/14-ai-llm-agent-architecture.md) → [docs/21 compliance & guardrails](docs/21-compliance-risk-and-guardrails.md) → (prompt rules + guardrails within both) |
| **Scanners / scoring** | [docs/13 scanner engine & scoring](docs/13-scanner-engine-and-scoring.md) → [docs/15 ML & data science](docs/15-machine-learning-and-data-science.md) |
| **Database / schema** | [docs/11 database architecture](docs/11-database-architecture.md) → migration rules in [docs/27 coding standards](docs/27-coding-standards.md) |
| **Data pipelines / ingestion** | [docs/12 data ingestion & market data](docs/12-data-ingestion-and-market-data.md) → [docs/11 database](docs/11-database-architecture.md) |
| **Portfolio / risk / alerts** | [docs/16 portfolio & risk](docs/16-portfolio-and-risk-engine.md) → [docs/17 alerts](docs/17-alerts-and-notifications.md) |
| **News / sentiment / corp actions** | [docs/18 news sentiment & corporate actions](docs/18-news-sentiment-and-corporate-actions.md) |
| **Backtesting / strategy builder** | [docs/19 backtesting & strategy builder](docs/19-backtesting-and-strategy-builder.md) |
| **Infrastructure / deployment** | [docs/22 infra, DevOps & observability](docs/22-infrastructure-devops-and-observability.md) → [docs/23 security](docs/23-security-auth-and-privacy.md) |
| **Anything compliance-touching** | [docs/21 compliance, risk & guardrails](docs/21-compliance-risk-and-guardrails.md) **FIRST**, before any other doc |
| **Admin panel** | [docs/20 admin panel](docs/20-admin-panel.md) |
| **QA / tests / release** | [docs/25 QA, testing & release](docs/25-qa-testing-and-release-process.md) |

Full index: [docs/README.md](docs/README.md). Ordered, feature-wise **build plan** (how/what-order, with task checklists, tests, gates): [docs/steps/README.md](docs/steps/README.md).

---

## 6. GitNexus rule — query the graph before complex changes

For any non-trivial code change (multi-file, refactor, new feature, backend/DB/AI/pipeline change), **use the GitNexus knowledge graph first** to query affected modules, inspect the dependency graph, check call chains, and understand the impact radius — *then* modify code. See [.gitnexus.md](.gitnexus.md) and [docs/26](docs/26-gitnexus-knowledge-graph.md). The matching skills (`gitnexus-exploring`, `gitnexus-impact-analysis`, `gitnexus-debugging`, `gitnexus-refactoring`) are the preferred way to do this.

---

## 7. Coding rules

- **Stack of record.** Frontend: Next.js (App Router) + React + TypeScript (strict) + Tailwind + Framer Motion + TanStack Query + Zustand. Backend: Python 3.11+ + FastAPI + Celery + Redis. Data: Polars/Pandas/NumPy, **no TA-Lib** (vectorized / pandas-ta). DB: PostgreSQL + TimescaleDB (local-first: **DuckDB**), ClickHouse, OpenSearch, pgvector, S3. AI: LangGraph + LlamaIndex + Anthropic SDK. See [docs/06](docs/06-frontend-architecture.md), [docs/09](docs/09-backend-architecture.md).
- **Local-first first.** The MVP is built and validated on one M1 Mac (DuckDB, vectorized indicators, FastAPI, Claude Haiku) before any cloud spend — see [SPEC.md §12](SPEC.md). Do not stand up the full cloud stack to ship the Mode-A core.
- **Determinism.** Financial calculations and scanner scoring must be deterministic and unit-tested against known series. Critical logic (scoring, corporate-action adjustment, AI grounding/guardrails) MUST have tests.
- **Standard API envelope** (`data` / `meta` with `as_of` + `data_confidence` / `error`) — see [docs/10](docs/10-api-contracts.md), [docs/27](docs/27-coding-standards.md).
- **Type everything.** Strict TypeScript; Python type hints + mypy. No silent `any`.
- **Secrets via env only.** Never hard-code keys. `ANTHROPIC_API_KEY` and all secrets come from env / `.env` (gitignored). See [docs/23](docs/23-security-auth-and-privacy.md).
- Full standards: [docs/27 coding standards](docs/27-coding-standards.md).

## 8. Design rules

Dark-first, premium, AI-native, evidence-led. Use the tokens and component patterns in [docs/07](docs/07-design-system-and-ui-ux.md). Animations (Framer Motion) must be polished but must **never harm readability, performance or financial seriousness**; always honor `prefers-reduced-motion`. Every insight surface must have an **evidence affordance** (a way to see the data behind the claim).

For all UI/visual work, use the **`ui-ux-pro-max`** design skill (installed in `.claude/skills/`; reinstall via `npx -y ui-ux-pro-max-cli@latest init --ai claude`) — it covers styles, color palettes, typography, **3D/Three.js**, and UI review. Its suggestions are advisory: they must still obey the Mode-A evidence-led constraints, tokens, and motion rules in [docs/07](docs/07-design-system-and-ui-ux.md) (no buy-lean styling, no certainty signals).

## 9. Documentation rules

- Docs are the source of truth. **When behavior changes, update the relevant `/docs` file in the same change.** Code and docs drift = a bug.
- New product decisions go in [docs/30 decision log](docs/30-decision-log.md). Compliance-affecting changes also update [docs/21](docs/21-compliance-risk-and-guardrails.md).
- Keep terminology consistent with [docs/29 glossary](docs/29-glossary.md).

## 10. Branch & commit rules

- Never commit directly to `main`. Branch per change: `feat/…`, `fix/…`, `docs/…`, `chore/…`, `refactor/…`.
- **Conventional Commits** for messages. Open a PR; the PR description states what changed, which docs were updated, and which tests were added. See [docs/27](docs/27-coding-standards.md) for the PR checklist.
- **Only commit or push when the user asks.** Do not auto-commit.

## 11. Testing rules

- Add/extend tests with every behavior change. Layers: unit, integration, API-contract, scanner-logic (golden series), data-quality, AI-output (grounding/number-traceability), guardrail (blocked-phrase enforcement), visual-regression, E2E, load, security — see [docs/25](docs/25-qa-testing-and-release-process.md).
- The **AI verification harness must be green** and the **compliance design-review checklist** must pass before any user-facing output ships.

---

## 12. The standard change workflow (every task)

1. **Read** [SPEC.md](SPEC.md) + the reading-map rows for your change (§5). No code before this.
2. **Query GitNexus** for impact radius on non-trivial changes (§6).
3. **Plan** the change; identify affected files, APIs, tables, docs.
4. **Compliance check** (§3): does any output cross a Mode-A boundary? If yes, stop and flag.
5. **Implement** following the coding/design rules.
6. **Update docs** that the change affects (§9).
7. **Add/Update tests**; run checks; ensure AI harness + guardrails green (§11).
8. **Summarize** what changed, docs updated, tests added.

Detailed per-change-type workflows: [docs/28 agentic development workflows](docs/28-agentic-development-workflows.md).

---

**Remember: Saakshya means evidence. If you cannot show the evidence behind an output, do not ship the output.**

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **Saakshya** (2827 symbols, 4559 relationships, 36 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/Saakshya/context` | Codebase overview, check index freshness |
| `gitnexus://repo/Saakshya/clusters` | All functional areas |
| `gitnexus://repo/Saakshya/processes` | All execution flows |
| `gitnexus://repo/Saakshya/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
