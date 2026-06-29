# Steps · 10 · V5 Backtesting & ML Ranking
> Read first: [SPEC.md](../../SPEC.md) (esp. §6.3, §6.5) · [Roadmap](../02-product-roadmap.md) · [Backtesting & strategy builder](../19-backtesting-and-strategy-builder.md) · [Machine learning & data science](../15-machine-learning-and-data-science.md) · [Scanner engine & scoring](../13-scanner-engine-and-scoring.md) · [AI/LLM agent architecture](../14-ai-llm-agent-architecture.md) · [Compliance & guardrails](../21-compliance-risk-and-guardrails.md)

**Maps to:** Roadmap V5 · SPEC Phase 4
**Status:** Not started   |   **Regulatory mode:** A (an inflated backtest is an **implied-performance compliance risk**; ML output is **measurement, never a return promise** — no RA-gated parts in this step)
**Prerequisites:** [09-v4-strategy-builder.md](09-v4-strategy-builder.md) (strategy schema/engine), [00-phase-0-derisk.md](00-phase-0-derisk.md) (M3b validation), V1 scanner engine, deep adjusted history **including delisted/merged names** + point-in-time index membership ([12 — data ingestion](../12-data-ingestion-and-market-data.md))

## Overview
Two coupled workstreams, each gated on integrity/measurement discipline:

1. **Backtesting engine** — a historical simulator that **ships ONLY with the five mandatory integrity controls as a hard ship-gate** ([SPEC.md §6.3](../../SPEC.md), [19 §0, §4](../19-backtesting-and-strategy-builder.md)): survivorship-bias control, look-ahead control, point-in-time index membership, realistic fills (slippage + liquidity caps), and honest "past performance" framing. **Build the controls before exposing any results.** Plus metrics + reporting (equity curve, drawdown, Sharpe/Sortino/Calmar, trade log) and the **Backtest Interpreter Agent** ([14 §5.7](../14-ai-llm-agent-architecture.md)).

2. **ML ranking / signal-quality evolution** — the disciplined path rule-based → LogReg/GBM baseline → **LightGBM/XGBoost/CatBoost** → **learning-to-rank** → hybrid (ML + rules + human validation) ([15 §1](../15-machine-learning-and-data-science.md)), with **MLOps** (MLflow tracking + registry, Feast feature store, Evidently drift monitoring). Every output is a **probability band / measured separation, never a return promise**; ML **augments, never replaces** the explainable rule-based core.

### NON-NEGOTIABLE boundaries
- The backtest engine **refuses to run** if the dataset lacks delisted names, lacks point-in-time membership, or lacks a fills/slippage model ([19 §4 acc.](../19-backtesting-and-strategy-builder.md)). The five controls are **ship-blocking**.
- Every result, export, and shared view renders **"Past performance does not indicate future results."** + the **exposed-assumptions** block ([19 §6](../19-backtesting-and-strategy-builder.md)). An inflated or selectively-framed backtest is a **compliance incident** ([SPEC.md §6.3](../../SPEC.md)).
- ML outputs are **probability bands, never exact price/return** ([SPEC.md §3.3, §4 ML row](../../SPEC.md), [15 §0](../15-machine-learning-and-data-science.md)). **No model reaches production without passing eval AND measurement validation** ([15 §5](../15-machine-learning-and-data-science.md)).
- ML ranking stays **descriptive lists** under Mode A — no entry/target/stop, no "what to buy" ([15 §0.6](../15-machine-learning-and-data-science.md)). On validation failure/drift breach, **fall back to the rule-based score** ([15 §6](../15-machine-learning-and-data-science.md)).

