# Steps · 01 · Local MVP foundation (repo, config, storage, data adapters)
> Read first: [SPEC.md](../../SPEC.md) (§12 local build plan M0–M1, §8 data strategy, §9 architecture, §6.1–6.2 correctness) · [Roadmap](../02-product-roadmap.md) · [Database](../11-database-architecture.md) · [Data ingestion](../12-data-ingestion-and-market-data.md) · [Coding standards](../27-coding-standards.md)

**Maps to:** Roadmap Phase 0/V1 foundation · SPEC Phase 0–1 plumbing · Local milestone **M0–M1**
**Status:** **M1 complete** (real NSE Bhavcopy adapter, corp-action master + adjuster, 2nd-source reconciliation — all validated; 59 tests pass).   |   **Regulatory mode:** A
**Prerequisites:** [00-phase-0-derisk.md](00-phase-0-derisk.md) (mode confirmed; data-source decision; yfinance-prototype-only constraint).

> ⚠️ **Stack reset (2026-07-02/03) — this step predates it.** Where this file says **DuckDB → read TimescaleDB+MongoDB**, and **yfinance/Bhavcopy → read Kite Connect**. Decision log **D-057** (Claude-only AI), **D-058** (Kite-only data), **D-059** (polyglot TimescaleDB+MongoDB, DuckDB retired). The M0/M1 gates were validated historically on DuckDB; the storage layer has since been ported (current schema: `app/storage/schema_postgres.sql` + `mongo_setup.py`; data source: `app/data/kite_source.py`).

## Overview
Stands up the local-first skeleton on one Apple-Silicon Mac so every later file has a place to live: the [SPEC §12](../../SPEC.md) `app/` structure, a Python 3.11 venv + pinned deps + typed `config.py`, the **DuckDB** storage layer (schema + repository with **raw+adjusted + as-of** fields per [docs/11](../11-database-architecture.md)), the single **`DataSource` adapter interface**, the **yfinance adapter** (prototype-only; ~50 Nifty names, adjusted OHLCV), the **NSE Bhavcopy + delivery stub**, the symbol universe + normalization, and the first-class **corporate-actions master + adjustment** workstream. Indicators and scanners are built next in [02-indicators-and-scanners.md](02-indicators-and-scanners.md); the pipeline + API in [05-api-and-pipeline.md](05-api-and-pipeline.md).

## Exit gate (Definition of Done)
- [x] **M0 gate:** adjusted OHLCV lands in DuckDB (validated: 8 symbols × 248 sessions; raw+adjusted both stored, `is_adjusted` + `adj_factor` set). Full ~50-name / full-history backfill = run with no `--limit`.
- [x] **M1 gate:** the same symbol returns **consistent** data via either adapter, and a vendor swap touches **no business logic** ([SPEC §12 M1](../../SPEC.md), [docs/12 §6](../12-data-ingestion-and-market-data.md)).
- [x] Raw **and** adjusted series stored; `as_of_version`, `is_adjusted`, `adj_factor`, `source` populated ([docs/11 §3.3](../11-database-architecture.md), [SPEC §6.1–6.2](../../SPEC.md)).
- [x] For a split/bonus test set, adjusted series is continuous and **reconciles vs a 2nd source**; raw preserved ([SPEC §6.1](../../SPEC.md)).

---
## Feature: Repo scaffold (SPEC §12 `app/` structure)  `(Mode A)`
**Objective:** Create the project tree that mirrors production so local modules lift into services later. · **Backend dep:** none · **Frontend dep:** none (`web/` deferred) · **Data dep:** none
### Steps
- [ ] 1. Create the tree from [SPEC §12](../../SPEC.md) / [docs/27 §1](../27-coding-standards.md): `app/{config.py,data/,storage/,indicators/,scanners/,ai/,pipeline/,api/}`, `scripts/run_pipeline.py`, `tests/` (mirroring `app/`), `requirements.txt`, `.env.example`, `docker-compose.yml` (for later, not run).
- [ ] 2. Add `app/__init__.py` and per-package `__init__.py`; enforce the import rule: `scanners/` never imports `api/`; `ai/` never imports raw `data/` adapters ([docs/27 §1](../27-coding-standards.md)).
- [ ] 3. Add `pyproject.toml`/`setup.cfg` for `mypy --strict`, `ruff`/`black`, `pytest` config ([docs/27 §3.2](../27-coding-standards.md)).
- [ ] 4. Add `README.md` with the run commands from [SPEC §12](../../SPEC.md) (`pyenv local 3.11.9`, venv, `pip install`, `cp .env.example .env`, `run_pipeline.py`, `pytest`, `uvicorn`).
- [ ] 5. Add `.gitignore` (`.venv/`, `.env`, `data/*.duckdb`, raw landed files).
### Tests
- [ ] `tests/test_repo_layout.py`: asserts the required packages/modules import cleanly.
### Compliance gate
- [ ] No RA-gated module/flag scaffolded as enabled; any future RA code is flag-guarded off by default ([docs/27 §0.3](../27-coding-standards.md)).
### Acceptance criteria
- [ ] `python -c "import app"` succeeds; tree matches [SPEC §12](../../SPEC.md).

