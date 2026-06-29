# 04 — Feature Modules

In-depth definition of every Saakshya product module: purpose, data, dependencies, states, personalization, analytics, and required regulatory mode.

> Read first: [SPEC.md](../SPEC.md) (canonical source of truth).

---

## 0. How to read this file

Each module defines: **Purpose · Input data · Backend dependency · Frontend components · User actions · Empty / Loading / Error / Success states · Personalization (Mode-A navigation-only) · Analytics events · Future enhancements · Required mode**.

**Mode legend** ([SPEC.md §4](../SPEC.md)): **A** = Mode-A safe · **A+RA** = needs RA before the directive parts · **B** = RA-only · **N/A** = infrastructure.

**Universal rules for every module:**
- AI explains structured signals; it **never invents** numbers, prices, news, targets, returns, or recommendations.
- No per-stock entry/target/SL, no "candidate" buy-leans (RA-gated).
- Always-prohibited phrases (guarantee, sure-shot, risk-free, multibagger, buy now, assured/confirmed target) are blocked **at output time** ([SPEC.md §6.9](../SPEC.md)).
- Personalization is **navigation-only** (layout, followed sectors, default filters) — never per-stock behavioural suggestions ([SPEC.md §7](../SPEC.md)).
- Displayed values are **as-of versioned**; AI suppressed (not guessed) when critical inputs missing.

**Module index by mode and version:**

| Module | Mode | Ships | Pillar |
|---|---|---|---|
| Market dashboard | A | V1 | Market intelligence |
| Momentum / volume / RSI / MA scanners | A | V1 | Technical scanners |
| Breakout / breakdown scanners | A | V1 | Technical scanners |
| Screener library | A | V1 | Technical scanners |
| Sector dashboard | A | V1 | Sector intelligence |
| Risk engine | A | V1 | Risk monitoring |
| Stock detail page | A | V1 | Market intelligence |
| AI stock summary | A | V2 | AI explanations |
| Watchlist | A | V2 | Portfolio intelligence |
| News sentiment | A | V2 | News sentiment |
| AI daily market brief | A | V2 | Market intelligence |
| AI assistant | A | V2 | AI explanations |
| Notification center | A | V2 | Alerts |
| User profile | A / N/A | V2 | Accounts |
| Portfolio tracker | A | V3 | Portfolio intelligence |
| Alerting | A | V3 | Alerts |
| Theme baskets | A | V3 | Sector intelligence |
| Corporate announcements | A | V2–V3 | News sentiment |
| Peer comparison | A | V3 | Portfolio intelligence |
| Institutional activity | A | V4 (Phase 4 premium) | Market intelligence |
| Personalization (navigation) | A | V2+ | Accounts |
| Strategy / scanner builder | A | V4 | Backtesting & strategy |
| Backtesting | A | V5 | Backtesting & strategy |
| Pricing / subscription | A / N/A | V2+ | Monetization |
| Admin panel | N/A | V1+ | Governance |

---

## 1. Market dashboard

- **Purpose:** EOD/T+1 overview of indices, market breadth, and a **descriptive** AI market summary.
- **Input data:** Index OHLCV; breadth (advances/declines, % above 50/200-DMA); sector aggregates; as-of date; data-confidence.
- **Backend dependency:** Ingestion + corp-action adjustment; indicator + breadth computation; sector aggregation; AI market-summary generation under guardrails. See [Backend](09-backend-architecture.md), [Data ingestion](12-data-ingestion-and-market-data.md).
- **Frontend components:** Index cards, breadth widgets, sector heat strip, AI summary card, as-of + confidence badge.
- **User actions:** Drill into sector/scanner; change followed-sector ordering.
- **States:** *Empty* — pre-market or no data: show last as-of + "awaiting next EOD." *Loading* — skeleton cards. *Error* — "Market data unavailable for this date"; AI summary suppressed. *Success* — full dashboard with confidence badge.
- **Personalization:** Followed sectors prioritized in layout; default index focus.
- **Analytics events:** `dashboard_view`, `sector_strip_click`, `market_summary_view`.
- **Future:** Intraday breadth (V7, live-data tier).
- **Mode:** **A** — AI market summary must be **descriptive, not directive**.