## Exit gate (Definition of Done)
- [ ] The engine **blocks the run** (integrity preflight) when the universe lacks delisted names, when point-in-time membership is absent, or when no slippage/volume model is configured ([19 §4](../19-backtesting-and-strategy-builder.md)).
- [ ] A **look-ahead unit test** (using post-decision-date data) **fails the run** ([19 §4 acc.](../19-backtesting-and-strategy-builder.md)).
- [ ] Metrics reconcile against a hand-checked toy strategy; equity curve and trade log are mutually consistent.
- [ ] **No result view (including exports) renders without the disclaimer + assumptions** ([19 §6](../19-backtesting-and-strategy-builder.md)).
- [ ] The Backtest Interpreter Agent restates assumptions + past-performance caveat and **refuses to narrate** if the integrity audit did not pass ([14 §5.7](../14-ai-llm-agent-architecture.md)).
- [ ] ML serving uses **Feast point-in-time features (train == serve)**; every prediction is attributable to a model version; ML output is a probability band framed as measurement; fail-safe falls back to the rule-based score.

---
## Feature: Five mandatory integrity controls (ship-gate)  `(Mode A)`
**Objective:** Build the five controls **before** any backtest result is exposed; the engine refuses to run without them ([SPEC.md §6.3](../../SPEC.md), [19 §4](../19-backtesting-and-strategy-builder.md)). · **Backend dep:** integrity preflight gate; survivorship-aware universe; as-of corp-action-adjusted price access; point-in-time membership service; fills/slippage/volume-cap model. · **Frontend dep:** preflight-failure surfacing (block + reason). · **Data dep:** adjusted OHLCV incl. **delisted/merged** names, point-in-time index membership, delivery/volume, benchmark series ([12](../12-data-ingestion-and-market-data.md)).

