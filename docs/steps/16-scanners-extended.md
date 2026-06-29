# Steps · 16 · Scanners (extended set)
> Read first: [SPEC.md](../../SPEC.md) (§3/§5 Mode-A language, §6.1–6.2 correctness, §6.5 validation, §12) · [Roadmap](../02-product-roadmap.md) (V1–V3) · [Scanner engine](../13-scanner-engine-and-scoring.md) (§4.5–4.13) · [Feature modules](../04-feature-modules.md) · [API contracts](../10-api-contracts.md)

**Maps to:** Roadmap **V1–V3** · SPEC Phase 1–3 · **Status:** Not started · **Regulatory mode:** A
**Prerequisites:** [02-indicators-and-scanners.md](02-indicators-and-scanners.md) (indicators, shared scanner mechanics, eligibility, normalize, composite, vocabulary, schema, AI-explanation payload) · [03-scanner-score-validation.md](03-scanner-score-validation.md) (M3b validation governance). AI wording is [04-ai-explanation-layer.md](04-ai-explanation-layer.md); portfolio-risk surfaces also tie to [08-v3-portfolio-risk-alerts.md](08-v3-portfolio-risk-alerts.md).

## Overview
Step 02 built the indicator layer, the shared scanner substrate (eligibility / normalize / composite / vocabulary / schema / AI-explanation payload) and the first four scanners (momentum, volume breakout, RSI, moving-average). This step adds the **remaining rule-based scanners** documented in [docs/13 §4.5–4.13](../13-scanner-engine-and-scoring.md): **breakout, breakdown, sector-strength, low-risk momentum, high-risk/high-reward, near-52-week-high, 200-DMA-reclaim, oversold-recovery, and the portfolio-risk scanner.**

Every scanner here **reuses** step 02's shared mechanics unchanged: the eligibility gate (`app/scanners/eligibility.py`), the `scale`/`pct_rank`/`clamp01` normalizers, the `NEUTRAL`-on-missing-input rule, the canonical output record (`app/scanners/schema.py`), the closed signal-tag/risk-flag vocabulary (`app/scanners/vocabulary.py`), and the facts-only AI-explanation payload contract ([docs/13 §6](../13-scanner-engine-and-scoring.md)). Output is **descriptive Mode-A** — events and computed facts only: **no entry/target/stop-loss, no "candidate" buy-leans, no "buy the breakout"/"sell the breakdown"** ([SPEC §3](../../SPEC.md), [§5](../../SPEC.md), [docs/13 §0.4, §8](../13-scanner-engine-and-scoring.md)). Where a scanner contributes to the blended composite, it stamps `weightsVersion=weights-v1-hypothesis` + `validationStatus=PENDING_M3B`; the blended composite stays gated on [03-scanner-score-validation.md](03-scanner-score-validation.md) before any UI ([docs/13 §3.3](../13-scanner-engine-and-scoring.md)).

**False-signal discipline is first-class here.** Several of these scanners detect *events* (breakout, breakdown, reclaim, oversold bounce). Each MUST emit its false-signal risk flag (`FALSE_BREAKOUT_RISK`, `FALSE_BREAKDOWN_RISK`) on weak-volume or marginal-margin conditions, and the AI explanation MUST surface it ([docs/13 §4.5–4.6, §4.11–4.12](../13-scanner-engine-and-scoring.md)).