## 2. Momentum scanner

- **Purpose:** Rank instruments by a validated momentum score; show **score + sub-scores + reasons + risk flags**.
- **Input data:** Adjusted OHLCV; returns; relative strength; volume ratio; RSI/MA inputs.
- **Backend dependency:** Indicator library; scanner engine with **validated** scoring (M3b); risk-flag computation. See [Scanner engine](13-scanner-engine-and-scoring.md).
- **Frontend components:** Results table (score, sub-scores, reasons, risk flags), filters, sort, add-to-watchlist.
- **User actions:** Filter (sector/risk), sort, open stock, add to watchlist, create alert.
- **States:** *Empty* — no matches: "No instruments match this filter today." *Loading* — table skeleton. *Error* — "Scanner unavailable for this date." *Success* — ranked list with reasons.
- **Personalization:** Default filters from stated risk preference; followed sectors first.
- **Analytics events:** `scanner_view{type=momentum}`, `scanner_filter`, `scanner_result_click`, `scanner_to_watchlist`.
- **Future:** Custom weights via builder (V4); ML-ranked variant (V5).
- **Mode:** **A** — neutral language ("appears in the momentum scanner"); **no buy-leans**.

## 3. Volume breakout scanner

- **Purpose:** Surface unusual volume / delivery expansion.
- **Input data:** Volume; **delivery quantity / delivery %** (NSE sec_bhavdata); 20-day average volume.
- **Backend dependency:** Delivery-file ingestion paired with bhavcopy by date; volume-ratio scoring.
- **Frontend components:** Results table (volume ratio, delivery %, reasons, risk flags).
- **User actions:** Filter, sort, open stock, watchlist, alert.
- **States:** As §2; *Error* if delivery file missing for the date → flag reduced confidence.
- **Personalization:** Default filters; followed sectors.
- **Analytics events:** `scanner_view{type=volume}`, etc.
- **Future:** Block-deal correlation (data-dependent).
- **Mode:** **A**.

## 4. RSI scanner

- **Purpose:** Find oversold/overbought conditions descriptively.
- **Input data:** RSI (adjusted series); MA context.
- **Backend dependency:** RSI computation; scanner engine.
- **Frontend components:** Results table (RSI value, context, risk flags).
- **User actions:** Filter by RSI band, sort, open, watchlist, alert.
- **States:** As §2.
- **Personalization:** Default RSI band from risk preference.
- **Analytics events:** `scanner_view{type=rsi}`.
- **Future:** Divergence detection.
- **Mode:** **A** — "RSI is elevated → pullback risk higher"; never "buy oversold."

## 5. Moving average scanner

- **Purpose:** Filter by MA relationships (above/below 20/50/200-DMA, crossovers).
- **Input data:** SMA/EMA 20/50/200 on adjusted series.
- **Backend dependency:** MA computation; crossover detection.
- **Frontend components:** Results table (MA state, crossover flags).
- **User actions:** Filter, sort, open, watchlist, alert.
- **States:** As §2.
- **Personalization:** Default MA set.
- **Analytics events:** `scanner_view{type=ma}`.
- **Future:** Multi-timeframe MA stacks.
- **Mode:** **A** — "trading above its 50-DMA" (descriptive).

## 6. Breakout scanner

- **Purpose:** Detect price breaking above a historical resistance range.
- **Input data:** Adjusted OHLC; range/structure detection; volume confirmation.
- **Backend dependency:** Breakout detection; **false-breakout risk flag**.
- **Frontend components:** Results table (breakout event, false-breakout risk flag).
- **User actions:** Filter, sort, open, watchlist, alert.
- **States:** As §2.
- **Personalization:** Followed sectors.
- **Analytics events:** `scanner_view{type=breakout}`.
- **Future:** Pattern library.
- **Mode:** **A** — false-breakout risk flag OK; **no "buy the breakout"** phrasing.

