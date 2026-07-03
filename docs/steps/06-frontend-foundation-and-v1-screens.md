# Steps · 06 · Frontend Foundation & V1 Screens

> Read first: [SPEC.md](../../SPEC.md) · [Roadmap](../02-product-roadmap.md) · [Frontend Architecture](../06-frontend-architecture.md) · [Design System & UI/UX](../07-design-system-and-ui-ux.md) · [Screen-by-Screen](../08-screen-by-screen-documentation.md) · [IA & URL Paths](../05-information-architecture-and-url-paths.md) · [API Contracts](../10-api-contracts.md) · [Compliance & Guardrails](../21-compliance-risk-and-guardrails.md)

**Maps to:** Roadmap V1 (UI) · SPEC Phase 1 · Local milestone M6
**Status:** Complete (M6 — 2026-06-30)   |   **Regulatory mode:** A

> **Post-M6 addition (2026-07-03, D-060):** the public **home/landing page at `/`** (`web/app/page.tsx` → `web/src/components/marketing/Landing.tsx`) is built per [08 §1](../08-screen-by-screen-documentation.md) — evidence-led hero, feature bands, descriptive scanner preview, CTAs to `/signup` + `/scanners/momentum`, `NotAdviceBanner`. A subtle **3D data-orb** (`@react-three/fiber`) anchors the hero, loaded client-only with a **static gradient fallback for `prefers-reduced-motion`**; 3D is hero-only (docs/07 forbids motion that harms data-screen legibility). `TopNav` now surfaces **Log in / Start free** for signed-out users. Type-clean; production build green. `/` previously just `redirect()`-ed to `/market`.
**Prerequisites:** [05-api-and-pipeline.md](05-api-and-pipeline.md) (M5 endpoints live) · [04-ai-explanation-layer.md](04-ai-explanation-layer.md) (grounded AI + blocked-phrase export)

## Overview
Scaffold the Next.js (App Router) web app per [06](../06-frontend-architecture.md), apply the dark-first design tokens + motion rules from [07](../07-design-system-and-ui-ux.md), wire TanStack Query (server state) + Zustand (UI state), set up charting (TradingView Lightweight Charts + ECharts, lazy/client-only), and build the **V1 public screens** from [08](../08-screen-by-screen-documentation.md): market dashboard, scanner directory + detail, stock detail (with evidence drawer, **no entry/target/SL**), and the sector dashboard. The frontend **never originates a number** — it renders API payloads from [10](../10-api-contracts.md) and traces every figure to an evidence drawer ([06 §0](../06-frontend-architecture.md)). RA-gated slots render `RaGatedPlaceholder`; AI text is display-only and pre-verified, always wrapped with a grounding badge + not-advice banner. Animations honor `prefers-reduced-motion` and never delay reading a value ([07 §3.3](../07-design-system-and-ui-ux.md)).

The frontend is **deferred until M5 is validated** ([06 §0](../06-frontend-architecture.md)); this step is the M6 thin-UI deliverable. Authenticated/admin/Phase-2+ screens (watchlist, portfolio, AI chat, etc.) are out of scope here — they land in [07-v2-accounts-watchlist-ai-news.md](07-v2-accounts-watchlist-ai-news.md) and later.

## Exit gate (Definition of Done)
- [ ] `web/` scaffold matches the folder structure + route groups in [06 §1–§2](../06-frontend-architecture.md); pages are thin, domain components do the work.
- [ ] Design tokens from [07 §1](../07-design-system-and-ui-ux.md) live in `src/styles/tokens.css` and are surfaced to Tailwind; components use **semantic** classes only (no raw hex/px).
- [ ] TanStack Query + typed Zod client (mirroring [10](../10-api-contracts.md)) + Zustand UI stores wired; no ad-hoc `fetch`, no client-side financial computation.
- [ ] Charts (`PriceChart`, ECharts wrappers) are lazy, client-only, theme-token-driven, and respect reduce-motion.
- [ ] V1 screens render with all four core states (loading/error/empty/suppressed) and the global `NotAdviceBanner`.
- [ ] **No** entry/target/SL or buy/sell copy anywhere; the build-time blocked-phrase lint (mirrored from step 04) fails the build on any hit ([06 §13](../06-frontend-architecture.md), [SPEC §6.9](../../SPEC.md)).
- [ ] E2E: pick a stock → see indicators, scanner score, grounded explanation ([SPEC §12 M6](../../SPEC.md)).
- [ ] Component + visual-regression + the E2E test green.

