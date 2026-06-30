# Steps · 02 · Indicators & rule-based scanners
> Read first: [SPEC.md](../../SPEC.md) (§12 M2–M3, §6.1–6.2 correctness, §3/§5 Mode-A language, §6.5 validation) · [Roadmap](../02-product-roadmap.md) (V1) · [Scanner engine](../13-scanner-engine-and-scoring.md) · [Data ingestion](../12-data-ingestion-and-market-data.md) · [Coding standards](../27-coding-standards.md)

**Maps to:** Roadmap **V1** · SPEC Phase 1 · Local milestone **M2–M3**
**Status:** Complete (M2+M3 implementation done — 90 tests green, ruff clean, mypy clean)   |   **Regulatory mode:** A
**Prerequisites:** [01-local-mvp-foundation.md](01-local-mvp-foundation.md) (adjusted OHLCV in DuckDB, storage repository, corp-action adjuster). Score *validation* is [03-scanner-score-validation.md](03-scanner-score-validation.md); AI explanation is [04-ai-explanation-layer.md](04-ai-explanation-layer.md).

## Overview
Builds the deterministic intelligence core: a **vectorized indicators module** (RSI, SMA 20/50/200, EMA, ATR, MACD, Bollinger, multi-window returns, volume ratio, relative strength) with golden-series unit tests + 2nd-source reconciliation, then the **rule-based scanners** (momentum, volume breakout, RSI, moving-average) that emit **0–100 composite + sub-scores + plain-language reasons + risk flags + the structured AI-explanation payload**. Output is **descriptive Mode-A** — no entry/target/SL, no "candidate" buy-leans, no "buy the breakout" ([SPEC §3](../../SPEC.md), [§5](../../SPEC.md), [docs/13 §0.4](../13-scanner-engine-and-scoring.md)). The composite uses the documented weights **flagged as `weights-v1-hypothesis`, `validationStatus=PENDING_M3B`** — the blended composite is gated on [03-scanner-score-validation.md](03-scanner-score-validation.md) before any UI.

## Exit gate (Definition of Done)
- [x] **M2 gate:** indicator unit tests pass vs known series, and a sample reconciles vs a 2nd source ([SPEC §12 M2](../../SPEC.md)).
- [x] **M3 gate:** the momentum scanner emits 0–100 score, sub-scores, plain-language reasons, risk flags; output is **descriptive (Mode A)**, **no buy-lean language**, missing sub-scores **marked neutral** ([SPEC §12 M3](../../SPEC.md), [docs/13 §3.2](../13-scanner-engine-and-scoring.md)).
- [x] Every displayed number is **reproducible from as-of versioned adjusted inputs**; the AI-explanation payload contains **only** values present in the output schema ([docs/13 §1](../13-scanner-engine-and-scoring.md)).
- [x] Composite carries `weightsVersion` + `validationStatus=PENDING_M3B`; blended composite **not** wired to any UI yet ([docs/13 §3.3](../13-scanner-engine-and-scoring.md)).

