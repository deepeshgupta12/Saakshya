# 08 — Screen-by-Screen Documentation

> One-line purpose: Implementation-ready spec for every important Saakshya screen — layout, sections, components, states, behaviors, animations, and analytics.
> Read first: [SPEC.md](../SPEC.md)

Related: [IA & URL Paths](05-information-architecture-and-url-paths.md) · [Frontend Architecture](06-frontend-architecture.md) · [Design System](07-design-system-and-ui-ux.md) · [API Contracts](10-api-contracts.md) · [Compliance & Guardrails](21-compliance-risk-and-guardrails.md) · [Analytics & SEO](24-analytics-seo-and-growth.md)

---

## 0. Conventions

Every screen below specifies: **Purpose · Route & access · Layout · Sections/components · User actions & CTAs · Data shown · Empty / error / loading states · Mobile vs desktop · Animation · Analytics events · Backend / Frontend / Data dependency · Acceptance criteria.** Components cross-link to [07](07-design-system-and-ui-ux.md); data to [10](10-api-contracts.md); routes to [05](05-information-architecture-and-url-paths.md).

**Global compliance overlay (applies to every screen):** descriptive language only (SPEC §3, §5); `NotAdviceBanner` on all data/AI surfaces; AI text carries a grounding badge + "View evidence"; **no** entry/target/SL or buy/sell wording (RA-gated, rendered as `RaGatedPlaceholder` where a slot exists); blocked phrases impossible by build-time lint (SPEC §6.9).

---

## 1. Landing page — `/` (public, indexed)

- **Purpose:** Communicate "best Indian-equity screener + best explanations, evidence-first" and convert to signup. Never "what to buy".
- **Layout:** Single-column scroll, glass top-nav, full-bleed hero, alternating feature bands, pricing teaser, footer.
- **Sections/components:** `LandingHero` (headline, subhead, dual CTA "Start free" / "See a live scanner"), `MarketTeaser` (delayed index strip + breadth, descriptive), `ScannerPreviewCard` (sample momentum results, score + reasons, blurred-beyond-N for anon), `EvidenceStoryBlock` (badge→evidence-drawer demo), `AiExplainerDemo` (sample grounded summary + not-advice), `PricingTeaser`, `Footer` with legal links.
- **CTAs:** Start free → `/signup`; See scanner → `/scanners/momentum`; View pricing → `/pricing`.
- **Data shown:** Cached EOD market snapshot + sample scanner rows (`?preview=1`).
- **Empty/error:** If snapshot unavailable, hero renders without the live strip (graceful) — never blocks the page. Error: static fallback content.
- **Loading:** SSG shell instant; teaser data ISR-cached, skeleton strip if revalidating.
- **Mobile:** Stacked, single CTA prominent, teaser as horizontal scroll.
- **Desktop:** Two-column feature bands; subtle parallax-free reveal on scroll.
- **Animation:** Section fade/slide on scroll-in (`--motion-base`); chart line-reveal once in the demo; reduce-motion disables.
- **Analytics:** `landing_view`, `cta_signup_click`, `cta_scanner_click`, `pricing_teaser_click`, `evidence_demo_open`.
- **Backend dep:** `GET /market/summary`, `GET /scanners/momentum?preview=1`. **Frontend dep:** `(marketing)` group, SSG+ISR ([06 §7](06-frontend-architecture.md)). **Data dep:** EOD snapshot cache.
- **Acceptance:** Loads with no advisory language; LCP < 2.5s; live strip degrades gracefully; all CTAs route correctly.

---

## 2. Market dashboard — `/market` (public, indexed)

- **Purpose:** EOD market state: indices, breadth, sector heat, descriptive AI market summary, movers.
- **Layout:** Header (date + as-of); index strip; two-column grid (breadth + AI summary), sector heatmap full-width, movers tables tabbed.
- **Sections/components:** `IndexStrip`, `BreadthPanel` (advance/decline, % above 50/200-DMA), `SectorHeatmap`, `AiMarketSummaryCard` (descriptive, grounded), `MarketMoversTable` (gainers/losers/most-active/most-delivery — descriptive, no "top picks"), `DataConfidenceIndicator`.
- **User actions/CTAs:** Click index/sector/stock → detail; toggle mover tabs; "View evidence" on AI card; change as-of date (historical view).
- **Data shown:** Index levels/%chg, breadth ratios, sector momentum, movers, AI summary text + grounding ref.
- **Empty:** Pre-market/no session: "Latest EOD data: <date>" with last published set. **Error:** inline error card + retry; AI card suppressed if inputs missing (SPEC §6.2). **Loading:** skeletons matching grid.
- **Mobile:** Index strip horizontal scroll; heatmap compact grid; tables → stacked cards.
- **Desktop:** Multi-pane; heatmap interactive tooltips.
- **Animation:** Heatmap tile fade+scale stagger; AI summary reveal; count-ups on breadth (once).
- **Analytics:** `market_view`, `sector_tile_click`, `mover_tab_change`, `market_ai_evidence_open`, `as_of_change`.
- **Backend dep:** `GET /market/summary`, `/market/breadth`, `/sectors`, `/market/ai-summary`. **Frontend dep:** `(market)`, ISR post-EOD. **Data dep:** EOD batch + confidence flags.
- **Acceptance:** All figures trace to payload; AI summary is descriptive + grounded or suppressed; confidence indicator reflects backend; as-of reproduces historical values.

---

## 3. Scanner listing (directory) — `/scanners` (public, indexed)

- **Purpose:** Browse all scanners with freshness and result counts.
- **Layout:** Grid of `ScannerCard`s (momentum, volume-breakout, rsi, moving-average, breakout, breakdown), each with last-run time, result count, one-line "what it measures".
- **CTAs:** Open scanner; "what is this scanner?" → learn link.
- **Data shown:** Scanner catalog metadata + counts.
- **Empty/error/loading:** Catalog rarely empty; error → retry; loading → card skeletons.
- **Mobile/desktop:** Responsive grid (1→2→3 cols).
- **Animation:** Card stagger fade-in.
- **Analytics:** `scanner_directory_view`, `scanner_card_open`.
- **Backend dep:** `GET /scanners`. **Frontend dep:** ISR. **Data dep:** scanner catalog + last-run.
- **Acceptance:** Each card states what it measures (descriptive), never "best buys".