---

## Feature: App scaffold & folder structure  `(Mode A)`
**Objective:** Stand up the Next.js App Router project with the route groups, providers, and layering rules from [06](../06-frontend-architecture.md). · **Backend dep:** M5 FastAPI base URL. · **Frontend dep:** [06 §1–§3](../06-frontend-architecture.md). · **Data dep:** none.
### Steps
- [ ] 1. Initialize `web/` (Next.js App Router, TypeScript strict) with the exact tree from [06 §1](../06-frontend-architecture.md): `app/(marketing)`, `app/(market)`, `app/(app)`, `app/(auth)`, `app/admin`, `app/api`, plus `src/{components,hooks,lib,stores,styles,types,constants}`, `middleware.ts`, and config files (`tailwind.config.ts`, `next.config.ts`, `tsconfig.json`, `vitest.config.ts`, `playwright.config.ts`).
- [ ] 2. Create `app/layout.tsx` (root: `<html>`, theme attribute from cookie to avoid flash, providers) and `app/globals.css`. Add `(market)/layout.tsx` for the public data shell (top nav + footer); leave `(app)`/`admin` layouts as stubs (out of M6 scope).
- [ ] 3. Add `src/lib/query/client.ts` (TanStack `QueryClient` with EOD-aligned `staleTime`/`gcTime`) and a `Providers` client component (`QueryClientProvider` + theme). Add `HydrationBoundary` prefetch helpers for SSR pages ([06 §4–§5](../06-frontend-architecture.md)).
- [ ] 4. Enforce layering with ESLint import rules: `ui/` primitives import only React/Tailwind/tokens; pages compose domain components + prefetch only; no business logic in `app/` ([06 §3, §14](../06-frontend-architecture.md)).
- [ ] 5. Add absolute `@/` import alias and `import 'server-only'` guards on server modules.
### Tests
- [ ] `test_route_groups_render` — each V1 route segment mounts with its group layout.
- [ ] Lint check: a domain import inside a `ui/` primitive fails ESLint.
### Compliance gate
- [ ] No `/recommendations`/`/picks`/`/calls` route exists; RA-gated routes are absent from the v1 router ([05 §0](../05-information-architecture-and-url-paths.md)).
### Acceptance criteria
- [ ] Folder structure, route groups, and RSC/Client split match [06 §1–§3](../06-frontend-architecture.md).

---

