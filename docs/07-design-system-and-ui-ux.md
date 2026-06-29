# 07 — Design System & UI/UX

> One-line purpose: The complete visual language of Saakshya — premium, AI-native, evidence-led, dark-first — with concrete tokens, component styles, and motion rules.
> Read first: [SPEC.md](../SPEC.md)

Related: [Frontend Architecture](06-frontend-architecture.md) · [Screen-by-Screen](08-screen-by-screen-documentation.md) · [IA & URL Paths](05-information-architecture-and-url-paths.md) · [Compliance & Guardrails](21-compliance-risk-and-guardrails.md)

> **Design tooling — use the `ui-ux-pro-max` skill.** For all UI/visual work on Saakshya (page & component design; style / color-palette / typography / font-pairing decisions; **3D / Three.js** hero and data-viz; UI-code review), use the installed **`ui-ux-pro-max`** skill (in `.claude/skills/`). It ships companions: `ui-styling` (Tailwind + shadcn/ui), `design-system` (token architecture), `brand`, `banner-design`, `slides`. These are git-ignored installed tooling — reinstall with `npx -y ui-ux-pro-max-cli@latest init --ai claude`. **Its output is advisory and must still conform to the tokens, motion rules, and Mode-A evidence-led constraints in this document and [SPEC.md](../SPEC.md):** no buy-lean / urgency styling, color is descriptive of state (never a call to act), and `prefers-reduced-motion` is always honored.

---

## 0. Design principles

1. **Evidence-led, not hype-led.** The UI's job is to make data *trustworthy and legible*. Every signal is visually tied to its evidence (badge → evidence drawer). No persuasive "buy this" styling — no green "GO" buttons next to stocks, no urgency banners. Seriousness over flash.
2. **Premium & AI-native.** Deep, calm dark surfaces; glass accents; intelligent summary cards; smooth, restrained motion. It should feel like a high-end terminal, not a tips app.
3. **Dark-first, light optional.** Default theme is dark (reduces eye strain for data-dense, long sessions); a fully-supported light mode uses the same semantic tokens.
4. **Financial seriousness constrains delight.** Motion and color must never reduce readability, imply a recommendation, or signal certainty. Bullish/bearish color is descriptive of *state*, never a *call to act*.
5. **Color is never the only signal** (accessibility + SPEC neutrality): always pair with sign, icon, or label.

---

## 1. Design tokens

Tokens are CSS variables under `:root` (dark default) and `[data-theme="light"]`, surfaced to Tailwind via `tailwind.config.ts`. Components reference **semantic** tokens, never raw values.

### 1.1 Color — surfaces (dark-first)

| Token | Dark value | Light value | Use |
|---|---|---|---|
| `--surface-base` | `#070B14` (near-black navy) | `#F7F9FC` | App background |
| `--surface-1` | `#0B1220` (deep navy) | `#FFFFFF` | Primary cards |
| `--surface-2` | `#111A2E` (graphite-navy) | `#F1F4FA` | Nested cards, table header |
| `--surface-3` | `#18243C` | `#E7ECF5` | Hover, raised |
| `--surface-glass` | `rgba(17,26,46,0.6)` | `rgba(255,255,255,0.6)` | Glass panels (with blur) |
| `--border-subtle` | `rgba(255,255,255,0.08)` | `rgba(15,23,42,0.08)` | Hairline borders |
| `--border-strong` | `rgba(255,255,255,0.16)` | `rgba(15,23,42,0.16)` | Emphasis borders |

### 1.2 Color — text

| Token | Dark | Light | Use |
|---|---|---|---|
| `--text-primary` | `#E6EDF7` | `#0B1220` | Primary text |
| `--text-secondary` | `#9FB0C9` | `#475569` | Secondary/labels |
| `--text-muted` | `#6B7C99` | `#7A8699` | Hints, captions |
| `--text-inverse` | `#0B1220` | `#FFFFFF` | On accent fills |

All pairings verified ≥ **4.5:1** on their intended surface (≥ 3:1 for large text / UI).

### 1.3 Color — semantic / market