---

## 4. Scanner detail — `/scanners/momentum` · `/volume-breakout` · `/rsi` · `/[scanner-slug]` (public, indexed)

- **Purpose:** Ranked scanner results with **score + reasons + risk flags**. Language: "appears in the X scanner".
- **Canonical scanner list (all render via this shared scanner-detail template — steps 02, 16):** `momentum`, `volume-breakout`, `rsi`, `moving-average`, `breakout`, `breakdown`, `sector-strength`, `near-52-week-high`, `200-dma-reclaim`, `oversold-recovery`. Each is a first-class route (`/scanners/<slug>`, see [05 §2](05-information-architecture-and-url-paths.md)); the `[scanner-slug]` resolver maps these slugs to this same screen. Unknown slug → 404. Each scanner states **what it measures** (descriptive) and its validation note; false-breakout/breakdown surface as **risk flags**, never "buy/sell the move".
- **Layout:** Header (scanner name, what it measures, last-run, validation note), filter rail/sheet, results table, optional quick-look drawer.
- **Sections/components:** `ScannerHeader`, `ScannerFilters` (sector, index, score band, risk-flag presence — **no "buy" preset**), `ScannerResultsTable` rows = symbol, last price/%chg, `ScoreBadge`, `ReasonChips`, `RiskFlagChip`, sub-score sparkline; `EvidenceDrawer` per row; pagination/virtualization.
- **User actions/CTAs:** Sort, filter, open evidence, add-to-watchlist (auth), set alert (auth, "entered scanner"), open stock detail.
- **Data shown:** Score (0–100, validated SPEC §6.5), sub-scores, reasons, risk flags, price/%chg, as-of.
- **Empty:** "No stocks match the current filters" + reset. **Error:** retry card. **Loading:** row skeletons + sticky header.
- **Mobile:** Filters in bottom sheet; rows show symbol+score+top reason, expand for detail; evidence as bottom sheet.
- **Desktop:** Full table + side filter rail + right evidence drawer.
- **Animation:** Row stagger; newly-entered rows one-time accent flash; score count-up once; drawer slide-in.
- **Analytics:** `scanner_view{slug}`, `scanner_filter_apply`, `scanner_sort`, `scanner_row_evidence_open`, `watchlist_add{from:scanner}`, `alert_create{from:scanner}`.
- **Backend dep:** `GET /scanners/{slug}` (+ filters), `POST /me/watchlist/items`, `POST /alerts`. **Frontend dep:** ISR list + client controls. **Data dep:** validated scores, reasons, risk flags, as-of.
- **Acceptance:** Membership phrasing only ("appears in…"); no buy-lean/target language; every score/reason traceable in evidence drawer; false-breakout shows as **risk flag**, never "buy the breakout".

---

## 5. Stock detail — `/stocks/[symbol]` (public, indexed)

- **Purpose:** Full evidence dossier for one stock — facts, chart, indicators, scanner memberships, descriptive S/R, risk, news, AI summary, corp actions. **No entry/target/SL** (RA-gated → `RaGatedPlaceholder`).
- **Layout:** Sticky `StockHeader` (name, symbol, price, %chg, sector, risk badge); main = `PriceChart` + tabbed panels; right rail = AI summary + scanner memberships + key stats.
- **Sections/components:** `StockHeader`, `PriceChart` (candles, volume, MAs, descriptive S/R lines), `IndicatorPanel` (RSI, MACD, ATR, BBands, volume ratio — values + state), `ScannerMembershipChips`, `RiskBadge`+`RiskPanel`, `AiStockSummaryCard`+`EvidenceDrawer`, `NewsList`+sentiment, `CorporateActionsTable`, `KeyStats`, **`PeersSection`** (comparative — see §5a), **`FundamentalsPanel`** (descriptive valuation bands + earnings summary — see §5b), **`InstitutionalActivityPanel`** (FII/DII, bulk/block — premium/Phase-4 — see §5c), **`AnnouncementsSection`** (summarized, source-linked — see §5d), **`RaGatedPlaceholder`** where levels would be (Phase 5). Panels surface as in-page tabs (`?tab=peers|fundamentals|institutional|announcements`); `Peers` and `Announcements` also have standalone routes (§5a, §5d).
- **User actions/CTAs:** Add to watchlist, set alert (event-based), open evidence, switch chart timeframe/indicators, expand news, ask AI about this stock → `/ai` prefilled.
- **Data shown:** OHLC series (adjusted, SPEC §6.1), indicators, scanner tags, descriptive support/resistance, risk score+drivers, news+sentiment+sources, corp actions, key stats. **AI summary descriptive, grounded, runtime-verified (SPEC §6.6).**
- **Empty:** Thin-data/illiquid symbol → "Limited data available" + confidence note. **Error:** per-panel error, page still renders header. **Loading:** header instant (SSR), chart skeleton, panel skeletons.
- **Mobile:** Header condenses on scroll; chart full-width; panels as accordion; right-rail content below chart; evidence as bottom sheet.
- **Desktop:** 3-zone layout; persistent right rail.
- **Animation:** Chart line-reveal once; risk-pulse if a new risk flag; score count-up; AI reveal; drawer slide-in.
- **Analytics:** `stock_view{symbol}`, `chart_timeframe_change`, `indicator_toggle`, `stock_ai_evidence_open`, `watchlist_add{from:stock}`, `alert_create{from:stock}`, `ask_ai_from_stock`.
- **Backend dep:** `GET /stocks/{symbol}/overview · /indicators · /scanners · /ai-summary · /news · /corporate-actions · /risk`. **Frontend dep:** ISR per symbol + client chart/panels. **Data dep:** corp-action-adjusted series, validated scores, grounded AI, confidence flags.
- **Acceptance:** No entry/target/SL anywhere (placeholder only); S/R framed historically ("historically a resistance zone"); every AI number traces to evidence or the card is suppressed; adjusted series used so indicators are correct across splits/bonuses.

---

## 5a. Peers section / page — `/stocks/[symbol]` (Peers tab) · `/stocks/[symbol]/peers` (public, indexed)

