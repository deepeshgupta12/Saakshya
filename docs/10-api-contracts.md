# 10 — API Contracts

> Every API group and endpoint for Saakshya: method, path, purpose, request/response schemas, error codes, auth, cache, and rate limits — under a single standard envelope.
>
> Read first: [SPEC.md](../SPEC.md)

---

## 0. Conventions

- **Base path:** `/api/v1`. Versioning is in the URI; deprecations announced via `Deprecation`/`Sunset` headers.
- **Mode A v1** ([SPEC §2–§5](../SPEC.md)): **no endpoint returns per-stock entry/target/SL, "candidate" buy-leans, or ranked "what to buy".** AI and `levels` endpoints are explicitly mode-gated below. RA-gated fields are absent (not null) until Mode B is in force.
- **Evidence-first** ([SPEC §6.6](../SPEC.md)): every data value is reproducible; responses carry `as_of` and `data_confidence`.
- **Auth:** Bearer JWT (or API key for Enterprise). `public` = no auth. Plan gating per [SPEC §11](../SPEC.md): Free / Premium / Pro / Enterprise.
- **Cache:** TTL is gateway/CDN behavior. `eod` = cache until next pipeline run (long TTL, keyed by `as_of`); `short` = seconds–minutes; `none` = per-user or generative.
- **Rate limit:** per-user/plan token bucket; AI endpoints stricter. Exceeding → `429`.

### 0.1 Standard response envelope

```json
{
  "data": { },
  "meta": {
    "as_of": "2026-06-26",
    "data_confidence": "high",
    "source": "nse_bhavcopy",
    "is_adjusted": true,
    "generated_at": "2026-06-27T02:14:08Z",
    "request_id": "req_8f1c...",
    "page": { "limit": 50, "offset": 0, "total": 1873 }
  },
  "error": null
}
```

- `as_of` — point-in-time date the data is reproducible for ([SPEC §6.2](../SPEC.md)).
- `data_confidence` — `high | medium | low | suppressed` (user-visible indicator, [SPEC §6.2](../SPEC.md)). `suppressed` means a critical input was missing and the value/AI output was **not guessed**.
- `is_adjusted` — whether prices are corporate-action adjusted ([SPEC §6.1](../SPEC.md)).
- `page` — present on list endpoints.

### 0.2 Standard error format

```json
{
  "data": null,
  "meta": { "request_id": "req_8f1c..." },
  "error": {
    "code": "PLAN_REQUIRED",
    "message": "This scanner requires the Premium plan.",
    "details": { "required_plan": "premium", "current_plan": "free" },
    "retriable": false
  }
}
```

### 0.3 Common error codes

| HTTP | code | Meaning |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Malformed params/body |
| 401 | `UNAUTHENTICATED` | Missing/invalid token |
| 403 | `FORBIDDEN` | Authenticated but not allowed |
| 403 | `PLAN_REQUIRED` | Feature needs a higher plan |
| 403 | `MODE_GATED` | Feature requires RA (Mode B); absent in v1 |
| 404 | `NOT_FOUND` | Unknown symbol/resource |
| 409 | `CONFLICT` | Duplicate/state conflict |
| 422 | `DATA_SUPPRESSED` | Critical input missing; value not guessed |
| 429 | `RATE_LIMITED` | Over rate limit (`Retry-After`) |
| 500 | `INTERNAL` | Unexpected error |
| 503 | `PIPELINE_UNAVAILABLE` | EOD data not yet published for date |

> **Local-first ([SPEC §12](../SPEC.md)):** auth/plan-gating/rate-limit may be stubbed; envelope, `as_of`, `data_confidence`, and the guardrail check on AI output remain.

---

## 1. Auth API

### POST /api/auth/register
- **Purpose:** create account. **Auth:** public. **Cache:** none. **Rate:** 5/min/IP.
- **Body:** `{ "email": "u@x.com", "password": "•••", "display_name": "Asha" }`
- **200:** `{ "data": { "user_id": "usr_1", "email": "u@x.com" } }`
- **Errors:** 400 `VALIDATION_ERROR`, 409 `CONFLICT` (email exists).