| Token | Dark | Light | Meaning (descriptive only) |
|---|---|---|---|
| `--accent` | `#5B8DEF` (electric indigo-blue) | `#3B6FE0` | Brand, primary actions, AI |
| `--accent-strong` | `#7AA2FF` | `#2B5BD6` | Active/hover accent |
| `--bullish` | `#2FBF71` (calm green) | `#15924E` | Price up / positive state |
| `--bearish` | `#E5484D` (muted red) | `#C62B30` | Price down / negative state |
| `--neutral` | `#8B98AD` | `#64748B` | Unchanged / no signal |
| `--warning` | `#E8A33D` (amber) | `#B9791A` | Elevated risk / caution |
| `--info` | `#46B4C7` | `#1E8AA0` | Informational |
| `--ai` | `#9A7BFF` (violet) | `#6D4DE6` | AI-generated content accent |

> Greens/reds are **desaturated** vs. typical trading apps — descriptive state, not an excited buy/sell signal (SPEC §3). Risk uses amber, distinct from bearish red.

### 1.4 Typography

Font: **Inter** (UI) + **IBM Plex Mono / JetBrains Mono** (numeric/tabular). Tabular figures (`font-variant-numeric: tabular-nums`) for all prices/metrics so columns align.

| Token | Size / line-height | Use |
|---|---|---|
| `--text-display` | 40 / 48, 700 | Landing hero |
| `--text-h1` | 30 / 38, 700 | Page title |
| `--text-h2` | 24 / 32, 600 | Section |
| `--text-h3` | 20 / 28, 600 | Card title |
| `--text-body-lg` | 16 / 24, 400 | Body |
| `--text-body` | 14 / 22, 400 | Default UI |
| `--text-sm` | 13 / 20, 400 | Secondary |
| `--text-xs` | 12 / 16, 500 | Labels, chips |
| `--text-mono` | 13 / 20, mono | Prices, metrics, code |

### 1.5 Spacing scale (4px base)

`--space-0 0 · 1 4 · 2 8 · 3 12 · 4 16 · 5 20 · 6 24 · 8 32 · 10 40 · 12 48 · 16 64`. Component padding and grid gaps use these only.

### 1.6 Radii

| Token | Value | Use |
|---|---|---|
| `--radius-sm` | 6px | Chips, badges, inputs |
| `--radius-md` | 10px | Buttons |
| `--radius-lg` | 14px | Cards |
| `--radius-xl` | 20px | Panels, modals, sheets |
| `--radius-full` | 9999px | Pills, avatars |

### 1.7 Elevation (shadows + glass)

Dark theme leans on **borders + subtle glow** more than drop shadows.

| Token | Value | Use |
|---|---|---|
| `--elev-0` | none | Flat |
| `--elev-1` | `0 1px 2px rgba(0,0,0,.4)` | Cards |
| `--elev-2` | `0 4px 16px rgba(0,0,0,.45)` | Raised, dropdowns |
| `--elev-3` | `0 12px 40px rgba(0,0,0,.55)` | Modals, command palette |
| `--glow-accent` | `0 0 0 1px var(--accent), 0 0 24px rgba(91,141,239,.25)` | Focused/active accent |
| `--glow-risk` | `0 0 0 1px var(--warning), 0 0 18px rgba(232,163,61,.20)` | Risk-pulse (subtle) |

### 1.8 Z-index, blur, motion tokens

