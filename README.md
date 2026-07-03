# Saakshya

**AI-powered, evidence-first Indian equity research, market-intelligence, scanner, portfolio-intelligence and decision-support platform** for NSE/BSE markets.

> *Saakshya* (Sanskrit) means **evidence**. Every scanner result, score, AI insight, risk note and summary must be data-backed, explainable, and traceable. The AI layer **explains** deterministic signals — it never invents prices, numbers, news, targets, returns, or recommendations.

Saakshya is positioned as **research, analytics, scanning and decision support — not advice, not tips, and not guaranteed returns.** It launches in regulatory **Mode A** (pure analytics); recommendation-flavored features are gated behind SEBI Research-Analyst registration. See [SPEC.md](SPEC.md) for the full legal/correctness/economics rationale.

---

## Start here

| You are… | Read |
|---|---|
| **Any AI coding agent / Claude Code session** | [CLAUDE.md](CLAUDE.md) — the operating manual. Read it first, every session. |
| **Anyone (product, eng, design, compliance)** | [SPEC.md](SPEC.md) — the canonical, reconciled source of truth. |
| **Looking for a specific spec** | [docs/README.md](docs/README.md) — the full documentation index (30 files). |
| **Working with the code knowledge graph** | [.gitnexus.md](.gitnexus.md) → [docs/26](docs/26-gitnexus-knowledge-graph.md). |

---

## Repository structure

```
Saakshya/
├── CLAUDE.md          # Operating manual for AI/coding sessions (read first)
├── SPEC.md            # Canonical reconciled product + build specification
├── README.md          # This file
├── .gitnexus.md       # GitNexus knowledge-graph usage rules
├── .gitignore
└── docs/              # The product + engineering bible (30 modular specs)
    ├── README.md      # Documentation index
    ├── 01-product-overview.md … 30-decision-log.md
```

Application code is **implemented through the M7 milestone** (data pipeline, indicators, scanners, score validation, AI explanation layer, FastAPI API, and the Next.js web app) and validated by a green test suite. A **2026-07 stack reset** (decision log D-057/058/059) fixed the foundations: **AI** = Anthropic Claude only (Haiku/Sonnet); **market data** = Zerodha Kite Connect only; **storage** = polyglot **TimescaleDB (analytics core) + MongoDB (user/app documents)**, run locally via `docker compose`. See [SPEC.md §12](SPEC.md) and [docs/02 roadmap](docs/02-product-roadmap.md).

## Stack

- **Frontend:** Next.js (App Router) · React · TypeScript · Tailwind · Framer Motion · TanStack Query · Zustand · React Three Fiber (landing 3D) · TradingView Lightweight Charts / ECharts
- **Backend:** Python 3.11+ · FastAPI · (Celery · Redis in production)
- **Data:** Polars/Pandas/NumPy (no TA-Lib) · **Zerodha Kite Connect** (sole EOD source, D-058)
- **Storage:** **TimescaleDB** (analytics core — OHLC/indicators/scanners/AI/news, hypertables) · **MongoDB** (user/app documents) — polyglot, D-059 (DuckDB retired)
- **AI:** Anthropic SDK — **Claude Haiku** (`claude-haiku-4-5-20251001`) default / Sonnet premium, provider-abstracted (D-057)
- **Infra:** AWS · Docker · Kubernetes · Terraform · GitHub Actions · OpenTelemetry/Prometheus/Grafana/Sentry

## Local-first quick start (target — once code lands at milestone M0)

```bash
pyenv local 3.11.9
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # arm64 wheels, no TA-Lib
cp .env.example .env                    # then set ANTHROPIC_API_KEY
python scripts/run_pipeline.py          # ingest -> compute -> scan
pytest                                  # indicator + verification tests
uvicorn app.main:app --reload           # API at :8000
```

---

> **Not investment advice.** Saakshya is a research and decision-support tool. It summarizes publicly available data and SEBI positions as of mid-2026; confirm the current regulatory regime with qualified Indian securities counsel before launch. See [docs/21 compliance](docs/21-compliance-risk-and-guardrails.md).