### POST /api/auth/login
- **Purpose:** issue tokens. **Auth:** public. **Cache:** none. **Rate:** 10/min/IP.
- **Body:** `{ "email": "u@x.com", "password": "•••" }`
- **200:** `{ "data": { "access_token": "ey...", "refresh_token": "ey...", "expires_in": 900, "plan": "free" } }`
- **Errors:** 401 `UNAUTHENTICATED`, 429 `RATE_LIMITED`.

### POST /api/auth/refresh
- **Purpose:** rotate access token. **Auth:** refresh token. **Body:** `{ "refresh_token": "ey..." }`
- **200:** `{ "data": { "access_token": "ey...", "expires_in": 900 } }` · **Errors:** 401.

### POST /api/auth/logout
- **Purpose:** revoke refresh token. **Auth:** Bearer. **200:** `{ "data": { "ok": true } }`.

---

## 2. Market API

### GET /api/market/summary
- **Purpose:** top-of-app EOD market snapshot (key indices, advances/declines headline). **Auth:** Bearer (Free). **Cache:** `eod`. **Rate:** 60/min.
- **Params:** `date?` (defaults latest published).
- **200:**
```json
{
  "data": {
    "session_date": "2026-06-26",
    "indices": [
      { "symbol": "NIFTY50", "close": 23456.7, "change": 112.3, "change_pct": 0.48 },
      { "symbol": "SENSEX", "close": 77123.4, "change": 351.2, "change_pct": 0.46 }
    ],
    "breadth": { "advances": 1320, "declines": 540, "unchanged": 60 },
    "headline": "Broad market closed higher; advance/decline favoured advances."
  },
  "meta": { "as_of": "2026-06-26", "data_confidence": "high", "is_adjusted": true }
}
```
- **Errors:** 503 `PIPELINE_UNAVAILABLE`. **Mode note:** `headline` is descriptive, guardrail-checked.

### GET /api/market/breadth
- **Purpose:** market breadth detail (A/D, new highs/lows, % above MAs). **Auth:** Bearer. **Cache:** `eod`. **Rate:** 60/min.
- **Params:** `date?`, `universe?` (`nifty500|all`).
- **200:** `{ "data": { "advances": 1320, "declines": 540, "unchanged": 60, "new_highs": 41, "new_lows": 12, "pct_above_50dma": 58.2, "pct_above_200dma": 47.1 } }`

### GET /api/indices
- **Purpose:** list indices with EOD OHLC. **Auth:** Bearer. **Cache:** `eod`. **Rate:** 60/min.
- **Params:** `date?`, `group?` (`broad|sectoral|thematic`).
- **200:** `{ "data": [ { "symbol": "NIFTYBANK", "name": "Nifty Bank", "open": 51200, "high": 51640, "low": 51010, "close": 51590, "change_pct": 0.71 } ] }`

---

## 3. Sector API

### GET /api/sectors
- **Purpose:** sector strength dashboard. **Auth:** Bearer. **Cache:** `eod`. **Rate:** 60/min.
- **Params:** `date?`, `sort?` (`strength|change`).
- **200:**
```json
{ "data": [
  { "sector_id": "SEC_IT", "name": "IT", "strength_score": 72.4, "change_pct": 1.2, "breadth_pct_up": 68, "rank": 1 },
  { "sector_id": "SEC_FIN", "name": "Financials", "strength_score": 64.1, "change_pct": 0.5, "breadth_pct_up": 55, "rank": 2 }
] }
```

### GET /api/sectors/{id}/summary
- **Purpose:** one sector: score breakdown, constituents, leaders/laggards (descriptive). **Auth:** Bearer. **Cache:** `eod`. **Rate:** 60/min.
- **200:**
```json
{ "data": {
  "sector_id": "SEC_IT", "name": "IT", "strength_score": 72.4,
  "sub_scores": { "momentum": 70, "breadth": 75, "relative_strength": 72 },
  "constituents": [ { "symbol": "TCS", "change_pct": 1.4, "above_50dma": true } ],
  "narrative": "IT showed broad participation with most constituents above their 50-DMA."
} }
```
- **Errors:** 404 `NOT_FOUND`. **Mode note:** `narrative` descriptive, guardrail-checked.