## 7. Breakdown scanner

- **Purpose:** Detect price breaking below a historical support range.
- **Input data:** Adjusted OHLC; structure detection; volume.
- **Backend dependency:** Breakdown detection; risk flag.
- **Frontend components:** Results table (breakdown event, risk flag).
- **User actions:** As §6.
- **States:** As §2.
- **Personalization:** Followed sectors.
- **Analytics events:** `scanner_view{type=breakdown}`.
- **Future:** Pattern library.
- **Mode:** **A** — state the event; **no "sell the breakdown"** phrasing.

## 8. Sector dashboard

- **Purpose:** Rank sector strength and momentum (explicitly lower-risk analysis).
- **Input data:** Sector-aggregated index technicals; constituent breadth.
- **Backend dependency:** Sector aggregation + scoring.
- **Frontend components:** Sector ranking table/heatmap, sector detail drill-down.
- **User actions:** Open sector, follow sector, drill to constituents.
- **States:** *Empty* — "No sector data for this date." *Loading* — heatmap skeleton. *Error* — date unavailable. *Success* — ranked sectors.
- **Personalization:** Followed sectors highlighted.
- **Analytics events:** `sector_view`, `sector_follow`.
- **Future:** Sector rotation visualizations.
- **Mode:** **A** — descriptive; index/sector technical analysis is lower-risk.

## 9. Theme baskets

- **Purpose:** Curated thematic **bucket views** (e.g., "EV", "PSU banks") — **not** model portfolios.
- **Input data:** Theme→symbol definitions; constituent technicals.
- **Backend dependency:** Basket definitions; constituent aggregation.
- **Frontend components:** Basket list, basket detail (constituents + aggregate technicals).
- **User actions:** Open basket, view constituents, follow.
- **States:** Standard.
- **Personalization:** Followed themes.
- **Analytics events:** `basket_view`, `basket_follow`.
- **Future:** User-defined themes.
- **Mode:** **A** — **bucket views, not model portfolios**.

## 10. Stock detail page

- **Purpose:** Single-instrument hub: facts, scores, **descriptive** support/resistance, AI summary, news, peers.
- **Input data:** Adjusted OHLCV; full indicator set; scanner memberships; risk score; news; corp actions.
- **Backend dependency:** Indicator + scanner + risk services; AI summary; news/sentiment. See [API contracts](10-api-contracts.md).
- **Frontend components:** Price chart, indicator panel, scanner-membership tags, descriptive S/R, risk panel, AI summary card, news feed, peer strip.
- **User actions:** Add to watchlist, create alert, compare peers, read AI summary.
- **States:** *Empty* — delisted/no data: clear notice. *Loading* — section skeletons. *Error* — "Data unavailable"; AI suppressed. *Success* — full page with as-of + confidence.
- **Personalization:** Layout/section order.
- **Analytics events:** `stock_view`, `stock_ai_summary_view`, `stock_add_watchlist`, `stock_create_alert`.
- **Future:** Charting depth; fundamentals bands (Phase 3).
- **Mode:** **A** — **remove entry/target/SL/invalidation zones** (RA-gated); keep descriptive S/R.

## 11. AI stock summary

- **Purpose:** Plain-language explanation of a stock's structured signals.
- **Input data:** Structured payload only — computed metrics, scanner tags, news summaries, risk markers.
- **Backend dependency:** Payload contract; LLM (Claude Haiku default, premium for synthesis); **runtime validator** (numbers/facts vs payload); guardrail (blocked phrases); audit log; caching (regenerate-on-change). See [AI architecture](14-ai-llm-agent-architecture.md).
- **Frontend components:** Summary card with "not investment advice", as-of, confidence; regenerate (where allowed).
- **User actions:** Read; expand reasons.
- **States:** *Empty/Suppressed* — critical input missing: "Summary unavailable — incomplete data" (**not guessed**). *Loading* — streaming/skeleton. *Error* — verification failed → regenerate or suppress. *Success* — verified summary.
- **Personalization:** None on content (navigation only).
- **Analytics events:** `ai_summary_view`, `ai_summary_suppressed`, `ai_summary_verify_fail`.
- **Future:** Multi-signal synthesis agent (V6).
- **Mode:** **A** — grounded, runtime-verified; drop directive tails ("before fresh action" → "a level to watch").