- **Purpose:** **Comparative** view of like companies for one symbol (step 18 — [steps/18](steps/18-peer-comparison.md)). **COMPARATIVE not directive:** helps the user see how a stock sits among peers; **never** "switch to", "better pick", "buy the cheaper peer", or an actionable ranking.
- **Route & access:** in-page section on `/stocks/[symbol]` and standalone `/stocks/[symbol]/peers`; public, indexed.
- **Layout:** `PeerComparisonHeader` (subject symbol pinned, peer-set basis disclosed — e.g. "same sector, similar market-cap band"), `PeerComparisonTable` (subject row highlighted, peer rows below), `NotAdviceBanner`.
- **Sections/components:** `PeerComparisonTable` columns = symbol, market-cap band, price/%chg, momentum score + state, RSI band, volume ratio, risk flag, descriptive valuation band; `PeerMetricColumns` (toggle which descriptive metrics show); `EvidenceDrawer` per cell/row.
- **User actions/CTAs:** Sort by a column (descriptive ordering only — clearly not a buy-rank), add a peer to watchlist (auth), open a peer's stock detail, open evidence. **No "compare to act"/switch CTA.**
- **Data shown:** Per-symbol descriptive metrics for subject + peers, peer-set derivation note, as-of.
- **Empty:** "Not enough comparable peers" (thin sector / unique name) + the subject's own row. **Suppressed:** a metric column is suppressed if its inputs fail confidence (SPEC §6.2), not faked. **Error:** per-table retry; header still renders. **Loading:** row skeletons.
- **Mobile:** subject pinned at top; peers as horizontally scrollable comparison cards; evidence as bottom sheet.
- **Desktop:** full comparison table with sticky subject row + column headers.
- **Animation:** row stagger on load; subject-row highlight (no value-changing motion); `prefers-reduced-motion` disables.
- **Analytics:** `peers_view{symbol}`, `peers_sort{metric}`, `peers_metric_toggle`, `peer_open{symbol}`, `peers_evidence_open`, `watchlist_add{from:peers}`.
- **Backend dep:** `GET /stocks/{symbol}/peers`, `GET /stocks/{symbol}/overview`, `POST /me/watchlist/items`. **Frontend dep:** ISR per symbol + client table controls ([05 §2](05-information-architecture-and-url-paths.md)). **Data dep:** sector/size-derived peer set, descriptive metrics, confidence flags.
- **Acceptance:** Comparative framing only; no buy/switch/ranking-to-act CTA or copy; peer-set basis disclosed; every metric traces to evidence or is suppressed.

---

## 5b. Fundamentals / valuation panel — `/stocks/[symbol]` (Fundamentals tab) (public, indexed)

- **Purpose:** **Descriptive** fundamentals + **valuation bands** and an **earnings summary** for one symbol (step 21 — [steps/21](steps/21-fundamentals-valuation.md)). Valuation is presented as **bands/ranges with historical/peer context** ("trades in the upper end of its 5-yr P/E band"), **never** "cheap → buy" / "expensive → sell" / fair-value target.
- **Route & access:** in-page panel/tab on `/stocks/[symbol]` (`?tab=fundamentals`); public, indexed; no separate route (route note in [05 §2](05-information-architecture-and-url-paths.md)).
- **Layout:** `FundamentalsPanel` → `ValuationBands` (P/E, P/B, EV/EBITDA, dividend yield shown as current value vs historical band and vs peer-median band), `EarningsSummary` (revenue/EPS trend, latest-result descriptive recap, surprise vs estimate as a fact), `KeyRatios` (descriptive), `NotAdviceBanner`.
- **Sections/components:** `ValuationBands` (band bars with current marker), `EarningsSummary` (per-period table + plain-language descriptive summary), `EvidenceDrawer` (source + as-of per figure).
- **User actions/CTAs:** Toggle band metric, expand a period, open evidence/source filing. **No "valuation says buy/sell" CTA.**
- **Data shown:** Valuation ratios + their historical and peer bands, earnings trend, latest-result recap, as-of.
- **Empty:** "Fundamentals not available for this symbol" (e.g. recently listed) + confidence note. **Suppressed:** band hidden if data confidence insufficient (SPEC §6.2). **Error:** per-panel retry. **Loading:** band/table skeletons.
- **Mobile:** bands stacked; earnings table → period cards.
- **Desktop:** bands + earnings side-by-side within the panel.
- **Animation:** band marker settle once; count-ups on ratios once; reduce-motion disables.
- **Analytics:** `fundamentals_view{symbol}`, `valuation_band_toggle`, `earnings_period_expand`, `fundamentals_evidence_open`.
- **Backend dep:** `GET /stocks/{symbol}/fundamentals`. **Frontend dep:** ISR per symbol. **Data dep:** point-in-time fundamentals, historical + peer bands, confidence flags.
- **Acceptance:** Valuation framed as descriptive bands/ranges with context, never as cheap/expensive-to-act or a fair-value target; earnings recap factual and source-linked; figures trace to evidence or are suppressed.

---

## 5c. Institutional activity panel — `/stocks/[symbol]` (Institutional tab) (public shell, premium/Phase-4)

- **Purpose:** **Factual** institutional-activity surface (step 22 — [steps/22](steps/22-institutional-activity.md)): FII/DII holding/flow trend, bulk deals, block deals for one symbol. **Premium / Phase-4 surface, data-availability dependent.** Strictly factual: "FIIs reduced their stake by X% this quarter", **never** "institutions are selling — exit".
- **Route & access:** in-page panel/tab on `/stocks/[symbol]` (`?tab=institutional`); public route shell, **premium tier gate** inside, Phase-4 availability ([05 §2](05-information-architecture-and-url-paths.md)).
- **Layout:** `InstitutionalActivityPanel` → `OwnershipTrend` (FII/DII % over time), `BulkDealsTable`, `BlockDealsTable`, `NotAdviceBanner`, upgrade gate for non-premium.
- **Sections/components:** `OwnershipTrend` chart, `BulkDealsTable` / `BlockDealsTable` (date, party, qty, price — as disclosed), `EvidenceDrawer` (exchange disclosure source + as-of).
- **User actions/CTAs:** Toggle FII/DII series, open a deal's source disclosure, change as-of/period. **No "follow the institutions" / act CTA.**
- **Data shown:** FII/DII ownership %, quarter-on-quarter change (factual), bulk/block deal records, as-of.
- **Empty:** "No bulk/block deals disclosed for this period" / "Institutional holding data not available for this symbol". **Suppressed:** panel renders an availability note where the data source is absent (data-availability dependent) rather than fabricating. **Gated:** non-premium → `RaGatedPlaceholder`-style upgrade gate (tier, not RA). **Error:** per-panel retry. **Loading:** skeletons.
- **Mobile:** trend chart full-width; deal tables → cards.
- **Desktop:** trend + deal tables stacked within panel.
- **Animation:** trend line-reveal once; reduce-motion disables.
- **Analytics:** `institutional_view{symbol}`, `institutional_series_toggle`, `institutional_deal_source_open`, `institutional_upgrade_gate_view`.
- **Backend dep:** `GET /stocks/{symbol}/institutional`. **Frontend dep:** premium gate; ISR/short-window where data exists. **Data dep:** exchange-disclosed FII/DII + bulk/block records, availability flag, as-of.
- **Acceptance:** Strictly factual disclosure framing, no directive copy; premium-gated + Phase-4; absent data shown as an availability note, never fabricated; deals source-linked to the exchange disclosure.

