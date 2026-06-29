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

-- primary_symbol is already UNIQUE (indexed); no separate index needed.
CREATE INDEX IF NOT EXISTS idx_daily_ohlc_stock_date ON daily_ohlc (stock_id, session_date);
CREATE INDEX IF NOT EXISTS idx_corp_actions_stock ON corporate_actions (stock_id, ex_date);
