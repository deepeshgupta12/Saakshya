-- Saakshya local DuckDB schema (mirror of the Alembic intent, docs/11 §7).
-- Principles: raw + adjusted series, as-of/point-in-time versioning, survivorship
-- preserved (delisted/merged never hard-deleted). SPEC §6.1–6.3.

CREATE SEQUENCE IF NOT EXISTS seq_sector_id START 1;
CREATE SEQUENCE IF NOT EXISTS seq_industry_id START 1;
CREATE SEQUENCE IF NOT EXISTS seq_stock_id START 1;
CREATE SEQUENCE IF NOT EXISTS seq_exch_sym_id START 1;
CREATE SEQUENCE IF NOT EXISTS seq_corp_action_id START 1;
CREATE SEQUENCE IF NOT EXISTS seq_dq_log_id START 1;

CREATE TABLE IF NOT EXISTS sector_master (
    sector_id   BIGINT DEFAULT nextval('seq_sector_id') PRIMARY KEY,
    name        VARCHAR NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS industry_master (
    industry_id BIGINT DEFAULT nextval('seq_industry_id') PRIMARY KEY,
    name        VARCHAR NOT NULL UNIQUE,
    sector_id   BIGINT);

-- Survivorship: status may be 'listed' | 'delisted' | 'merged'; rows are NEVER deleted.
CREATE TABLE IF NOT EXISTS stock_master (
    stock_id        BIGINT DEFAULT nextval('seq_stock_id') PRIMARY KEY,
    isin            VARCHAR,                 -- nullable: backfilled from NSE/vendor in M1+
    primary_symbol  VARCHAR NOT NULL UNIQUE,
    name            VARCHAR NOT NULL,
    sector_id       BIGINT REFERENCES sector_master(sector_id),
    parent_isin     VARCHAR,
    status          VARCHAR NOT NULL DEFAULT 'listed',
    listed_on       DATE,
    delisted_on     DATE,
    created_at      TIMESTAMP DEFAULT now()
);

-- Symbol-change history: which ticker mapped to which stock over which window.
CREATE TABLE IF NOT EXISTS exchange_symbols (
    id          BIGINT DEFAULT nextval('seq_exch_sym_id') PRIMARY KEY,
    stock_id    BIGINT NOT NULL,
    exchange    VARCHAR NOT NULL,            -- 'NSE' | 'BSE'
    symbol      VARCHAR NOT NULL,            -- '.NS' / '.BO' vendor ticker
    series      VARCHAR,
    valid_from  DATE NOT NULL DEFAULT DATE '1990-01-01',
    valid_to    DATE,
    UNIQUE (exchange, symbol, valid_from)
);

-- EOD bars: BOTH raw and adjusted, point-in-time versioned.
-- A restatement inserts a NEW as_of_version rather than overwriting history (SPEC §6.2).
CREATE TABLE IF NOT EXISTS daily_ohlc (
    stock_id      BIGINT NOT NULL,
    session_date  DATE NOT NULL,
    open_raw      DOUBLE NOT NULL,
    high_raw      DOUBLE NOT NULL,
    low_raw       DOUBLE NOT NULL,
    close_raw     DOUBLE NOT NULL,
    open_adj      DOUBLE NOT NULL,
    high_adj      DOUBLE NOT NULL,
    low_adj       DOUBLE NOT NULL,
    close_adj     DOUBLE NOT NULL,
    volume        BIGINT NOT NULL,
    delivery_qty  BIGINT,                    -- NULL from yfinance (no delivery %)
    delivery_pct  DOUBLE,
    is_adjusted   BOOLEAN NOT NULL DEFAULT FALSE,
    adj_factor    DOUBLE NOT NULL DEFAULT 1.0,
    source        VARCHAR NOT NULL,
    as_of_version INTEGER NOT NULL DEFAULT 1,
    reconciled    BOOLEAN NOT NULL DEFAULT FALSE,
    ingested_at   TIMESTAMP DEFAULT now(),
    PRIMARY KEY (stock_id, session_date, as_of_version)
);

CREATE TABLE IF NOT EXISTS index_ohlc (
    index_symbol  VARCHAR NOT NULL,          -- e.g. '^NSEI' (NIFTY 50)
    session_date  DATE NOT NULL,
    open          DOUBLE NOT NULL,
    high          DOUBLE NOT NULL,
    low           DOUBLE NOT NULL,
    close         DOUBLE NOT NULL,
    volume        BIGINT,
    source        VARCHAR NOT NULL,
    as_of_version INTEGER NOT NULL DEFAULT 1,
    ingested_at   TIMESTAMP DEFAULT now(),
    PRIMARY KEY (index_symbol, session_date, as_of_version)
);

-- Placeholder for milestone M2 (02-indicators-and-scanners). Indicator columns added there.
CREATE TABLE IF NOT EXISTS technical_indicators (
    stock_id          BIGINT NOT NULL,
    session_date      DATE NOT NULL,
    indicator_version INTEGER NOT NULL DEFAULT 1,
    as_of_version     INTEGER NOT NULL DEFAULT 1,
    computed_at       TIMESTAMP DEFAULT now(),
    PRIMARY KEY (stock_id, session_date, indicator_version, as_of_version)
);

-- First-class corporate-action master (SPEC §6.1). Drives the adjustment engine (M1).
CREATE TABLE IF NOT EXISTS corporate_actions (
    action_id       BIGINT DEFAULT nextval('seq_corp_action_id') PRIMARY KEY,
    stock_id        BIGINT NOT NULL,
    action_type     VARCHAR NOT NULL,        -- split | bonus | dividend | rights | merger | symbol_change
    ex_date         DATE NOT NULL,
    ratio_from      DOUBLE,
    ratio_to        DOUBLE,
    dividend_amount DOUBLE,
    new_symbol      VARCHAR,
    factor          DOUBLE,                  -- cumulative adjustment factor at ex_date
    source          VARCHAR NOT NULL,
    reconciled      BOOLEAN NOT NULL DEFAULT FALSE,
    as_of_version   INTEGER NOT NULL DEFAULT 1,
    ingested_at     TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS data_quality_logs (
    log_id       BIGINT DEFAULT nextval('seq_dq_log_id') PRIMARY KEY,
    job_id       VARCHAR NOT NULL,
    source       VARCHAR NOT NULL,
    session_date DATE,
    stock_id     BIGINT,
    check_type   VARCHAR NOT NULL,           -- missing_candle | abnormal_jump | duplicate | reconcile_mismatch | ...
    severity     VARCHAR NOT NULL,           -- info | warn | error
    status       VARCHAR NOT NULL,           -- ok | quarantined | corrected
    detail       VARCHAR,
    created_at   TIMESTAMP DEFAULT now()
);

-- Scanner results: one row per (scanner, stock, session, as_of_version).
-- sub_scores/facts/signal_tags/risk_flags stored as JSON strings.
-- Composite gated on validationStatus = VALIDATED before any UI (SPEC §6.5, docs/13 §3.3).
CREATE SEQUENCE IF NOT EXISTS seq_scanner_result_id START 1;

CREATE TABLE IF NOT EXISTS scanner_results (
    result_id         BIGINT DEFAULT nextval('seq_scanner_result_id') PRIMARY KEY,
    scanner           VARCHAR NOT NULL,
    stock_id          BIGINT NOT NULL,
    session_date      DATE NOT NULL,
    composite_score   DOUBLE,
    sub_scores        VARCHAR,
    facts             VARCHAR,
    signal_tags       VARCHAR,
    risk_flags        VARCHAR,
    data_confidence   VARCHAR NOT NULL DEFAULT 'MEDIUM',
    weights_version   VARCHAR NOT NULL DEFAULT 'weights-v1-hypothesis',
    validation_status VARCHAR NOT NULL DEFAULT 'PENDING_M3B',
    as_of_version     INTEGER NOT NULL DEFAULT 1,
    engine_version    VARCHAR NOT NULL DEFAULT '1.0.0',
    computed_at       TIMESTAMP DEFAULT now(),
    UNIQUE (scanner, stock_id, session_date, as_of_version)
);

-- Scanner definitions: one row per scanner. validated flips to TRUE after M3b (SPEC §6.5).
CREATE TABLE IF NOT EXISTS scanner_definitions (
    id            VARCHAR NOT NULL PRIMARY KEY,
    name          VARCHAR NOT NULL,
    owner_user_id VARCHAR,
    plan_required VARCHAR,
    weights       VARCHAR,
    version       INTEGER NOT NULL DEFAULT 1,
    validated     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMP DEFAULT now()
);

-- AI generation audit log: immutable record of every generation (docs/14 §7, SPEC §6.6).
-- Append-only: no UPDATE or DELETE API. Every outcome (publish/suppress/degrade) writes one row.
CREATE TABLE IF NOT EXISTS ai_audit_log (
    audit_id              VARCHAR NOT NULL PRIMARY KEY,
    timestamp             TIMESTAMP NOT NULL DEFAULT now(),
    intent                VARCHAR NOT NULL,
    agent                 VARCHAR,
    prompt_id             VARCHAR NOT NULL,
    prompt_version        VARCHAR NOT NULL,
    model_tier            VARCHAR NOT NULL,
    model_id              VARCHAR NOT NULL,
    payload_hash          VARCHAR NOT NULL,
    payload_json          VARCHAR NOT NULL,
    raw_output            VARCHAR,
    grounding_report_json VARCHAR,
    guardrail_report_json VARCHAR,
    compliance_decision   VARCHAR NOT NULL DEFAULT 'PASS',
    user_visible_output   VARCHAR,
    suppressed            BOOLEAN NOT NULL DEFAULT FALSE,
    degraded              BOOLEAN NOT NULL DEFAULT FALSE,
    as_of_version         VARCHAR,
    tokens_in             INTEGER DEFAULT 0,
    tokens_out            INTEGER DEFAULT 0,
    cost_usd              DOUBLE DEFAULT 0.0
);

-- AI summary cache: serve cached summary when signal category is unchanged (docs/14 §3).
CREATE TABLE IF NOT EXISTS ai_summary_cache (
    symbol          VARCHAR NOT NULL,
    signal_category VARCHAR NOT NULL,
    summary         VARCHAR NOT NULL,
    audit_id        VARCHAR NOT NULL,
    as_of           DATE NOT NULL,
    model_version   VARCHAR NOT NULL,
    created_at      TIMESTAMP DEFAULT now(),
    PRIMARY KEY (symbol, signal_category)
);

-- Daily AI call counter for the hard ceiling (docs/14 §3, SPEC §6.8).
CREATE TABLE IF NOT EXISTS ai_daily_calls (
    call_date  DATE NOT NULL PRIMARY KEY,
    call_count INTEGER NOT NULL DEFAULT 0
);

-- primary_symbol is already UNIQUE (indexed); no separate index needed.
CREATE INDEX IF NOT EXISTS idx_daily_ohlc_stock_date ON daily_ohlc (stock_id, session_date);
CREATE INDEX IF NOT EXISTS idx_corp_actions_stock ON corporate_actions (stock_id, ex_date);
CREATE INDEX IF NOT EXISTS idx_scanner_results_date ON scanner_results (scanner, session_date);
CREATE INDEX IF NOT EXISTS idx_ai_audit_log_timestamp ON ai_audit_log (timestamp);
CREATE INDEX IF NOT EXISTS idx_ai_audit_log_symbol ON ai_audit_log (intent, agent);

-- ============================================================
-- V3 — Portfolio, Risk & Alerts (docs/16, docs/17, step 08)
-- ============================================================

-- Portfolios: one per user (v1); cost_basis_method controls FIFO vs WAVG reducer.
-- Holdings are PII-class — never logged in plaintext (docs/23 §5).
CREATE TABLE IF NOT EXISTS portfolios (
    portfolio_id   VARCHAR NOT NULL PRIMARY KEY,
    user_id        VARCHAR NOT NULL,
    name           VARCHAR NOT NULL,
    cost_basis_method VARCHAR NOT NULL DEFAULT 'FIFO',  -- FIFO | WEIGHTED_AVG
    created_at     TIMESTAMP DEFAULT now(),
    updated_at     TIMESTAMP DEFAULT now()
);

-- Transactions: the source of truth for cost basis and realized P&L (docs/16 §1.2).
-- Append-only; corporate-action synthesizer inserts BONUS/SPLIT rows automatically.
CREATE TABLE IF NOT EXISTS transactions (
    txn_id         VARCHAR NOT NULL PRIMARY KEY,
    portfolio_id   VARCHAR NOT NULL,
    symbol         VARCHAR NOT NULL,
    exchange       VARCHAR NOT NULL DEFAULT 'NSE',
    type           VARCHAR NOT NULL,  -- BUY|SELL|BONUS|SPLIT|DIVIDEND|RIGHTS|MERGER_IN|MERGER_OUT
    quantity       DOUBLE NOT NULL,
    price          DOUBLE NOT NULL,
    trade_date     DATE NOT NULL,
    charges        DOUBLE NOT NULL DEFAULT 0.0,
    source         VARCHAR NOT NULL DEFAULT 'MANUAL',  -- MANUAL | BROKER_SYNC | CORP_ACTION
    corp_action_adjusted BOOLEAN NOT NULL DEFAULT FALSE,
    as_of_version  INTEGER NOT NULL DEFAULT 1,
    created_at     TIMESTAMP DEFAULT now()
);

-- Alert definitions: one rule per row, evaluated EOD after the pipeline (docs/17 §4).
-- ra_gated=TRUE rows are never evaluated in Mode A (docs/17 §3).
CREATE TABLE IF NOT EXISTS alert_definitions (
    alert_id       VARCHAR NOT NULL PRIMARY KEY,
    user_id        VARCHAR NOT NULL,
    type           VARCHAR NOT NULL,   -- scanner_entry|price_above|portfolio_risk|…
    scope_symbol   VARCHAR,
    scope_scanner  VARCHAR,
    scope_sector   VARCHAR,
    condition_json VARCHAR NOT NULL DEFAULT '{}',
    cadence        VARCHAR NOT NULL DEFAULT 'EOD',
    channels_json  VARCHAR NOT NULL DEFAULT '["in_app"]',
    throttle_json  VARCHAR NOT NULL DEFAULT '{"max_per_day":3,"cooldown_minutes":720}',
    ra_gated       BOOLEAN NOT NULL DEFAULT FALSE,
    enabled        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMP DEFAULT now(),
    updated_at     TIMESTAMP DEFAULT now()
);

-- Alert events: one row per fired alert instance (docs/17 §4 fired-alert shape).
-- dedup_key uniqueness within the as_of_date prevents duplicate alerts (docs/17 §5).
CREATE TABLE IF NOT EXISTS alert_events (
    event_id       VARCHAR NOT NULL PRIMARY KEY,
    alert_id       VARCHAR NOT NULL,
    as_of_date     DATE NOT NULL,
    payload_json   VARCHAR NOT NULL DEFAULT '{}',
    dedup_key      VARCHAR NOT NULL,
    rendered_text  VARCHAR NOT NULL,
    guardrail_status VARCHAR NOT NULL DEFAULT 'passed',
    channels_json  VARCHAR NOT NULL DEFAULT '[]',
    delivery_log_json VARCHAR NOT NULL DEFAULT '[]',
    created_at     TIMESTAMP DEFAULT now(),
    UNIQUE (dedup_key, as_of_date)
);

CREATE INDEX IF NOT EXISTS idx_transactions_portfolio ON transactions (portfolio_id, trade_date);
CREATE INDEX IF NOT EXISTS idx_transactions_symbol ON transactions (portfolio_id, symbol);
CREATE INDEX IF NOT EXISTS idx_alert_events_date ON alert_events (as_of_date, alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_definitions_user ON alert_definitions (user_id, enabled);

-- ============================================================
-- V4 — Strategy / Scanner Builder (docs/19, step 09)
-- ============================================================

-- Strategy definitions: versioned; prior versions are immutable (audit trail).
-- strategy_json holds the full typed condition tree per docs/19 §7.
CREATE TABLE IF NOT EXISTS strategy_definitions (
    strategy_id    VARCHAR NOT NULL PRIMARY KEY,
    owner_user_id  VARCHAR NOT NULL,
    name           VARCHAR NOT NULL,
    version        INTEGER NOT NULL DEFAULT 1,
    strategy_json  VARCHAR NOT NULL,
    is_library     BOOLEAN NOT NULL DEFAULT FALSE,
    validation_status VARCHAR NOT NULL DEFAULT 'PENDING',  -- PENDING|VALID|INVALID
    created_at     TIMESTAMP DEFAULT now(),
    updated_at     TIMESTAMP DEFAULT now()
);

-- Screener library: prebuilt Mode-A list-producing filters (docs/19 §; step 09).
-- Seeded from app/strategy/library.py; read-only for end users.
CREATE TABLE IF NOT EXISTS screener_library (
    library_id     VARCHAR NOT NULL PRIMARY KEY,
    name           VARCHAR NOT NULL,
    description    VARCHAR,
    category       VARCHAR,            -- momentum|value|technical|breadth
    strategy_json  VARCHAR NOT NULL,
    created_at     TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_strategy_owner ON strategy_definitions (owner_user_id);
CREATE INDEX IF NOT EXISTS idx_screener_category ON screener_library (category);