## Exit gate (Definition of Done)
- [ ] Each scanner emits the **canonical output record** (score/sub-scores where applicable, facts, signalTags, riskFlags, weightsVersion, validationStatus, asOfVersion, engineVersion) reproducible from as-of versioned adjusted inputs ([docs/13 §5](../13-scanner-engine-and-scoring.md)).
- [ ] Every event scanner (breakout/breakdown/reclaim/oversold-recovery) raises its **false-signal risk flag** under weak-volume / marginal-margin conditions; the flag is in `riskFlags`, not buried ([docs/13 §4.5–4.6, §4.11–4.12](../13-scanner-engine-and-scoring.md)).
- [ ] Only vocabulary from `app/scanners/vocabulary.py` is emitted; no scanner can produce a tag/flag outside the closed set ([docs/13 §3.4](../13-scanner-engine-and-scoring.md)).
- [ ] Each scanner's AI-explanation payload is **facts-only** — no forward price/target/return/stop ([docs/13 §6](../13-scanner-engine-and-scoring.md)).
- [ ] No scanner field can be reworded into "buy the breakout", "sell", "exit", "safe buy", "high reward", "buy the dip", or any always-prohibited phrase; asserted by a language contract test ([SPEC §3.3](../../SPEC.md), [docs/13 §8](../13-scanner-engine-and-scoring.md)).
- [ ] High-risk/high-reward results carry **≥1 mandatory risk flag**; low-risk-momentum is a **risk-tier filter**, never labelled "safe"/"low-risk buy" ([docs/13 §4.8–4.9](../13-scanner-engine-and-scoring.md)).
- [ ] Portfolio-risk scanner output is **factual event reporting**; no field reduces to "reduce"/"sell"/"rebalance"; holdings never leave the grounded facts-only payload ([docs/13 §4.13](../13-scanner-engine-and-scoring.md)).
- [ ] Composite-bearing scanners stamp `weightsVersion` + `validationStatus=PENDING_M3B`; blended composite not wired to any UI until [03-scanner-score-validation.md](03-scanner-score-validation.md) passes.

---
## Feature: Breakout scanner  `(Mode A)`
**Objective:** Detect price clearing a recent resistance/consolidation high on supportive volume — reported as an **event**, never "buy the breakout" ([docs/13 §4.5](../13-scanner-engine-and-scoring.md)). · **Backend dep:** indicators, shared mechanics ([02](02-indicators-and-scanners.md)) · **Frontend dep:** none (consumed by scanner list / stock detail later) · **Data dep:** adjusted OHLCV, volume ratio, ATR%
### Steps
- [ ] 1. `app/scanners/breakout.py` per [docs/13 §4.5](../13-scanner-engine-and-scoring.md): `resistance = max(high, lookback=N)` (default N=20, also 55); `breakout = close > resistance_prev AND vol_ratio >= 1.5`; `conviction = scale(vol_ratio,1.5,4)` blended with the close-vs-resistance margin. Lookback `N` and the `1.5` volume gate from **versioned config**, not constants.
- [ ] 2. `false_breakout_risk = close within 1*ATR of resistance OR vol_ratio < 1.5` → set `FALSE_BREAKOUT_RISK`. **Weak-volume breakout always carries the flag.**
- [ ] 3. Tags `BREAKOUT_CONFIRMED`; risk flags `FALSE_BREAKOUT_RISK`, `ELEVATED_VOLATILITY`, `EARNINGS_SOON`.
- [ ] 4. Emit `facts` (`close, resistance_20d, vol_ratio, atr_pct`) and plain-language reasons built only from tags/facts: "closed above a level that has historically acted as resistance, on above-average volume" — **descriptive event, no buy-lean** ([docs/13 §4.5](../13-scanner-engine-and-scoring.md)).
- [ ] 5. Build the facts-only AI-explanation payload `{ symbol, asOfDate, scanner, facts:{close, resistance_20d, vol_ratio}, signalTags, riskFlags }`; persist as-of versioned to `scanner_results`.
### Tests
- [ ] `tests/scanners/test_breakout.py` (**critical-logic, golden**): on a committed series, `resistance`, `vol_ratio`, and membership reproduce; a weak-volume close above resistance raises `FALSE_BREAKOUT_RISK`; a marginal close (within 1·ATR) raises it too.
- [ ] `tests/scanners/test_breakout_language.py`: no "buy the breakout"/target/stop/always-prohibited phrasing in any field; payload exposes no forward-looking field.
### Compliance gate
- [ ] Breakout is an **event** ("closed above a level that has historically acted as resistance"), never "buy the breakout"; no entry/target/SL anywhere ([docs/13 §4.5, §8](../13-scanner-engine-and-scoring.md)).
### Acceptance criteria
- [ ] Descriptive event + facts + risk flags; weak-volume/marginal breakouts flagged; numbers reproducible from adjusted inputs; payload = facts only.