---
## Feature: Vectorized indicators module  `(Mode A)`
**Objective:** Pure, vectorized pandas/NumPy indicators on the **adjusted** series — no TA-Lib — with golden tests and 2nd-source reconciliation. · **Backend dep:** storage (adjusted OHLCV) · **Frontend dep:** none · **Data dep:** corp-action-adjusted series ([01](01-local-mvp-foundation.md))
### Steps
- [x] 1. `app/indicators/core.py`: `compute_rsi(closes, period=14)`, `sma(series, n)` for 20/50/200, `ema(series, n=21)`, `atr(high, low, close, 14)`, `macd(closes)` (+signal), `bollinger(closes, 20, 2)` (upper/lower). RSI returns **NaN for warm-up, never 0** ([docs/27 §3.2](../27-coding-standards.md)). Vectorized only ([SPEC §9](../../SPEC.md), [docs/27 §7.3](../27-coding-standards.md)).
- [x] 1a. `app/indicators/core.py` — **ADX** `adx_14(high, low, close, period=14)` via Wilder smoothing of `+DM/-DM/TR → +DI/-DI → DX → ADX` exactly per [docs/13 §3.5](../13-scanner-engine-and-scoring.md). Writes `adx_14`. **NaN through the ~2×14 warm-up, never 0**.
- [x] 1b. `app/indicators/core.py` — **Stochastic RSI** `stoch_rsi(closes, rsi_period=14, stoch_period=14, k=3, d=3)` = stochastic transform of `rsi_14` → `%K` (`stoch_rsi_k`), `%D` (`stoch_rsi_d`) per [docs/13 §3.5](../13-scanner-engine-and-scoring.md). Flat-window (`max==min`) → `NaN`/NEUTRAL, **never divide-by-zero**.
- [x] 1c. `app/indicators/core.py` — **Pivot Points** `pivots(prev_high, prev_low, prev_close)` (classic floor-trader) → `pivot, pivot_r1, pivot_r2, pivot_s1, pivot_s2` from the **prior session** adjusted H/L/C per [docs/13 §3.5](../13-scanner-engine-and-scoring.md). Descriptive support/resistance only — **no target/entry semantics**.
- [x] 1d. **VWAP — deferred to V7 (intraday-only).** Do **not** compute `vwap` in EOD v1: one bar/day makes it meaningless. Leave the `technical_indicators.vwap` column **NULL in EOD mode**; it lands with live/intraday data (V7) ([docs/13 §3.5](../13-scanner-engine-and-scoring.md), [docs/11 §3.3](../11-database-architecture.md)). No scanner/payload/AI may reference VWAP until then.
- [x] 2. `app/indicators/returns.py`: multi-window total returns `ret_5d/ret_20d/ret_60d` (and 21d/63d/126d for momentum), `volume_ratio_20`, and `relative_strength` vs index/sector ([docs/11 §3.3](../11-database-architecture.md)).
- [x] 3. All functions consume **adjusted** columns and carry/propagate `as_of` of inputs ([docs/27 §0.2](../27-coding-standards.md)); type hints on every public function ([docs/27 §3.2](../27-coding-standards.md)).
- [x] 4. `app/indicators/compute.py`: compute the full set per symbol — including `adx_14`, `stoch_rsi_k`, `stoch_rsi_d`, `pivot`/`pivot_r1`/`pivot_r2`/`pivot_s1`/`pivot_s2` (`vwap` left **NULL**, V7) — and persist to `technical_indicators` with `indicator_version` + `as_of_version` ([docs/11 §3.3](../11-database-architecture.md)).
- [x] 5. Missing/insufficient lookback → value is `NaN` (downstream marks sub-score **neutral**), never fabricated ([docs/13 §3.2](../13-scanner-engine-and-scoring.md)).
### Tests
- [x] `tests/indicators/test_core.py` (**critical-logic, golden**): committed golden series → RSI/SMA/EMA/ATR/MACD/Bollinger match expected values within tolerance; warm-up windows are NaN.
- [x] `tests/indicators/test_adx.py` (**critical-logic, golden**): `adx_14` matches a committed Wilder-smoothed golden series within tolerance; `+DI/-DI/DX` intermediates correct; warm-up window is NaN, never 0.
- [x] `tests/indicators/test_stoch_rsi.py` (**critical-logic, golden**): `stoch_rsi_k`/`stoch_rsi_d` match a committed golden series; flat-window (`max==min`) → NaN/NEUTRAL, no divide-by-zero; bounded 0–100.
- [x] `tests/indicators/test_pivots.py` (**critical-logic, golden**): `pivot, pivot_r1/r2, pivot_s1/s2` equal the classic floor-trader values from a committed prior-session H/L/C fixture; uses prior-session (not current) bar.
- [x] `tests/indicators/test_returns.py`: returns/volume-ratio/relative-strength match hand-computed fixtures.
- [x] `tests/indicators/test_reconciliation.py` (**M2 gate**): on a sample, indicators reconcile vs a **2nd source** within tolerance ([SPEC §12 M2](../../SPEC.md), [SPEC §6.1](../../SPEC.md)).
### Compliance gate
- [x] Indicators computed **only on adjusted, as-of versioned** series ([SPEC §6.1–6.2](../../SPEC.md), [docs/13 §0.5](../13-scanner-engine-and-scoring.md)).
### Acceptance criteria
- [x] **M2:** golden tests green; sample reconciles vs 2nd source; persisted indicators reproducible for their `as_of`.