## 12. News sentiment

- **Purpose:** Classify finance news sentiment/impact and resolve it to symbols.
- **Input data:** News feeds; curated **symbol-alias + corporate-hierarchy** map; finance-tuned sentiment classifier.
- **Backend dependency:** News→symbol resolution with **confidence scores + surfacing threshold**; finance-tuned classifier evaluated vs labelled Indian-market set; retained source links + timestamps. See [News & sentiment](18-news-sentiment-and-corporate-actions.md).
- **Frontend components:** News feed per stock/sector; sentiment tag; source link + timestamp; confidence indicator.
- **User actions:** Open source; filter by sentiment.
- **States:** *Empty* — no news. *Loading* — feed skeleton. *Error* — feed unavailable. *Success* — tagged items with sources.
- **Personalization:** Followed sectors/instruments.
- **Analytics events:** `news_view`, `news_source_click`.
- **Future:** Event clustering.
- **Mode:** **A** — do not exaggerate impact; hard entity resolution required.

## 13. Corporate announcements

- **Purpose:** Surface and simplify corporate filings/announcements.
- **Input data:** Exchange announcement feeds; corp-action master.
- **Backend dependency:** Announcement ingestion; simplification under guardrails.
- **Frontend components:** Announcement list, simplified summary, source link.
- **User actions:** Open, filter.
- **States:** Standard.
- **Personalization:** Followed instruments.
- **Analytics events:** `announcement_view`.
- **Future:** Auto-link to affected indicators.
- **Mode:** **A** — simplify; **do not exaggerate impact**.

## 14. Watchlist

- **Purpose:** Save and track instruments; filter-based discovery.
- **Input data:** User watchlist items; per-item EOD indicators.
- **Backend dependency:** Watchlist store; per-item indicator hydration. See [Database](11-database-architecture.md).
- **Frontend components:** Watchlist table, add/remove, multiple lists, "suggested (filter-based) watchlist."
- **User actions:** Create/rename/delete list; add/remove items; create alerts.
- **States:** *Empty* — "Add your first instrument." *Loading* — skeleton. *Error* — load failed. *Success* — hydrated lists.
- **Personalization:** Followed sectors in suggestions (filter-based, not per-user buy-leans).
- **Analytics events:** `watchlist_create`, `watchlist_add`, `watchlist_remove`.
- **Future:** Shared watchlists.
- **Mode:** **A** — "AI suggested watchlist" must be **filter-based discovery**, not per-user buy-leans.

## 15. Portfolio tracker

- **Purpose:** Track holdings and their technical/risk state with **factual** notes.
- **Input data:** User holdings (symbol, qty); per-holding indicators + risk; portfolio aggregates.
- **Backend dependency:** Portfolio store; risk engine; portfolio AI summary under guardrails. See [Portfolio & risk](16-portfolio-and-risk-engine.md).
- **Frontend components:** Holdings table, portfolio risk panel, factual holdings notes, portfolio AI summary.
- **User actions:** Add/edit holdings; review risk; subscribe to alerts.
- **States:** *Empty* — "Add holdings." *Loading* — skeleton. *Error* — load failed. *Success* — holdings + risk.
- **Personalization:** Layout only.
- **Analytics events:** `portfolio_create`, `portfolio_add_holding`, `portfolio_risk_view`.
- **Future:** Broker import (V8).
- **Mode:** **A** — "X broke its 50-DMA" is factual; **never** "sell X".

## 16. Risk engine