---

## 4. Stock API

### GET /api/stocks/search
- **Purpose:** symbol/name search. **Auth:** Bearer. **Cache:** `short`. **Rate:** 120/min.
- **Params:** `q` (required), `limit?` (≤20), `exchange?`.
- **200:** `{ "data": [ { "symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "isin": "INE040A01034", "exchange": "NSE", "sector": "Financials" } ] }`
- **Errors:** 400 `VALIDATION_ERROR` (missing `q`).

### GET /api/stocks/{symbol}/overview
- **Purpose:** stock detail header — last EOD OHLCV, key indicators, scanner memberships, risk score. **Auth:** Bearer. **Cache:** `eod`. **Rate:** 120/min.
- **200:**
```json
{ "data": {
  "symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "isin": "INE040A01034",
  "ohlc": { "open": 1670, "high": 1689, "low": 1662, "close": 1685, "volume": 9123456, "delivery_pct": 61.2 },
  "indicators": { "rsi_14": 58.3, "sma_50": 1620.4, "sma_200": 1554.1, "above_50dma": true, "volume_ratio_20": 1.8 },
  "scanner_memberships": ["momentum", "volume-breakout"],
  "risk_score": { "value": 42, "band": "moderate" }
}, "meta": { "as_of": "2026-06-26", "data_confidence": "high", "is_adjusted": true } }
```
- **Errors:** 404 `NOT_FOUND`, 422 `DATA_SUPPRESSED`. **Mode note:** memberships use neutral language; **no entry/target/SL**.

### GET /api/stocks/{symbol}/technicals
- **Purpose:** full indicator set + optional OHLC series. **Auth:** Bearer. **Cache:** `eod`. **Rate:** 120/min.
- **Params:** `range?` (`1m|3m|6m|1y|max`), `adjusted?` (default `true`).
- **200:**
```json
{ "data": {
  "symbol": "HDFCBANK",
  "latest": { "rsi_14": 58.3, "macd": 4.1, "macd_signal": 3.2, "atr_14": 21.5,
              "bb_upper": 1712, "bb_lower": 1601, "ema_21": 1655, "sma_20": 1648,
              "sma_50": 1620.4, "sma_200": 1554.1, "ret_20d_pct": 6.4, "volume_ratio_20": 1.8 },
  "series": [ { "date": "2026-06-26", "close": 1685, "rsi_14": 58.3 } ]
} }
```
- **Mode note:** descriptive support/resistance only via `levels`; technicals carry no trade instruction.

### GET /api/stocks/{symbol}/news
- **Purpose:** resolved news with sentiment. **Auth:** Bearer (Premium). **Cache:** `short`. **Rate:** 60/min.
- **Params:** `limit?`, `since?`.
- **200:**
```json
{ "data": [ {
  "article_id": "news_44", "headline": "Q1 results beat estimates",
  "published_at": "2026-06-25T11:00:00Z", "source": "ExampleWire", "url": "https://...",
  "link_confidence": 0.94, "sentiment": { "label": "positive", "score": 0.71, "model_version": "fin-sent-2.1" }
} ] }
```
- **Errors:** 403 `PLAN_REQUIRED`. **Mode note:** below-threshold links not surfaced ([SPEC §6.4](../SPEC.md)).