---
## Feature: Scanner shared mechanics (eligibility, normalization, composite, tags/flags)  `(Mode A)`
**Objective:** The shared engine substrate every scanner uses ([docs/13 §3](../13-scanner-engine-and-scoring.md)). · **Backend dep:** indicators · **Frontend dep:** none · **Data dep:** indicators, sector classification, delivery %
### Steps
- [x] 1. `app/scanners/eligibility.py`: the universe gate ([docs/13 §3.1](../13-scanner-engine-and-scoring.md)) — listing status active for the as-of date, adjusted close ≥ ₹10, 20-day median traded value ≥ ₹1 crore, required-lookback completeness, no quarantined candle in lookback, corp-action reconciled. Thresholds from **versioned config**, not code constants ([docs/13 §7](../13-scanner-engine-and-scoring.md)).
- [x] 2. `app/scanners/normalize.py`: `clamp01`, `scale(value, lo, hi)`, `pct_rank(value, distribution)` exactly per [docs/13 §3.2](../13-scanner-engine-and-scoring.md). Missing input → `NEUTRAL` sentinel, **excluded** from the weighted sum with weight **redistributed pro-rata** (never silently penalized).
- [x] 3. `app/scanners/composite.py`: weighted sum of the seven sub-scores with the documented weights — **priceMomentum 25, volumeExpansion 20, maTrend 15, sectorStrength 15, rsiHealth 10, newsSentiment 10, riskAdjustment 5** ([docs/13 §3.3](../13-scanner-engine-and-scoring.md)); renormalize across available sub-scores when any is NEUTRAL. Read weights from versioned config `weights-v1-hypothesis` and **stamp into every result** ([docs/13 §3.3](../13-scanner-engine-and-scoring.md)).
- [x] 4. `app/scanners/vocabulary.py`: the **only** semantic vocabulary passed to AI — signal tags (`MOMENTUM_STRONG`, `VOLUME_EXPANSION`, `ABOVE_50DMA`, `ABOVE_200DMA`, `MA_STACKED_BULLISH`, `RSI_BULLISH_BAND`, `SECTOR_LEADER`, …) and risk flags (`RSI_OVERBOUGHT`, `RSI_OVERSOLD`, `ELEVATED_VOLATILITY`, `EXTENDED_FROM_MA`, `FALSE_BREAKOUT_RISK`, `LOW_LIQUIDITY`, `DATA_INCOMPLETE`, …) ([docs/13 §3.4](../13-scanner-engine-and-scoring.md)). The engine cannot emit a tag outside this set.
- [x] 5. `app/scanners/schema.py`: the canonical output record ([docs/13 §5](../13-scanner-engine-and-scoring.md)) — `scanner, symbol, asOfDate, dataConfidence, compositeScore, subScores, facts, signalTags, riskFlags, weightsVersion, validationStatus, asOfVersion, engineVersion` — and the AI-explanation payload ([docs/13 §6](../13-scanner-engine-and-scoring.md)). `validationStatus` defaults to `PENDING_M3B`.
### Tests
- [x] `tests/scanners/test_normalize.py` (**critical-logic**): `scale`/`pct_rank`/`clamp01` correct; NEUTRAL excluded + weights renormalized to sum 1.0.
- [x] `tests/scanners/test_composite.py` (**critical-logic**): composite reproducible from persisted sub-scores; renormalization on NEUTRAL; weight vector stamped.
- [x] `tests/scanners/test_eligibility.py`: penny/illiquid/quarantined/unreconciled names excluded with logged reason.
### Compliance gate
- [x] Tags/flags are the only vocabulary handed to AI; no directive tag exists; missing input → NEUTRAL not zero ([docs/13 §3.2](../13-scanner-engine-and-scoring.md), [§3.4](../13-scanner-engine-and-scoring.md)).
### Acceptance criteria
- [x] Composite computes from sub-scores with correct renormalization; every result carries `weightsVersion` + `validationStatus`.