## Feature: Tailwind + design tokens  `(Mode A)`
**Objective:** Encode the dark-first visual language from [07](../07-design-system-and-ui-ux.md) as CSS variables + Tailwind semantic utilities. · **Backend dep:** none. · **Frontend dep:** [07 §1–§2](../07-design-system-and-ui-ux.md). · **Data dep:** none.
### Steps
- [ ] 1. Create `src/styles/tokens.css` with `:root` (dark default) + `[data-theme="light"]` blocks for every token in [07 §1](../07-design-system-and-ui-ux.md): surfaces (`--surface-base/1/2/3/glass`), borders, text, semantic/market (`--accent`, `--bullish`, `--bearish`, `--neutral`, `--warning`, `--info`, `--ai`), typography scale, spacing (4px base), radii, elevation/glow, z-index, blur, motion timing/easing.
- [ ] 2. Map semantic tokens into `tailwind.config.ts` (e.g. `bg-surface-1`, `text-secondary`, `text-bullish`, `border-subtle`, `shadow-elev-2`); add `tabular-nums` utility and Inter + mono font config via `next/font` ([07 §1.4](../07-design-system-and-ui-ux.md)).
- [ ] 3. Add a `cva`-based variant system; forbid raw hex/px in components via an ESLint/Stylelint rule ([06 §13](../06-frontend-architecture.md)).
- [ ] 4. Wire theme persistence: `useThemeStore` (Zustand + `persist`), SSR cookie read to set `data-theme` with no flash, `color-scheme` set for native controls ([07 §4](../07-design-system-and-ui-ux.md)).
### Tests
- [ ] `test_tokens_present_both_themes` — every documented token resolves under dark and light.
- [ ] Visual regression: token swatch sheet matches baseline in both themes.
### Compliance gate
- [ ] Greens/reds are the desaturated descriptive tokens; no urgency/guarantee styling; market color always paired with a non-color signal ([07 §0, §1.3](../07-design-system-and-ui-ux.md)).
### Acceptance criteria
- [ ] Components consume semantic tokens only; contrast pairings meet WCAG 2.2 AA ([07 §5](../07-design-system-and-ui-ux.md)).

---

## Feature: Base layout, nav & command palette  `(Mode A)`
**Objective:** Build the shared app chrome — top nav, footer, and `Cmd/Ctrl+K` command palette — plus the mandatory compliance wrappers. · **Backend dep:** `GET /stocks/search` for palette symbol search. · **Frontend dep:** [07 §2.9, §2.11](../07-design-system-and-ui-ux.md), [06 §3](../06-frontend-architecture.md). · **Data dep:** symbol/sector/scanner catalog.
### Steps
- [ ] 1. Build `src/components/layout/`: `TopNav` (glass-on-scroll), `Footer` (legal links incl. disclaimer), `CommandPalette` (centered glass modal, fuzzy search across symbols/sectors/scanners/pages, keyboard-first, focus-trapped, `Esc` closes) ([07 §2.9](../07-design-system-and-ui-ux.md)).
- [ ] 2. Build `src/components/compliance/`: `NotAdviceBanner` (subtle, persistent on data/AI surfaces), `GroundingBadge` ("Grounded in this stock's signals · not investment advice"), `RaGatedPlaceholder` (muted card + lock glyph, "Available with Research Analyst registration" — never an empty target/SL widget) ([07 §2.7, §2.11](../07-design-system-and-ui-ux.md)).
- [ ] 3. Build `src/components/ui/` primitives used by V1: `Button`, `Card`, `Badge`, `ScoreBadge` (0–100 band→token, mono, opens evidence drawer, **no "buy strength" wording**), `DataTable`, `Chip`, `Skeleton`, `EmptyState`, `ErrorState` ([07 §2.2–2.6](../07-design-system-and-ui-ux.md)).
- [ ] 4. Mirror the blocked-phrase list into `src/constants/blocked-phrases.ts` from step 04's `blocked_phrases_export()`, and add the **custom ESLint rule** that fails the build on any blocked phrase / advisory word in a JSX string literal ([06 §13–§14](../06-frontend-architecture.md), [SPEC §6.9](../../SPEC.md)).
- [ ] 5. Add `src/lib/format` (`en-IN`, INR `₹`, percent/date) and `src/lib/flags` with `raRecommendationLayer=false`, `technicalLevels=false` (compile-time-OFF, no client toggle) ([06 §10](../06-frontend-architecture.md)).
- [ ] 6. Add `src/lib/motion` shared Framer Motion variants + `useReducedMotion` wiring so every animated component honors reduce-motion consistently ([07 §3.3](../07-design-system-and-ui-ux.md)).
### Tests
- [ ] `test_command_palette_keyboard` — `Cmd/Ctrl+K` opens; arrow/enter navigate; `Esc` closes; focus restored.
- [ ] `test_blocked_phrase_lint_fails_build` — a JSX literal with "buy now" fails lint.
- [ ] `test_score_badge_shows_number` — numeric score always rendered; color is secondary.
### Compliance gate
- [ ] `NotAdviceBanner`/`GroundingBadge`/`RaGatedPlaceholder` exist and are the mandated wrappers; build fails on blocked phrases ([06 §3, §14](../06-frontend-architecture.md)).
### Acceptance criteria
- [ ] Shared chrome + compliance wrappers + UI primitives are available to all V1 screens.

