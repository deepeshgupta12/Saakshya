# Steps · 17 · Corporate announcements

> Read first: [SPEC.md](../../SPEC.md) (§6.1 corp-action master, §6.4 entity resolution, §6.6 grounding, §3/§5 Mode-A language, §3.3 always-prohibited) · [Roadmap](../02-product-roadmap.md) (V2–V3 / Phase 2–3) · [News & corporate actions](../18-news-sentiment-and-corporate-actions.md) (§6, §9) · [Data ingestion](../12-data-ingestion-and-market-data.md) (§5 corp-action adjust) · [Feature modules](../04-feature-modules.md) (§13) · [API contracts](../10-api-contracts.md) · [Database](../11-database-architecture.md)

**Maps to:** Roadmap V2–V3 · SPEC Phase 2–3
**Status:** Not started   |   **Regulatory mode:** A
**Prerequisites:** [01-local-mvp-foundation.md](01-local-mvp-foundation.md) (DataSource adapter, `corporate_actions` master, corp-action adjuster) · [04-ai-explanation-layer.md](04-ai-explanation-layer.md) (payload contract, runtime verifier, guardrails, audit log) · [05-api-and-pipeline.md](05-api-and-pipeline.md) (pipeline + envelope) · [07-v2-accounts-watchlist-ai-news.md](07-v2-accounts-watchlist-ai-news.md) (news pipeline, entity resolver, sentiment — this module is **distinct from** but reuses it)

## Overview
This module ingests **exchange corporate announcements** (board meetings, results, dividends, bonus, splits, rights, buybacks, fundraising, rating updates, pledging, shareholding changes, large orders, acquisitions, regulatory notices), classifies them, resolves each to a listed symbol, produces a **plain-language AI summary that does not exaggerate impact**, and — for action-bearing types — emits **structured corporate-action events into the `corporate_actions` master** that drives price adjustment ([18 §9](../18-news-sentiment-and-corporate-actions.md), [01](01-local-mvp-foundation.md)).

It is **distinct from news sentiment** ([07](07-v2-accounts-watchlist-ai-news.md), [18 §1–8](../18-news-sentiment-and-corporate-actions.md)): news sentiment classifies wire/curated coverage and assigns a finance-tuned sentiment; corporate announcements are the **issuer's own exchange filings** — the authoritative, highest-reliability source (`exchange_filing`, [18 §2.1](../18-news-sentiment-and-corporate-actions.md)). The two share the entity resolver and the summarizer guardrails but have separate ingestion, separate category semantics, and one extra responsibility: **feeding the adjustment engine**. That feed is **first-class correctness** ([SPEC §6.1](../../SPEC.md)) — a missed bonus/split silently corrupts every indicator, scanner, and backtest.

**The two non-negotiables here:** (1) the AI **summarizes without exaggerating impact** ("a bonus issue was announced; record date 14 Jul" — never "buy before the bonus for guaranteed gains"), retains **source links + timestamps**, and invents nothing ([18 §8](../18-news-sentiment-and-corporate-actions.md), [SPEC §6.6](../../SPEC.md)); (2) a corporate-action event extracted from an announcement is **provisional until reconciled against a second source** ([SPEC §6.1](../../SPEC.md)) and **does not alter the adjusted price series** until reconciled.

## Exit gate (Definition of Done)
- [ ] Exchange announcements ingest behind the `DataSource` adapter, normalize to the canonical announcement record, and dedup against the news store (no double-surfacing of the same event) ([12 §3](../12-data-ingestion-and-market-data.md), [18 §3](../18-news-sentiment-and-corporate-actions.md)).
- [ ] Every announcement resolves to a symbol with a confidence ≥ the surfacing threshold or is held in the review queue — never surfaced below threshold ([18 §4.2](../18-news-sentiment-and-corporate-actions.md)).
- [ ] A dividend/split/bonus/buyback/rights/M&A announcement produces a **structured `corporate_actions` record** linked to its `source_announcement_id`, `confidence`, and `reconciled=false` ([18 §9](../18-news-sentiment-and-corporate-actions.md)).
- [ ] An **unreconciled** corp-action event surfaces as an announcement but **does not adjust** the price series; a reconciled split/bonus correctly triggers back-adjustment downstream ([SPEC §6.1](../../SPEC.md), [12 §5](../12-data-ingestion-and-market-data.md)).
- [ ] Every AI announcement summary is runtime-verified (no invented numbers), passes the blocked-phrase guardrail at output time, and retains source link + publish timestamp ([18 §8](../18-news-sentiment-and-corporate-actions.md), [SPEC §6.6](../../SPEC.md)).
- [ ] No announcement summary, label, or chip contains a buy/sell directive or any always-prohibited phrase ([SPEC §3.3](../../SPEC.md)).

