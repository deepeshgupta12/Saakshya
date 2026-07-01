# Steps · 07 · V2 — Accounts, Watchlist, AI & News
> Read first: [SPEC.md](../../SPEC.md) · [Roadmap](../02-product-roadmap.md) · [Feature modules](../04-feature-modules.md) · [AI architecture](../14-ai-llm-agent-architecture.md) · [News & sentiment](../18-news-sentiment-and-corporate-actions.md) · [Security & auth](../23-security-auth-and-privacy.md) · [API contracts](../10-api-contracts.md) · [Screens](../08-screen-by-screen-documentation.md)

**Maps to:** Roadmap V2 · SPEC Phase 2
**Status:** Complete (2026-07-01) — Auth, IDOR suite, Watchlist (backend + frontend), OAuth stub (Google OIDC route + oauth_identities), AI brief, News pipeline (DB schema, RSS ingestor, entity resolver, heuristic sentiment, API endpoints, stock-page UI) all implemented. Finance-tuned ML sentiment classifier deferred to step 15.   |   **Regulatory mode:** A
**Prerequisites:** [04-ai-explanation-layer.md](04-ai-explanation-layer.md) · [05-api-and-pipeline.md](05-api-and-pipeline.md) · [06-frontend-foundation-and-v1-screens.md](06-frontend-foundation-and-v1-screens.md)

## Overview
V2 is the first user-personalization layer. It adds **user accounts + auth** (JWT/OAuth, RBAC, row-scoping), **watchlists** (multiple lists, items, scanner tags), the **AI stock summary** surfaced in-product, the **AI daily market brief** (event-reporting), and **news sentiment** (ingestion, entity resolution with a confidence threshold, finance-tuned sentiment, retained source links). Every AI surface here is **grounded → runtime-verified → guardrail-checked → audit-logged**; every news→symbol link carries a confidence score and is held below a surfacing threshold. Nothing in this phase is directive: the brief reports what entered/exited scanners and what to *monitor*, never a ranked "what to buy"; the "AI suggested watchlist" is **filter-based discovery**, never a per-user buy-lean.

The AI explanation engine, payload contract, runtime verifier, guardrail layer, and audit log are **built in step 04**; this phase *surfaces* them in the product and adds the news payloads they consume. Auth and entitlement plumbing built here is reused by every later phase (08+).

## Exit gate (Definition of Done)
- [ ] Email/password + OAuth signup/login issue short-lived JWT access + rotating refresh tokens; refresh-reuse detection self-revokes the token family ([23 §1](../23-security-auth-and-privacy.md)).
- [ ] Every user-owned read (watchlist, preferences) is row-scoped server-side; an IDOR test suite passes ([23 §2](../23-security-auth-and-privacy.md)).
- [ ] Watchlists support multiple lists with Free/Premium caps enforced at the gateway via `PLAN_REQUIRED` ([10 §6](../10-api-contracts.md)).
- [ ] AI stock summary + daily market brief served grounded, runtime-verified, guardrail-passed, and audit-logged; **suppressed (not guessed)** when critical inputs are missing ([14 §6](../14-ai-llm-agent-architecture.md)).
- [ ] AI verification harness **blocks fabricated numbers** in regression tests; daily brief contains **no ranked "what to buy"** ([02 §5](../02-product-roadmap.md)).
- [ ] News→symbol links carry confidence scores; below-threshold links are held in a review queue and **never surfaced or alerted on** ([18 §4](../18-news-sentiment-and-corporate-actions.md)).
- [ ] Finance-tuned sentiment beats a general-model baseline on the labelled Indian-market set ([18 §7](../18-news-sentiment-and-corporate-actions.md)).
- [ ] AI cost stays within the monthly ceiling at projected scale; summaries served from cache when signals unchanged ([14 §3](../14-ai-llm-agent-architecture.md)).
- [ ] Signup records the not-advice + AI-use acknowledgement ([08 §16](../08-screen-by-screen-documentation.md), [SPEC §6.7](../../SPEC.md)).