---
## Feature: Breakdown scanner  `(Mode A)`
**Objective:** Mirror of the breakout scanner — detect price losing a recent support level as a **factual event**, never "sell"/"exit" ([docs/13 §4.6](../13-scanner-engine-and-scoring.md)). · **Backend dep:** indicators, shared mechanics · **Frontend dep:** none · **Data dep:** adjusted OHLCV, volume ratio, ATR%, news sentiment
### Steps
- [ ] 1. `app/scanners/breakdown.py` per [docs/13 §4.6](../13-scanner-engine-and-scoring.md): `support = min(low, lookback=N)`; `breakdown = close < support_prev AND vol_ratio >= 1.5`; `false_breakdown_risk = close within 1*ATR of support OR vol_ratio < 1.5` → `FALSE_BREAKDOWN_RISK`.
- [ ] 2. Tags `BREAKDOWN_CONFIRMED`; risk flags `FALSE_BREAKDOWN_RISK`, `ELEVATED_VOLATILITY`, `NEWS_SENTIMENT_NEGATIVE` (when paired negative sentiment is present).
- [ ] 3. Emit `facts` (`close, support_20d, vol_ratio`) and reasons: "closed below a level that has historically acted as support" — **never "sell"/"exit"**.
- [ ] 4. Build the facts-only AI-explanation payload `{ symbol, asOfDate, scanner, facts:{close, support_20d, vol_ratio}, signalTags, riskFlags }`; persist as-of versioned.
### Tests
- [ ] `tests/scanners/test_breakdown.py` (**critical-logic, golden**): `support`/membership reproduce; weak-volume / within-1·ATR close raises `FALSE_BREAKDOWN_RISK`; negative-sentiment pairing sets `NEWS_SENTIMENT_NEGATIVE`.
- [ ] `tests/scanners/test_breakdown_language.py`: no "sell"/"exit"/prescriptive/always-prohibited phrasing; payload facts-only.
### Compliance gate
- [ ] Breakdown reported as an event ("closed below a level that has historically acted as support"); never "sell"/"exit" ([docs/13 §4.6, §8](../13-scanner-engine-and-scoring.md)).
### Acceptance criteria
- [ ] Descriptive event + facts + risk flags; false-breakdown flagged on weak volume; reproducible; payload facts-only.

---
## Feature: Sector-strength scanner  `(Mode A)`
**Objective:** Rank sectors by relative strength and breadth; surface leading/lagging sectors — explicitly lower-risk index/sector analysis ([docs/13 §4.7](../13-scanner-engine-and-scoring.md), [SPEC §4](../../SPEC.md)). · **Backend dep:** sector classification, indicator layer, index returns · **Frontend dep:** none (feeds sector screen + composite `sectorStrength` sub-score) · **Data dep:** sector index returns (1m/3m), constituent SMAs, Nifty returns
### Steps
- [ ] 1. `app/scanners/sector_strength.py` per [docs/13 §4.7](../13-scanner-engine-and-scoring.md): `sector_rs = ret_3m(sector) - ret_3m(NIFTY)`; `breadth_pct = count(constituent.close > constituent.sma50) / count(constituents)`; `sectorScore = 0.5*pct_rank(sector_rs, sectors) + 0.5*scale(breadth_pct, 0.3, 0.8)`.
- [ ] 2. Tags `SECTOR_LEADER` (top quartile); risk flag `DATA_INCOMPLETE` when constituents have gaps — incomplete constituents excluded from breadth, **never counted as below-MA**.
- [ ] 3. Output is **sector-keyed** (not symbol-keyed): `{ sector, asOfDate, scanner, sectorScore, facts:{ret_3m_pct, sector_rs_pct, breadth_pct, constituents}, signalTags, riskFlags }`. Reuse `app/scanners/schema.py` with the sector key variant.
- [ ] 4. Expose `sectorScore` for the composite `sectorStrength` sub-score consumed by per-symbol scanners ([docs/13 §3.3](../13-scanner-engine-and-scoring.md)); persist as-of versioned.
- [ ] 5. Reasons: "the auto sector is leading, with 71% of constituents above their 50-DMA" — descriptive.
### Tests
- [ ] `tests/scanners/test_sector_strength.py` (**critical-logic, golden**): `sector_rs`, `breadth_pct`, `sectorScore` reproduce on a committed multi-sector fixture; constituent gaps → `DATA_INCOMPLETE`, excluded from breadth, not counted below-MA.
### Compliance gate
- [ ] Descriptive sector framing; no "rotate into"/"buy the sector" phrasing; sector strength is comparative, not directive ([docs/13 §4.7, §8](../13-scanner-engine-and-scoring.md)).
### Acceptance criteria
- [ ] Sector ranking reproducible from index/constituent inputs; breadth excludes gapped constituents; feeds composite sub-score.