---
## Feature: Announcement ingestion & classification  `(Mode A)`
**Objective:** Ingest NSE/BSE corporate-announcement feeds behind the `DataSource` adapter, normalize to a canonical announcement record, dedup against the news store, and classify each into the announcement taxonomy that drives summaries, the corp-action feed, and alert routing.
**Backend dep:** announcement ingestion worker, `DataSource.fetch_announcements`, normalizer, dedup against `news_item`, multi-label announcement classifier with category priors · **Frontend dep:** none (consumed by display + corp-action feed below) · **Data dep:** source registry (`exchange_filing` reliability, [18 §2.1](../18-news-sentiment-and-corporate-actions.md)), `corporate_actions` master, stock master.

### Steps
- [ ] 1. Extend the adapter in `app/data/sources/base.py`: `fetch_announcements(self, since: date) -> list[AnnouncementRow]` (NSE/BSE corporate-announcement endpoints; `supports("announcements")`); free/unofficial adapters return `supports("redistribution") == False` and are prototype-only ([12 §3.1](../12-data-ingestion-and-market-data.md), [SPEC §8](../../SPEC.md)).
- [ ] 2. `app/announcements/models.py`: the canonical announcement record (`announcement_id`, `exchange`, `raw_subject`, `body`, `attachment_url`, `source_id`, `filing_ts`, `dissemination_ts`, `as_of_version`) per the [18 §2.2](../18-news-sentiment-and-corporate-actions.md) news-item shape, plus `category[]`, `resolved_symbol`, `link_confidence`. Persist to an `announcements` table ([11 §3](../11-database-architecture.md)).
- [ ] 3. `app/announcements/ingest.py`: ingest → normalize → **dedup against `news_item`** so the same event (filing + wire coverage) collapses to one cluster with retained source links ([18 §3](../18-news-sentiment-and-corporate-actions.md)); the exchange filing is the canonical member by reliability.
- [ ] 4. `app/announcements/classify.py`: multi-label classifier into the announcement taxonomy — `board_meeting`, `results`, `dividend`, `bonus`, `split`, `rights`, `buyback`, `fundraising`, `rating_action`, `pledging`, `shareholding_change`, `large_order`, `acquisition` (M&A), `regulatory_notice`, `management_change`, `litigation`, `governance_issue` — mapping onto the [18 §6](../18-news-sentiment-and-corporate-actions.md) category set. Tag which categories `feed corp_actions` (dividend/bonus/split/buyback/rights/M&A).
- [ ] 5. Persist with `as_of_version`; reuse the data-confidence indicator ([12 §4.2](../12-data-ingestion-and-market-data.md)); a parse-failed attachment marks `data_confidence: low`, never a guessed field.

### Tests
- [ ] `tests/announcements/test_ingest.py`: a sample NSE announcement feed normalizes to the canonical record; the same event arriving as filing + wire dedups to one cluster with both source links retained.
- [ ] `tests/announcements/test_classify.py`: a bonus-issue filing tags `bonus` (and `feeds_corp_actions=true`); a pledging disclosure tags `pledging` (no corp-action feed); a board-meeting notice tags `board_meeting`.
- [ ] A non-redistributable source is refused for commercial publish ([SPEC §8](../../SPEC.md)).

### Compliance gate
- [ ] Ingestion publishes only from a redistribution-reviewed source; `data_confidence` set on every record ([12 §3](../12-data-ingestion-and-market-data.md), [SPEC §8](../../SPEC.md)).
- [ ] Classification labels are **factual category tags**, never directive; no label implies an action.

### Acceptance criteria
- [ ] Announcements ingest, dedup, and classify into the taxonomy; action-bearing categories are flagged for the corp-action feed ([18 §6](../18-news-sentiment-and-corporate-actions.md)).

---
## Feature: Symbol resolution & corporate-action master feed  `(Mode A · first-class correctness)`
**Objective:** Resolve each announcement to a listed symbol with a confidence score, and for action-bearing types extract a **structured corporate-action event** into the `corporate_actions` master — **provisional until reconciled against a second source**, so it informs users immediately but only drives back-adjustment after reconciliation.
**Backend dep:** entity resolver (reused from [07](07-v2-accounts-watchlist-ai-news.md)/[18 §4](../18-news-sentiment-and-corporate-actions.md)), corp-action extractor, reconciliation-against-2nd-source worker, `corporate_actions` master writer · **Frontend dep:** none (feeds the adjuster + display) · **Data dep:** symbol-alias + corporate-hierarchy map, `corporate_actions` master, second reconciliation source ([12 §3](../12-data-ingestion-and-market-data.md)).