---
## Feature: User accounts & authentication  `(Mode A)`
**Objective:** Email/password + OAuth signup/login with JWT access + rotating refresh tokens, RBAC, per-user row-scoping, and tier entitlements — the auth foundation every later feature depends on.
**Backend dep:** auth service, token signing (RS256), refresh-rotation store, Argon2id hashing, RBAC middleware, tier-entitlement check · **Frontend dep:** `(auth)` route group, login/signup screens, OAuth buttons, session handling · **Data dep:** `users`, `refresh_tokens`, `oauth_identities`, `consents`, `user_preferences` tables.

### Steps
- [ ] 1. Create the auth data model: `users` (id, email unique, `password_hash`, `display_name`, `plan`, `created_at`), `refresh_tokens` (token family id, rotation chain, `revoked`, reuse-detection flag), `oauth_identities` (provider, subject, user_id), `consents` (user_id, `not_advice`, `ai_use_notice`, version, ts), `user_preferences` (risk_preference, followed_sectors[], layout). Migration in `app/storage/migrations/` (DuckDB local; Postgres prod schema mirrored).
- [ ] 2. Implement password handling in `app/auth/passwords.py`: Argon2id with per-user salt, ≥12-char minimum, HaveIBeenPwned k-anonymity breach check; never store plaintext/reversible ([23 §1](../23-security-auth-and-privacy.md)).
- [ ] 3. Implement token service in `app/auth/tokens.py`: RS256-signed JWT access (~15 min) carrying `user_id` + `plan` + scopes; rotating refresh tokens with family tracking and **reuse detection that revokes the family on replay** ([23 §1](../23-security-auth-and-privacy.md)).
- [ ] 4. Implement `POST /api/auth/register` (5/min/IP), `POST /api/auth/login` (10/min/IP), `POST /api/auth/refresh`, `POST /api/auth/logout` in `app/api/routes/auth.py`, exactly matching the bodies/responses in [10 §1](../10-api-contracts.md); login errors **must not leak account existence** ([08 §16](../08-screen-by-screen-documentation.md)).
- [ ] 5. Add OAuth 2.0 / OIDC social sign-in (Google) in `app/auth/oauth.py`; map provider subject → `oauth_identities` → user; first-login creates the account + consent record.
- [ ] 6. Implement RBAC + ownership middleware in `app/auth/authz.py`: `can(actor, action, resource)`; every user-owned object read/write is **ownership-checked server-side** (no IDOR); tier gating (`PLAN_REQUIRED`) is an authz check inside routes, not separate URLs ([23 §2](../23-security-auth-and-privacy.md)).
- [ ] 7. Record consents at signup (`not_advice`, `ai_use_notice`) with version + timestamp; surface acknowledgement UI on `/signup` and the AI-use notice plumbing for future Mode B ([SPEC §6.7](../../SPEC.md), [14 §11](../14-ai-llm-agent-architecture.md)).
- [ ] 8. Build login/signup screens per [08 §16](../08-screen-by-screen-documentation.md): centered card, OAuth buttons, `?next=` preserved, inline field/auth-error states, rate-limit messaging.
- [ ] 9. (Local-first) Auth/plan-gating may be stubbed per [10 §0](../10-api-contracts.md), but the envelope, `as_of`, `data_confidence`, and AI guardrail checks remain non-optional.

### Tests
- [ ] IDOR suite: user A cannot read/write any of user B's watchlists/preferences (403/404, never leak).
- [ ] A replayed refresh token revokes the whole token family; no endpoint accepts an unsigned/expired JWT.
- [ ] Passwords are Argon2id-hashed, breach-checked, and never logged; a known-breached password is rejected.
- [ ] `PLAN_REQUIRED` is returned (not a silent allow) when a Free user hits a Premium watchlist cap.
- [ ] Login with a wrong password and login with a nonexistent email return indistinguishable responses.

