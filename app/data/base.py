"""The single vendor-agnostic data seam (SPEC §8, docs/12 §3.1).

Business logic (indicators, scanners, AI) depends ONLY on this interface, never on a
concrete vendor — so swapping yfinance → NSE Bhavcopy → a licensed vendor touches no
downstream code. Each source declares capabilities via ``supports(...)``; the
publish-guard refuses commercial output from non-redistributable sources.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class OHLCRow(BaseModel):
    """One EOD bar as returned by a source, keyed by the source's symbol/ticker."""

    model_config = ConfigDict(extra="forbid")
    symbol: str
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
    source: str = "unknown"


class DeliveryRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str
    session_date: date
    delivery_qty: int
    delivery_pct: float


class CorpActionRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str
    action_type: str  # split | bonus | dividend | rights | merger | symbol_change
    ex_date: date
    ratio_from: float | None = None
    ratio_to: float | None = None
    dividend_amount: float | None = None
    new_symbol: str | None = None
    source: str = "unknown"


# Capabilities a source may declare.
CAP_ADJUSTED = "adjusted"
CAP_DELIVERY_PCT = "delivery_pct"
CAP_REDISTRIBUTION = "redistribution"


@runtime_checkable
class DataSource(Protocol):
    """Contract every EOD source implements (docs/12 §3.1)."""

    name: str

    def fetch_history(self, symbols: Iterable[str], period: str) -> list[OHLCRow]:
        """Full-history backfill for the given tickers (used by M0 ingest)."""
        ...

    def fetch_eod(self, symbols: Iterable[str], session_date: date) -> list[OHLCRow]:
        """The bars for a single session (daily incremental; used from the pipeline)."""
        ...

    def fetch_delivery(self, session_date: date) -> list[DeliveryRow] | None:
        """Delivery quantity/percentage, or ``None`` if the source lacks it."""
        ...

    def fetch_corporate_actions(
        self, symbols: Iterable[str], since: date
    ) -> list[CorpActionRow]:
        """Corporate actions feeding the corp-action master (SPEC §6.1)."""
        ...

    def supports(self, capability: str) -> bool:
        """Whether this source provides ``capability`` (e.g. ``CAP_REDISTRIBUTION``)."""
        ...


class PublishGuardError(RuntimeError):
    """Raised when commercial publish is attempted from a non-redistributable source."""


def assert_publishable(source: DataSource) -> None:
    """Block commercial publishing of data from sources without redistribution rights.

    Kite Connect data is licensed for the authenticated user only; commercial
    redistribution stays blocked until a redistribution licence is in force (SPEC §8).
    """
    if not source.supports(CAP_REDISTRIBUTION):
        raise PublishGuardError(
            f"Source '{source.name}' has no commercial redistribution rights; "
            "personal/local use only (SPEC §8)."
        )


def get_source(name: str | None = None) -> DataSource:
    """Return the configured (or named) data source. Defaults to settings.active_data_source.

    Kite Connect is the sole supported source (D-058); yfinance/Bhavcopy were removed.
    """
    # Imported lazily to keep the seam dependency-light and avoid import cycles.
    from app.config import get_settings

    resolved = name or get_settings().active_data_source
    if resolved == "kite":
        from app.data.kite_source import KiteSource

        return KiteSource()
    raise ValueError(f"Unknown or not-yet-registered data source: {resolved!r}")