---
## Feature: Low-risk momentum scanner  `(Mode A)`
**Objective:** Momentum names filtered to lower volatility/drawdown — a **risk-tier filter**, never a "safe buy" label ([docs/13 §4.8](../13-scanner-engine-and-scoring.md)). · **Backend dep:** momentum scanner output ([02](02-indicators-and-scanners.md)), ATR%, drawdown, beta · **Frontend dep:** none · **Data dep:** momentum sub-score, ATR%, 90-day max drawdown, beta vs Nifty
### Steps
- [ ] 1. `app/scanners/low_risk_momentum.py` per [docs/13 §4.8](../13-scanner-engine-and-scoring.md): enters when `momentumRaw >= 70 AND atr_pct <= 40th percentile AND max_drawdown_90d <= 15% AND beta <= 1.1`; `lowRiskScore = momentumRaw * (1 - clamp01(atr_pct_rank))` (momentum **discounted** by volatility). Thresholds from versioned config.
- [ ] 2. Tags `MOMENTUM_STRONG`; risk flags rarely set by construction but `EARNINGS_SOON` still surfaced.
- [ ] 3. Emit `facts` (`momentum_raw, atr_pct, max_drawdown_90d_pct, beta`); reasons: "shows momentum with comparatively low recent volatility". **The label is a risk tier, never "safe"/"low-risk buy".**
- [ ] 4. Facts-only AI-explanation payload; persist as-of versioned with `weightsVersion`/`validationStatus`.
### Tests
- [ ] `tests/scanners/test_low_risk_momentum.py` (**critical-logic**): membership gates (momentum/ATR/drawdown/beta) and `lowRiskScore` discount reproduce on a fixture.
- [ ] `tests/scanners/test_low_risk_momentum_language.py`: no "safe"/"low-risk buy"/return-implying phrasing in any field.
### Compliance gate
- [ ] "Low-risk" describes the **volatility tier**, not a recommendation; no "safe"/"low-risk buy"/return implication ([docs/13 §4.8](../13-scanner-engine-and-scoring.md), [SPEC §3.3](../../SPEC.md)).
### Acceptance criteria
- [ ] Tier filter reproducible; momentum discounted by volatility; no "safe buy" language anywhere.