---

## Feature: Charting setup  `(Mode A)`
**Objective:** Lazy, client-only chart wrappers driven by theme tokens that plot **already-computed** API series — never client computation. · **Backend dep:** `GET /stocks/{sym}/technicals` (series). · **Frontend dep:** [06 §8](../06-frontend-architecture.md), [07 §2.3](../07-design-system-and-ui-ux.md). · **Data dep:** corp-action-adjusted OHLC + indicator series.
### Steps
- [ ] 1. Create `src/components/charts/PriceChart.tsx` (TradingView Lightweight Charts): candles + volume + MA overlays + descriptive S/R lines; `"use client"`, lazy via `next/dynamic` (`ssr:false`), skeleton sized to final dimensions (no CLS) ([06 §8](../06-frontend-architecture.md)).
- [ ] 2. Create `src/components/charts/EChart.tsx` wrapper + `SectorHeatmap` and `BreadthPanel` viz using the perceptually-uniform bullish↔neutral↔bearish ramp ([07 §2.3](../07-design-system-and-ui-ux.md)).
- [ ] 3. Charts read theme tokens at runtime (recolor on theme switch); disable the left→right line-reveal on reduce-motion and on data refresh ([07 §3.2](../07-design-system-and-ui-ux.md)).
- [ ] 4. Charts consume pre-computed series only; if a value isn't in the payload it isn't plotted ([06 §8, §13](../06-frontend-architecture.md)).
### Tests
- [ ] `test_chart_lazy_no_ssr` — `PriceChart` is dynamically imported with `ssr:false` and renders a skeleton placeholder.
- [ ] `test_chart_no_layout_shift` — skeleton matches final chart dimensions (CLS guard).
### Compliance gate
- [ ] No gradient "hype" fills by default; S/R rendered descriptively (historical framing), never as entry/target/SL ([07 §2.3](../07-design-system-and-ui-ux.md), [08 §5](../08-screen-by-screen-documentation.md)).
### Acceptance criteria
- [ ] Charts are lazy/client-only, token-driven, reduce-motion-aware, and plot only API series ([06 §8](../06-frontend-architecture.md)).

---

## Feature: TanStack Query + Zustand wiring  `(Mode A)`
**Objective:** A typed, Zod-validated API client and centralized query keys for server state; Zustand for UI-only state — strictly separated. · **Backend dep:** M5 endpoints ([10](../10-api-contracts.md)). · **Frontend dep:** [06 §4–§5](../06-frontend-architecture.md). · **Data dep:** envelope `data`/`meta` shapes.
### Steps
- [ ] 1. Create `src/lib/api/` typed functions per [10](../10-api-contracts.md) with Zod schemas for the standard envelope (`data`, `meta.as_of`, `meta.data_confidence`, `error`) and each M5 payload; invalid shapes throw and surface an error state, never render unvalidated data ([06 §5](../06-frontend-architecture.md)).
- [ ] 2. Create `src/constants/query-keys.ts` + `src/lib/query/keys.ts`: `['market','summary',date]`, `['scanner',slug,filters]`, `['stock',symbol,'overview']`, `['stock',symbol,'technicals',range]`, `['stock',symbol,'ai-summary',signalVersion]`, `['sectors']`, `['sector',slug]` ([06 §4](../06-frontend-architecture.md)).
- [ ] 3. Create hooks in `src/hooks/`: `useMarketSummary`, `useScanner`, `useStockOverview`, `useStockTechnicals`, `useStockAiSummary`, `useSectors`, `useSector`. AI-summary hook keys by symbol + signal-version so cache aligns with backend regenerate-on-change ([06 §4](../06-frontend-architecture.md), [05 caching](05-api-and-pipeline.md)).
- [ ] 4. Create Zustand UI stores in `src/stores/`: `useThemeStore`, `useUiStore` (sidebar/palette/density/reduce-motion override), `useFilterStore` (scanner filter panel). **Never** store server data here ([06 §4](../06-frontend-architecture.md)).
- [ ] 5. SSR prefetch with `QueryClient` + `HydrationBoundary` on public pages so first paint is data-complete (no double fetch) ([06 §4–§5](../06-frontend-architecture.md)).
### Tests
- [ ] `test_zod_rejects_bad_envelope` — a response missing `meta.as_of` throws and renders `ErrorState`.
- [ ] `test_ui_store_has_no_server_data` — store shape contains only UI keys.
### Compliance gate
- [ ] No client-side derivation of indicators/scores/signals; "score color" maps server value → token only ([06 §4, §13](../06-frontend-architecture.md)).
### Acceptance criteria
- [ ] All data flows through typed Query hooks; UI state is Zustand-only; suppression/low-confidence states are representable ([06 §5–§6](../06-frontend-architecture.md)).