---
## Feature: Momentum scanner  `(Mode A)`  *(the M3 deliverable)*
**Objective:** Surface persistent momentum + relative strength vs Nifty; the scanner whose score gets validated in [03-scanner-score-validation.md](03-scanner-score-validation.md). · **Backend dep:** indicators, shared mechanics · **Frontend dep:** none · **Data dep:** adjusted closes, Nifty returns, ATR%
### Steps
- [x] 1. `app/scanners/momentum.py` per [docs/13 §4.1](../13-scanner-engine-and-scoring.md): `ret_1m/3m/6m`, `rs_3m = ret_3m(stock) - ret_3m(NIFTY)`, `blended_ret = 0.5*ret_3m + 0.3*ret_6m + 0.2*ret_1m`, `momentumRaw = 0.6*pct_rank(blended_ret, universe) + 0.4*pct_rank(rs_3m, universe)`.
- [x] 2. Membership: enters when `momentumRaw ≥ 70 AND rs_3m > 0`; `MOMENTUM_STRONG` tag at `≥ 85`; `SECTOR_LEADER` if sector sub-score ≥ 80.
- [x] 3. Risk flags: `ELEVATED_VOLATILITY` (ATR% ≥ 90th pct), `EXTENDED_FROM_MA` (price > 15% above 50-DMA), `RSI_OVERBOUGHT`.
- [x] 4. Emit `facts` (`ret_1m_pct, ret_3m_pct, ret_6m_pct, rs_3m_pct, atr_pct, pct_above_50dma`) and **plain-language reasons** built only from tags/facts (e.g. "appears in the momentum scanner; trading above its 50-DMA; relative strength positive vs Nifty") — descriptive, **no buy-lean** ([docs/13 §4.1](../13-scanner-engine-and-scoring.md), [SPEC §5](../../SPEC.md)).
- [x] 5. Build the AI-explanation payload `{symbol, asOfDate, scanner, compositeScore, subScores, signalTags, riskFlags, facts}` — computed facts only, **no forward price/target/return** ([docs/13 §4.1, §6](../13-scanner-engine-and-scoring.md)).
- [x] 6. Persist to `scanner_results` (as-of versioned, UNIQUE(scanner_id, stock_id, session_date, as_of_version)) with `validationStatus=PENDING_M3B` ([docs/11 §3.5](../11-database-architecture.md)).
### Tests
- [x] `tests/scanners/test_momentum.py` (**critical-logic, golden**): `momentumRaw` and every fact reproducible from adjusted series on a committed fixture; membership/tag thresholds correct.
- [x] `tests/scanners/test_momentum_language.py`: reasons contain **no** prohibited/buy-lean phrasing; payload exposes no forward-looking field (guardrail-style assertion, [docs/13 §6](../13-scanner-engine-and-scoring.md)).
### Compliance gate
- [x] Output descriptive; `validationStatus=PENDING_M3B`; blended composite **suppressed from any UI** until validated ([docs/13 §3.3, §4.1](../13-scanner-engine-and-scoring.md), [SPEC §6.5](../../SPEC.md)).
### Acceptance criteria
- [x] **M3:** 0–100 score + sub-scores + reasons + risk flags; missing sub-scores neutral; no buy-lean language; payload = facts only ([SPEC §12 M3](../../SPEC.md)).