### GET /api/stocks/{symbol}/ai-summary
- **Purpose:** grounded, descriptive AI explanation of the stock's current signals. **Auth:** Bearer (Premium). **Cache:** `eod` (served from cache when signals unchanged, [SPEC §6.8](../SPEC.md)). **Rate:** 30/min, AI bucket.
- **200:**
```json
{ "data": {
  "symbol": "HDFCBANK",
  "summary": "This stock is showing positive short-term momentum because it is trading above its 20-DMA and 50-DMA, and recent volume is higher than its 20-day average. Sector strength is supportive. However, RSI is elevated, so the risk of a short-term pullback is higher. The nearest resistance level is one to watch.",
  "evidence": [ { "claim": "trading above its 50-DMA", "field": "indicators.above_50dma", "value": true } ],
  "model_version": "claude-haiku-4-5-20251001", "audit_id": "aud_991",
  "disclaimer": "Not investment advice."
}, "meta": { "data_confidence": "high" } }
```
- **Errors:** 422 `DATA_SUPPRESSED` (critical input missing → **suppressed, not guessed**, [SPEC §6.2](../SPEC.md)), 429. **Mode note:** every number traces to payload; banned phrases blocked at output ([SPEC §6.6](../SPEC.md), [§6.9](../SPEC.md)); **no entry/target/SL**, no directive tail.

### GET /api/stocks/{symbol}/peers
- **Purpose:** comparative peer table (descriptive). **Auth:** Bearer (Premium). **Cache:** `eod`. **Rate:** 60/min.
- **200:** `{ "data": { "symbol": "TCS", "peers": [ { "symbol": "INFY", "change_pct_20d": 5.1, "rsi_14": 60, "relative_strength": 1.04 } ] } }`
- **Mode note:** comparative, not directive ([SPEC §4](../SPEC.md)).

### GET /api/stocks/{symbol}/levels
- **Purpose:** **descriptive, historical** support/resistance zones only. **Auth:** Bearer. **Cache:** `eod`. **Rate:** 60/min.
- **200:**
```json
{ "data": {
  "symbol": "HDFCBANK",
  "resistance": [ { "price": 1712, "framing": "historically a resistance zone" } ],
  "support": [ { "price": 1601, "framing": "a level that has acted as support" } ]
} }
```
- **Mode note (critical):** **NO entry/target/stop-loss/invalidation zones** — those are RA-gated (Phase 5). Such fields return `MODE_GATED` if requested ([SPEC §3.2](../SPEC.md), [§4](../SPEC.md), [§5](../SPEC.md)).

---

## 5. Scanner API

### GET /api/scanners
- **Purpose:** list available scanners + plan gating. **Auth:** Bearer. **Cache:** `eod`. **Rate:** 60/min.
- **200:** `{ "data": [ { "id": "momentum", "name": "Momentum", "plan": "free" }, { "id": "volume-breakout", "name": "Volume Breakout", "plan": "premium" } ] }`

### GET /api/scanners/momentum
- **Purpose:** momentum scanner results (score + reasons + risk flags). **Auth:** Bearer (Free, limited). **Cache:** `eod`. **Rate:** 60/min.
- **Params:** `date?`, `universe?`, `limit?`, `offset?`, `min_score?`, `sort?`.
- **200:**
```json
{ "data": [ {
  "symbol": "TATAMOTORS", "score": 81, 
  "sub_scores": { "momentum": 25, "volume": 18, "trend": 22, "relative_strength": 16 },
  "reasons": [ "trading above its 50-DMA", "20-day return in the top decile", "volume expanded 1.9x vs its 20-day average" ],
  "risk_flags": [ "RSI elevated (72)" ]
} ], "meta": { "as_of": "2026-06-26", "data_confidence": "high" } }
```
- **Mode note:** "appears in the momentum scanner" framing; scores validated ([SPEC §6.5](../SPEC.md)); missing sub-scores marked neutral.

### GET /api/scanners/volume-breakout
- **Purpose:** volume/delivery breakout results. **Auth:** Bearer (Premium). **Cache:** `eod`. **Rate:** 60/min.
- **Params:** `date?`, `min_volume_ratio?`, `min_delivery_pct?`.
- **200:** `{ "data": [ { "symbol": "BEL", "volume_ratio_20": 3.2, "delivery_pct": 64.1, "score": 77, "reasons": ["volume expanded 3.2x"], "risk_flags": ["false-breakout risk: thin prior range"] } ] }`
- **Mode note:** false-breakout **risk flag** allowed; **no "buy the breakout"** ([SPEC §4](../SPEC.md)).