### Steps
- [ ] 1. Implement the **integrity preflight gate** in `app/backtest/preflight.py` (per the [19 §4](../19-backtesting-and-strategy-builder.md) flow): block with a typed reason if (a) universe lacks delisted names → `survivorship risk`, (b) no point-in-time membership → `look-ahead risk`, (c) no slippage/volume model → `unrealistic fills`.
- [ ] 2. **Survivorship-bias control** (`app/backtest/universe.py`): resolve a historical universe that **includes delisted/merged names** for each period; reject a universe that silently drops losers.
- [ ] 3. **Look-ahead control** (`app/backtest/asof.py`): every decision at bar *t* uses **only data available as of t**, including **corp-action-adjusted prices as-of that date** ([SPEC.md §6.1–6.3](../../SPEC.md)). No future split/earnings knowledge.
- [ ] 4. **Point-in-time index membership** (`app/backtest/membership.py`): a stock is in NIFTY/sector index only on dates it actually was.
- [ ] 5. **Realistic fills** (`app/backtest/fills.py`): configurable slippage bps (larger for small/mid-caps) + **volume cap** (a trade takes at most X% of that bar's volume; excess unfilled/partial) + transaction-cost bps per side ([19 §3.2](../19-backtesting-and-strategy-builder.md)).
- [ ] 6. **Honest framing** (`app/backtest/framing.py`): attach the mandatory disclaimer + **exposed-assumptions** block (data window, universe with delisted-inclusion noted, costs, slippage, volume cap, fill model, survivorship/look-ahead caveats) to **every** result object before it leaves the engine ([19 §6](../19-backtesting-and-strategy-builder.md)).

### Tests
- [ ] **Survivorship fixture:** a universe missing delisted names is **rejected** by preflight; including them changes results materially (documented).
- [ ] **Look-ahead fixture:** a run that references post-decision-date data (e.g. a split known early) **fails** ([19 §4 acc.](../19-backtesting-and-strategy-builder.md)).
- [ ] **Point-in-time fixture:** testing today's index members on past dates is rejected; membership resolves correctly per date.
- [ ] **Fills fixture:** an order exceeding the volume cap is rejected/partial; costs + slippage reduce returns vs a frictionless run ([19 §3.2 acc.](../19-backtesting-and-strategy-builder.md)).
- [ ] Every result object carries the disclaimer + full assumption set ([19 §6](../19-backtesting-and-strategy-builder.md)).

### Compliance gate
- [ ] The engine **cannot produce a result** with any of the five controls absent ([SPEC.md §6.3](../../SPEC.md)).
- [ ] No result/export renders without **"Past performance does not indicate future results."** + assumptions ([19 §6](../19-backtesting-and-strategy-builder.md)).
- [ ] Results are **never** framed as expected/likely future returns; an inflated/selectively-framed backtest is escalated as a compliance incident ([21](../21-compliance-risk-and-guardrails.md)).

### Acceptance criteria
- [ ] Engine refuses to run on missing delisted names, missing membership, or missing fills model ([19 §4](../19-backtesting-and-strategy-builder.md)).
- [ ] Look-ahead unit test fails the run.
- [ ] Disclaimer + exposed assumptions on every result.

---
## Feature: Simulation engine, metrics & reporting  `(Mode A)`
**Objective:** Event-driven simulator (gated behind the §preflight) plus metrics and visual reporting. · **Backend dep:** chronological event-driven simulator over the [09 strategy schema](09-v4-strategy-builder.md); metric calculators; signal-decay sweep; chart-data serializers; benchmark series. · **Frontend dep:** equity/drawdown charts, trade-log table, metric cards, benchmark overlay. · **Data dep:** adjusted OHLCV (as-of), delivery/volume, point-in-time membership, benchmark (NIFTY 50 / sector).

### Steps
- [ ] 1. Implement the **simulation loop** in `app/backtest/engine.py` per [19 §3.1](../19-backtesting-and-strategy-builder.md): per bar in chronological order — resolve point-in-time universe → evaluate exits (stop/target/trailing/time/condition) → evaluate entries → apply fills (slippage + volume cap) → apply costs → update equity/cash/positions → record trades + equity point. **Only data available as of the bar** is used (look-ahead control).
- [ ] 2. Implement **metric calculators** (`app/backtest/metrics.py`) per [19 §5](../19-backtesting-and-strategy-builder.md): total/annualized return (CAGR), win rate, avg win/loss, profit factor, **max drawdown**, **Sharpe**, **Sortino**, **Calmar**, trade count, avg holding period, **signal decay** (edge vs signal→entry delay).
- [ ] 3. Serialize chart data: **equity curve (vs benchmark)**, **drawdown chart**, **trade log** (entry/exit/P&L/holding), per-metric table.
- [ ] 4. Frontend: render charts + trade-log + metric cards with benchmark overlay; the §framing disclaimer/assumptions block is **inseparable** from every result view (incl. exports).
- [ ] 5. API: `POST /backtest/run`, `GET /backtest/{id}` per [10 — API contracts](../10-api-contracts.md); results carry integrity-audit status.

### Tests
- [ ] Metrics reconcile against a **hand-checked toy strategy** ([19 §5 acc.](../19-backtesting-and-strategy-builder.md)).
- [ ] Equity curve and trade log are **mutually consistent** (equity deltas reconcile to logged trades).
- [ ] **Signal-decay sweep** runs across configured delays.
- [ ] The example strategy JSON ([19 §7](../19-backtesting-and-strategy-builder.md)) validates, passes §preflight, and yields a report carrying the disclaimer + assumptions.

### Compliance gate
- [ ] No result view or export renders without the disclaimer + assumptions ([19 §6](../19-backtesting-and-strategy-builder.md)).
- [ ] Stop/target/trailing are treated as **historical exit-simulation parameters**, never surfaced as live per-stock levels ([19 §7 note](../19-backtesting-and-strategy-builder.md), [SPEC.md row 5.21](../../SPEC.md)).

### Acceptance criteria
- [ ] Metrics reconcile; equity curve ↔ trade log consistent ([19 §5](../19-backtesting-and-strategy-builder.md)).
- [ ] Signal-decay sweep executes across delays.

---
## Feature: Backtest Interpreter Agent  `(Mode A)`
**Objective:** Narrate backtest results with **honest framing**, restating assumptions and the past-performance caveat; **no extrapolation to future returns** ([14 §5.7](../14-ai-llm-agent-architecture.md)). · **Backend dep:** Backtest Interpreter Agent (premium tier); integrity-audit status input; verification → guardrail → compliance-review pipeline ([14 §6, §5.8](../14-ai-llm-agent-architecture.md)). · **Frontend dep:** narrative panel attached to the result. · **Data dep:** computed backtest metrics + assumptions + survivorship/look-ahead audit status.

### Steps
- [ ] 1. Implement the agent per [14 §5.7](../14-ai-llm-agent-architecture.md): tools `get_backtest_result`; output schema with `metrics`, `assumptions`, `framing:"Past performance does not indicate future results."`, `disclaimer`.
- [ ] 2. Enforce **fail behavior**: if the integrity audit did **not** pass → the agent **refuses to narrate** ([14 §5.7](../14-ai-llm-agent-architecture.md)).
- [ ] 3. Route output through runtime verification (every number traces to the backtest payload) → guardrail (block "would have made you", "guaranteed", "assured") → compliance review → audit log ([14 §6, §7](../14-ai-llm-agent-architecture.md), [19 §6](../19-backtesting-and-strategy-builder.md)).

### Tests
- [ ] A guardrail test **blocks return-promise phrasing** in AI-generated backtest commentary ([19 §6 acc.](../19-backtesting-and-strategy-builder.md)).
- [ ] With integrity audit failed, the agent refuses to narrate.
- [ ] Every cited metric traces to the backtest result payload (no fabricated numbers).

### Compliance gate
- [ ] Narrative **must** restate assumptions + the past-performance caveat ([14 §5.7](../14-ai-llm-agent-architecture.md)).
- [ ] No extrapolation to future/expected returns; "would have made you" / "guaranteed" / "assured" blocked at output time ([19 §6](../19-backtesting-and-strategy-builder.md), [SPEC.md §3.3, §6.9](../../SPEC.md)).

### Acceptance criteria
- [ ] Agent restates framing + assumptions; refuses on failed audit; no ungrounded numbers.

---
## Feature: ML ranking / signal-quality evolution + MLOps  `(Mode A)`
**Objective:** Add learned signal-quality ranking that **augments** the rule-based core, outputting **probability bands / measured separation, never return promises**, on the disciplined evolution path with full MLOps ([15 §1–§6](../15-machine-learning-and-data-science.md)). · **Backend dep:** feature pipeline (point-in-time, no leakage), model training/serving behind an abstraction, model registry, drift monitoring; integrates with the AI audit log ([14 §7](../14-ai-llm-agent-architecture.md)). · **Frontend dep:** probability-band display as a **separately-labelled** measurement next to the rule-based score. · **Data dep:** corp-action-adjusted, point-in-time features + labels; deep history incl. delisted names.

### Steps
- [ ] 1. **Baseline first** (`app/ml/baseline/…`): LogReg / GBM signal-quality model producing a probability band ([15 §1, §2.1](../15-machine-learning-and-data-science.md)). Features per [15 §2.1](../15-machine-learning-and-data-science.md) (`ret_1m/3m/6m`, `rs_3m`, `momentum_raw`, `maTrend`, `vol_ratio`, `atr_pct`, `pct_above_50dma`, sector strength, `slope_50`).
- [ ] 2. **Stronger tabular models** (`app/ml/gbm/…`): **XGBoost / LightGBM / CatBoost** with **SHAP explainability retained** ([15 §1 table](../15-machine-learning-and-data-science.md)).
- [ ] 3. **Learning-to-rank** (`app/ml/ltr/…`): cross-sectional relative ranking whose output is a **ranked, descriptive list** ([15 §1](../15-machine-learning-and-data-science.md)).
- [ ] 4. **Probability bands** (`app/ml/bands.py`): banded likelihood of relative-strength persistence over a horizon (e.g. "55–65% historically persisted 21d"), **always with horizon + sample framing**, **never** a return promise ([15 §2.5](../15-machine-learning-and-data-science.md)).
- [ ] 5. **MLOps** ([15 §5](../15-machine-learning-and-data-science.md)): **MLflow** experiment tracking + **Registry** (stage gating staging→prod); **Feast** feature store (point-in-time, train == serve, no leakage); **Evidently** drift monitoring + alerting; scheduled + drift-triggered retraining behind a validation gate.
- [ ] 6. **Hybrid + fail-safe** ([15 §1, §6](../15-machine-learning-and-data-science.md)): ML augments rules + human validation; ML bands are **separately labelled**; on validation failure or drift breach, **fall back to the rule-based score** (the explainable v1 path is always available).
- [ ] 7. Evaluation ([15 §3](../15-machine-learning-and-data-science.md)): precision/recall/F1, AUC, hit rate, **signal return (measured, past-performance framed)**, drawdown-after-signal, false-positive rate, sector-wise + market-regime performance.

### Tests
- [ ] **Point-in-time / no-leakage:** train-time and serve-time features are **identical** via Feast ([15 §5 acc.](../15-machine-learning-and-data-science.md)); a leakage fixture (future label/feature) is caught.
- [ ] No model is promoted without passing **eval AND measurement validation** ([15 §5](../15-machine-learning-and-data-science.md)).
- [ ] Every prediction is **attributable to a model version** ([15 §5](../15-machine-learning-and-data-science.md)).
- [ ] Drift breach / validation failure **triggers fallback to the rule-based score** ([15 §6](../15-machine-learning-and-data-science.md)).
- [ ] Output is a **probability band**, never an exact price/return ([15 §0.2](../15-machine-learning-and-data-science.md)).

### Compliance gate
- [ ] ML output is **measurement-framed** (probability band + horizon + sample), **never a return promise** ([SPEC.md §3.3, §4 ML row](../../SPEC.md), [15 §7](../15-machine-learning-and-data-science.md)).
- [ ] ML ranking yields **descriptive lists** only — no entry/target/stop, no "what to buy" ([15 §0.6](../15-machine-learning-and-data-science.md)).
- [ ] "Signal return" / "drawdown after signal" obey backtesting honesty rules ([15 §3 note](../15-machine-learning-and-data-science.md), [SPEC.md §6.3](../../SPEC.md)).
- [ ] ML **augments, never replaces** the explainable rule-based core; the composite stays decomposable ([15 §1](../15-machine-learning-and-data-science.md)).

### Acceptance criteria
- [ ] Train == serve features (Feast point-in-time); no model ships without eval + measurement validation ([15 §5](../15-machine-learning-and-data-science.md)).
- [ ] Drift alerts trigger retraining; fail-safe falls back to rules ([15 §6](../15-machine-learning-and-data-science.md)).
- [ ] Every prediction attributable to a model version.

---
## Done-when
- [ ] Backtesting ships **only** with the five integrity controls as a hard, run-blocking ship-gate; survivorship / look-ahead / point-in-time / fills fixtures all enforce correctly.
- [ ] Metrics + reporting (equity curve, drawdown, Sharpe/Sortino/Calmar, trade log, signal decay) reconcile and always carry the disclaimer + exposed assumptions.
- [ ] Backtest Interpreter Agent narrates with honest framing, refuses on failed audit, and blocks return-promise phrasing.
- [ ] ML evolution (rule-based → GBM/LightGBM/XGBoost/CatBoost → learning-to-rank → hybrid) ships with MLflow/Feast/Evidently MLOps; outputs are **probability bands as measurement, never return promises**; descriptive lists only; fail-safe to the rule-based score.
- [ ] No backtest or ML output is framed as expected/likely future returns; an inflated backtest is treated as a compliance incident.