---

## Feature: V1 Screen — Market dashboard `/market`  `(Mode A)`
**Objective:** EOD market state — indices, breadth, sector heat, descriptive grounded AI summary, movers — per [08 §2](../08-screen-by-screen-documentation.md). · **Backend dep:** `GET /market/summary`, `/market/breadth`, `/sectors`, `/market/ai-summary`. · **Frontend dep:** `(market)` group, ISR post-EOD. · **Data dep:** EOD batch + confidence flags.
### Steps
- [ ] 1. `app/(market)/market/page.tsx` (thin, SSR prefetch) composing `src/components/market/`: `IndexStrip`, `BreadthPanel`, `SectorHeatmap`, `AiMarketSummaryCard`, `MarketMoversTable` (gainers/losers/most-active tabs — descriptive, **no "top picks"**), `DataConfidenceIndicator` ([08 §2](../08-screen-by-screen-documentation.md)).
- [ ] 2. Header shows session date + as-of; support `?as_of=` historical view (label the as-of date) ([06 §5](../06-frontend-architecture.md)).
- [ ] 3. `AiMarketSummaryCard` wraps the grounded `headline`/brief with `GroundingBadge` + "View evidence"; **suppressed** state ("Summary unavailable — required inputs missing") when the API marks it suppressed ([SPEC §6.2](../../SPEC.md)).
- [ ] 4. States: loading skeletons matching grid; per-card `ErrorState` + retry; pre-market empty → "Latest EOD data: <date>".
- [ ] 5. Animation: heatmap tile fade+scale stagger, AI reveal (block, no typewriter), breadth count-ups once; all disabled on reduce-motion ([07 §3.2–3.3](../07-design-system-and-ui-ux.md)).
- [ ] 6. Analytics: `market_view`, `sector_tile_click`, `mover_tab_change`, `market_ai_evidence_open`, `as_of_change` ([08 §2](../08-screen-by-screen-documentation.md)).
### Tests
- [ ] Component: `AiMarketSummaryCard` renders grounded text + badge, and the suppressed variant on a suppressed payload.
- [ ] Visual regression: market grid (dark + light).
### Compliance gate
- [ ] Headline/movers descriptive only; AI grounded or suppressed; confidence indicator reflects backend ([08 §2 acceptance](../08-screen-by-screen-documentation.md)).
### Acceptance criteria
- [ ] All figures trace to payload; as-of reproduces historical values; LCP target met ([08 §2](../08-screen-by-screen-documentation.md)).

---