### GET /api/scanners/rsi
- **Purpose:** RSI-based scanner (oversold/overbought membership, descriptive). **Auth:** Bearer (Free, limited). **Cache:** `eod`. **Rate:** 60/min.
- **Params:** `band?` (`overbought|oversold`), `period?` (default 14).
- **200:** `{ "data": [ { "symbol": "ITC", "rsi_14": 28.4, "band": "oversold", "reasons": ["RSI(14) below 30"] } ] }`

### POST /api/scanners/custom
- **Purpose:** run a user-defined no-code scanner (Phase 3). **Auth:** Bearer (Pro). **Cache:** `none`. **Rate:** 20/min.
- **Body:**
```json
{ "name": "My breakout", "universe": "nifty500",
  "rules": [ { "field": "rsi_14", "op": ">", "value": 60 },
             { "field": "volume_ratio_20", "op": ">=", "value": 2 } ],
  "logic": "AND", "sort": "volume_ratio_20", "limit": 50 }
```
- **200:** `{ "data": { "matched": 23, "results": [ { "symbol": "...", "fields": { "rsi_14": 63, "volume_ratio_20": 2.4 } } ] } }`
- **Errors:** 400 `VALIDATION_ERROR` (unknown field/op), 403 `PLAN_REQUIRED`. **Mode note:** output is a **list**, never calls ([SPEC §4](../SPEC.md)).

### POST /api/scanners/custom/backtest
- **Purpose:** backtest a custom scanner with integrity controls (Phase 4). **Auth:** Bearer (Pro). **Cache:** `none`. **Rate:** 5/min.
- **Body:** `{ "rules": [...], "logic": "AND", "from": "2022-01-01", "to": "2025-12-31", "rebalance": "weekly", "slippage_bps": 15 }`
- **202:** `{ "data": { "run_id": "bt_771", "status": "queued" } }` (poll `GET /api/backtest/{run_id}`).
- **Mode note:** survivorship/look-ahead/point-in-time enforced ([SPEC §6.3](../SPEC.md)); honest framing in results.

---

## 6. Watchlist API

### GET /api/watchlists
- **Auth:** Bearer. **Cache:** `none`. **Rate:** 60/min. **200:** `{ "data": [ { "id": "wl_1", "name": "Banks", "item_count": 8 } ] }`

### POST /api/watchlists
- **Body:** `{ "name": "Banks" }` · **201:** `{ "data": { "id": "wl_1", "name": "Banks" } }` · **Errors:** 409 (dup name), 403 `PLAN_REQUIRED` (Free list cap).

### GET /api/watchlists/{id}
- **200:** `{ "data": { "id": "wl_1", "name": "Banks", "items": [ { "symbol": "HDFCBANK", "added_at": "2026-06-01", "change_pct": 0.4 } ] } }` · **Errors:** 404.

### PUT /api/watchlists/{id}
- **Body:** `{ "name": "Indian Banks" }` · **200:** updated object · **Errors:** 404, 409.

### DELETE /api/watchlists/{id}
- **204** · **Errors:** 404.

### POST /api/watchlists/{id}/items
- **Body:** `{ "symbol": "ICICIBANK" }` · **201:** item · **Errors:** 404, 409 (already present), 403 (item cap).

### DELETE /api/watchlists/{id}/items/{symbol}
- **204** · **Errors:** 404.

> **Mode note:** "AI suggested watchlist" is **filter-based discovery**, never per-user buy-leans ([SPEC §4](../SPEC.md)).

---

## 7. Portfolio API

### POST /api/portfolio/holdings
- **Purpose:** add/update a holding. **Auth:** Bearer (Premium). **Cache:** `none`. **Rate:** 60/min.
- **Body:** `{ "symbol": "INFY", "quantity": 50, "avg_cost": 1450.0, "exchange": "NSE" }`
- **201:** `{ "data": { "holding_id": "hld_3", "symbol": "INFY", "quantity": 50, "avg_cost": 1450.0 } }`
- **Errors:** 400, 404 (unknown symbol), 403 `PLAN_REQUIRED`.