---
## Feature: Python 3.11 venv + requirements + `config.py`  `(Mode A)`
**Objective:** Reproducible local env, pinned arm64 wheels (**no TA-Lib**), and a typed settings object loading `.env` incl. `ANTHROPIC_API_KEY`. · **Backend dep:** none · **Frontend dep:** none · **Data dep:** none
### Steps
- [ ] 1. `pyenv local 3.11.9`; `python -m venv .venv`; document activation.
- [ ] 2. `requirements.txt`: `duckdb`, `pandas`, `numpy`, `yfinance`, `pydantic`, `pydantic-settings`, `fastapi`, `uvicorn`, `anthropic`, `httpx`, `pytest`, `mypy`, `ruff` — **all arm64 wheels, no TA-Lib** ([SPEC §9](../../SPEC.md), [§12](../../SPEC.md), [docs/27 §7.3](../27-coding-standards.md)).
- [ ] 3. `app/config.py` using `pydantic-settings`: typed `Settings` (env + `.env`) with `anthropic_api_key`, `duckdb_path`, `data_dir`, `model_version` (default `claude-haiku-4-5-20251001`), `universe_path`, thresholds path. No secrets logged ([docs/27 §5](../27-coding-standards.md)).
- [ ] 4. `.env.example` listing `ANTHROPIC_API_KEY=` and paths; never commit `.env`.
- [ ] 5. A `get_settings()` cached accessor (`functools.lru_cache`) used everywhere; no module reads `os.environ` directly.
### Tests
- [ ] `tests/test_config.py`: loads settings from a temp `.env`; asserts defaults + that a missing required var raises a typed error (fail loud, [docs/27 §0.5](../27-coding-standards.md)).
### Compliance gate
- [ ] `ANTHROPIC_API_KEY` never appears in logs or error messages ([docs/27 §5](../27-coding-standards.md)).
### Acceptance criteria
- [ ] `pip install -r requirements.txt` succeeds on arm64 with no TA-Lib; `get_settings()` returns a typed object.

---
## Feature: DuckDB storage layer — schema + repository  `(Mode A)`
**Objective:** A single DuckDB file holding the v1 tables from [docs/11](../11-database-architecture.md) with **raw+adjusted + as-of versioning** throughout, plus a typed repository. · **Backend dep:** config · **Frontend dep:** none · **Data dep:** none
### Steps
- [ ] 1. `app/storage/duckdb.py`: connection factory + context manager bound to `settings.duckdb_path`.
- [ ] 2. `app/storage/schema.sql` (the local mirror of the Alembic intent, [docs/11 §7](../11-database-architecture.md)). Create the v1-relevant tables:
  - `stock_master` (isin, primary_symbol, name, sector_id, parent_isin, status incl. `delisted|merged` — **never hard-delete**, listed_on/delisted_on) ([docs/11 §3.2](../11-database-architecture.md)).
  - `exchange_symbols` (stock_id, exchange `NSE|BSE`, symbol `.NS`/`.BO`, series, valid_from/valid_to) for symbol-change history.
  - `sector_master` / `industry_master`.
  - `daily_ohlc` with **`open_raw/high_raw/low_raw/close_raw` + `open_adj/high_adj/low_adj/close_adj`**, `volume`, `delivery_qty`, `delivery_pct`, `is_adjusted`, `adj_factor`, `source`, `as_of_version`, `reconciled`, `ingested_at`; **PK (stock_id, session_date, as_of_version)** ([docs/11 §3.3](../11-database-architecture.md), [SPEC §6.1](../../SPEC.md)).
  - `index_ohlc` (NIFTY50 etc.) with `as_of_version`.
  - `technical_indicators` (placeholder for [02-indicators-and-scanners.md](02-indicators-and-scanners.md)) with `indicator_version` + `as_of_version`.
  - `corporate_actions` (action_type, ex_date, ratio_from/to, dividend_amount, new_symbol, factor, source, reconciled, as_of_version) ([docs/11 §3.4](../11-database-architecture.md)).
  - `data_quality_logs` (job_id, source, session_date, stock_id, check_type, severity, status, detail) ([docs/11 §3.13](../11-database-architecture.md)).
