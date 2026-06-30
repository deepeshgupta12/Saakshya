"""Typed repository over DuckDB (docs/27 §3.2 — no bare dicts across boundaries).

Point-in-time discipline (SPEC §6.2): a restatement is written as a NEW
``as_of_version`` (a new row), never an overwrite of history. Reads return the
latest ``as_of_version`` per (stock_id, session_date).
"""

from __future__ import annotations

from datetime import date

import duckdb
from pydantic import BaseModel, ConfigDict


class StockMaster(BaseModel):
    """A listed (or delisted/merged — never deleted) instrument."""

    model_config = ConfigDict(extra="forbid")
    stock_id: int | None = None
    primary_symbol: str
    name: str
    sector_id: int | None = None
    isin: str | None = None
    parent_isin: str | None = None
    status: str = "listed"
    listed_on: date | None = None
    delisted_on: date | None = None


class OhlcBar(BaseModel):
    """One stored EOD bar — both raw and adjusted, point-in-time versioned."""

    model_config = ConfigDict(extra="forbid")
    stock_id: int
    session_date: date
    open_raw: float
    high_raw: float
    low_raw: float
    close_raw: float
    open_adj: float
    high_adj: float
    low_adj: float
    close_adj: float
    volume: int
    delivery_qty: int | None = None
    delivery_pct: float | None = None
    is_adjusted: bool = False
    adj_factor: float = 1.0
    source: str = "yfinance"
    as_of_version: int = 1
    reconciled: bool = False


