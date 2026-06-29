# 29 — Glossary

> One-line purpose: The single source of truth for every product, finance, technical, AI, and data-science term used across Saakshya — with category, a Mode-A-correct definition, and related docs.
> Read first: [SPEC.md](../SPEC.md)

Related: [Product Overview](01-product-overview.md) · [Scanner Engine & Scoring](13-scanner-engine-and-scoring.md) · [AI/LLM Agent Architecture](14-ai-llm-agent-architecture.md) · [Portfolio & Risk Engine](16-portfolio-and-risk-engine.md) · [Compliance & Guardrails](21-compliance-risk-and-guardrails.md) · [Decision Log](30-decision-log.md)

---

## 0. How to use this glossary

- **Definitions are Mode-A-correct.** Where a term could imply a recommendation, the definition states the **descriptive** framing Saakshya uses and flags any RA-gating (SPEC §3–§5). These definitions are also the source text for the public **market glossary pages** ([24 §3.1](24-analytics-seo-and-growth.md)) — keep them buy-lean-free.
- **Categories:** `Product` · `Finance` · `Technical` (indicators/chart concepts) · `AI` · `Data` (data-science / data-engineering) · `Regulatory`.
- One concept per row; alphabetical.

---

## 1. Terms

| Term | Category | Definition | Related docs |
|---|---|---|---|
| **Advance-decline (A/D)** | Finance | Market-breadth measure: the count of advancing stocks minus declining stocks over a session/period. Descriptive context for market health, never a buy/sell signal. | [01](01-product-overview.md) |
| **ADX (Average Directional Index)** | Technical | Indicator (0–100) measuring **trend strength** regardless of direction; higher = stronger trend. Wilder-smoothed, EOD-computable; `adx_14` in `technical_indicators`. Used descriptively in scanners/risk (≥25 strong, <20 ranging), never as a buy/sell trigger. | [13](13-scanner-engine-and-scoring.md), [11](11-database-architecture.md) |
| **Agent** | AI | A bounded AI workflow that performs a step (e.g., market-brief, stock-research, compliance-review). Each agent's **output** must pass Mode-A guardrails and grounding (SPEC §4, §6.6). Infrastructure compliance-review agent is required. | [14](14-ai-llm-agent-architecture.md) |
| **As-of versioning** | Data | Point-in-time storage so any displayed value is reproducible for the date it was shown; corrections re-emit dependents (SPEC §6.2). Carried as `as_of` on time-series, indicators, and API responses. | [11](11-database-architecture.md), [12](12-data-ingestion-and-market-data.md) |
| **ATR (Average True Range)** | Technical | Volatility measure: the average of true range over N periods. Feeds risk flags ("elevated short-term volatility"), not stop-loss levels (those are RA-gated). | [13](13-scanner-engine-and-scoring.md), [16](16-portfolio-and-risk-engine.md) |
| **Audit log (AI generation)** | AI | First-class record of prompt + input payload + model version + user-visible output for every AI generation (SPEC §6.6, §9). Linked from analytics via `audit_id`. | [14](14-ai-llm-agent-architecture.md), [24](24-analytics-seo-and-growth.md) |
| **Backtesting** | Data | Simulating a strategy on historical data. Ships **only** with integrity controls (survivorship, look-ahead, point-in-time, realistic fills); an inflated backtest is an implied-performance claim (SPEC §6.3). Phase 4. | [19](19-backtesting-and-strategy-builder.md) |
| **Bollinger Bands** | Technical | A moving average with bands at ±k standard deviations; describes volatility and relative price extension. Descriptive only. | [13](13-scanner-engine-and-scoring.md) |
| **Breakdown** | Technical | Price moving below a historically significant level. Saakshya reports the **event** ("broke below its 50-DMA"); no "sell the breakdown" phrasing (SPEC §5). | [13](13-scanner-engine-and-scoring.md) |
| **Breakout** | Technical | Price moving above a historically significant level, often with volume expansion. Reported as an event with a **false-breakout risk flag**; no "buy the breakout" phrasing (SPEC §4, §5). | [13](13-scanner-engine-and-scoring.md) |
| **Calmar ratio** | Finance | Return divided by maximum drawdown; a risk-adjusted performance measure shown only in integrity-controlled backtests, framed as measurement (SPEC §6.3). | [19](19-backtesting-and-strategy-builder.md) |
| **Corporate action** | Finance | Issuer event affecting the series: split, bonus, dividend, rights, merger, symbol change. Must be adjusted consistently or every indicator/backtest is corrupted (SPEC §6.1) — its own engineering workstream. | [12](12-data-ingestion-and-market-data.md), [18](18-news-sentiment-and-corporate-actions.md) |
| **Data-confidence indicator** | Data | User-visible signal of how reliable a displayed value is, derived from data-quality checks; AI summaries are **suppressed, not guessed**, when critical inputs are missing (SPEC §6.2). | [12](12-data-ingestion-and-market-data.md), [22](22-infrastructure-devops-and-observability.md) |
| **Delivery percentage** | Finance | Share of traded volume taken to delivery (vs intraday squared-off), from NSE `sec_bhavdata`. Strengthens the volume-breakout scanner (SPEC §8). | [12](12-data-ingestion-and-market-data.md), [13](13-scanner-engine-and-scoring.md) |
| **DMA / SMA / EMA** | Technical | Moving averages. **SMA** = simple (equal-weighted) mean over N days; **EMA** = exponential (recent-weighted); **DMA** = "day moving average" (e.g., 50-DMA), commonly an SMA over N trading days. Descriptive trend context. | [13](13-scanner-engine-and-scoring.md) |
| **Drawdown** | Finance | Peak-to-trough decline of an equity curve over a period; max drawdown is a core backtest risk metric (SPEC §6.3). | [19](19-backtesting-and-strategy-builder.md) |
| **Embedding** | AI | A vector representation of text used for semantic search/retrieval (RAG). Production-stack search/vector layer (pgvector/OpenSearch); deferred in local-first (SPEC §9). | [14](14-ai-llm-agent-architecture.md) |
| **EOD (End-of-day)** | Data | Market data captured after the session close; Saakshya is **EOD-first (T+1)** in v1 (SPEC §8). Suits swing trading, research, portfolio monitoring; avoids live-data licensing + compliance load. | [12](12-data-ingestion-and-market-data.md) |
| **Feature store** | Data | A managed store of computed features for ML, serving consistent point-in-time features to training and inference (Phase 4+). | [15](15-machine-learning-and-data-science.md) |
| **IA (Investment Adviser)** | Regulatory | SEBI-registered role permitting **personalized, client-specific advice** ("given your portfolio, do X") — Mode C. Strictest regime; **out of scope until registered** (SPEC §2). | [21](21-compliance-risk-and-guardrails.md) |
| **Invalidation zone** | Technical | The price area where a setup's thesis is considered void. **RA-gated (Mode B):** advisory-in-substance, **not shown in Mode A** (SPEC §4, §5). | [21](21-compliance-risk-and-guardrails.md) |
| **Learning-to-rank** | Data | ML technique that orders items by relevance; in Saakshya used to rank scanner results as **measurement**, never as a "what to buy" ranking (SPEC §4, §6.5). Phase 4+. | [15](15-machine-learning-and-data-science.md) |
| **LLM (Large Language Model)** | AI | The generative model used to **explain** structured signals. Default **Claude Haiku**; premium model for complex synthesis via provider abstraction (SPEC §9). Never invents numbers/prices/news/targets. | [14](14-ai-llm-agent-architecture.md) |
| **Look-ahead bias** | Data | Using information not available at the simulated decision point; a backtest integrity violation controlled by point-in-time data + as-of-adjusted prices (SPEC §6.3). | [19](19-backtesting-and-strategy-builder.md) |
| **MACD (Moving Average Convergence Divergence)** | Technical | Momentum indicator from the difference of two EMAs plus a signal line; describes momentum shifts. Descriptive only. | [13](13-scanner-engine-and-scoring.md) |
| **Market breadth** | Finance | How broadly a move is participated in (advance-decline, % above MA, new highs/lows). Descriptive market-health context. | [01](01-product-overview.md) |
| **Mode A / B / C** | Regulatory | Operating modes. **A** = pure analytics tool (v1; data/indicators/scanners, no per-stock entry/target/SL, no buy-leans). **B** = Registered Research Analyst (unlocks stock-specific research/levels). **C** = Investment Adviser (personalized advice). No feature ships until its mode is in force (SPEC §2, §4). | [21](21-compliance-risk-and-guardrails.md) |
| **Momentum score** | Product | A 0–100 score (with sub-scores + reasons + risk flags) measuring relative price strength; must be **validated** to carry signal (M3b, SPEC §6.5) and shown with evidence. Membership phrasing: "appears in the momentum scanner". | [13](13-scanner-engine-and-scoring.md) |
| **OHLC** | Finance | Open, High, Low, Close — the four prices summarizing a period's trading; with Volume = OHLCV. The base series for indicators. | [12](12-data-ingestion-and-market-data.md) |
| **Pivot Points** | Technical | Classic floor-trader levels derived from the **previous session's** High/Low/Close: `pivot = (H+L+C)/3`, with `R1/R2` (resistance) and `S1/S2` (support). EOD-computable; `pivot`/`pivot_r1`/`pivot_r2`/`pivot_s1`/`pivot_s2` in `technical_indicators`. Used as **descriptive support/resistance** reference levels ("trading above its daily pivot"), never targets or entries (SPEC §5). | [13](13-scanner-engine-and-scoring.md), [11](11-database-architecture.md) |
| **Point-in-time** | Data | The discipline of using only data as it existed at a given date (incl. corp-action-adjusted prices and index membership as-of that date). Core to as-of versioning and backtest integrity (SPEC §6.2, §6.3). | [11](11-database-architecture.md), [19](19-backtesting-and-strategy-builder.md) |
| **RA (Registered Research Analyst)** | Regulatory | SEBI-registered role (Mode B) permitting stock-specific research/recommendations behind a formal research report; **gates** entry/target/SL and candidate features; mandatory AI-use disclosure (SPEC §2, §6.7). Registration runs in parallel to the Mode-A launch. | [21](21-compliance-risk-and-guardrails.md) |
| **RAG (Retrieval-Augmented Generation)** | AI | Grounding an LLM in retrieved source text. In Saakshya, retrieval is constrained to the **structured payload / approved sources**; the model may reference nothing else (SPEC §6.6). | [14](14-ai-llm-agent-architecture.md) |
| **Relative strength** | Finance | A security's performance relative to a benchmark/peer set/sector. The momentum score is validated against **realized relative strength** (M3b, SPEC §6.5). Distinct from RSI. | [13](13-scanner-engine-and-scoring.md) |
| **Resistance** | Technical | A price area that has historically capped advances. Framed descriptively/historically ("historically a resistance zone"), never as a target (SPEC §5). | [13](13-scanner-engine-and-scoring.md) |
| **RSI (Relative Strength Index)** | Technical | Momentum oscillator (0–100) measuring speed/size of recent moves; high/low values are **descriptive states** (elevated/depressed), not buy/sell triggers. Distinct from relative strength. | [13](13-scanner-engine-and-scoring.md) |
| **Sector rotation** | Finance | The shifting of relative strength between sectors over time. Shown as descriptive sector analytics (explicitly lower-risk, SPEC §4). | [13](13-scanner-engine-and-scoring.md) |
| **SEBI** | Regulatory | Securities and Exchange Board of India — the regulator whose RA/IA rules govern what Saakshya may say and ship; the precedence rule defers to SEBI constraints over product ambition (SPEC §0, §2). | [21](21-compliance-risk-and-guardrails.md) |
| **Sharpe ratio** | Finance | Excess return per unit of total volatility; risk-adjusted performance shown only in integrity-controlled backtests, framed as measurement (SPEC §6.3). | [19](19-backtesting-and-strategy-builder.md) |
| **Slippage** | Finance | Difference between expected and actual fill price; modeled (with liquidity caps for small/mid-caps) so backtests are realistic, not inflated (SPEC §6.3). | [19](19-backtesting-and-strategy-builder.md) |
| **Sortino ratio** | Finance | Like Sharpe but penalizes only downside volatility; risk-adjusted backtest measure, framed honestly (SPEC §6.3). | [19](19-backtesting-and-strategy-builder.md) |
| **Stochastic RSI** | Technical | RSI passed through a stochastic oscillator for added sensitivity (faster 0–100 momentum oscillator). EOD-computable; `stoch_rsi_k`/`stoch_rsi_d` in `technical_indicators`. Descriptive momentum **state** only (>80 elevated, <20 depressed), never a trigger. | [13](13-scanner-engine-and-scoring.md), [11](11-database-architecture.md) |
| **Support** | Technical | A price area that has historically halted declines. Framed descriptively/historically ("a level that has acted as support"), never as an entry (SPEC §5). | [13](13-scanner-engine-and-scoring.md) |
| **Survivorship bias** | Data | Distortion from excluding delisted/merged names; controlled by including them for the period in backtests (SPEC §6.3). | [19](19-backtesting-and-strategy-builder.md) |
| **T+1** | Data | Trade date plus one — the EOD cadence: the previous session is ingested, processed, and delivered the next morning (SPEC §8). | [12](12-data-ingestion-and-market-data.md) |
| **Technical zone** | Technical | A descriptive price area derived from indicators/history (e.g., a historical resistance zone). **Distinct from** entry/target/SL/invalidation zones, which are RA-gated (SPEC §4, §5). | [13](13-scanner-engine-and-scoring.md) |
| **Vector database** | AI | A store for embeddings enabling semantic retrieval (pgvector/OpenSearch in production; deferred locally, SPEC §9). | [14](14-ai-llm-agent-architecture.md) |
| **Volume anomaly** | Technical | Volume materially above its own baseline (e.g., 2× the 20-day average), often paired with delivery%. Descriptive evidence; feeds the volume-breakout scanner. | [13](13-scanner-engine-and-scoring.md) |
| **VWAP (Volume-Weighted Average Price)** | Technical | Average price weighted by volume over a period; descriptive reference level. **Intraday-only — deferred to V7:** requires intra-session price×volume accumulation, so it is **not computed in EOD v1** (`technical_indicators.vwap` is NULL until live/intraday data lands). No scanner/AI may reference it until then. | [13](13-scanner-engine-and-scoring.md), [11](11-database-architecture.md) |
| **Watchlist candidate (Mode-A nuance)** | Product | In Saakshya, a watchlist entry is **filter-based discovery** ("matches this filter" / "appears in the scanner"), **not** a buy-lean. The buy-lean sense of "candidate" is RA-gated (SPEC §4, §5). | [05](05-information-architecture-and-url-paths.md), [21](21-compliance-risk-and-guardrails.md) |

---

## 2. Always-prohibited phrases (every mode)

Listed here for reference; enforced at output time by the guardrail engine (SPEC §3.3, §6.9): **guarantee · assured/confirmed target · risk-free · multibagger · sure-shot · buy now · best stock for you · assured target** and any implied/explicit return claim. See [21](21-compliance-risk-and-guardrails.md).

---

## 3. Related documents

- [13 — Scanner Engine & Scoring](13-scanner-engine-and-scoring.md)
- [14 — AI/LLM Agent Architecture](14-ai-llm-agent-architecture.md)
- [15 — Machine Learning & Data Science](15-machine-learning-and-data-science.md)
- [16 — Portfolio & Risk Engine](16-portfolio-and-risk-engine.md)
- [19 — Backtesting & Strategy Builder](19-backtesting-and-strategy-builder.md)
- [21 — Compliance, Risk & Guardrails](21-compliance-risk-and-guardrails.md)
- [30 — Decision Log](30-decision-log.md)