---

## 5d. Corporate announcements section / page — `/stocks/[symbol]` (Announcements tab) · `/stocks/[symbol]/announcements` (public, indexed)

- **Purpose:** Surface and **simplify** corporate filings/announcements for one symbol (step 17 — [steps/17](steps/17-corporate-announcements.md)). **Summarized WITHOUT exaggeration**, source-linked, timestamped. No "big news — buy"/impact-hype framing.
- **Route & access:** in-page section on `/stocks/[symbol]` (`?tab=announcements`) and dedicated feed `/stocks/[symbol]/announcements`; public, indexed. Optional global feed `/announcements`.
- **Layout:** `AnnouncementsHeader` (symbol, category filter, count), `AnnouncementsFeed` (reverse-chronological), `AnnouncementCard` (category tag, headline, neutral one-line summary, timestamp, `SourceLink`), `NotAdviceBanner`.
- **Sections/components:** `AnnouncementCard`, `CategoryFilter` (results, dividends, board meetings, allotments, ratings, etc.), `SourceLink` (exchange/filing), neutral AI/template summary with grounding.
- **User actions/CTAs:** Filter by category, open source filing, open linked stock (global feed), expand full summary.
- **Data shown:** Announcement category, neutral summary, timestamp, source URL, as-of.
- **Empty:** "No announcements in this period/category". **Suppressed:** if a summary can't be grounded, show the headline + source link only, no fabricated summary (SPEC §6.6/§6.8). **Error:** per-feed retry. **Loading:** card skeletons.
- **Mobile:** single-column feed; category filter in sheet.
- **Desktop:** feed + sticky category rail.
- **Animation:** card fade-in on load/new; reduce-motion disables.
- **Analytics:** `announcements_view{symbol}`, `announcement_filter{category}`, `announcement_source_open`, `announcement_expand`, (global) `announcement_symbol_open`.
- **Backend dep:** `GET /stocks/{symbol}/announcements` (and `GET /announcements` for the global feed). **Frontend dep:** ISR/short-window ([05 §2](05-information-architecture-and-url-paths.md)). **Data dep:** filing feed, entity resolution, grounded neutral summaries, source links.
- **Acceptance:** Summaries are neutral and **not exaggerated**; every item is source-linked and timestamped; ungroundable summaries degrade to headline+source; no buy/sell/impact-hype language.

---

## 6. Sector page — `/sectors/[sector-slug]` (public, indexed)

- **Purpose:** One sector's strength, constituents, breadth, leaders/laggards (descriptive).
- **Layout:** `SectorHeader` (name, index level/%chg, momentum rank), `SectorIndexChart`, `ConstituentTable`, `SectorBreadthPanel`.
- **CTAs:** Open constituent stock; add sector to followed (auth); filter constituents.
- **Data shown:** Sector index series, momentum score, breadth, constituent metrics.
- **Empty/error/loading:** thin sector note; per-panel error; skeletons.
- **Mobile/desktop:** chart-first mobile, two-pane desktop.
- **Animation:** chart reveal, table stagger.
- **Analytics:** `sector_view{slug}`, `sector_follow_toggle`, `constituent_open`.
- **Backend dep:** `GET /sectors/{slug} · /constituents · /breadth`, `PATCH /me/preferences` (follow). **Frontend dep:** ISR. **Data dep:** sector EOD + breadth.
- **Acceptance:** Comparative/descriptive only; leaders/laggards never framed as buy/sell.

---

## 7. Theme basket page — `/themes/[theme-slug]` (public, indexed, Phase 3)

- **Purpose:** A **bucket view, not a model portfolio** (SPEC §4).
- **Layout:** `ThemeHeader`, prominent `ThemeDisclaimerBanner` ("This is a bucket view for research, not a recommended portfolio"), `ThemeConstituentTable`, aggregate descriptive stats.
- **CTAs:** Open constituent; add constituents to watchlist.
- **Data shown:** Theme membership, aggregate descriptive metrics.
- **Empty/error/loading:** standard.
- **Animation:** table stagger.
- **Analytics:** `theme_view{slug}`, `theme_constituent_open`, `theme_watchlist_add`.
- **Backend dep:** `GET /themes/{slug} · /constituents`. **Frontend dep:** ISR. **Data dep:** theme membership data.
- **Acceptance:** Disclaimer banner present; no weights/returns/allocation implying a portfolio recommendation.

---

## 8. Watchlist — `/watchlist` (auth)

- **Purpose:** Track symbols with descriptive metrics + scanner memberships + inline alerts.
- **Layout:** `WatchlistTabs` (multiple lists — Free 1, Premium unlimited), `WatchlistTable`, `AddSymbolDialog`.
- **CTAs:** Add/remove symbol, create list, set alert on row, open stock.
- **Data shown:** price/%chg, score, scanner tags, risk flag, last alert.
- **Empty:** "Add your first symbol" CTA + symbol search. **Error:** retry. **Loading:** skeleton rows.
- **Mobile:** stacked cards; add via bottom sheet.
- **Animation:** watchlist-add confirmation pulse + toast; row settle.
- **Analytics:** `watchlist_view`, `watchlist_add`, `watchlist_remove`, `watchlist_list_create`, `alert_create{from:watchlist}`.
- **Backend dep:** `GET/POST/DELETE /me/watchlist[/items]`. **Frontend dep:** Query + mutations, optimistic add. **Data dep:** per-symbol EOD + scores.
- **Acceptance:** Tier limits enforced with upgrade gate; "AI suggested watchlist" (if present) is filter-based discovery, never per-user buy-leans (SPEC §4).