- **Purpose:** Defensible, differentiating risk scoring at instrument and portfolio level.
- **Input data:** Volatility, drawdown, ATR, concentration, liquidity, beta.
- **Backend dependency:** Risk model; traceable risk-flag generation. See [Portfolio & risk](16-portfolio-and-risk-engine.md).
- **Frontend components:** Risk score badge, risk factor breakdown, elevated-risk caveats.
- **User actions:** Inspect risk factors.
- **States:** *Empty/Suppressed* — insufficient history. *Success* — score + factor breakdown.
- **Personalization:** None on scoring.
- **Analytics events:** `risk_view`, `risk_factor_expand`.
- **Future:** Scenario stress tests.
- **Mode:** **A** — risk scoring is defensible and differentiating.

## 17. Alerting

- **Purpose:** Notify users of **events** (scanner entry/exit, MA cross) — never prescriptive.
- **Input data:** Scanner memberships, indicator crossings, news events; EOD batch.
- **Backend dependency:** Alert rule store; EOD-batch evaluation; delivery (in-app/email). See [Alerts](17-alerts-and-notifications.md).
- **Frontend components:** Alert builder, alert list, delivery settings.
- **User actions:** Create/edit/delete alerts; choose channels.
- **States:** *Empty* — "No alerts yet." *Loading* — skeleton. *Error* — delivery failure flagged. *Success* — active alerts + history.
- **Personalization:** Followed instruments.
- **Analytics events:** `alert_create`, `alert_triggered`, `alert_delivered`.
- **Future:** Real-time alerts (V7, live tier).
- **Mode:** **A** — **event-reporting only** ("entered the scanner"); never "buy at open." EOD-batch in v1.

## 18. AI daily market brief

- **Purpose:** Morning brief reporting events and what to **monitor** — never a ranked "what to buy."
- **Input data:** Overnight EOD pipeline outputs; scanner entries/exits; sector shifts; notable events.
- **Backend dependency:** Brief generation agent under guardrails + grounding; overnight latency budget; audit log.
- **Frontend components:** Brief card/page; sections (breadth, scanner movers, sectors, events); "not investment advice".
- **User actions:** Read; drill into referenced items.
- **States:** *Empty* — not yet generated. *Loading* — skeleton. *Error* — generation failed → fallback non-AI digest. *Success* — verified brief.
- **Personalization:** Followed sectors emphasized.
- **Analytics events:** `brief_view`, `brief_item_click`.
- **Future:** Personalized (navigation) emphasis.
- **Mode:** **A** — reports events + what to monitor; **never** a ranked "what to buy."

## 19. Peer comparison

- **Purpose:** Compare an instrument against peers — comparative, not directive.
- **Input data:** Peer mappings; comparable indicators/valuation bands.
- **Backend dependency:** Peer mapping; comparison computation.
- **Frontend components:** Peer table/matrix; comparative metrics; sortable columns; per-metric as-of + confidence badge.
- **User actions:** Select/deselect peers; choose comparison metrics; sort; open a peer's stock detail; add a peer to watchlist.
- **States:** *Empty* — no peers mapped: "No peers mapped for this instrument." *Loading* — matrix skeleton. *Error* — "Comparison data unavailable for this date"; affected metrics suppressed (**not guessed**). *Success* — comparison matrix with as-of + confidence.
- **Personalization:** None on content/ranking (navigation only — followed peers may surface first in selection).
- **Analytics events:** `peer_compare_view`, `peer_select`, `peer_metric_change`, `peer_result_click`.
- **Future:** Custom peer sets; valuation-band overlays (Phase 3).
- **Mode:** **A** — **comparative, not directive**; no "X is better than Y, buy X" framing; differences stated descriptively.

## 20. Strategy / scanner builder

- **Purpose:** No-code rule builder; outputs are **lists**, not calls.
- **Input data:** Indicator/scanner primitives; user-composed rules.
- **Backend dependency:** Rule engine; saved-scanner store; preview execution. See [Strategy builder](19-backtesting-and-strategy-builder.md).
- **Frontend components:** Rule canvas, condition pickers, preview list, save.
- **User actions:** Compose rules; preview; save; run.
- **States:** *Empty* — blank canvas. *Loading* — preview running. *Error* — invalid rule. *Success* — matching list saved.
- **Personalization:** Saved scanners per user.
- **Analytics events:** `builder_open`, `builder_save`, `builder_run`.
- **Future:** Rule templates; ML-ranked outputs (V5).
- **Mode:** **A** — outputs are **lists, not calls**.