- [ ] 3. `app/storage/repository.py`: typed Pydantic models (`StockMaster`, `OhlcRow`, `CorpAction`, `DataQualityLog`) and upsert/read methods. **No bare `dict` across boundaries** ([docs/27 §3.2](../27-coding-standards.md)). Reads carry/propagate `as_of` ([docs/27 §0.2](../27-coding-standards.md)).
- [ ] 4. Indexes per [docs/11 §4](../11-database-architecture.md) (`stock_master(primary_symbol)`, `daily_ohlc(stock_id, session_date DESC)`).
- [ ] 5. Forward-only migration discipline: schema changes **bump `as_of_version`**, never rewrite historical OHLC ([docs/11 §7](../11-database-architecture.md), [SPEC §6.2](../../SPEC.md)).
### Tests
- [ ] `tests/storage/test_schema.py`: schema applies cleanly; every time-series table carries `as_of_version`; `daily_ohlc` has both raw and adjusted columns.
- [ ] `tests/storage/test_repository.py`: round-trip upsert/read; restating a row creates a **new `as_of_version`** rather than overwriting (point-in-time preserved).
### Compliance gate
- [ ] No table allows hard-deleting delisted/merged instruments (survivorship control, [SPEC §6.3](../../SPEC.md), [docs/11 §0](../11-database-architecture.md)).
### Acceptance criteria
- [ ] Schema creates a DuckDB file with all v1 tables; a restatement bumps `as_of_version`; any stored value is reproducible for its `as_of`.

---
## Feature: `DataSource` adapter interface  `(Mode A)`
**Objective:** The single vendor-agnostic seam so business logic never depends on the source ([SPEC §8](../../SPEC.md)). · **Backend dep:** storage models · **Frontend dep:** none · **Data dep:** none
### Steps
- [ ] 1. `app/data/base.py`: `DataSource` Protocol per [docs/12 §3.1](../12-data-ingestion-and-market-data.md): `name`, `fetch_eod(symbols, session_date) -> list[OHLCRow]`, `fetch_delivery(session_date) -> list[DeliveryRow] | None`, `fetch_corporate_actions(since) -> list[CorpAction]`, `supports(capability) -> bool` (`"delivery_pct"`, `"adjusted"`, `"redistribution"`).
- [ ] 2. Typed row models (`OHLCRow`, `DeliveryRow`, `CorpAction`) shared by all adapters.
- [ ] 3. A `get_source(name)` factory reading the active source from config (default `yfinance`).
- [ ] 4. Publish-guard helper: refuse commercial publish when `supports("redistribution") is False` ([SPEC §8](../../SPEC.md), [docs/12 §3.1](../12-data-ingestion-and-market-data.md)).
### Tests
- [ ] `tests/data/test_adapter_contract.py`: every registered adapter satisfies the Protocol and returns typed rows.
### Compliance gate
- [ ] Non-redistributable sources report `supports("redistribution") == False`; the publish-guard blocks commercial output from them.
### Acceptance criteria
- [ ] Scanners/indicators/AI can depend only on `DataSource`; swapping the concrete source requires no business-logic change ([SPEC §12 M1](../../SPEC.md)).