---
## Feature: High-risk / high-reward scanner  `(Mode A)`
**Objective:** The symmetric tier — high momentum **with** explicit elevated-risk flags; risk is **loud** ([docs/13 §4.9](../13-scanner-engine-and-scoring.md)). · **Backend dep:** momentum scanner, ATR%, gap frequency, volatility percentile · **Frontend dep:** none · **Data dep:** momentum sub-score, ATR%, gap frequency 30d, volatility percentile
### Steps
- [ ] 1. `app/scanners/high_risk_high_reward.py` per [docs/13 §4.9](../13-scanner-engine-and-scoring.md): enters when `momentumRaw >= 75 AND atr_pct >= 80th percentile`; `highRiskScore = momentumRaw` (reported **alongside, NOT net of**, risk).
- [ ] 2. Tags `MOMENTUM_STRONG`, `VOLUME_EXPANSION`; **mandatory ≥1 risk flag** from `ELEVATED_VOLATILITY`, `GAP_RISK`, `EXTENDED_FROM_MA` — assert at construction that a result cannot ship with zero risk flags.
- [ ] 3. Emit `facts` (`momentum_raw, atr_pct, vol_pctile, gap_freq_30d`); the AI explanation **MUST surface the risk flags**. Reasons: "strong momentum but elevated short-term volatility — risk is elevated".
- [ ] 4. Facts-only AI-explanation payload; persist as-of versioned.
### Tests
- [ ] `tests/scanners/test_high_risk_high_reward.py` (**critical-logic**): membership gate and `highRiskScore` reproduce; **a result with zero risk flags is impossible** (assertion test).
- [ ] `tests/scanners/test_high_risk_language.py`: no "high reward as expected return"/"multibagger"/return-claim phrasing; risk flags present in payload.
### Compliance gate
- [ ] Every result carries ≥1 risk flag; "high reward" is never framed as expected return; no "multibagger" ([docs/13 §4.9](../13-scanner-engine-and-scoring.md), [SPEC §3.3](../../SPEC.md)).
### Acceptance criteria
- [ ] Score reported alongside (not net of) risk; mandatory risk flag enforced; risk surfaced in explanation.

---
## Feature: Near-52-week-high scanner  `(Mode A)`
**Objective:** Descriptive proximity to the 52-week high ([docs/13 §4.10](../13-scanner-engine-and-scoring.md)). · **Backend dep:** indicators, shared mechanics · **Frontend dep:** none · **Data dep:** adjusted close, 252-session high
### Steps
- [ ] 1. `app/scanners/near_52w_high.py` per [docs/13 §4.10](../13-scanner-engine-and-scoring.md): `high_52w = max(high, 252)`; `pct_from_high = (close - high_52w) / high_52w`; `near = pct_from_high >= -0.03` (within 3%, configurable). `< 252` candles → excluded via eligibility, not fabricated.
- [ ] 2. Tags `NEAR_52W_HIGH`; risk flags `EXTENDED_FROM_MA`, `RSI_OVERBOUGHT`.
- [ ] 3. Emit `facts` (`close, high_52w, pct_from_high`); reasons: "trading within 1% of its 52-week high".
- [ ] 4. Facts-only AI-explanation payload; persist as-of versioned.
### Tests
- [ ] `tests/scanners/test_near_52w_high.py` (**critical-logic, golden**): `high_52w`/`pct_from_high`/membership reproduce; `<252` candles excluded with logged reason; extended/overbought flags fire correctly.
### Compliance gate
- [ ] Pure proximity statement; no "at new highs, buy"/breakout-buy implication; no target ([docs/13 §4.10, §8](../13-scanner-engine-and-scoring.md)).
### Acceptance criteria
- [ ] Proximity reproducible; warm-up handled via eligibility; descriptive only.

---
## Feature: 200-DMA-reclaim scanner  `(Mode A)`
**Objective:** Detect a cross back above the 200-DMA (long-term trend reclaim) — an **event report** ([docs/13 §4.11](../13-scanner-engine-and-scoring.md)). · **Backend dep:** indicators (SMA200), shared mechanics · **Frontend dep:** none · **Data dep:** close, SMA200, prior-session close vs SMA200, volume ratio
### Steps
- [ ] 1. `app/scanners/reclaim_200dma.py` per [docs/13 §4.11](../13-scanner-engine-and-scoring.md): `reclaim = (close_prev <= sma200_prev) AND (close > sma200) AND vol_ratio >= 1.2`; `days_below_prior = consecutive sessions close was below sma200 before reclaim`.
- [ ] 2. Tags `RECLAIMED_200DMA`, `ABOVE_200DMA`; risk flags `FALSE_BREAKOUT_RISK` (thin volume), `DATA_INCOMPLETE` (`<200` candles → excluded via eligibility).
- [ ] 3. Emit `facts` (`close, sma200, vol_ratio, days_below_prior`); reasons: "closed back above its 200-DMA after 38 sessions below it".
- [ ] 4. Facts-only AI-explanation payload; persist as-of versioned.
### Tests
- [ ] `tests/scanners/test_reclaim_200dma.py` (**critical-logic, golden**): reclaim cross + `days_below_prior` reproduce; thin-volume reclaim raises `FALSE_BREAKOUT_RISK`; `<200` candles excluded.
### Compliance gate
- [ ] Reclaim reported as an event; no "buy the reclaim"/target/SL; thin-volume reclaim carries the false-signal flag ([docs/13 §4.11, §8](../13-scanner-engine-and-scoring.md)).
### Acceptance criteria
- [ ] Cross + days-below reproducible; weak-volume reclaim flagged; descriptive only.