## 21. Backtesting

- **Purpose:** Test strategy/scanner logic on history with integrity controls.
- **Input data:** Deep adjusted history **incl. delisted/merged**; point-in-time index membership.
- **Backend dependency:** Backtest engine with **survivorship + look-ahead + point-in-time** controls; realistic fills (slippage + liquidity caps). See [Backtesting](19-backtesting-and-strategy-builder.md).
- **Frontend components:** Config panel, run, results with exposed assumptions + "past performance does not indicate future results".
- **User actions:** Configure window/universe; run; review.
- **States:** *Empty* — no run yet. *Loading* — running. *Error* — config invalid / data gap. *Success* — results + assumptions.
- **Personalization:** Saved backtests.
- **Analytics events:** `backtest_run`, `backtest_view`.
- **Future:** Walk-forward analysis.
- **Mode:** **A** — ships **only** with integrity controls; an inflated backtest is an implied-performance claim.

## 22. Admin panel

- **Purpose:** Governance: blocked-phrase list, prompt versions, source reliability, AI audit logs.
- **Input data:** Versioned guardrail lists; prompts; source-reliability config; AI generation audit records.
- **Backend dependency:** Admin services; audit-log store; guardrail/prompt versioning. See [Admin panel](20-admin-panel.md).
- **Frontend components:** Blocked-phrase editor, prompt manager, source-reliability table, audit-log viewer.
- **User actions:** Edit lists/prompts; review audits; manage sources.
- **States:** Standard admin states; change history retained.
- **Personalization:** Role-based.
- **Analytics events:** `admin_phrase_edit`, `admin_prompt_publish`, `admin_audit_view`.
- **Future:** Automated regression gating on prompt change.
- **Mode:** **N/A** — infrastructure; compliance-review agent required.

## 23. Pricing / subscription

- **Purpose:** Freemium tiers (Free / Premium / Pro / Enterprise-API) with value framing.
- **Input data:** Tier definitions; entitlements; usage limits.
- **Backend dependency:** Billing; entitlement enforcement; usage metering (incl. AI-spend per user). See [SPEC.md §11](../SPEC.md).
- **Frontend components:** Pricing page, upgrade prompts, billing portal.
- **User actions:** Upgrade/downgrade; manage billing.
- **States:** Standard.
- **Personalization:** Tier-based entitlements.
- **Analytics events:** `pricing_view`, `upgrade_prompt_view`, `subscription_start`.
- **Future:** RA fee-cap-aware tiers if Mode B.
- **Mode:** **A / N/A** — value framing only; no return promises; SEBI fee cap (~₹1.51L/yr/family) applies under RA.

## 24. User profile

- **Purpose:** Account settings, risk preference, followed sectors, notification channels, consent.
- **Input data:** User account; preferences; consent records (terms, AI-use notice).
- **Backend dependency:** Auth; preferences store; consent records. See [Security & auth](23-security-auth-and-privacy.md).
- **Frontend components:** Profile form, preference toggles, consent/legal section.
- **User actions:** Edit preferences; manage channels; review consents.
- **States:** Standard.
- **Personalization:** Drives navigation personalization (transparent, user-editable).
- **Analytics events:** `profile_update`, `preference_change`.
- **Future:** Data export / deletion (privacy).
- **Mode:** **A / N/A** — preferences personalize **navigation**, never recommendations.

## 25. Notification center