### GET /api/portfolio/summary
- **Purpose:** valuation + P&L from latest EOD prices. **Auth:** Bearer (Premium). **Cache:** `none` (computed per request, reproducible from `as_of`). **Rate:** 60/min.
- **200:**
```json
{ "data": {
  "market_value": 245300.0, "invested": 222000.0, "pnl": 23300.0, "pnl_pct": 10.5,
  "holdings": [ { "symbol": "INFY", "quantity": 50, "avg_cost": 1450, "ltp": 1612, "pnl_pct": 11.2 } ]
}, "meta": { "as_of": "2026-06-26", "is_adjusted": true } }
```

### GET /api/portfolio/risk
- **Purpose:** **factual** per-holding risk events + aggregate concentration. **Auth:** Bearer (Pro). **Cache:** `none`. **Rate:** 60/min.
- **200:**
```json
{ "data": {
  "concentration": { "top_holding_pct": 28.4, "sector_max_pct": 41.0 },
  "flags": [ { "symbol": "INFY", "event": "broke below its 50-DMA", "as_of": "2026-06-26" } ]
} }
```
- **Mode note:** flags are **events**, never "sell X" ([SPEC §4](../SPEC.md)).

---

## 8. Alert API

### GET /api/alerts
- **Auth:** Bearer (Premium). **Cache:** `none`. **200:** `{ "data": [ { "id": "al_1", "type": "scanner_entry", "target": "momentum", "symbol": null, "active": true } ] }`

### POST /api/alerts
- **Body:**
```json
{ "type": "scanner_entry", "target": "momentum", "symbol": "TCS", "channels": ["in_app", "email"] }
```
- **201:** `{ "data": { "id": "al_1", "active": true } }` · **Errors:** 400, 403 `PLAN_REQUIRED`.
- **Mode note:** EOD-batch; **event-reporting only** ("entered the scanner"), never "buy at open" ([SPEC §4](../SPEC.md)).

### PUT /api/alerts/{id}
- **Body:** `{ "active": false }` · **200:** updated · **Errors:** 404.

### DELETE /api/alerts/{id}
- **204** · **Errors:** 404.

### GET /api/alerts/{id}/events
- **200:** `{ "data": [ { "event_id": "ae_5", "fired_at": "2026-06-27T02:30:00Z", "message": "TCS entered the momentum scanner", "cause": { "scanner": "momentum", "score": 81 } } ] }`

---

## 9. AI API

