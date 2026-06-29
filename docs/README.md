# Saakshya Documentation — Index

This `/docs` directory is the **Saakshya product & engineering bible**: a modular, implementation-ready source of truth for product managers, frontend/backend/data/AI/ML engineers, designers, QA, DevOps, compliance reviewers, and future AI coding agents.

> **Read before anything else:** [CLAUDE.md](../CLAUDE.md) (operating manual) and [SPEC.md](../SPEC.md) (canonical reconciled spec). Where any doc here conflicts with `SPEC.md`, **SPEC.md wins**.
>
> **Building it?** These docs say *what* to build. The ordered, feature-wise **implementation step plan** (*how* and *in what order*) lives in **[steps/](steps/README.md)** — start there.

## How to use this documentation

- Each file is a standalone, deep specification. Every feature defines its **backend dependency, frontend dependency, data dependency, and acceptance criteria**.
- The [CLAUDE.md reading map](../CLAUDE.md) tells you **which files to read for which kind of change** — follow it. **No code before reading the relevant docs.**
- Cross-links use relative paths between files; follow them to trace a feature end-to-end (module → screen → API → table → scanner/AI logic → compliance).
- All content honors the non-negotiables: **Mode-A scope**, **evidence-first**, **AI explains-never-invents**, **EOD/T+1 first**, **rule-based explainable scanners**, and the **always-prohibited language** list.

## The files

### Product & planning
| File | Purpose |
|---|---|
| [01-product-overview.md](01-product-overview.md) | What Saakshya is: name meaning, promise, market, philosophy, vision, differentiation, the 10 product pillars. |
| [02-product-roadmap.md](02-product-roadmap.md) | Full V1–V9 roadmap mapped to SPEC's risk-first Phase 0–5, with objective/value/dependencies/acceptance per version. |
| [03-user-personas-and-journeys.md](03-user-personas-and-journeys.md) | 7 personas + 11 detailed user journeys. |
| [04-feature-modules.md](04-feature-modules.md) | Every product module (26) with deps, states, personalization, analytics, regulatory mode. |

### Information architecture, frontend & design
| File | Purpose |
|---|---|
| [05-information-architecture-and-url-paths.md](05-information-architecture-and-url-paths.md) | Full IA + every public/auth/admin route + API naming principles. |
| [06-frontend-architecture.md](06-frontend-architecture.md) | Next.js App Router architecture, RSC vs client, state, caching, perf, a11y, frontend coding rules. |
| [07-design-system-and-ui-ux.md](07-design-system-and-ui-ux.md) | Dark-first, evidence-led design system: tokens, components, Framer Motion animation principles. |
| [08-screen-by-screen-documentation.md](08-screen-by-screen-documentation.md) | Every screen: layout, sections, states, mobile/desktop, animation, analytics events. |

### Backend, API, data
| File | Purpose |
|---|---|
| [09-backend-architecture.md](09-backend-architecture.md) | All backend services, responsibilities, dependencies, EOD pipeline orchestration. |
| [10-api-contracts.md](10-api-contracts.md) | Every API group with payloads, errors, auth, cache, rate limits; the standard envelope. |
| [11-database-architecture.md](11-database-architecture.md) | Store choices + all tables (columns/keys/indexes), partitioning, retention, migrations, as-of versioning. |
| [12-data-ingestion-and-market-data.md](12-data-ingestion-and-market-data.md) | EOD/T+1 pipeline, layered DataSource adapter, corporate-action adjustment, data-quality checks. |

### Intelligence: scanners, AI, ML
| File | Purpose |
|---|---|
| [13-scanner-engine-and-scoring.md](13-scanner-engine-and-scoring.md) | The deterministic scanner engine: 13 scanners, scoring weights, formulas, output + AI-explanation payloads. |
| [14-ai-llm-agent-architecture.md](14-ai-llm-agent-architecture.md) | LangGraph/LlamaIndex, 8 agents, grounding contract, runtime verification harness, guardrails, audit log. |
| [15-machine-learning-and-data-science.md](15-machine-learning-and-data-science.md) | Rule-based → ML evolution, features, evaluation metrics, MLOps, the M3b score-validation spike. |

### Domain engines
| File | Purpose |
|---|---|
| [16-portfolio-and-risk-engine.md](16-portfolio-and-risk-engine.md) | Holdings, P&L, allocation/concentration/risk, health score, Mode-A portfolio AI summary. |
| [17-alerts-and-notifications.md](17-alerts-and-notifications.md) | All alert types, EOD vs live behavior, channels, templates, throttling. |
| [18-news-sentiment-and-corporate-actions.md](18-news-sentiment-and-corporate-actions.md) | News ingestion, entity resolution, finance-tuned sentiment, corporate-announcement intelligence. |
| [19-backtesting-and-strategy-builder.md](19-backtesting-and-strategy-builder.md) | No-code strategy builder + backtesting with the mandatory integrity controls. |

### Platform, compliance, operations
| File | Purpose |
|---|---|
| [20-admin-panel.md](20-admin-panel.md) | Admin modules + RBAC roles/permissions. |
| [21-compliance-risk-and-guardrails.md](21-compliance-risk-and-guardrails.md) | **The compliance contract:** modes, prohibited/safe language, guardrail pipeline, audit, SEBI context. |
| [22-infrastructure-devops-and-observability.md](22-infrastructure-devops-and-observability.md) | AWS architecture, IaC, CI/CD, observability, AI-spend meter, DR. |
| [23-security-auth-and-privacy.md](23-security-auth-and-privacy.md) | Authn/authz, encryption, PII, AI-log security, threat model. |

### Growth, quality, process
| File | Purpose |
|---|---|
| [24-analytics-seo-and-growth.md](24-analytics-seo-and-growth.md) | Analytics events, trust KPIs, Mode-A-safe SEO, growth loops. |
| [25-qa-testing-and-release-process.md](25-qa-testing-and-release-process.md) | Test layers (incl. scanner/data-quality/AI-grounding/guardrail tests), release checklist. |
| [26-gitnexus-knowledge-graph.md](26-gitnexus-knowledge-graph.md) | Install/configure/use GitNexus; per-change-type graph workflows; setup status. |
| [27-coding-standards.md](27-coding-standards.md) | Per-layer standards, naming, typing, API envelope, commits, branches, PR checklist. |
| [28-agentic-development-workflows.md](28-agentic-development-workflows.md) | The 9-step agent loop + per-change-type workflows for AI coding agents. |

### Reference
| File | Purpose |
|---|---|
| [29-glossary.md](29-glossary.md) | All product/finance/technical/AI/data terms, with Mode-A framing and RA-gating flags. |
| [30-decision-log.md](30-decision-log.md) | Append-only decision log, seeded with the 14 foundational decisions. |

---

*Keep these docs in sync with the code: when behavior changes, update the relevant file in the same change. See [CLAUDE.md §9](../CLAUDE.md).*