- **Purpose:** Central inbox for alerts, briefs, and system messages.
- **Input data:** Triggered alerts; briefs; system notices.
- **Backend dependency:** Notification store; delivery fan-out. See [Alerts](17-alerts-and-notifications.md).
- **Frontend components:** Inbox list, read/unread state, filters (alerts / briefs / system), per-channel delivery settings, bulk mark-read.
- **User actions:** Read; mark read/unread; filter by type; manage channels (in-app/email); drill into the referenced item.
- **States:** *Empty* — "No notifications." *Loading* — inbox skeleton. *Error* — "Notifications unavailable" / flagged delivery failure. *Success* — inbox with read/unread + sources.
- **Personalization:** Followed-instrument/sector relevance ordering (navigation-only).
- **Analytics events:** `notification_view`, `notification_read`, `notification_filter`, `notification_channel_change`.
- **Future:** Push (mobile); digest grouping.
- **Mode:** **A** — notification content remains **event-reporting** ("entered the scanner"); never prescriptive ("buy now").

## 26. AI assistant

- **Purpose:** Conversational interface that answers **only** from structured payloads.
- **Input data:** Structured payloads (metrics, scanner tags, news summaries, risk markers).
- **Backend dependency:** LLM + payload contract; **runtime validator**; guardrails; audit log. See [AI architecture](14-ai-llm-agent-architecture.md).
- **Frontend components:** Chat UI; grounded answers with sources/as-of; "not investment advice".
- **User actions:** Ask about stock/sector/scanner result.
- **States:** *Suppressed* — out-of-scope or missing data: declines / asks for valid context. *Loading* — streaming. *Error* — verification fail → regenerate/decline. *Success* — grounded answer.
- **Personalization:** None on content.
- **Analytics events:** `assistant_query`, `assistant_verify_fail`, `assistant_decline`.
- **Future:** Agentic multi-step research (V6).
- **Mode:** **A** — answers only from payload; **no** targets/recommendations; never invents.

## 27. Screener library

- **Purpose:** Library of **prebuilt, named filters** (e.g., "Near 52-week high on rising volume", "Above 200-DMA in strong sectors", "Oversold in uptrend") that run as one-click curated scans — the discovery on-ramp before users build their own.
- **Input data:** Curated screen definitions (composed of the same indicator/scanner primitives); adjusted OHLCV + indicators + scanner memberships + risk flags for the result universe.
- **Backend dependency:** Reuses the rule/scanner engine to execute saved screen definitions; screen-definition catalog (versioned); preview/run execution. See [Scanner engine](13-scanner-engine-and-scoring.md), [Strategy builder](19-backtesting-and-strategy-builder.md).
- **Frontend components:** Screen catalog (cards grouped by intent), result table (score, reasons, risk flags), "open in builder" link to the strategy / scanner builder (§20) for customization.
- **User actions:** Browse screens; run a screen; open results; add to watchlist; create alert; **fork a prebuilt screen into the strategy builder** to customize.
- **States:** *Empty* — no matches today: "No instruments match this screen today." *Loading* — catalog/result skeleton. *Error* — "Screen unavailable for this date." *Success* — named screen + ranked list with reasons.
- **Personalization:** Followed sectors prioritized in results; screens relevant to stated risk preference surfaced first (navigation-only).
- **Analytics events:** `screener_library_view`, `screen_run{screen_id}`, `screen_result_click`, `screen_to_builder`, `screen_to_watchlist`.
- **Future:** User-saved screens promoted into a personal library; shared/community screens.
- **Mode:** **A** — outputs are **lists, not calls**; screen names are descriptive, never "buy" intents.

## 28. Institutional activity