> All AI endpoints: payload-contract grounded, runtime-verified, audit-logged, banned-phrase blocked at output ([SPEC §6.6](../SPEC.md), [§6.9](../SPEC.md)). **Mode A:** no entry/target/SL, no ranked "what to buy", no directive tails. Suppress (don't guess) on missing critical inputs.

### POST /api/ai/ask
- **Purpose:** free-form Q&A grounded strictly in available structured data (no invention). **Auth:** Bearer (Premium). **Cache:** `none`. **Rate:** 10/min, AI bucket.
- **Body:** `{ "question": "Why is TCS in the momentum scanner today?", "symbol": "TCS" }`
- **200:**
```json
{ "data": {
  "answer": "TCS appears in the momentum scanner because its 20-day return is in the top decile and it is trading above its 50-DMA, with volume above its 20-day average. RSI is elevated, so short-term pullback risk is higher.",
  "evidence": [ { "claim": "above its 50-DMA", "field": "indicators.above_50dma", "value": true } ],
  "audit_id": "aud_1002", "model_version": "claude-haiku-4-5-20251001",
  "disclaimer": "Not investment advice."
} }
```
- **Errors:** 422 `DATA_SUPPRESSED`, 429. **Mode note:** refuses/blocks any directive or out-of-scope request.

### GET /api/ai/market-brief
- **Purpose:** descriptive EOD market brief — events + what to **monitor**, never a ranked "what to buy". **Auth:** Bearer (Premium). **Cache:** `eod`. **Rate:** 30/min.
- **200:** `{ "data": { "date": "2026-06-26", "brief": "Markets closed higher with broad participation. IT and Financials led on breadth. 41 stocks made new 1-month highs. Stocks that entered the momentum scanner today: TATAMOTORS, BEL. Elevated RSI in several names suggests higher short-term volatility to monitor.", "audit_id": "aud_1003" } }`
- **Mode note:** "stocks that entered/exited the momentum scanner today", not actionable picks ([SPEC §5](../SPEC.md)).

### GET /api/ai/stock-summary/{symbol}
- **Purpose:** alias of `GET /api/stocks/{symbol}/ai-summary` (AI-namespace convenience). Same contract, cache, and Mode-A constraints.

### POST /api/ai/strategy-builder
- **Purpose:** translate a natural-language description into a **no-code scanner rule set** (a list-producing filter), Phase 4. **Auth:** Bearer (Pro). **Cache:** `none`. **Rate:** 10/min, AI bucket.
- **Body:** `{ "description": "high relative strength large caps with rising volume" }`
- **200:**
```json
{ "data": {
  "rules": [ { "field": "relative_strength", "op": ">", "value": 1.0 },
             { "field": "market_cap_band", "op": "=", "value": "large" },
             { "field": "volume_ratio_20", "op": ">=", "value": 1.5 } ],
  "logic": "AND",
  "note": "Outputs a filtered list of matching stocks. Not investment advice.",
  "audit_id": "aud_1004"
} }
```
- **Mode note:** produces filter rules / lists, **never calls** ([SPEC §4](../SPEC.md)).

---

## 10. News API

### GET /api/news
- **Purpose:** market-wide resolved news feed with sentiment. **Auth:** Bearer (Premium). **Cache:** `short`. **Rate:** 60/min.
- **Params:** `symbol?`, `sector?`, `since?`, `limit?`, `min_confidence?`.
- **200:** same article shape as §4 `/stocks/{symbol}/news`. **Mode note:** below-threshold links not surfaced.

### GET /api/news/announcements
- **Purpose:** corporate announcements (results, splits, board meetings). **Auth:** Bearer (Premium). **Cache:** `short`.
- **200:** `{ "data": [ { "symbol": "RELIANCE", "type": "board_meeting", "headline": "Board to consider Q1 results", "date": "2026-07-12", "url": "https://..." } ] }`
- **Mode note:** "do not exaggerate impact" ([SPEC §4](../SPEC.md)).

---

## 11. Strategy & Backtesting API

### GET /api/strategies
- **Auth:** Bearer (Pro). **Cache:** `none`. **200:** `{ "data": [ { "id": "str_1", "name": "RS momentum", "created_at": "2026-05-01" } ] }`

### POST /api/strategies
- **Body:** `{ "name": "RS momentum", "rules": [...], "logic": "AND", "rebalance": "weekly" }`
- **201:** `{ "data": { "id": "str_1" } }`.

### POST /api/backtest/run
- **Purpose:** queue a backtest with integrity controls. **Auth:** Bearer (Pro). **Cache:** `none`. **Rate:** 5/min.
- **Body:** `{ "strategy_id": "str_1", "from": "2021-01-01", "to": "2025-12-31", "slippage_bps": 15, "liquidity_cap_pct_adv": 5, "universe": "nifty500" }`
- **202:** `{ "data": { "run_id": "bt_771", "status": "queued" } }`
- **Mode note:** look-ahead/survivorship/point-in-time membership enforced ([SPEC §6.3](../SPEC.md)).

### GET /api/backtest/{run_id}
- **Purpose:** fetch status/results. **Auth:** Bearer (Pro). **Cache:** `none`.
- **200 (done):**
```json
{ "data": {
  "run_id": "bt_771", "status": "completed",
  "assumptions": { "slippage_bps": 15, "survivorship_controlled": true, "look_ahead_controlled": true, "point_in_time_membership": true },
  "metrics": { "cagr_pct": 14.2, "max_drawdown_pct": -22.1, "sharpe": 0.9, "trades": 412, "win_rate_pct": 51 },
  "disclaimer": "Past performance does not indicate future results."
} }
```
- **Errors:** 404, 202-style `status: "running"`. **Mode note:** assumptions exposed; honest framing mandatory.

---

## 12. Admin API

> **Auth:** Bearer with `admin` scope (RBAC). **Cache:** `none`. **Rate:** 30/min. All changes versioned and attributed.

### GET /api/admin/data-quality
- **Purpose:** ingestion job & data-quality status, quarantine list. **200:** `{ "data": { "jobs": [ { "date": "2026-06-26", "source": "nse_bhavcopy", "status": "ok", "quarantined": 3 } ], "quarantine": [ { "symbol": "XYZ", "reason": "abnormal_jump", "as_of": "2026-06-26" } ] } }`

### POST /api/admin/data-quality/{symbol}/correct
- **Purpose:** correct + re-emit dependents. **Body:** `{ "date": "2026-06-26", "action": "reingest", "note": "vendor restated" }` · **200:** `{ "data": { "requeued": ["indicators", "scanners", "ai_summary"] } }` ([SPEC §6.2](../SPEC.md)).

### GET/POST/PUT /api/admin/prompts
- **Purpose:** versioned AI prompt management. **POST body:** `{ "key": "stock_summary", "version": 7, "template": "...", "model": "claude-haiku-4-5-20251001" }` · **200:** version record. **Mode note:** changes trigger the evaluation harness ([SPEC §6.6](../SPEC.md)).

### GET/POST/PUT /api/admin/scanner-rules
- **Purpose:** manage scanner definitions/rules/weights. **POST body:** `{ "scanner_id": "momentum", "weights": { "momentum": 0.25, "volume": 0.20, "trend": 0.30, "relative_strength": 0.25 } }` · **200:** version record. **Mode note:** weight changes require validation evidence ([SPEC §6.5](../SPEC.md)).

### GET/POST/PUT /api/admin/compliance-rules
- **Purpose:** versioned blocked-phrase/pattern list. **POST body:** `{ "version": 12, "blocked_patterns": ["guaranteed", "sure-shot", "risk-free", "buy now", "target confirmed", "multibagger"] }` · **200:** version record. **Mode note:** enforced **at output time** ([SPEC §6.9](../SPEC.md), [§3.3](../SPEC.md)).

---

## 13. Billing API

### GET /api/billing/subscription
- **Auth:** Bearer. **Cache:** `none`. **200:** `{ "data": { "plan": "premium", "status": "active", "renews_at": "2026-07-26" } }`

### POST /api/billing/subscribe
- **Body:** `{ "plan": "pro", "payment_token": "tok_..." }` · **200:** `{ "data": { "plan": "pro", "status": "active" } }`
- **Errors:** 402-style `PAYMENT_FAILED`, 409. **Mode note:** RA-operated tiers respect the SEBI fee cap (~₹1.51L/yr/family) ([SPEC §11](../SPEC.md)).

### POST /api/billing/cancel
- **200:** `{ "data": { "plan": "premium", "status": "canceled", "active_until": "2026-07-26" } }`

### GET /api/billing/transactions
- **200:** `{ "data": [ { "id": "txn_9", "amount": 999, "currency": "INR", "status": "paid", "at": "2026-06-26" } ] }`

---

## 14. Cross-cutting acceptance criteria

- **Envelope:** every 2xx carries `data` + `meta.as_of` + `meta.data_confidence`; every error uses the standard error object.
- **Reproducibility:** any data value is reconstructable from stored series for its `as_of` ([SPEC §6.2](../SPEC.md)).
- **Mode A:** no endpoint exposes entry/target/SL, buy-leans, or ranked picks; requesting RA-gated fields returns `MODE_GATED`.
- **AI:** every AI response carries `audit_id` + `model_version`; outputs are grounded, guardrail-checked, and suppressed (not guessed) when inputs are missing.
- **Plan gating:** Free vs Premium vs Pro enforced at the gateway with `PLAN_REQUIRED`.