---
## Feature: Oversold-recovery scanner  `(Mode A)`
**Objective:** Detect a bounce from oversold RSI with confirmation — descriptive, **never** a "buy the dip" call ([docs/13 §4.12](../13-scanner-engine-and-scoring.md)). · **Backend dep:** RSI series ([02](02-indicators-and-scanners.md)), close, volume ratio · **Frontend dep:** none · **Data dep:** RSI(14) series, adjusted close, volume ratio, news sentiment
### Steps
- [ ] 1. `app/scanners/oversold_recovery.py` per [docs/13 §4.12](../13-scanner-engine-and-scoring.md): `was_oversold = min(rsi_14, lookback=5) < 30`; `recovering = rsi_14_today > rsi_14_yesterday AND rsi_14_today > 35`; `confirm = close_today > close_yesterday AND vol_ratio >= 1.2`; enters when `was_oversold AND recovering AND confirm`.
- [ ] 2. Tags `OVERSOLD_RECOVERY`; risk flags `ELEVATED_VOLATILITY`, `FALSE_BREAKOUT_RISK` (unconfirmed/thin bounce), `NEWS_SENTIMENT_NEGATIVE` (bounce against bad news).
- [ ] 3. Emit `facts` (`rsi_14, rsi_14_prev, rsi_min_5d, vol_ratio`); reasons: "RSI turned up from oversold territory on above-average volume". **Never "buy the dip".**
- [ ] 4. Facts-only AI-explanation payload; persist as-of versioned.
### Tests
- [ ] `tests/scanners/test_oversold_recovery.py` (**critical-logic, golden**): the three-gate membership reproduces; a bounce against negative sentiment sets `NEWS_SENTIMENT_NEGATIVE`; an unconfirmed/thin bounce sets `FALSE_BREAKOUT_RISK`.
- [ ] `tests/scanners/test_oversold_recovery_language.py`: no "buy the dip"/prescriptive/always-prohibited phrasing.
### Compliance gate
- [ ] Reported as an RSI event; never "buy the dip"; bounce-against-bad-news risk surfaced ([docs/13 §4.12, §8](../13-scanner-engine-and-scoring.md)).
### Acceptance criteria
- [ ] Three-gate membership reproducible; risk against bad news flagged; descriptive only.