### Compliance gate
- [ ] Signup cannot complete without the not-advice + AI-use acknowledgement recorded ([SPEC §6.7](../../SPEC.md)).
- [ ] Portfolio/PII is never collected here beyond product need; consent records are retained ([23 §5](../23-security-auth-and-privacy.md)).

### Acceptance criteria
- [ ] Tokens are short-lived + revocable; stolen refresh token is detectable and self-revoking ([23 §1](../23-security-auth-and-privacy.md)).
- [ ] Every user data read is row-scoped; admin actions resolve through the RBAC matrix at runtime ([23 §2](../23-security-auth-and-privacy.md)).

---
## Feature: Watchlists  `(Mode A)`
**Objective:** Multiple named watchlists per user, with items hydrated by per-item EOD indicators, scanner-membership tags, and risk flags; Free=1 list, Premium=unlimited. "Suggested watchlist" is **filter-based discovery**, never a per-user buy-lean.
**Backend dep:** watchlist store, per-item indicator/scanner-tag hydration, tier-cap enforcement · **Frontend dep:** `WatchlistTabs`, `WatchlistTable`, `AddSymbolDialog` ([08 §8](../08-screen-by-screen-documentation.md)) · **Data dep:** `watchlists`, `watchlist_items`; reads V1 indicators + scanner memberships ([13](../14-ai-llm-agent-architecture.md) shares the scanner layer).

### Steps
- [ ] 1. Create `watchlists` (id, user_id, name unique-per-user, created_at) and `watchlist_items` (watchlist_id, symbol, added_at) tables; enforce per-user name uniqueness.
- [ ] 2. Implement the watchlist API in `app/api/routes/watchlists.py` exactly per [10 §6](../10-api-contracts.md): `GET/POST /api/watchlists`, `GET/PUT/DELETE /api/watchlists/{id}`, `POST /api/watchlists/{id}/items`, `DELETE /api/watchlists/{id}/items/{symbol}`. Return `409 CONFLICT` on dup name / already-present item; `403 PLAN_REQUIRED` on Free list/item cap.
- [ ] 3. Hydrate each item on read with EOD `change_pct`, score, scanner-membership tags, and risk flag from the V1 scanner/indicator outputs (no new market math — reuse [05](05-api-and-pipeline.md) outputs).
- [ ] 4. Enforce tier caps server-side in the authz layer: Free = 1 list / capped items; Premium = unlimited ([08 §8](../08-screen-by-screen-documentation.md)).
- [ ] 5. Build the watchlist screen per [08 §8](../08-screen-by-screen-documentation.md): tabs for multiple lists, optimistic add with confirmation pulse + toast, empty-state symbol search, skeleton rows, upgrade gate on cap.
- [ ] 6. "Suggested watchlist" (if shown) is a **filter-derived list** (e.g. followed-sector + scanner membership), labelled as discovery; it must **not** be framed as per-user recommendations ([04 §14](../04-feature-modules.md), [SPEC §4](../../SPEC.md)).

### Tests
- [ ] Free user is blocked at the second list with `PLAN_REQUIRED`; Premium user is not.
- [ ] Adding a duplicate symbol to a list returns `409`; the list is unchanged.
- [ ] Item hydration reflects the current as-of scanner membership and risk flag.
- [ ] A user cannot mutate another user's watchlist (row-scope test).

### Compliance gate
- [ ] No watchlist surface (including "suggested") contains buy/sell, target/SL, or "candidate" buy-lean wording — copy reviewed against the blocked-phrase list ([SPEC §5](../../SPEC.md)).
- [ ] Scanner tags on items use membership language ("appears in the momentum scanner"), not directives.

### Acceptance criteria
- [ ] Tier limits enforced with an upgrade gate; "AI suggested watchlist" is filter-based discovery, never per-user buy-leans ([08 §8](../08-screen-by-screen-documentation.md)).