---
## Feature: Volume breakout, RSI, and moving-average scanners  `(Mode A)`
**Objective:** The remaining V1 rule-based scanners, same descriptive contract. · **Backend dep:** indicators, shared mechanics, delivery % · **Frontend dep:** none · **Data dep:** volume, delivery %, RSI, SMAs
### Steps
- [x] 1. `app/scanners/volume_breakout.py` per [docs/13 §4.2](../13-scanner-engine-and-scoring.md): `vol_ratio = volume / sma(volume,20)`, `delivery_z`, `volumeRaw = 0.6*scale(vol_ratio,1,4) + 0.4*scale(delivery_z,-1,3)`; enters at `vol_ratio ≥ 2.0`; **delivery-missing days mark `delivery_z` NEUTRAL, never zero** ([docs/13 §4.2](../13-scanner-engine-and-scoring.md)). Permitted phrasing: "volume expanded N× vs its 20-day average".
- [x] 2. `app/scanners/rsi.py` per [docs/13 §4.3](../13-scanner-engine-and-scoring.md): band classification (`OVERSOLD <30`, `RECOVERY_WATCH`, `BULLISH_BAND 45–65`, `ELEVATED`, `OVERBOUGHT >70`); `rsiHealth` peaks ~58; tags/flags `RSI_BULLISH_BAND` / `RSI_OVERBOUGHT` / `RSI_OVERSOLD`. Permitted: "RSI is elevated, so the risk of a short-term pullback is higher".
- [x] 3. `app/scanners/moving_average.py` per [docs/13 §4.4](../13-scanner-engine-and-scoring.md): `above_20/50/200`, `stacked_bullish = sma20>sma50>sma200`, `slope_50`, `maTrendRaw = 40*above_50 + 30*above_200 + 20*stacked_bullish + 10*scale(slope_50,-0.05,0.05)`; tags `ABOVE_50DMA/ABOVE_200DMA/MA_STACKED_BULLISH`; flag `EXTENDED_FROM_MA`.
- [x] 4. Each builds the same canonical output schema + AI-explanation payload (facts only) and persists as-of versioned results.
### Tests
- [x] `tests/scanners/test_volume_breakout.py`: `vol_ratio` correct; delivery-missing → `delivery_z` NEUTRAL not zero.
- [x] `tests/scanners/test_rsi.py`: band thresholds + `rsiHealth` curve correct.
- [x] `tests/scanners/test_moving_average.py`: stacking/slope/flags correct on a fixture.
- [x] `tests/scanners/test_scanner_language.py`: across all four scanners, **no** "buy the breakout", target, stop, or always-prohibited phrasing appears in any field ([docs/13 §8](../13-scanner-engine-and-scoring.md), [SPEC §3.3, §5](../../SPEC.md)).
### Compliance gate
- [x] Breakout reported as an **event** ("closed above a level that has historically acted as resistance"), never "buy the breakout"; no entry/target/SL anywhere ([docs/13 §4.5, §8](../13-scanner-engine-and-scoring.md)).
### Acceptance criteria
- [x] Four scanners emit descriptive score+reasons+risk flags; all numbers reproducible from adjusted inputs; payloads = facts only.

---
## Done-when
- [x] **M2:** indicators pass golden tests and reconcile vs a 2nd source ([SPEC §12 M2](../../SPEC.md)).
- [x] **M3:** momentum (+ volume/RSI/MA) scanners emit 0–100 score, sub-scores, plain-language reasons, risk flags; descriptive Mode-A; neutral on missing input ([SPEC §12 M3](../../SPEC.md)).
- [x] Composite stamped `weights-v1-hypothesis` / `PENDING_M3B`; blended composite not wired to UI until [03-scanner-score-validation.md](03-scanner-score-validation.md) passes ([SPEC §6.5](../../SPEC.md)).
- [x] AI-explanation payloads ready for [04-ai-explanation-layer.md](04-ai-explanation-layer.md) (facts-only, no forward-looking fields).