---
## Feature: Portfolio-risk scanner  `(Mode A)`
**Objective:** Scan a **user's holdings** for factual risk events — "you hold X; it broke its 50-DMA" is factual; "sell X" is never produced ([docs/13 §4.13](../13-scanner-engine-and-scoring.md)). · **Backend dep:** [portfolio/risk engine](08-v3-portfolio-risk-alerts.md), per-holding indicators, concentration/correlation helpers · **Frontend dep:** consumed by the portfolio risk panel ([08](08-v3-portfolio-risk-alerts.md), [docs/08 §9](../08-screen-by-screen-documentation.md)) · **Data dep:** user holdings (symbol, qty, avg cost — held privately), per-holding indicators, sector exposure, pairwise correlation
### Steps
- [ ] 1. `app/scanners/portfolio_risk.py` per [docs/13 §4.13](../13-scanner-engine-and-scoring.md): per-holding flags `BROKE_50DMA, BROKE_200DMA, RSI_OVERBOUGHT, ELEVATED_VOLATILITY, NEWS_SENTIMENT_NEGATIVE, NEAR_52W_HIGH`; `concentration = max(weight_i)`; `sector_concentration = max(sector_weight)`; `portfolio_vol = sqrt(wᵀ Σ w)` (Σ = covariance of holding returns).
- [ ] 2. Portfolio-level risk flags `SINGLE_NAME_CONCENTRATION` (weight > 25%), `SECTOR_CONCENTRATION` (sector > 40%), `ELEVATED_PORTFOLIO_VOL`, plus per-holding flags. Thresholds from versioned config, mirroring scanner-score governance. **No directive signal tags.**
- [ ] 3. Output `{ portfolioId, asOfDate, scanner, portfolioFlags, facts:{single_name_max_weight_pct, sector_max_weight_pct, portfolio_vol_annual_pct}, holdings:[{symbol, weight_pct, flags, facts}] }`. Holdings are PII-class — never logged in plaintext ([08](08-v3-portfolio-risk-alerts.md)).
- [ ] 4. AI-explanation payload = grounded facts only: `{ portfolioId, asOfDate, portfolioFlags, facts, holdings:[{symbol, weight_pct, flags, facts}] }`. Permitted: "your portfolio has 47% in financials; ICICIBANK closed below its 50-DMA". **Prohibited:** "reduce"/"sell"/"rebalance into"/any prescriptive action.
- [ ] 5. Persist as-of versioned, row-scoped to the owning user; do not let holdings facts leave the grounded payload.
### Tests
- [ ] `tests/scanners/test_portfolio_risk.py` (**critical-logic**): per-holding flags, concentration, and `portfolio_vol` reproduce on a fixture portfolio; a 47%-financials portfolio sets `SECTOR_CONCENTRATION`.
- [ ] `tests/scanners/test_portfolio_risk_language.py`: **no** output field reduces to "reduce"/"sell"/"rebalance"/always-prohibited; a contract test asserts no prescriptive rewording is possible from the emitted facts/flags.
- [ ] `tests/scanners/test_portfolio_risk_scope.py`: another user cannot read these results (row-scope/IDOR); holdings absent from logs ([08](08-v3-portfolio-risk-alerts.md)).
### Compliance gate
- [ ] Factual event reporting only; no "reduce"/"sell"/"rebalance"; holdings never leave the grounded facts-only payload to the AI ([docs/13 §4.13](../13-scanner-engine-and-scoring.md), [SPEC §3.3](../../SPEC.md)).
### Acceptance criteria
- [ ] Per-holding + portfolio flags reproducible; no field rewordable into a prescription; holdings PII-class throughout.

---
## Done-when
- [ ] All nine scanners emit the canonical descriptive output record reproducible from as-of versioned adjusted inputs; only closed-vocabulary tags/flags appear ([docs/13 §3.4, §5](../13-scanner-engine-and-scoring.md)).
- [ ] Every event scanner raises its false-signal flag on weak-volume/marginal conditions; high-risk results carry a mandatory risk flag; low-risk-momentum is never labelled "safe" ([docs/13 §4.5–4.12](../13-scanner-engine-and-scoring.md)).
- [ ] Portfolio-risk output is factual event reporting only; no field reduces to a prescription; holdings stay PII-class and row-scoped ([docs/13 §4.13](../13-scanner-engine-and-scoring.md), [08](08-v3-portfolio-risk-alerts.md)).
- [ ] Every AI-explanation payload is facts-only (no forward price/target/return/stop); language contract tests pass across all scanners ([docs/13 §6, §8](../13-scanner-engine-and-scoring.md)).
- [ ] Composite-bearing scanners stamp `weights-v1-hypothesis`/`PENDING_M3B`; blended composite not wired to UI until [03-scanner-score-validation.md](03-scanner-score-validation.md) passes ([SPEC §6.5](../../SPEC.md)).