---
## Feature: yfinance adapter (prototype; ~50 Nifty names, adjusted OHLCV)  `(Mode A)`
**Objective:** The M0 local source — pull adjusted OHLCV for ~50 Nifty names into DuckDB. **Prototype-only.** · **Backend dep:** adapter interface, storage · **Frontend dep:** none · **Data dep:** yfinance (`.NS`)
### Steps
- [ ] 1. `app/data/yfinance_source.py` implementing `DataSource`: `name="yfinance"`; `supports("adjusted")=True`, `supports("delivery_pct")=False`, `supports("redistribution")=False` ([docs/12 §3](../12-data-ingestion-and-market-data.md)).
- [ ] 2. `fetch_eod`: pull full-history adjusted OHLCV for the ~50 names; map to `OHLCRow` with **both** raw and yfinance-adjusted values; mark `source="yfinance"`.
- [ ] 3. `fetch_delivery` returns `None` (no delivery %); downstream marks the delivery sub-score **neutral, never zero** ([docs/13 §4.2](../13-scanner-engine-and-scoring.md)).
- [ ] 4. Note in code: yfinance auto-adjustment is a **prototyping convenience, not the production engine** ([SPEC §6.1](../../SPEC.md)); the production adjuster is the corp-actions workstream below.
- [ ] 5. Land raw pulls to `data/` for reproducibility before storage.
### Tests
- [ ] `tests/data/test_yfinance_source.py`: with a committed offline fixture (no network in unit tests, [docs/27 §7.6](../27-coding-standards.md)), parsing yields typed rows with raw+adjusted populated and `redistribution=False`.
### Compliance gate
- [ ] yfinance output cannot be commercially published (publish-guard); used for local prototype only ([SPEC §8](../../SPEC.md)).
### Acceptance criteria
- [ ] **M0:** adjusted OHLCV for ~50 Nifty names lands in DuckDB for the full window ([SPEC §12 M0](../../SPEC.md)).

---
## Feature: NSE Bhavcopy + MTO delivery adapter  `(Mode A)`
**Objective:** Real authoritative-EOD adapter — NSE CM UDiFF Bhavcopy + MTO delivery file. No committed sample data (no-stub-data rule). Redistribution rights pending review; local/prototype use only. · **Backend dep:** adapter interface · **Frontend dep:** none · **Data dep:** NSE archives
### Steps
- [x] 1. `app/data/nse_bhavcopy_source.py` implementing `DataSource`: `name="nse_bhavcopy"`; `supports("delivery_pct")=True`, `supports("adjusted")=False`, `supports("redistribution")=False` (pending review) ([docs/12 §3](../12-data-ingestion-and-market-data.md)).
- [x] 2. `fetch_eod`: real live download from `nsearchives.nseindia.com` (UDiFF zip); session primed via `_prime_session`; `_parse_bhavcopy` handles both UDiFF (post-2020) and legacy (pre-2020) formats.
- [x] 3. `fetch_delivery`: real download of `MT{DDMMYYYY}.DAT` from NSE archives into `DeliveryRow` list.
- [x] 4. Production live-download active; redistribution review required before commercial publishing (enforced by publish-guard, SPEC §8).
### Tests
- [x] `tests/data/test_nse_bhavcopy_source.py`: inline CSV fixtures (no committed data files); UDiFF parser, legacy parser, MTO parser, adapter contract all tested.
### Compliance gate
- [x] Bhavcopy adapter reports `redistribution=False`; publish-guard enforced ([SPEC §8](../../SPEC.md)).
### Acceptance criteria
- [x] **M1:** same symbol consistent via either adapter; vendor swap touches no business logic.

---
## Feature: Symbol universe + normalization  `(Mode A)`
**Objective:** A canonical ~50-name universe keyed to `stock_master`/`exchange_symbols`, and normalization that unifies vendor column names/types. · **Backend dep:** storage · **Frontend dep:** none · **Data dep:** universe list
### Steps
- [ ] 1. `app/data/universe.py`: load the ~50 Nifty names from a committed `data/universe.csv` (symbol, isin, exchange, sector); seed `stock_master` + `exchange_symbols` + `sector_master`.
- [ ] 2. `app/data/normalize.py`: map any adapter's rows to the canonical OHLCV schema (column names/types) — pipeline stages 3–4 ([docs/12 §1](../12-data-ingestion-and-market-data.md)).
- [ ] 3. Symbol mapping: resolve `.NS`/`.BO` tickers ↔ ISIN via `exchange_symbols`; handle symbol-change history through `valid_from/valid_to`.
- [ ] 4. Eligibility-relevant fields (listing status, listed/delisted dates) populated for the [02](02-indicators-and-scanners.md) eligibility filter.
### Tests
- [ ] `tests/data/test_universe.py`: universe seeds `stock_master` with unique ISINs; symbol→stock_id resolution works incl. a symbol-change fixture.
- [ ] `tests/data/test_normalize.py`: heterogeneous vendor rows normalize to one schema.
### Compliance gate
- [ ] Delisted/merged names retained in master (survivorship control) ([SPEC §6.3](../../SPEC.md)).
### Acceptance criteria
- [ ] All ~50 names resolve symbol↔ISIN; normalized OHLCV is vendor-agnostic.