## Feature: V1 Screen — Scanner directory + detail `/scanners`, `/scanners/momentum`(+siblings)  `(Mode A)`
**Objective:** Browse scanners, then view ranked results with **score + reasons + risk flags** and per-row evidence — membership language only. · **Backend dep:** `GET /scanners`, `GET /scanners/momentum` (+ `/rsi`, `/volume-breakout`). · **Frontend dep:** ISR list + client controls. · **Data dep:** validated scores, descriptive reasons, risk flags, as-of.
### Steps
- [ ] 1. `app/(market)/scanners/page.tsx` → `ScannerDirectoryGrid` of `ScannerCard`s (last-run, result count, one-line "what it measures") — each states what it measures, never "best buys" ([08 §3](../08-screen-by-screen-documentation.md)).
- [ ] 2. `app/(market)/scanners/momentum/page.tsx` (+ `/volume-breakout`, `/rsi`) composing `src/components/scanner/`: `ScannerHeader` (name, what it measures, last-run, **validation note** from [SPEC §6.5](../../SPEC.md)), `ScannerFilters` (sector/index/score-band/risk-flag presence — **no "buy" preset**), `ScannerResultsTable` (symbol, price/%chg, `ScoreBadge`, `ReasonChips`, `RiskFlagChip`, sub-score sparkline), `EvidenceDrawer` per row, virtualized + paginated ([08 §4](../08-screen-by-screen-documentation.md)).
- [ ] 3. Reasons render as descriptive chips ("above 50-DMA", "volume 2× 20-day avg"); `RiskFlagChip` amber; false-breakout shows as a **risk flag**, never "buy the breakout" ([07 §2.5, §2.11](../07-design-system-and-ui-ux.md), [08 §4](../08-screen-by-screen-documentation.md)).
- [ ] 4. `EvidenceDrawer` maps each row figure → source metric/scanner tag/value/as-of (the literal "evidence" embodiment) — right drawer (desktop) / bottom sheet (mobile) ([07 §2.8](../07-design-system-and-ui-ux.md)).
- [ ] 5. States: empty "No stocks match the current filters" + reset; retry card on error; row skeletons + sticky header on load.
- [ ] 6. Animation: row stagger, newly-entered rows one-time accent flash, score count-up once, drawer slide-in; reduce-motion disables ([07 §3.2](../07-design-system-and-ui-ux.md)).
- [ ] 7. Analytics: `scanner_directory_view`, `scanner_card_open`, `scanner_view{slug}`, `scanner_filter_apply`, `scanner_sort`, `scanner_row_evidence_open` ([08 §3–§4](../08-screen-by-screen-documentation.md)).
### Tests
- [ ] Component: `ScannerResultsTable` renders score/reasons/risk flags; `EvidenceDrawer` lists each figure's source.
- [ ] Visual regression: scanner table + evidence drawer.
### Compliance gate
- [ ] Membership phrasing ("appears in…"); no buy-lean/target language; every score/reason traceable in the evidence drawer ([08 §4 acceptance](../08-screen-by-screen-documentation.md)).
### Acceptance criteria
- [ ] Scores are the validated ones; filters never offer a "best stocks" preset; states all present ([08 §4](../08-screen-by-screen-documentation.md)).

---