`--z-base 0 · --z-sticky 100 · --z-drawer 200 · --z-modal 300 · --z-palette 400 · --z-toast 500`. Glass blur `--blur-glass: 16px`. Motion tokens in [§3](#3-motion--framer-motion).

---

## 2. Component & surface styles

### 2.1 Glassmorphism rules
Use **sparingly**, on overlay surfaces only (command palette, top nav on scroll, AI summary header, evidence drawer header): `background: var(--surface-glass); backdrop-filter: blur(var(--blur-glass)); border: 1px solid var(--border-subtle)`. **Never** on dense data tables or chart panels (hurts legibility). Always provide a solid fallback where backdrop-filter is unsupported.

### 2.2 Cards
`--surface-1`, `--radius-lg`, `--border-subtle`, `--elev-1`, padding `--space-5/6`. Header row: title (`h3`) + optional meta/badge + optional kebab. Hover lifts to `--surface-3` + `--elev-2` only when interactive. AI cards get an `--ai` left-accent rule + grounding badge.

### 2.3 Chart styles
Dark grid `rgba(255,255,255,.06)`; axis text `--text-muted`; candles `--bullish`/`--bearish`; MAs use `--accent` + tints; volume bars at 40% opacity. Crosshair `--text-secondary`. No gradient fills under price by default (avoids hype); soft area only for index sparklines. ECharts heatmaps use a perceptually-uniform bullish↔neutral↔bearish ramp.

### 2.4 Score badge
Round-rect pill, `--radius-sm`, mono numerals, 0–100. Band → color: **0–39** `--bearish` tint, **40–59** `--neutral`, **60–79** `--accent` tint, **80–100** `--bullish` tint, with a tiny band label (e.g. "High"). Always shows the numeric score (color is secondary). Clicking opens the **evidence drawer**. **No "buy strength" wording** — it's a measurement of the scanner score (validated, SPEC §6.5).

### 2.5 Data tables
`--surface-1` body, `--surface-2` sticky header, hairline row borders, `--space-3` cell padding, tabular-nums, right-aligned numerics. Row hover `--surface-3`. Sortable headers with caret. Up/down cells colored **and** signed (`+1.2%` green, `−0.8%` red). Virtualized for long lists; responsive → stacked cards on mobile ([06 §9](06-frontend-architecture.md)). Risk-flag column uses an amber chip.

### 2.6 Empty states
Centered illustration/glyph + one-line explanation + single primary action (e.g. "Add your first symbol"). Calm, never alarming. Distinct copy per surface ([08](08-screen-by-screen-documentation.md)).

### 2.7 AI cards & grounding
AI summary cards: `--ai` accent, "AI" chip, **grounding badge** ("Grounded in this stock's signals · not investment advice"), and a "View evidence" link that opens the evidence drawer listing every figure → source. Suppressed state: "Summary unavailable — required inputs missing" (SPEC §6.2). Never styled as a directive call-to-action.

### 2.8 Evidence drawer
Right-side drawer (desktop) / bottom sheet (mobile). Header (glass), then a list mapping each claim/number in the card to its source metric, scanner tag, value, and as-of date. This is the literal embodiment of "Saakshya = evidence." Slide-in animation per [§3](#3-motion--framer-motion).

### 2.9 Command palette
`Cmd/Ctrl+K`. Centered glass modal, `--elev-3`, fuzzy search across symbols, sectors, scanners, pages, actions. Keyboard-first; grouped results; recent + suggestions. Symbol results show last price + %chg (descriptive).

### 2.10 Modals, bottom sheets, filter panels
Modals: `--surface-1`, `--radius-xl`, `--elev-3`, focus-trapped, `Esc` to close, scrim `rgba(0,0,0,.6)`. Bottom sheets (mobile) for drawers/filters/actions, drag-to-dismiss. Filter panels: left rail (desktop) / sheet (mobile); chips for active filters; "reset" + result count; never offer a "best stocks" preset.

### 2.11 Badges, chips, banners
Reason chips (scanner): `--surface-2`, `--text-secondary`, icon + descriptive phrase ("above 50-DMA", "volume 2× 20-day avg"). Risk flag chip: amber. `NotAdviceBanner`: subtle, persistent on AI/scanner/portfolio surfaces. `RaGatedPlaceholder`: muted card, lock glyph, "Available with Research Analyst registration" — never an empty target/SL widget.

### 2.12 Responsive breakpoints

| Token | Min width | Layout shift |
|---|---|---|
| `sm` | 640 | Single → 2-col cards |
| `md` | 768 | Show secondary columns |
| `lg` | 1024 | Sidebar app shell, side drawers |
| `xl` | 1280 | Wider chart + side panel |
| `2xl` | 1536 | Max content 1440, multi-pane dashboards |

---

## 3. Motion — Framer Motion

Motion is **modern and polished but disciplined**: it guides attention and signals data freshness without harming readability, performance, or the product's financial seriousness. **Animation never delays a user reading a number, never implies certainty or a recommendation, and never loops in a way that nags.**

### 3.1 Global timing & easing tokens

| Token | Value | Use |
|---|---|---|
| `--motion-fast` | 120ms | Hover, press, chips |
| `--motion-base` | 200ms | Most enters/exits, fades |
| `--motion-slow` | 320ms | Drawers, sheets, page transitions |
| `--ease-standard` | `cubic-bezier(0.2,0,0,1)` | Default enter |
| `--ease-exit` | `cubic-bezier(0.4,0,1,1)` | Exits |
| `--ease-emphasis` | `cubic-bezier(0.2,0.8,0.2,1)` | Reveals, count-ups |

Defaults: opacity + small (4–12px) translate/scale. **No large bounces, no parallax, no confetti.** Spring only for drawers/sheets (gentle, low overshoot).

### 3.2 Specific animations

| Interaction | Behavior | Timing / easing |
|---|---|---|
| **Page transition** | Cross-fade + 8px upward settle on route change | `--motion-base`, `--ease-standard` |
| **Scanner row transition** | Staggered fade/slide-in (stagger 20–30ms, cap total ~300ms); rows that newly entered the scanner since last run get a one-time subtle accent flash | `--motion-base` |
| **Chart line reveal** | Price/MA line draws in left→right on first load only | `--motion-slow`, `--ease-emphasis`; **disabled** on reduce-motion & on data refresh |
| **Score count-up** | 0→value tween on first reveal; respects band color | 600ms ease-out, **once** |
| **AI summary reveal** | Card fades in; text reveals as a single block (no typewriter on financial text — avoids implying live "thinking") | `--motion-base`, `--ease-emphasis` |
| **Evidence drawer slide-in** | Slide from right (desktop) / up (mobile) with scrim fade | `--motion-slow`, gentle spring |
| **Sector heatmap tiles** | Tiles fade + scale 0.96→1 with positional stagger on first paint; color transitions tween on data change | `--motion-base` |
| **Watchlist-add confirmation** | Inline check pulse + toast; row settles into list | `--motion-fast`/`--motion-base` |
| **Alert-creation confirmation** | Button → check morph + toast "Alert set (EOD)" | `--motion-base` |
| **Risk pulse** | Very subtle one-shot amber `--glow-risk` pulse when a risk flag first appears; **does not loop**; calm, never alarmist | 800ms, single, ease-out |

### 3.3 Reduce-motion rule (mandatory)
When `prefers-reduced-motion: reduce` (or the user's preference override): **all** non-essential motion is disabled — no line-reveal, no count-up (show final value immediately), no stagger, no risk pulse, no slide (drawers appear with a simple opacity change). Use Framer Motion's `useReducedMotion()` and a shared `motion/` variants module so every animated component honors it consistently. Essential feedback (focus rings, toasts) remains but instant.

### 3.4 Performance guardrails
Animate only `transform`/`opacity` (GPU-friendly); never animate layout/`width`/`top` on large lists. Cap simultaneous animations; charts disable animation on background refresh. Motion must not push LCP/INP past targets in [06 §12](06-frontend-architecture.md).

---

## 4. Theming & implementation

- Tokens in `src/styles/tokens.css` (`:root` dark, `[data-theme="light"]`), exposed to Tailwind as semantic utilities (`bg-surface-1`, `text-secondary`, `text-bullish`). Components use semantic classes only.
- Theme toggle persists to Zustand+`localStorage` ([06 §4](06-frontend-architecture.md)); SSR reads cookie to avoid flash; `color-scheme` set for native controls.
- Charts read the same tokens at runtime so theme switches recolor charts.
- Shadcn UI primitives are restyled to these tokens (the "custom design system" over Shadcn).

---

## 5. Acceptance criteria

- **Frontend dependency:** All components consume semantic tokens (no raw hex/px); `ui/` primitives implement the styles in [§2](#2-component--surface-styles); motion uses the shared variants + tokens in [§3](#3-motion--framer-motion).
- **Data dependency:** Score badges, market colors, and risk flags map from API values to tokens; the UI never invents a score, color-implied call, or risk level absent from the payload.
- **Accessibility:** Token pairings meet WCAG 2.2 AA contrast; bullish/bearish/neutral/warning always carry a non-color signal; `prefers-reduced-motion` fully disables non-essential motion.
- **Compliance:** No styling frames a stock as a buy/sell action; RA-gated slots render `RaGatedPlaceholder`; AI cards always show grounding + not-advice; no urgency/guarantee styling anywhere (SPEC §3, §6.9).
- **Performance:** Animations are transform/opacity only, time-boxed per [§3.1](#31-global-timing--easing-tokens), and never delay rendering of data values or breach CWV targets.