---
## Feature: AI stock summary (surfaced)  `(Mode A)`
**Objective:** Surface the grounded, runtime-verified AI stock summary on the stock page and via the AI namespace, served from cache when signals are unchanged, suppressed (not guessed) when inputs are missing.
**Backend dep:** Stock Research Agent + payload builder + runtime verifier + guardrail + audit log (all from [04](04-ai-explanation-layer.md)/[14 §5.2](../14-ai-llm-agent-architecture.md)); regenerate-on-change cache · **Frontend dep:** `AiStockSummaryCard` + `EvidenceDrawer` ([08 §5](../08-screen-by-screen-documentation.md)) · **Data dep:** structured payload from indicators/scanners/risk + entity-resolved news (this phase's news feature).

### Steps
- [ ] 1. Wire `GET /api/stocks/{symbol}/ai-summary` and its alias `GET /api/ai/stock-summary/{symbol}` in `app/api/routes/ai.py` to the Stock Research Agent, returning the exact shape in [10 §4](../10-api-contracts.md): `summary`, `evidence[]`, `model_version`, `audit_id`, `disclaimer`.
- [ ] 2. Build the payload via the structured contract ([14 §4](../14-ai-llm-agent-architecture.md)): the model receives **only** `computed`/`signalTags`/`riskFlags`/`newsSummaries`; no forward price/target/stop exists upstream to pass.
- [ ] 3. Enforce regenerate-on-change caching: re-summarize only when the stock's signal *category* changes; otherwise serve cache (`eod` TTL keyed by as-of) ([14 §3](../14-ai-llm-agent-architecture.md), [SPEC §6.8](../../SPEC.md)).
- [ ] 4. On `data_confidence: LOW` or a missing critical field, return `422 DATA_SUPPRESSED` — **suppress, don't guess** ([14 §12](../14-ai-llm-agent-architecture.md)).
- [ ] 5. Drop directive tails at the agent guardrail ("…before fresh action" → "…is a level to watch"); no entry/target/SL ([14 §10](../14-ai-llm-agent-architecture.md)).
- [ ] 6. Render `AiStockSummaryCard` with as-of stamp, confidence badge, grounding badge + "View evidence" drawer, and the "Not investment advice" footer ([08 §5](../08-screen-by-screen-documentation.md)).

### Tests
- [ ] A fabricated number injected into the model output is caught by the runtime verifier → regenerate → suppress ([14 §6](../14-ai-llm-agent-architecture.md)).
- [ ] Injecting "sell"/"target"/"buy now" into output is blocked by the guardrail; the request never reaches the user.
- [ ] When a critical input is missing, the endpoint returns `422 DATA_SUPPRESSED`, never a guessed value.
- [ ] Unchanged signals serve a cached summary (no new LLM spend); a category change triggers regeneration.

### Compliance gate
- [ ] Every number in the summary traces to a payload field via the evidence list; outputs failing grounding are blocked ([SPEC §6.6](../../SPEC.md)).
- [ ] Banned phrases blocked at **output time**; every generation writes an audit-log row with prompt id/version, payload hash, model id, grounding report ([14 §7](../14-ai-llm-agent-architecture.md)).

### Acceptance criteria
- [ ] Every AI response carries `audit_id` + `model_version`; descriptive, grounded, suppressed-not-guessed on missing inputs ([10 §14](../10-api-contracts.md)).

---
## Feature: AI daily market brief  `(Mode A)`
**Objective:** A descriptive, event-reporting morning brief — indices, breadth, sector leaders/laggards, scanner entries/exits, and what to *monitor* — never a ranked "what to buy".
**Backend dep:** Market Brief Agent (premium tier) over breadth + sector scores + scanner deltas; overnight latency budget; non-AI fallback digest · **Frontend dep:** `DailyBriefCard` on `/dashboard` + brief page ([08 §18](../08-screen-by-screen-documentation.md)) · **Data dep:** overnight EOD pipeline outputs (indices, breadth, sector strength, scanner entry/exit deltas).

### Steps
- [ ] 1. Implement `GET /api/ai/market-brief` in `app/api/routes/ai.py` per [10 §9](../10-api-contracts.md), returning `{ date, brief, audit_id }`, `eod`-cached.
- [ ] 2. Build the Market Brief Agent ([14 §5.1](../14-ai-llm-agent-architecture.md)) over `get_market_breadth`, `get_sector_scores`, `get_scanner_deltas`; output schema with `toMonitor[]` event-framed, never "to buy".
- [ ] 3. Frame all movers as scanner-membership events — "stocks that entered/exited the momentum scanner today" — not actionable picks ([SPEC §5](../../SPEC.md)).
- [ ] 4. Run generation inside the overnight window (latency budget); on failure, serve the **non-AI templated digest** fallback ([14 §3](../14-ai-llm-agent-architecture.md), [04 §18](../04-feature-modules.md)).
- [ ] 5. Render `DailyBriefCard` (followed-sectors emphasized — navigation personalization only) with brief evidence drill-in and "Not investment advice" ([08 §18](../08-screen-by-screen-documentation.md)).

### Tests
- [ ] Golden-dataset regression: the brief never emits a ranked "what to buy" / "buy/sell next session"; directive phrasing is rejected ([14 §8](../14-ai-llm-agent-architecture.md)).
- [ ] Breadth/sector numbers in the brief all trace to the payload; an invented breadth number is blocked.
- [ ] On generation failure, the non-AI digest is served (never a fabricated brief).

### Compliance gate
- [ ] Brief reports events + what to monitor only; passes the Compliance Review Agent before display ([14 §5.8](../14-ai-llm-agent-architecture.md)).
- [ ] Personalization in the brief is navigation-only (which sectors to emphasize), never per-stock suggestions ([SPEC §7](../../SPEC.md)).

### Acceptance criteria
- [ ] Daily brief reports events + monitoring only; all figures traceable; carries an `audit_id` ([08 §18](../08-screen-by-screen-documentation.md)).

---
## Feature: News sentiment (ingestion → resolution → sentiment → surface)  `(Mode A)`
**Objective:** Ingest finance news, deduplicate, resolve each item to a listed symbol with a **confidence score + surfacing threshold**, classify with a **finance-tuned** sentiment model, score impact, and surface only above-threshold items with retained source links + timestamps — never exaggerating impact, never a buy/sell signal.
**Backend dep:** ingestion workers, dedup clustering, entity resolver, finance-tuned classifiers, impact scorer, News Impact Agent summarizer, as-of versioned store · **Frontend dep:** `NewsFeed`/`NewsCard` with `SentimentChip` + confidence + source link ([08 §14](../08-screen-by-screen-documentation.md)) · **Data dep:** source registry, curated symbol-alias + corporate-hierarchy map, sector map, labelled Indian-market evaluation set.

### Steps
- [ ] 1. Build the source registry (`src_*`: type, reliability, `redistribution_reviewed`) and the normalized `news_item` store (title, body, url, source_id, publish_ts, ingest_ts, `as_of_version`) per [18 §2](../18-news-sentiment-and-corporate-actions.md).
- [ ] 2. Implement near-duplicate clustering **before** resolution; pick one canonical item per cluster by source reliability + earliest credible timestamp; retain all member source links ([18 §3](../18-news-sentiment-and-corporate-actions.md)).
- [ ] 3. Build the curated **symbol-alias + corporate-hierarchy map** (`ent_*`: primary_symbol, aliases, listed_instruments, parent/subsidiaries, ticker-change history, sector) and the weighted-signal entity resolver producing `link_confidence ∈ [0,1]` ([18 §4.1–4.2](../18-news-sentiment-and-corporate-actions.md)).
- [ ] 4. Enforce the **surfacing threshold** (`SURFACING_THRESHOLD`, versioned config, e.g. 0.75): below-threshold links go to a **review queue**, never surfaced or alerted on; above-threshold links carry confidence for display/debug ([18 §4.2](../18-news-sentiment-and-corporate-actions.md)).
- [ ] 5. Implement category classification (results/order-win/M&A/dividend/bonus/split/buyback/…) feeding impact priors and (for corp-action categories) the corporate-action feed ([18 §6](../18-news-sentiment-and-corporate-actions.md)).
- [ ] 6. Build the **finance-tuned** sentiment classifier (positive/neutral/negative + confidence) evaluated against the labelled Indian-market set with a golden dataset + regression suite; it must handle finance framing ("misses estimates, stock rallies" is not a clean negative) ([18 §7.1](../18-news-sentiment-and-corporate-actions.md)).
- [ ] 7. Compute `impact ∈ [0,1]` = category_prior × source_reliability × magnitude × link_confidence; impact feeds news risk in the portfolio engine (consumed in [08-v3-portfolio-risk-alerts.md](08-v3-portfolio-risk-alerts.md)) and news alerts — a **measurement, never a return prediction** ([18 §7.2](../18-news-sentiment-and-corporate-actions.md)).
- [ ] 8. Summarize with the News Impact Agent ([14 §5.4](../14-ai-llm-agent-architecture.md)) under the payload contract: classification language only, source link + timestamp retained, no added facts, runtime-verified, guardrail-checked, no impact exaggeration ([18 §8](../18-news-sentiment-and-corporate-actions.md)).
- [ ] 9. Implement `GET /api/news`, `GET /api/stocks/{symbol}/news` (Premium), `GET /api/news/announcements` per [10 §4/§10](../10-api-contracts.md); below-threshold links are not returned.
- [ ] 10. Build `/news` + the per-stock news panel per [08 §14](../08-screen-by-screen-documentation.md): headline, source link, timestamp, `SentimentChip` + confidence, linked symbols above threshold.

### Tests
- [ ] A subsidiary-only headline (e.g. "JLR posts record sales") resolves below threshold and is **not** surfaced ([18 §4.3](../18-news-sentiment-and-corporate-actions.md)).
- [ ] An exact-name headline resolves above threshold and is surfaced with confidence; an ambiguous shared name is held until disambiguated.
- [ ] Three wire reports of one earnings release collapse into one cluster with three retained source links and one canonical summary.
- [ ] The finance-tuned classifier beats a general-model baseline on the labelled set; "misses estimates, stock rallies" is not auto-tagged a clean signal; low-confidence sentiment shows as neutral/uncertain.
- [ ] A summary referencing a number not in the payload is blocked/regenerated; an injected exaggeration ("set to surge") is caught by the guardrail.

### Compliance gate
- [ ] Sentiment is shown as a **classification** ("classified positive"), never "buy on this news"; impact is never framed as a return prediction ([SPEC §6.4](../../SPEC.md)).
- [ ] Every surfaced item retains a source link + publish timestamp; below-threshold items never reach a user surface or an alert ([18 §0–1](../18-news-sentiment-and-corporate-actions.md)).
- [ ] Prompt-injection safety: the summarizer references only the structured payload; injected directives in news text cannot ground ([23 §8](../23-security-auth-and-privacy.md)).

### Acceptance criteria
- [ ] News→symbol links carry confidence + source; finance-tuned sentiment beats baseline; impact not exaggerated; below-threshold links not surfaced ([08 §14](../08-screen-by-screen-documentation.md), [02 §5](../02-product-roadmap.md)).

---
## Done-when
- [ ] All five features pass their tests, compliance gates, and acceptance criteria; the Exit gate checklist is fully checked.
- [ ] The AI verification harness blocks fabricated numbers across the stock-summary, brief, and news-summary regression suites ([02 §5](../02-product-roadmap.md)).
- [ ] AI cost is within the monthly ceiling at projected scale; summaries serve from cache when signals are unchanged ([SPEC §6.8](../../SPEC.md)).
- [ ] No surface in this phase renders entry/target/SL, a "candidate" buy-lean, a ranked "what to buy", or any always-prohibited phrase; RA-gated slots show `RaGatedPlaceholder` ([08 §20](../08-screen-by-screen-documentation.md)).
- [ ] Auth/RBAC/row-scoping, consent records, and the AI audit log are in place for reuse by [08-v3-portfolio-risk-alerts.md](08-v3-portfolio-risk-alerts.md) and later phases.