## Feature: V1 Screen — Stock detail `/stocks/[symbol]` (evidence drawer, NO levels)  `(Mode A)`
**Objective:** Full evidence dossier — facts, chart, indicators, scanner memberships, descriptive S/R, risk, grounded AI summary — with **no entry/target/SL** (RA-gated → `RaGatedPlaceholder`). · **Backend dep:** `GET /stocks/{symbol}/overview`, `/technicals`, `/ai-summary` (V1 subset). · **Frontend dep:** ISR per symbol + client chart/panels. · **Data dep:** corp-action-adjusted series, validated scores, grounded AI, confidence flags.
### Steps
- [ ] 1. `app/(market)/stocks/[symbol]/page.tsx` (SSR header for first paint/SEO) composing `src/components/stock/`: sticky `StockHeader` (name, symbol, price, %chg, sector, `RiskBadge`), main `PriceChart` + tabbed `IndicatorPanel` (RSI/MACD/ATR/BBands/volume ratio — value + state), right rail `AiStockSummaryCard` + `ScannerMembershipChips` + `KeyStats` ([08 §5](../08-screen-by-screen-documentation.md)).
- [ ] 2. Render the levels slot as `RaGatedPlaceholder` ("Available with Research Analyst registration") — **never** an empty target/SL widget; descriptive S/R lines on the chart use historical framing only ([05 §3 RA-gated note](../05-information-architecture-and-url-paths.md), [08 §5](../08-screen-by-screen-documentation.md)).
- [ ] 3. `AiStockSummaryCard` (`--ai` accent, "AI" chip, `GroundingBadge`, "View evidence") renders the pre-verified API summary; `EvidenceDrawer` maps each claim → `evidence[].field`/`value`; suppressed state when the API returns `422 DATA_SUPPRESSED` ([07 §2.7–2.8](../07-design-system-and-ui-ux.md), [10 §4 ai-summary](../10-api-contracts.md)).
- [ ] 4. States: thin/illiquid symbol → "Limited data available" + confidence note; per-panel error (header still renders); chart + panel skeletons; unknown symbol → `not-found.tsx` ([08 §5](../08-screen-by-screen-documentation.md)).
- [ ] 5. Animation: chart line-reveal once, risk-pulse one-shot if a new risk flag (never loops/alarmist), score count-up, AI reveal, drawer slide-in; reduce-motion disables all ([07 §3.2–3.3](../07-design-system-and-ui-ux.md)).
- [ ] 6. Case-normalize symbol (`/stocks/tcs` 301 → `/stocks/TCS`) ([05 §6](../05-information-architecture-and-url-paths.md)).
- [ ] 7. Analytics: `stock_view{symbol}`, `chart_timeframe_change`, `indicator_toggle`, `stock_ai_evidence_open` ([08 §5](../08-screen-by-screen-documentation.md)).
### Tests
- [ ] Component: `IndicatorPanel` renders value + state; `AiStockSummaryCard` shows grounding badge and the suppressed variant; **no** entry/target/SL element exists in the DOM.
- [ ] Visual regression: stock page (dark + light), levels slot = placeholder.
### Compliance gate
- [ ] No entry/target/SL anywhere (placeholder only); S/R framed historically; every AI number traces to evidence or the card is suppressed ([08 §5 acceptance](../08-screen-by-screen-documentation.md), [SPEC §6.6](../../SPEC.md)).
### Acceptance criteria
- [ ] Adjusted series so indicators are correct across splits/bonuses; grounded AI or suppression; states all present ([08 §5](../08-screen-by-screen-documentation.md)).

---