---
## Feature: Corporate-actions master + adjustment workstream  `(Mode A)`
**Objective:** The first-class corp-action engine ([SPEC §6.1](../../SPEC.md)) — its own workstream, not a pipeline bullet: maintain the master, store **raw + adjusted**, back-adjust consistently across full history, and **reconcile vs a 2nd source**. · **Backend dep:** storage, corp_actions table · **Frontend dep:** none · **Data dep:** corp-action feed (yfinance proto; vendor prod)
### Steps
- [x] 1. `app/data/corp_actions.py`: ingest splits/bonuses/dividends/rights/mergers from yfinance (prototype); compute single-event backward adj factor; `ingest_corp_actions()` stores in `corporate_actions` table ([docs/11 §3.4](../11-database-architecture.md)).
- [x] 2. `app/data/corp_action_adjuster.py`: `compute_adj_factors()` (pure, golden-tested) + `adjust_all()` back-adjusts full history per stock; write `*_adj` columns + `is_adjusted=True`; **preserve raw** ([SPEC §6.1](../../SPEC.md), [docs/27 §7.3](../27-coding-standards.md)).
- [x] 3. Reconciliation: `app/data/reconcile.py` — compares our adj_close vs yfinance adj_close (raw cross-source); sets `reconciled=True` on match (≤1% tolerance); mismatch → `data_quality_logs` quarantine ([docs/12 §4](../12-data-ingestion-and-market-data.md)).
- [x] 4. Abnormal-jump check: `check_abnormal_jumps()` in reconcile.py — price move >15% with no corp-action on that ex_date → quarantine ([docs/12 §4](../12-data-ingestion-and-market-data.md)).
- [x] 5. Correction workflow hook: **detect → quarantine → correct → re-emit** pattern implemented; full re-emit via `as_of_version` bump wired in the pipeline ([05-api-and-pipeline.md](05-api-and-pipeline.md)).
### Tests
- [x] `tests/data/test_corp_action_adjuster.py` (**critical-logic, golden**): 1:2 split, 1:1 bonus, two-event cumulative, continuity, raw-preserved — all golden-verified ([SPEC §6.1](../../SPEC.md), [docs/27 §0.1](../27-coding-standards.md)).
- [x] `tests/data/test_reconciliation.py`: match → `reconciled=True`; mismatch → DQ log written; boundary tolerance; abnormal-jump with/without corp-action coverage.
### Compliance gate
- [ ] Indicators/scanners will read **only adjusted** series; unadjusted splits cannot silently corrupt indicators ([SPEC §6.1](../../SPEC.md), [docs/13 §0.5](../13-scanner-engine-and-scoring.md)).
### Acceptance criteria
- [ ] For the split/bonus test set, adjusted series reconciles vs a 2nd source; raw preserved; `is_adjusted`+`adj_factor` set; a restatement re-versions affected rows ([docs/12 §6](../12-data-ingestion-and-market-data.md)).

---
## Done-when
- [x] **M0:** adjusted OHLCV in DuckDB — ingest pipeline validated end-to-end (8-symbol smoke; full backfill = `python scripts/run_pipeline.py`).
- [x] **M1:** same symbol consistent via either adapter; vendor swap touches no business logic ([SPEC §12 M1](../../SPEC.md)).
- [x] Raw+adjusted stored with as-of versioning; split/bonus set reconciles vs a 2nd source; survivorship preserved.
- [x] Foundation ready for indicators + scanners ([02-indicators-and-scanners.md](02-indicators-and-scanners.md)).