- **Purpose:** Surface institutional footprints — **FII/DII** net activity, **bulk & block deals** — as factual context, never as a follow-the-money call.
- **Input data:** Exchange-published FII/DII provisional + final figures; bulk-deal and block-deal disclosures (symbol, qty, price, client, buy/sell); as-of date; data-availability flag. **Data-availability dependent** — coverage and timeliness vary by source.
- **Backend dependency:** Ingestion of FII/DII and bulk/block-deal feeds; symbol resolution; aggregation to instrument/sector; availability + confidence stamping. See [Data ingestion](12-data-ingestion-and-market-data.md), [News & sentiment](18-news-sentiment-and-corporate-actions.md).
- **Frontend components:** FII/DII net flow widget; bulk/block-deal table (date, symbol, client, qty, price, side); per-stock institutional-activity strip on the stock detail page.
- **User actions:** Filter by date/instrument/sector; open instrument; add to watchlist; create alert on bulk/block-deal events.
- **States:** *Empty* — "No disclosed institutional activity for this date/instrument." *Loading* — table/widget skeleton. *Error / Unavailable* — source not available for the date → show last as-of + reduced-confidence flag (**not guessed**). *Success* — disclosed activity with source + timestamp.
- **Personalization:** Followed instruments/sectors prioritized (navigation-only).
- **Analytics events:** `institutional_activity_view`, `bulk_deal_view`, `fii_dii_view`, `institutional_alert_create`.
- **Future:** Promoter pledge/shareholding-change linkage; deal-correlation with volume scanners (data-dependent).
- **Mode:** **A** — factual disclosure reporting only; **never** "FIIs are buying, so buy X." **Phase 4 premium**, gated on data availability and redistribution rights (see [decision log](30-decision-log.md)).

## 29. Personalization

- **Purpose:** Tailor **what is surfaced and where**, transparently and user-editably, without crossing into advice. Defined explicitly across two tiers so the A/C line does not creep across releases ([SPEC §7](../SPEC.md), [09 §user-profile](09-backend-architecture.md)).
- **Input data:** User preferences (followed sectors/instruments, stated risk preference, layout choices); educational-content taxonomy; **no per-stock behavioural history is used to derive suggestions in Mode A.**
- **Backend dependency:** Preferences store (navigation personalization only); content-relevance mapping. **Per-stock behavioural personalization is NOT built** until IA (Mode C) registration is in force. See [User profile](#24-user-profile), [Backend §user-profile](09-backend-architecture.md).
- **Frontend components:** Layout/section ordering; followed-sector prioritization across dashboards/scanners/brief; default scanner-filter prefill from risk preference; prioritized educational content rail.
- **User actions:** Set/edit followed sectors & instruments; set risk preference; reorder layout; all preferences transparent and reversible.
- **States:** *Empty* — no preferences set: neutral default layout. *Loading* — preference hydration skeleton. *Error* — preferences load failed → fall back to neutral defaults. *Success* — personalized navigation applied.
- **Personalization rules (the explicit A/C line):**
  - **(a) Mode A — navigation/layout personalization (buildable now):** personalize layout; prioritize followed sectors/instruments; default scanner filters to the **stated** risk preference; prioritize relevant educational content. This personalizes **navigation, not recommendations**.
  - **(b) Mode C — advisory personalization (IA-GATED, not built in Mode A):** per-stock **behavioural** nudges derived from what a user views (e.g., "because you view banking, consider HDFC Bank") are **Investment-Adviser (Mode C)** territory and are **gated behind IA registration** — designed but **not shipped** until then.
- **Analytics events:** `preference_change`, `followed_sector_change`, `layout_reorder`, `personalized_rail_view`.
- **Future:** Mode-C advisory personalization **only after IA registration**; richer educational-path personalization (still navigation-only) in Mode A.
- **Mode:** **A** for the navigation tier; the behavioural/advisory tier is **C (IA-gated)** and absent from the Mode-A build (flag-only). See [decision log](30-decision-log.md).

---

## 30. Related documents

- [01 — Product overview](01-product-overview.md)
- [02 — Product roadmap](02-product-roadmap.md)
- [03 — User personas and journeys](03-user-personas-and-journeys.md)
- [10 — API contracts](10-api-contracts.md)
- [13 — Scanner engine and scoring](13-scanner-engine-and-scoring.md)
- [14 — AI/LLM agent architecture](14-ai-llm-agent-architecture.md)
- [16 — Portfolio and risk engine](16-portfolio-and-risk-engine.md)
- [17 — Alerts and notifications](17-alerts-and-notifications.md)
- [18 — News sentiment and corporate actions](18-news-sentiment-and-corporate-actions.md)
- [19 — Backtesting and strategy builder](19-backtesting-and-strategy-builder.md)
- [21 — Compliance, risk and guardrails](21-compliance-risk-and-guardrails.md)