### Steps
- [ ] 1. Resolve symbol via the shared entity resolver ([18 §4.1–4.2](../18-news-sentiment-and-corporate-actions.md)): exact ticker/legal-name match scores high; below `SURFACING_THRESHOLD` (versioned, e.g. 0.75) the announcement is **held in the review queue**, never surfaced or fed to the corp-action master.
- [ ] 2. `app/announcements/corp_action_extract.py`: for `dividend/bonus/split/buyback/rights/acquisition`, extract the structured event — `action_type`, `ratio`/`amount`, `announce_date`, `record_date`, `ex_date` — into the [18 §9](../18-news-sentiment-and-corporate-actions.md) corp-action shape with `source_announcement_id`, `confidence`, `reconciled=false`.
- [ ] 3. **Reconciliation gate ([SPEC §6.1](../../SPEC.md)):** a news/announcement-derived event is **provisional**. `app/announcements/reconcile.py` matches it against a **second source** (vendor corp-action feed / exchange master); only on match is `reconciled=true` set. **Until reconciled it surfaces as an announcement but does NOT alter the adjusted price series** ([18 §9](../18-news-sentiment-and-corporate-actions.md), [12 §5](../12-data-ingestion-and-market-data.md)).
- [ ] 4. Write reconciled events to the `corporate_actions` master so the [01](01-local-mvp-foundation.md) adjuster back-adjusts the full history; a reconciled split/bonus then re-emits dependents (indicators → scanners → AI summaries) via the correction workflow ([12 §4.1](../12-data-ingestion-and-market-data.md)).
- [ ] 5. A reconciled corp-action event also generates the corporate-action alert ([08-v3-portfolio-risk-alerts.md](08-v3-portfolio-risk-alerts.md) §alerts) and the portfolio corp-action transaction ([16 §1.2](../16-portfolio-and-risk-engine.md)); cross-link, do not duplicate the logic here.
- [ ] 6. Admin review-queue tooling: below-threshold links and reconciliation mismatches land in a queue for manual resolution ([18 §4.2](../18-news-sentiment-and-corporate-actions.md)), never silently dropped or guessed.

### Tests
- [ ] `tests/announcements/test_corp_action_extract.py` (**critical-logic**): a 1:1 bonus filing extracts `action_type=BONUS, ratio=1:1` with the announce/record/ex dates and `reconciled=false`.
- [ ] `tests/announcements/test_reconcile.py` (**critical-logic, correctness gate**): an **unreconciled** event does **not** appear in the adjusted series (adjustment is a no-op); after a matching second source, `reconciled=true` and the split **correctly triggers back-adjustment** (continuous adjusted series, [SPEC §6.1](../../SPEC.md)).
- [ ] A subsidiary-only headline resolves below threshold and feeds **neither** the surface nor the corp-action master ([18 §4.3](../18-news-sentiment-and-corporate-actions.md)).
- [ ] A reconciliation mismatch quarantines the event into the review queue and writes a `data_quality_logs` row ([12 §4](../12-data-ingestion-and-market-data.md)).

### Compliance gate
- [ ] No unreconciled event mutates the adjusted price series ([SPEC §6.1](../../SPEC.md)); reconciliation against a second source is enforced before back-adjustment.
- [ ] Below-threshold resolutions are held, not surfaced or actioned ([18 §4.2](../18-news-sentiment-and-corporate-actions.md)).

### Acceptance criteria
- [ ] Action-bearing announcements produce structured, source-linked corp-action records; only reconciled events drive adjustment; the loop into [01](01-local-mvp-foundation.md)/[12](../12-data-ingestion-and-market-data.md) is closed ([18 §9](../18-news-sentiment-and-corporate-actions.md)).

---
## Feature: AI plain-language summary & announcement display  `(Mode A)`
**Objective:** Produce a grounded, runtime-verified, **non-exaggerating** plain-language summary of each announcement, and surface the announcements feed + per-stock corporate-actions panel with source links, timestamps, and upcoming record dates.
**Backend dep:** `announcement_summary_v1` payload builder, summarizer under the payload contract, runtime verifier, blocked-phrase guardrail, audit logger (all from [04](04-ai-explanation-layer.md)/[14 §5](../14-ai-llm-agent-architecture.md)) · **Frontend dep:** `AnnouncementFeed`, per-stock `CorporateActionsPanel` (upcoming record/ex dates), source link + timestamp + confidence badge ([04 §13](../04-feature-modules.md)) · **Data dep:** classified announcement, resolved symbol, corp-action record, source metadata.