---

## 9. Portfolio — `/portfolio` (auth, Premium+)

- **Purpose:** Holdings tracker + **factual** risk flags. Never prescriptive.
- **Layout:** `PortfolioSummaryCard` (value, day change, allocation by sector — descriptive), `PortfolioTable` (holdings), `PortfolioRiskPanel`, `AddHoldingDialog`/`ImportDialog`.
- **CTAs:** Add/import/edit holding, open holding's stock, view risk evidence. **No "sell"/"rebalance" CTA.**
- **Data shown:** qty, avg cost, current value, unrealized P/L (user's own data), risk flags ("X broke its 50-DMA"), concentration notes (descriptive).
- **Empty:** "Add or import your holdings". **Error:** retry; import errors show row-level validation. **Loading:** skeletons.
- **Mobile:** stacked holding cards; risk flags as chips.
- **Animation:** risk-pulse on new flag (one-shot); count-ups for totals once.
- **Analytics:** `portfolio_view`, `holding_add`, `portfolio_import`, `portfolio_risk_evidence_open`.
- **Backend dep:** `GET/POST /portfolio/holdings`, `GET /portfolio/risk`. **Frontend dep:** Query + mutations. **Data dep:** user holdings + EOD prices + risk engine ([16](16-portfolio-and-risk-engine.md)).
- **Acceptance:** Risk surfaced as **events/facts** ("broke 50-DMA", "elevated concentration"), never "sell X"; no target/SL; P/L is user's own data, not a return claim.

---

## 10. Alerts — `/alerts` (auth, Premium+)

- **Purpose:** Manage **event-reporting** alert rules (EOD-batch in v1). Never prescriptive.
- **Layout:** `AlertRuleList`, `AlertRuleEditor` (condition builder: "enters momentum scanner", "crosses 50-DMA", "RSI band change", "risk flag appears"), `AlertHistory`.
- **CTAs:** Create/edit/pause/delete rule; choose channel (in-app/email).
- **Data shown:** rules, last-triggered, history of events.
- **Empty:** "Create your first alert" with templates. **Error:** retry. **Loading:** skeletons.
- **Mobile:** editor as full sheet.
- **Animation:** alert-creation confirmation (button→check + "Alert set (EOD)" toast).
- **Analytics:** `alerts_view`, `alert_create`, `alert_edit`, `alert_delete`, `alert_history_view`.
- **Backend dep:** `GET/POST/PATCH/DELETE /alerts`, `GET /alerts/history`. **Frontend dep:** Query + mutations. **Data dep:** scanner/indicator event stream (EOD).
- **Acceptance:** All alert copy is event-based ("entered the scanner"), never "buy at open"; v1 alerts are EOD-batch (SPEC §4).

---

## 11. AI assistant — `/ai` (auth)

- **Purpose:** Conversationally **explain structured signals**; refuse "what should I buy". Grounded + runtime-verified (SPEC §6.6).
- **Layout:** `AiChatThread` (messages), composer with `SuggestedPrompts` ("Explain TCS's momentum signals", "What does the volume-breakout scanner show today?"), per-message `GroundingBadge` + `EvidenceCitation`.
- **CTAs:** Send, open cited evidence/stock, new thread, prefill from stock page.
- **Data shown:** AI text grounded only in computed metrics/scanner tags/news/risk markers; citations; not-advice banner.
- **Empty:** Welcome + suggested prompts + capability/limits note ("I explain signals; I don't give buy/sell advice"). **Error:** "Couldn't generate a grounded answer" → retry / non-AI fallback (SPEC §6.8). **Loading:** thinking indicator (no fake streaming of fabricated numbers).
- **Mobile:** full-height chat, suggestions as chips, sticky composer.
- **Animation:** AI summary reveal (block, no typewriter on numbers); citation chips fade-in.
- **Analytics:** `ai_chat_view`, `ai_message_send`, `ai_citation_open`, `ai_refusal{reason}`, `ai_fallback_served`.
- **Backend dep:** `POST /ai/chat`, `GET /ai/threads`. **Frontend dep:** streaming-safe client, Query for threads. **Data dep:** payload contract + grounding/verification + audit log (SPEC §6.6).
- **Acceptance:** Refuses recommendation/target/buy-sell asks with a Mode-A-safe explanation; every number/fact in answers traces to payload (else regenerated/blocked); responses carry grounding + not-advice; out-of-scope answered with non-AI fallback, never fabrication.

---

## 12. Strategy builder — `/strategy-builder` (auth, Pro+, Phase 4)

- **Purpose:** No-code scanner builder; outputs are **lists, not calls** (SPEC §4).
- **Layout:** `ConditionBuilder` (add/AND/OR conditions on indicators/scores/volume/sector), `StrategyCanvas`, live `ResultPreviewTable`, `SaveStrategyDialog`.
- **CTAs:** Add condition, preview run, save, run full, schedule, set alert on it.
- **Data shown:** condition set, preview result list (symbol + matched reasons).
- **Empty:** starter templates (descriptive). **Error:** invalid-condition inline errors; run errors → retry. **Loading:** preview skeleton.
- **Mobile:** stepwise builder in sheets.
- **Animation:** result rows stagger on preview.
- **Analytics:** `strategy_builder_view`, `condition_add`, `strategy_preview_run`, `strategy_save`, `strategy_run`.
- **Backend dep:** `GET/POST /strategies`, `POST /strategies/{id}/run`. **Frontend dep:** Query + mutations; Pro upgrade gate. **Data dep:** indicator/score universe (EOD).
- **Acceptance:** Output is a filtered **list** with descriptive reasons; no produced field is a buy/sell call, target, or SL.

---

## 13. Backtesting results — `/backtesting` (auth, Pro+, Phase 4)

- **Purpose:** Backtest a saved strategy with **integrity controls** + **honest framing** (SPEC §6.3).
- **Layout:** `BacktestConfigForm` (strategy, period, universe, costs), persistent `PastPerformanceBanner`, results: `EquityCurveChart`, `MetricsTable` (CAGR, max DD, hit rate, exposure), `AssumptionsPanel` (slippage, liquidity caps, point-in-time membership, survivorship inclusion), trade log.
- **CTAs:** Configure & run, change assumptions, export (Pro), compare runs.
- **Data shown:** equity curve, metrics, assumptions, trades — all with look-ahead/survivorship controls applied.
- **Empty:** "Configure a backtest". **Error:** validation + run errors; if integrity inputs missing, run is blocked with explanation. **Loading:** progress state for the run.
- **Mobile:** config sheet; chart + metrics stacked.
- **Animation:** equity curve line-reveal once; metric count-ups.
- **Analytics:** `backtest_view`, `backtest_run`, `backtest_assumptions_change`, `backtest_export`.
- **Backend dep:** `POST /backtests`, `GET /backtests/{id}`. **Frontend dep:** Query + mutation; Pro gate. **Data dep:** corp-action-adjusted history, delisted names, point-in-time membership (SPEC §6.3).
- **Acceptance:** "Past performance does not indicate future results" always visible; assumptions exposed; survivorship/look-ahead/point-in-time controls applied; results never framed as a return promise.

---

## 14. News — `/news` (public, indexed, Phase 2)

- **Purpose:** Market news + **finance-tuned** sentiment with sources, timestamps, confidence (SPEC §6.4).
- **Layout:** `NewsFeed` filterable by symbol/sector/sentiment; `NewsCard` (headline, source, time, `SentimentChip`, confidence, linked symbols).
- **CTAs:** Open source, open linked stock, filter.
- **Data shown:** headline, source link, timestamp, sentiment+confidence, symbol links above threshold.
- **Empty/error/loading:** "No recent news for this filter"; retry; skeleton cards.
- **Mobile:** single-column feed; filters in sheet.
- **Animation:** card fade-in on load/new.
- **Analytics:** `news_view`, `news_filter`, `news_source_open`, `news_symbol_open`.
- **Backend dep:** `GET /news`, `GET /news/sentiment`. **Frontend dep:** ISR/short-window. **Data dep:** entity-resolved, finance-tuned sentiment with confidence threshold (SPEC §6.4).
- **Acceptance:** Every news→symbol link shows confidence and source; sentiment from finance-tuned classifier; impact not exaggerated (SPEC §4).

---

## 15. Pricing — `/pricing` (public, indexed)

- **Purpose:** Compare Free/Premium/Pro/Enterprise (SPEC §11). RA-gated features shown as "coming with Research Analyst registration".
- **Layout:** `PricingTable` with `TierCard`s; `FaqAccordion`; monthly/annual toggle.
- **CTAs:** Choose plan → signup/checkout; contact sales (Enterprise).
- **Data shown:** plan features, prices, limits.
- **Empty/error/loading:** plans rarely fail; static fallback.
- **Mobile:** stacked cards; feature matrix collapsible.
- **Animation:** card hover lift; toggle transition.
- **Analytics:** `pricing_view`, `plan_select{tier}`, `billing_cycle_toggle`.
- **Backend dep:** `GET /billing/plans`. **Frontend dep:** SSG/ISR. **Data dep:** plan config.
- **Acceptance:** No advisory features advertised; RA-gated items clearly labeled as not-yet-available; fee-cap-aware tiering (SPEC §11) reflected.

---

## 16. Login / Signup — `/login` · `/signup` (public, noindex)

- **Purpose:** Authenticate / register.
- **Layout:** Centered card, brand, form, OAuth buttons, switch link, legal acknowledgement on signup.
- **CTAs:** Submit; OAuth; forgot password; switch login/signup.
- **Data shown:** form only.
- **Empty/error:** field validation; auth errors inline; rate-limit message. **Loading:** button spinner.
- **Mobile:** full-width card.
- **Animation:** subtle card fade; button loading morph.
- **Analytics:** `login_view`/`signup_view`, `auth_submit`, `auth_success`, `auth_error{reason}`, `oauth_click{provider}`.
- **Backend dep:** `POST /auth/login` / `/auth/signup`, NextAuth callbacks. **Frontend dep:** `(auth)` group, `?next=` preserved. **Data dep:** user store.
- **Acceptance:** `next` redirect honored; signup requires not-advice + AI-use acknowledgement (SPEC §6.7); errors never leak account existence.

---

## 17. Onboarding — `/onboarding` (auth)

- **Purpose:** First-run setup — **navigation personalization only** (SPEC §7): risk preference (default filters), followed sectors, watchlist seed, acknowledgements.
- **Layout:** `OnboardingStepper` (Risk preference → Follow sectors → Seed watchlist → Acknowledge & finish).
- **CTAs:** Next/back, skip, finish → `/dashboard`.
- **Data shown:** sector list, sample symbols.
- **Empty/error/loading:** standard; can skip any step.
- **Mobile:** full-screen steps.
- **Animation:** step transitions (slide/fade), confirmation on finish.
- **Analytics:** `onboarding_start`, `onboarding_step{n}`, `onboarding_skip`, `onboarding_complete`.
- **Backend dep:** `POST /me/onboarding`, `PATCH /me/preferences`. **Frontend dep:** stepper state in Zustand. **Data dep:** preferences store.
- **Acceptance:** Risk preference only sets **default filters/layout**, never per-stock suggestions; no behaviour-derived buy-leans (SPEC §7); acknowledgements recorded.

---

## 18. Dashboard (authenticated home) — `/dashboard` (auth)

- **Purpose:** Personalized navigation home: followed sectors, watchlist snapshot, alerts feed, daily brief (event-reporting), portfolio summary.
- **Layout:** Responsive grid of cards; greeting + date header.
- **Sections/components:** `DailyBriefCard` (compact mirror of the full **AI daily brief** — events + "what to monitor", never "what to buy"; deep-links to `/brief`, see §21), `WatchlistSnapshot`, `AlertsFeed`, `PortfolioSummaryCard`, `FollowedSectorsRow`, `MarketPulseStrip`.
- **CTAs:** Jump to watchlist/portfolio/alerts/scanners; open brief evidence.
- **Data shown:** user's followed/owned entities + EOD signals + brief.
- **Empty:** first-time → prompts to follow sectors/add watchlist (links to onboarding). **Error:** per-card retry. **Loading:** card skeletons.
- **Mobile:** single-column stacked cards; brief first.
- **Animation:** card stagger; brief reveal; count-ups once.
- **Analytics:** `dashboard_view`, `brief_evidence_open`, `dashboard_card_click{card}`.
- **Backend dep:** `GET /me/dashboard`, `/me/watchlist`, `/alerts`, `/market/ai-brief`, `/portfolio/summary`. **Frontend dep:** SSR + Query hydration, noindex. **Data dep:** user prefs + EOD + grounded brief.
- **Acceptance:** Daily brief reports events + monitoring only (SPEC §4); personalization is navigation-only; all figures traceable.

---

## 19. Admin screens — `/admin/*` (admin only, noindex/disallow)

Shared shell: `AdminOverviewGrid` + role-gated nav. All actions audited.

| Screen | Purpose | Key components | Backend dep |
|---|---|---|---|
| `/admin` | System health, pipeline status, **AI-spend meter**, compliance flags | `PipelineStatusCard`, `AiSpendMeter`, `ComplianceFlagFeed` | `GET /admin/overview · /pipeline/status · /ai-spend` |
| `/admin/data-health` | Anomalies, corp-action reconcile, **confidence**, correction workflow (detect→quarantine→correct→re-emit) | `AnomalyTable`, `CorpActionReconcilePanel`, `CorrectionWorkflowModal`, `ConfidenceGauge` | `GET /admin/data-health`, `POST /admin/data/{quarantine,correct,reemit}` |
| `/admin/prompts` | Prompt registry/versions, **eval harness**, payload-contract viewer, provider config | `PromptVersionList`, `PromptEditor`, `EvalHarnessPanel`, `ProviderConfigForm` | `GET/POST /admin/prompts`, `POST /admin/prompts/{id}/eval`, `GET /admin/ai/audit-log` |
| `/admin/scanners` | Scoring weights, thresholds, **M3b validation evidence**, schedule | `WeightEditor`, `ValidationEvidencePanel`, `ScannerScheduleForm` | `GET/PATCH /admin/scanners`, `GET /admin/scanners/{slug}/validation` |
| `/admin/compliance` | **Blocked-phrase registry (versioned)**, guardrail rules, review queue, audit search, block events | `BlockedPhraseRegistry`, `GuardrailRuleEditor`, `ReviewQueue`, `AuditLogSearch` | `GET/POST /admin/compliance/phrases · /audit · /blocks` |
| `/admin/users` | Roles, tiers, **RA-client + fee-cap (~₹1.51L/yr/family)** tracking, support | `UserTable`, `RoleEditor`, `SubscriptionPanel`, `FeeCapTracker` | `GET /admin/users`, `PATCH /admin/users/{id}`, `GET /admin/users/{id}/fee-cap` |

- **States:** loading skeleton tables; empty queues with "nothing to review"; errors with retry; destructive actions require confirm + reason (audited).
- **Mobile:** admin is desktop-first; functional but compact on tablet.
- **Animation:** minimal — admin prioritizes legibility/speed over motion.
- **Analytics (internal):** `admin_action{type}`, `compliance_phrase_edit`, `prompt_publish`, `data_correction_apply`, `scanner_weight_change`.
- **Backend dep / Frontend dep / Data dep:** as per row + [05 §4](05-information-architecture-and-url-paths.md); admin bundles never ship to public ([06 §12](06-frontend-architecture.md)).
- **Acceptance:** Every admin mutation writes an audit log entry; blocked-phrase + prompt changes are versioned; data corrections re-emit dependent indicators **and** AI summaries (SPEC §6.2); RA fee-cap tracked when Mode B is in force.

---

## 21. AI daily market brief — `/brief` (public, indexed)

- **Purpose:** Dedicated, **permalinkable** AI daily market brief (step 07 — [steps/07](steps/07-v2-accounts-watchlist-ai-news.md)). **Event-reporting, never "what to buy".** The dashboard `DailyBriefCard` (§18) is a compact mirror that deep-links here.
- **Route & access:** `/brief`, public, indexed ([05 §2](05-information-architecture-and-url-paths.md)); `?as_of=` renders a historical day's brief (canonical strips it).
- **Layout:** `BriefHeader` (trading date + as-of + grounding badge), then scannable sections in order: market summary → indices → sectors → movers → scanner entries/exits → risk highlights → what-to-monitor; persistent `NotAdviceBanner`.
- **Sections/components:** `BriefMarketSummary` (descriptive recap of the session), `BriefIndicesGrid` (index levels/%chg), `BriefSectorRotation` (which sectors led/lagged — descriptive), `BriefMoversList` (notable gainers/losers/most-active — factual, no "top picks"), `BriefScannerDeltaList` (**scanner entries/exits** — "entered/exited the X scanner today"), `BriefRiskHighlights` (factual risk-flag changes), `BriefWhatToMonitor` (events/levels to watch — monitoring, not directives), `EvidenceDrawer` per claim.
- **User actions/CTAs:** Open evidence on any section, jump to a referenced stock/sector/scanner, change as-of (historical brief), copy permalink/share.
- **Data shown:** All figures EOD-cached + grounded; scanner deltas vs prior session; as-of.
- **Empty:** Pre-market/no fresh brief → "Latest brief: <date>" with last published brief. **Suppressed:** any section whose inputs fail grounding/confidence is suppressed with a note, never fabricated (SPEC §6.2/§6.6). **Error:** per-section error + retry; non-AI fallback for the summary block (SPEC §6.8). **Loading:** section skeletons; brief is largely SSR/ISR.
- **Mobile:** single-column scannable sections; sticky date header; evidence as bottom sheet.
- **Desktop:** two-column where dense (indices/sectors side-by-side); reading width for the summary.
- **Animation:** section reveal on scroll-in; count-ups on indices once; reduce-motion disables.
- **Analytics:** `brief_view`, `brief_section_evidence_open{section}`, `brief_entity_open{type}`, `brief_as_of_change`, `brief_share`.
- **Backend dep:** `GET /market/ai-brief`, `GET /market/summary`, `GET /sectors`, `GET /scanners` (entry/exit deltas). **Frontend dep:** SSR/ISR post-EOD ([05 §2](05-information-architecture-and-url-paths.md)). **Data dep:** EOD batch + grounded brief + scanner deltas + confidence flags.
- **Acceptance:** Every section is event-reporting/descriptive; "what-to-monitor" lists events/levels to watch, never buy/sell actions; all figures trace to evidence or are suppressed; as-of reproduces a historical brief; non-AI fallback served if the summary can't be grounded.

---

## 22. Screener library — `/screeners` · `/screeners/[slug]` (public, indexed)

- **Purpose:** Browse, run, and save **screeners** with **list-only** outputs (step 20 — [steps/20](steps/20-screener-library.md)). A curated/saved-criteria catalog that hands off to the no-code builder. **No buy/rank-to-act CTA.**
- **Route & access:** `/screeners` (library index) and `/screeners/[slug]` (one screener); public, indexed ([05 §2](05-information-architecture-and-url-paths.md)). Save requires auth; run is public.
- **Layout (index):** `ScreenerLibraryGrid` of `ScreenerCard`s (name, one-line "what it filters for", last-run, result count), `ScreenerFilters` (category: fundamental/technical/mixed). **Layout (detail):** `ScreenerHeader` (name, criteria summary, last-run), `ScreenerCriteriaPanel` (read-only criteria), `ScreenerResultsTable` (list-only), action row (Run / Save / Open in builder).
- **Sections/components:** `ScreenerCard`, `ScreenerCriteriaPanel`, `ScreenerResultsTable` (symbol + matched descriptive reasons, no score-to-act), `SaveScreenerDialog` (auth), `OpenInBuilderButton` (handoff to `/strategy-builder` with criteria prefilled), `EvidenceDrawer`.
- **User actions/CTAs:** Browse/filter library, open a screener, **run** (list-only results), **save** (auth, tier-gated depth), **"Open in builder"** handoff, add a result to watchlist, open a result's stock. **No buy/switch CTA.**
- **Data shown:** Screener catalog metadata; on run, the matching symbol **list** with matched reasons; as-of.
- **Empty:** index → "No screeners match this filter"; detail run → "No stocks match these criteria" + adjust/open-in-builder. **Suppressed:** a criterion's contribution is suppressed if inputs fail confidence. **Error:** retry on run; header still renders. **Loading:** card/row skeletons; run shows a progress state.
- **Mobile:** library as 1-col cards; criteria + results stacked; actions in a sticky bar.
- **Desktop:** library grid (2–3 col); detail = criteria rail + results table.
- **Animation:** card stagger; result rows stagger on run; reduce-motion disables.
- **Analytics:** `screener_library_view`, `screener_card_open`, `screener_run{slug}`, `screener_save`, `screener_open_in_builder`, `watchlist_add{from:screener}`.
- **Backend dep:** `GET /screeners`, `GET /screeners/{slug}`, `POST /screeners/{slug}/run`, `POST /screeners` (save). **Frontend dep:** ISR catalog + client run controls; builder handoff. **Data dep:** screener definitions + EOD indicator/fundamental universe.
- **Acceptance:** Output is a filtered **list** with descriptive reasons; no produced field is a buy/sell call, target, rank-to-act, or "switch"; "Open in builder" preserves criteria; save is tier-gated.

---

## 23. Notification center — `/notifications` (auth)

- **Purpose:** In-app **inbox** of delivered alert/news events with read/unread (step 24 — [steps/24](steps/24-account-surfaces.md)). **Event-reporting only** — mirrors fired `/alerts` and news events; never "buy"/"sell".
- **Route & access:** `/notifications`, auth, Free+ (depth/retention per tier), noindex ([05 §3](05-information-architecture-and-url-paths.md)).
- **Layout:** `NotificationInbox` shell → `NotificationFilters` (type: alert/news/system; symbol; date; read/unread), `NotificationList` of `NotificationRow`s, `MarkAllReadButton`.
- **Sections/components:** `NotificationRow` (icon by type, event headline e.g. "TCS entered the momentum scanner", timestamp, read/unread dot, deep-link to source surface), `NotificationFilters`, `MarkAllReadButton`, `EmptyInboxState`.
- **User actions/CTAs:** Mark read/unread, mark-all-read, filter, open a notification's source (stock/scanner/news), clear/dismiss.
- **Data shown:** Delivered events (alert fires, news events, system), read state, timestamp, deep-link target.
- **Empty:** `EmptyInboxState` — "You're all caught up" + link to set up alerts (`/alerts`). **Error:** retry; mark-read mutations optimistic with rollback. **Loading:** row skeletons.
- **Mobile:** full-height list; filters in a sheet; swipe-to-mark-read; mark-all in header.
- **Desktop:** list with filter rail; bulk actions in toolbar.
- **Animation:** new-item fade-in; read-state dot transition; reduce-motion disables.
- **Analytics:** `notifications_view`, `notification_open`, `notification_mark_read`, `notifications_mark_all_read`, `notification_filter`.
- **Backend dep:** `GET /me/notifications`, `PATCH /me/notifications/{id}`, `POST /me/notifications/read-all`. **Frontend dep:** Query + optimistic mutations. **Data dep:** delivered alert/news event stream (EOD-batch in v1).
- **Acceptance:** All inbox copy is event-reporting ("entered the scanner", "new announcement"), never directive; read/unread + filters work; empty state guides to alert setup; v1 events are EOD-batch.

---

## 20. Cross-screen acceptance criteria

- **Backend dependency:** Every screen's data maps to endpoints in [10](10-api-contracts.md); nothing is fabricated client-side ([06 §13](06-frontend-architecture.md)).
- **Frontend dependency:** Components match [07](07-design-system-and-ui-ux.md); RSC/Client split and states per [06](06-frontend-architecture.md); all four core states (empty/error/loading/suppressed) implemented.
- **Data dependency:** EOD/T+1 cadence (SPEC §8); corp-action-adjusted series (SPEC §6.1); validated scores (SPEC §6.5); grounded/verified AI (SPEC §6.6); confidence + suppression honored (SPEC §6.2).
- **Compliance:** No screen renders entry/target/SL, buy/sell, recommendation, or blocked phrases in Mode A; RA-gated slots show `RaGatedPlaceholder`; AI surfaces carry grounding + not-advice; alerts/briefs are event-reporting only.
- **Animation/A11y:** Motion follows [07 §3](07-design-system-and-ui-ux.md) timing/easing and never delays data legibility; `prefers-reduced-motion` honored; WCAG 2.2 AA met.
