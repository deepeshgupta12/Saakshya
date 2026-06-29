"""Normalize source rows (vendor-keyed) into stored bars (stock_id-keyed).

Pipeline stages 3–4 (docs/12 §1): unify any adapter's ``OHLCRow`` to the canonical
``OhlcBar`` schema, resolving the vendor ticker to a ``stock_id``. Unmapped tickers are
reported (never silently dropped) so the pipeline can log a data-quality warning.
"""

from __future__ import annotations

from app.data.base import OHLCRow
from app.storage.repository import OhlcBar


def to_bars(
    rows: list[OHLCRow],
    ticker_to_stock_id: dict[str, int],
    as_of_version: int = 1,
) -> tuple[list[OhlcBar], list[str]]:
    """Map adapter rows to stored bars. Returns (bars, sorted unmapped tickers)."""
    bars: list[OhlcBar] = []
    unmapped: set[str] = set()
    for row in rows:
        stock_id = ticker_to_stock_id.get(row.symbol)
        if stock_id is None:
            unmapped.add(row.symbol)
            continue
        bars.append(
            OhlcBar(
                stock_id=stock_id,
                session_date=row.session_date,
                open_raw=row.open_raw,
                high_raw=row.high_raw,
                low_raw=row.low_raw,
                close_raw=row.close_raw,
                open_adj=row.open_adj,
                high_adj=row.high_adj,
                low_adj=row.low_adj,
                close_adj=row.close_adj,
                volume=row.volume,
                delivery_qty=row.delivery_qty,
                delivery_pct=row.delivery_pct,
                is_adjusted=row.is_adjusted,
                adj_factor=row.adj_factor,
                source=row.source,
                as_of_version=as_of_version,
                reconciled=False,
            )
        )
    return bars, sorted(unmapped)
