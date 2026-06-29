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
        return int(
            self._conn.execute(
                "SELECT sector_id FROM sector_master WHERE name = ?", [name]
            ).fetchone()[0]
        )

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
        return int(
            self._conn.execute(
                "SELECT stock_id FROM stock_master WHERE primary_symbol = ?",
                [stock.primary_symbol],
            ).fetchone()[0]
        )

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
        return int(
            self._conn.execute(
                "SELECT id FROM exchange_symbols WHERE exchange = ? AND symbol = ?",
                [exchange, symbol],
            ).fetchone()[0]
        )

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
