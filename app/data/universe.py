"""Symbol universe loading + seeding into the stock master (docs/steps/01).

The committed ``data/universe.csv`` is a representative ~50-name Nifty universe for the
local prototype. ISIN is intentionally NOT hand-entered (evidence-first: ISINs are
sourced from the Kite instrument master / a licensed vendor (D-058); ``stock_master``
keys on a generated ``stock_id`` with a unique ``primary_symbol`` until ISIN is backfilled.
Survivorship is preserved — delisted/merged names are kept, never deleted (SPEC §6.3).
"""

from __future__ import annotations

import csv
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.config import get_settings
from app.storage.repository import Repository, StockMaster

NSE = "NSE"


class UniverseEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str  # primary_symbol, e.g. "RELIANCE"
    name: str
    sector: str
    exchange: str = NSE

    @property
    def yf_ticker(self) -> str:
        """NSE ticker in the legacy ``.NS`` form; KiteSource normalises it to a Kite tradingsymbol."""
        return f"{self.symbol}.NS"


def load_universe(path: Path | None = None) -> list[UniverseEntry]:
    csv_path = path or get_settings().universe_path
    entries: list[UniverseEntry] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            entries.append(
                UniverseEntry(
                    symbol=row["symbol"].strip(),
                    name=row["name"].strip(),
                    sector=row["sector"].strip(),
                )
            )
    return entries


def seed_universe(repo: Repository, entries: list[UniverseEntry]) -> dict[str, int]:
    """Seed sector/stock/exchange-symbol tables; return ``yf_ticker -> stock_id``."""
    ticker_to_stock_id: dict[str, int] = {}
    for entry in entries:
        sector_id = repo.upsert_sector(entry.sector)
        stock_id = repo.upsert_stock(
            StockMaster(
                primary_symbol=entry.symbol,
                name=entry.name,
                sector_id=sector_id,
                status="listed",
            )
        )
        repo.upsert_exchange_symbol(stock_id, entry.exchange, entry.yf_ticker, series="EQ")
        ticker_to_stock_id[entry.yf_ticker] = stock_id
    return ticker_to_stock_id