## Feature: V1 Screen — Sector dashboard `/sectors` & `/sectors/[slug]`  `(Mode A)`
**Objective:** Ranked sector strength + one-sector detail (constituents, breadth, leaders/laggards) — comparative/descriptive only. · **Backend dep:** `GET /sectors`, `/sectors/{id}/summary`. · **Frontend dep:** ISR. · **Data dep:** sector EOD + breadth. (Per-constituent endpoints land with later steps; V1 uses the summary payload's `constituents`.)
### Steps
- [ ] 1. `app/(market)/sectors/page.tsx` → `SectorHeatmap` + `SectorRankTable` (strength score, change_pct, breadth, rank) from `GET /sectors` ([08 §6](../08-screen-by-screen-documentation.md), [10 §3](../10-api-contracts.md)).
- [ ] 2. `app/(market)/sectors/[slug]/page.tsx` → `SectorHeader` (name, momentum rank), `SectorIndexChart` (ECharts/PriceChart), `ConstituentTable` (from `/sectors/{id}/summary` constituents), `SectorBreadthPanel`; `narrative` (descriptive, guardrail-checked) rendered with `NotAdviceBanner` ([08 §6](../08-screen-by-screen-documentation.md), [10 §3](../10-api-contracts.md)).
- [ ] 3. States: thin-sector note; per-panel error; skeletons; unknown slug → 404 ([05 §6](../05-information-architecture-and-url-paths.md)).
- [ ] 4. Animation: chart reveal once, table stagger; reduce-motion disables.
- [ ] 5. Analytics: `sector_view{slug}`, `constituent_open` ([08 §6](../08-screen-by-screen-documentation.md)).
### Tests
- [ ] Component: `SectorRankTable` renders ranked descriptive metrics; constituent click routes to `/stocks/[symbol]`.
- [ ] Visual regression: sector dashboard + detail.
### Compliance gate
- [ ] Comparative/descriptive only; leaders/laggards never framed as buy/sell ([08 §6 acceptance](../08-screen-by-screen-documentation.md)).
### Acceptance criteria
- [ ] Sector heat + detail render from EOD data with correct states and no advisory framing.

---

## Feature: Tests — component, visual-regression & E2E  `(Mode A)`
**Objective:** Prove the V1 surface renders correctly, stays visually stable, and delivers the M6 end-to-end flow. · **Backend dep:** running M5 API (or mocked). · **Frontend dep:** Vitest + Testing Library, Playwright ([06 §13](../06-frontend-architecture.md)). · **Data dep:** fixture payloads matching [10](../10-api-contracts.md).
### Steps
- [ ] 1. Component tests (Vitest + Testing Library) for `ScoreBadge`, `EvidenceDrawer`, `AiStockSummaryCard` (grounded + suppressed), `ScannerResultsTable`, `RaGatedPlaceholder`, `NotAdviceBanner`.
- [ ] 2. Visual-regression snapshots (Playwright) for market, scanner detail, stock detail, sector dashboard in **both** dark and light, and with `prefers-reduced-motion`.
- [ ] 3. **E2E (the M6 deliverable):** open `/scanners/momentum` → pick a stock → land on `/stocks/[symbol]` → assert visible indicators, the scanner score badge, and a grounded AI explanation with a grounding badge; assert **no** entry/target/SL element exists ([SPEC §12 M6](../../SPEC.md), [08 §5](../08-screen-by-screen-documentation.md)).
- [ ] 4. Reduce-motion E2E: with `prefers-reduced-motion: reduce`, assert final values render immediately (no count-up/line-reveal) ([07 §3.3](../07-design-system-and-ui-ux.md)).
- [ ] 5. Build-lint E2E: blocked-phrase lint fails the build on an introduced advisory string ([06 §13](../06-frontend-architecture.md)).
### Tests
- [ ] All component + visual-regression suites green; the pick-a-stock E2E passes.
### Compliance gate
- [ ] E2E asserts absence of entry/target/SL and presence of grounding + not-advice on AI output.
### Acceptance criteria
- [ ] CI runs component, visual-regression, and E2E; reduce-motion and blocked-phrase guards verified.

---

## Done-when
- [ ] `web/` scaffold, route groups, RSC/Client split, and state separation (Query=server, Zustand=UI) match [06](../06-frontend-architecture.md); design tokens + motion match [07](../07-design-system-and-ui-ux.md).
- [ ] Charts are lazy/client-only/token-driven and plot only API series; no client-side financial computation.
- [ ] Market dashboard, scanner directory + detail, stock detail (evidence drawer, **no levels**), and sector dashboard render with loading/error/empty/suppressed states and `NotAdviceBanner`.
- [ ] AI text is display-only, pre-verified, always grounding-badged + not-advice; RA-gated slots render `RaGatedPlaceholder`; build fails on any blocked phrase.
- [ ] Animations honor `prefers-reduced-motion` and never delay data legibility; WCAG 2.2 AA met on V1 routes.
- [ ] The M6 E2E passes: pick a stock → indicators, scanner score, grounded explanation ([SPEC §12 M6](../../SPEC.md)).