class DataQualityLog(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str
    source: str
    check_type: str
    severity: str = "info"
    status: str = "ok"
    session_date: date | None = None
    stock_id: int | None = None
    detail: str | None = None


class CorpActionRecord(BaseModel):
    """One corporate action row — stores the single-event backward price-adjustment factor."""

    model_config = ConfigDict(extra="forbid")
    action_id: int | None = None
    stock_id: int
    action_type: str  # split | bonus | dividend | rights | merger | symbol_change
    ex_date: date
    ratio_from: float | None = None
    ratio_to: float | None = None
    dividend_amount: float | None = None
    new_symbol: str | None = None
    factor: float | None = None  # single-event backward adj factor; None if not computable yet
    source: str
    reconciled: bool = False
    as_of_version: int = 1


_OHLC_COLS = (
    "stock_id, session_date, open_raw, high_raw, low_raw, close_raw, "
    "open_adj, high_adj, low_adj, close_adj, volume, delivery_qty, delivery_pct, "
    "is_adjusted, adj_factor, source, as_of_version, reconciled"
)


class Repository:
    """Thin typed data-access layer bound to an open DuckDB connection."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    # --- reference data -------------------------------------------------
    def upsert_sector(self, name: str) -> int:
        row = self._conn.execute(
            "SELECT sector_id FROM sector_master WHERE name = ?", [name]
        ).fetchone()
        if row is not None:
            return int(row[0])
        self._conn.execute("INSERT INTO sector_master (name) VALUES (?)", [name])
        inserted = self._conn.execute(
            "SELECT sector_id FROM sector_master WHERE name = ?", [name]
        ).fetchone()
        assert inserted is not None
        return int(inserted[0])

    def upsert_stock(self, stock: StockMaster) -> int:
        """Get-or-insert by ``primary_symbol`` (idempotent). Returns the stock_id.

        Existing rows are returned as-is (not mutated) — DuckDB's UPDATE/ON-CONFLICT
        has constraint-index limitations on this sequence-keyed table, and seeding only
        needs stable identity. Metadata restatements are handled via the as-of pipeline.
        """
        existing = self.get_stock_id(stock.primary_symbol)
        if existing is not None:
            return existing
        self._conn.execute(
            "INSERT INTO stock_master "
            "(isin, primary_symbol, name, sector_id, parent_isin, status, listed_on, delisted_on) "
            "VALUES (?,?,?,?,?,?,?,?)",
            [
                stock.isin, stock.primary_symbol, stock.name, stock.sector_id,
                stock.parent_isin, stock.status, stock.listed_on, stock.delisted_on,
            ],
        )
        inserted = self._conn.execute(
            "SELECT stock_id FROM stock_master WHERE primary_symbol = ?",
            [stock.primary_symbol],
        ).fetchone()
        assert inserted is not None
        return int(inserted[0])

    def get_stock_id(self, primary_symbol: str) -> int | None:
        row = self._conn.execute(
            "SELECT stock_id FROM stock_master WHERE primary_symbol = ?", [primary_symbol]
        ).fetchone()
        return int(row[0]) if row is not None else None

    def upsert_exchange_symbol(
        self, stock_id: int, exchange: str, symbol: str, series: str | None = None
    ) -> int:
        row = self._conn.execute(
            "SELECT id FROM exchange_symbols WHERE exchange = ? AND symbol = ?",
            [exchange, symbol],
        ).fetchone()
        if row is not None:
            return int(row[0])
        self._conn.execute(
            "INSERT INTO exchange_symbols (stock_id, exchange, symbol, series) VALUES (?,?,?,?)",
            [stock_id, exchange, symbol, series],
        )
        inserted = self._conn.execute(
            "SELECT id FROM exchange_symbols WHERE exchange = ? AND symbol = ?",
            [exchange, symbol],
        ).fetchone()
        assert inserted is not None
        return int(inserted[0])

    def resolve_ticker(self, exchange: str, symbol: str, on: date | None = None) -> int | None:
        """Resolve a vendor ticker → stock_id, honoring symbol-change validity windows."""
        as_of = on or date.today()
        row = self._conn.execute(
            "SELECT stock_id FROM exchange_symbols WHERE exchange = ? AND symbol = ? "
            "AND valid_from <= ? AND (valid_to IS NULL OR valid_to >= ?) "
            "ORDER BY valid_from DESC LIMIT 1",
            [exchange, symbol, as_of, as_of],
        ).fetchone()
        return int(row[0]) if row is not None else None

    # --- EOD bars -------------------------------------------------------
    def upsert_ohlc(self, bars: list[OhlcBar]) -> int:
        if not bars:
            return 0
        params = [
            [
                b.stock_id, b.session_date, b.open_raw, b.high_raw, b.low_raw, b.close_raw,
                b.open_adj, b.high_adj, b.low_adj, b.close_adj, b.volume, b.delivery_qty,
                b.delivery_pct, b.is_adjusted, b.adj_factor, b.source, b.as_of_version,
                b.reconciled,
            ]
            for b in bars
        ]
        self._conn.executemany(
            f"INSERT INTO daily_ohlc ({_OHLC_COLS}) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT (stock_id, session_date, as_of_version) DO UPDATE SET "
            "open_raw=excluded.open_raw, high_raw=excluded.high_raw, low_raw=excluded.low_raw, "
            "close_raw=excluded.close_raw, open_adj=excluded.open_adj, high_adj=excluded.high_adj, "
            "low_adj=excluded.low_adj, close_adj=excluded.close_adj, volume=excluded.volume, "
            "delivery_qty=excluded.delivery_qty, delivery_pct=excluded.delivery_pct, "
            "is_adjusted=excluded.is_adjusted, adj_factor=excluded.adj_factor, "
            "source=excluded.source, reconciled=excluded.reconciled, ingested_at=now()",
            params,
        )
        return len(params)

    def count_ohlc(self, stock_id: int | None = None) -> int:
        if stock_id is None:
            row = self._conn.execute("SELECT count(*) FROM daily_ohlc").fetchone()
        else:
            row = self._conn.execute(
                "SELECT count(*) FROM daily_ohlc WHERE stock_id = ?", [stock_id]
            ).fetchone()
        assert row is not None  # count() always returns a row
        return int(row[0])

    def max_as_of_version(self, stock_id: int, session_date: date) -> int | None:
        row = self._conn.execute(
            "SELECT max(as_of_version) FROM daily_ohlc WHERE stock_id=? AND session_date=?",
            [stock_id, session_date],
        ).fetchone()
        return int(row[0]) if row and row[0] is not None else None

    def latest_bars(self, stock_id: int, limit: int = 5) -> list[OhlcBar]:
        """Return the most recent bars, taking the latest as_of_version per session."""
        rows = self._conn.execute(
            f"SELECT {_OHLC_COLS} FROM daily_ohlc WHERE stock_id = ? "
            "QUALIFY row_number() OVER (PARTITION BY session_date ORDER BY as_of_version DESC) = 1 "
            "ORDER BY session_date DESC LIMIT ?",
            [stock_id, limit],
        ).fetchall()
        cols = [c.strip() for c in _OHLC_COLS.split(",")]
        return [OhlcBar(**dict(zip(cols, r, strict=True))) for r in rows]

    # --- corporate actions ----------------------------------------------
    def upsert_corporate_action(self, rec: CorpActionRecord) -> None:
        """Insert or skip (idempotent) by (stock_id, action_type, ex_date)."""
        exists = self._conn.execute(
            "SELECT action_id FROM corporate_actions "
            "WHERE stock_id=? AND action_type=? AND ex_date=?",
            [rec.stock_id, rec.action_type, rec.ex_date],
        ).fetchone()
        if exists is not None:
            return
        self._conn.execute(
            "INSERT INTO corporate_actions "
            "(stock_id, action_type, ex_date, ratio_from, ratio_to, dividend_amount, "
            "new_symbol, factor, source, reconciled, as_of_version) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [
                rec.stock_id, rec.action_type, rec.ex_date,
                rec.ratio_from, rec.ratio_to, rec.dividend_amount,
                rec.new_symbol, rec.factor, rec.source, rec.reconciled, rec.as_of_version,
            ],
        )

    def get_corporate_actions(self, stock_id: int) -> list[CorpActionRecord]:
        """All actions for a stock, ordered by ex_date ASC."""
        rows = self._conn.execute(
            "SELECT action_id, stock_id, action_type, ex_date, ratio_from, ratio_to, "
            "dividend_amount, new_symbol, factor, source, reconciled, as_of_version "
            "FROM corporate_actions WHERE stock_id=? ORDER BY ex_date ASC",
            [stock_id],
        ).fetchall()
        return [
            CorpActionRecord(
                action_id=r[0], stock_id=r[1], action_type=r[2], ex_date=r[3],
                ratio_from=r[4], ratio_to=r[5], dividend_amount=r[6],
                new_symbol=r[7], factor=r[8], source=r[9], reconciled=bool(r[10]),
                as_of_version=r[11],
            )
            for r in rows
        ]

    def get_all_bars(self, stock_id: int, as_of_version: int = 1) -> list[OhlcBar]:
        """All bars for a stock at the given as_of_version, ordered by session_date ASC."""
        rows = self._conn.execute(
            f"SELECT {_OHLC_COLS} FROM daily_ohlc "
            "WHERE stock_id=? AND as_of_version=? ORDER BY session_date ASC",
            [stock_id, as_of_version],
        ).fetchall()
        cols = [c.strip() for c in _OHLC_COLS.split(",")]
        return [OhlcBar(**dict(zip(cols, r, strict=True))) for r in rows]

    def update_bar_adjustments(
        self,
        stock_id: int,
        as_of_version: int,
        updates: list[tuple[float, float, float, float, float, bool, bool, date]],
    ) -> int:
        """Bulk-update adj columns (no as_of bump — adjustment derives from stored corp actions).

        Each tuple: (adj_factor, open_adj, high_adj, low_adj, close_adj, is_adjusted,
                     reconciled, session_date)
        """
        if not updates:
            return 0
        params = [(u[0], u[1], u[2], u[3], u[4], u[5], u[6], stock_id, u[7], as_of_version)
                  for u in updates]
        self._conn.executemany(
            "UPDATE daily_ohlc SET "
            "adj_factor=?, open_adj=?, high_adj=?, low_adj=?, close_adj=?, "
            "is_adjusted=?, reconciled=? "
            "WHERE stock_id=? AND session_date=? AND as_of_version=?",
            params,
        )
        return len(params)

    # --- data quality ---------------------------------------------------
    def write_quality_log(self, log: DataQualityLog) -> None:
        self._conn.execute(
            "INSERT INTO data_quality_logs "
            "(job_id, source, session_date, stock_id, check_type, severity, status, detail) "
            "VALUES (?,?,?,?,?,?,?,?)",
            [
                log.job_id, log.source, log.session_date, log.stock_id,
                log.check_type, log.severity, log.status, log.detail,
            ],
        )

    # --- technical indicators -------------------------------------------
    def get_indicators_for_date(
        self,
        session_date: date,
        as_of_version: int = 1,
    ) -> list[dict[str, object]]:
        """All indicator rows for a session date (one per stock, latest indicator_version).

        Returns a list of dicts keyed by column name, including stock_id and
        primary_symbol for scanner use.
        """
        rows = self._conn.execute(
            "SELECT ti.stock_id, sm.primary_symbol, "
            "ti.rsi_14, ti.sma_20, ti.sma_50, ti.sma_200, ti.ema_21, ti.atr_14, "
            "ti.macd_line, ti.macd_signal, ti.bb_upper, ti.bb_mid, ti.bb_lower, "
            "ti.adx_14, ti.stoch_rsi_k, ti.stoch_rsi_d, "
            "ti.pivot, ti.pivot_r1, ti.pivot_r2, ti.pivot_s1, ti.pivot_s2, "
            "ti.vwap, ti.ret_5d, ti.ret_21d, ti.ret_63d, ti.ret_126d, "
            "ti.volume_ratio_20, ti.rel_strength_63d "
            "FROM technical_indicators ti "
            "JOIN stock_master sm ON sm.stock_id = ti.stock_id "
            "WHERE ti.session_date = ? AND ti.as_of_version = ? "
            "QUALIFY row_number() OVER "
            "  (PARTITION BY ti.stock_id ORDER BY ti.indicator_version DESC) = 1",
            [session_date, as_of_version],
        ).fetchall()

        cols = [
            "stock_id", "symbol",
            "rsi_14", "sma_20", "sma_50", "sma_200", "ema_21", "atr_14",
            "macd_line", "macd_signal", "bb_upper", "bb_mid", "bb_lower",
            "adx_14", "stoch_rsi_k", "stoch_rsi_d",
            "pivot", "pivot_r1", "pivot_r2", "pivot_s1", "pivot_s2",
            "vwap", "ret_5d", "ret_21d", "ret_63d", "ret_126d",
            "volume_ratio_20", "rel_strength_63d",
        ]
        return [dict(zip(cols, r, strict=True)) for r in rows]

    def count_indicators(self, session_date: date | None = None) -> int:
        if session_date is None:
            row = self._conn.execute(
                "SELECT count(*) FROM technical_indicators"
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT count(*) FROM technical_indicators WHERE session_date=?",
                [session_date],
            ).fetchone()
        assert row is not None
        return int(row[0])

    # --- scanner results ------------------------------------------------
    def upsert_scanner_result(
        self,
        scanner: str,
        stock_id: int,
        session_date: date,
        composite_score: float | None,
        sub_scores_json: str,
        facts_json: str,
        signal_tags_json: str,
        risk_flags_json: str,
        data_confidence: str,
        weights_version: str,
        validation_status: str,
        as_of_version: int,
        engine_version: str,
    ) -> None:
        self._conn.execute(
            "INSERT INTO scanner_results "
            "(scanner, stock_id, session_date, composite_score, sub_scores, facts, "
            "signal_tags, risk_flags, data_confidence, weights_version, validation_status, "
            "as_of_version, engine_version) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT (scanner, stock_id, session_date, as_of_version) DO UPDATE SET "
            "composite_score=excluded.composite_score, sub_scores=excluded.sub_scores, "
            "facts=excluded.facts, signal_tags=excluded.signal_tags, "
            "risk_flags=excluded.risk_flags, data_confidence=excluded.data_confidence, "
            "weights_version=excluded.weights_version, "
            "validation_status=excluded.validation_status, "
            "engine_version=excluded.engine_version, computed_at=now()",
            [
                scanner, stock_id, session_date, composite_score,
                sub_scores_json, facts_json, signal_tags_json, risk_flags_json,
                data_confidence, weights_version, validation_status,
                as_of_version, engine_version,
            ],
        )

    def count_scanner_results(self, scanner: str | None = None) -> int:
        if scanner is None:
            row = self._conn.execute(
                "SELECT count(*) FROM scanner_results"
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT count(*) FROM scanner_results WHERE scanner=?", [scanner]
            ).fetchone()
        assert row is not None
        return int(row[0])