### Steps
- [ ] 1. Build the `announcement_summary_v1` payload ([18 §8](../18-news-sentiment-and-corporate-actions.md)): canonical subject/body excerpt, category, resolved symbol, structured corp-action fields (ratio/dates) where present, source metadata — the summarizer **may reference nothing else** ([SPEC §6.6](../../SPEC.md)).
- [ ] 2. Implement the summarizer prompt + agent (cheap model default) enforcing the [18 §8](../18-news-sentiment-and-corporate-actions.md) wording rules: **classification/factual language, no exaggeration of impact** ("may affect near-term sentiment", never "set to surge"); retain source link + publish timestamp in the output.
- [ ] 3. Runtime-verify every named number/date against the payload (block/regenerate on mismatch), run the blocked-phrase guardrail at output time, and write the generation to the AI audit log ([18 §8](../18-news-sentiment-and-corporate-actions.md), [SPEC §6.6](../../SPEC.md)). On missing critical fields, **suppress the summary, never guess** ([12 §4.2](../12-data-ingestion-and-market-data.md)).
- [ ] 4. Implement the API per [10](../10-api-contracts.md): `GET /api/announcements` (feed, filterable by symbol/category, followed-instrument scoped), `GET /api/stocks/{symbol}/announcements`, `GET /api/stocks/{symbol}/corporate-actions` (with `reconciled` status + upcoming record/ex dates). Standard envelope + `data_confidence`.
- [ ] 5. Build the announcement feed + per-stock corporate-actions panel ([04 §13](../04-feature-modules.md)): simplified summary, **source link + timestamp always shown**, category chip, confidence badge, upcoming-record-date display; "This is information, not investment advice" footer; **no** "buy before the bonus" / action CTA.

### Tests
- [ ] `tests/announcements/test_summary_language.py` (**guardrail**): injecting an exaggeration ("set to surge", "multibagger") or a directive ("buy before the bonus") is caught at output time ([18 §8](../18-news-sentiment-and-corporate-actions.md), [SPEC §3.3](../../SPEC.md)).
- [ ] A summary referencing a number/date not in the payload is blocked/regenerated by the runtime verifier.
- [ ] Every surfaced announcement shows a source link + publish timestamp; a below-threshold item never reaches the feed.
- [ ] When a critical field is missing, the summary is suppressed (not guessed) and the item shows `data_confidence: low`.
- [ ] Every generation writes an audit-log row (prompt id/version, payload hash, model id, grounding report) ([SPEC §6.6](../../SPEC.md)).

### Compliance gate
- [ ] The summary simplifies and reports; it **does not exaggerate impact** and carries source link + timestamp ([18 §8](../18-news-sentiment-and-corporate-actions.md), [04 §13](../04-feature-modules.md)).
- [ ] No "buy"/"sell"/"book"/target or any always-prohibited phrase in any summary, chip, or label ([SPEC §3.3](../../SPEC.md)).

### Acceptance criteria
- [ ] Announcements surface with simplified, non-exaggerating summaries and retained sources; corporate-actions panel shows reconciled status + upcoming dates; passes the Compliance Review Agent before display ([14 §5](../14-ai-llm-agent-architecture.md)).

---
## Done-when
- [ ] All three features pass their tests, compliance gates, and acceptance criteria; the Exit gate checklist is fully checked.
- [ ] Action-bearing announcements feed the `corporate_actions` master; **no unreconciled event alters the adjusted price series**, and a reconciled split/bonus correctly triggers back-adjustment downstream ([SPEC §6.1](../../SPEC.md), [12 §5](../12-data-ingestion-and-market-data.md), [18 §9](../18-news-sentiment-and-corporate-actions.md)).
- [ ] Every surfaced announcement is entity-resolved above threshold, carries source link + timestamp, and (where AI-summarized) is runtime-verified and audit-logged ([18 §4.2, §8](../18-news-sentiment-and-corporate-actions.md), [SPEC §6.6](../../SPEC.md)).
- [ ] No announcement output exaggerates impact or contains a buy/sell directive or any always-prohibited phrase ([SPEC §3.3, §5](../../SPEC.md)).
- [ ] This module remains **distinct from** news sentiment ([07-v2-accounts-watchlist-ai-news.md](07-v2-accounts-watchlist-ai-news.md), [18 §1–8](../18-news-sentiment-and-corporate-actions.md)) while reusing its resolver/guardrails; cross-links to [01](01-local-mvp-foundation.md)/[12](../12-data-ingestion-and-market-data.md) (adjustment) and [08](08-v3-portfolio-risk-alerts.md) (alerts) are in place, not duplicated.
