"""Portfolio aggregate analytics and allocation views (docs/16 §2).

All numbers are derived from Position objects — no forward prices, no targets.
Weights sum to 100 % (± 0.1 rounding) per the acceptance criteria.
"""

from __future__ import annotations

from typing import Any

from app.portfolio.positions import Position


def aggregate_metrics(positions: list[Position], as_of_date: Any = None) -> dict[str, Any]:
    """Compute portfolio-level totals from a list of hydrated positions."""
    total_invested       = sum(p.invested_value for p in positions)
    total_current        = sum(p.current_value for p in positions if p.current_value is not None)
    total_unrealized_pnl = sum(p.unrealized_pnl for p in positions if p.unrealized_pnl is not None)
    total_realized_pnl   = sum(p.realized_pnl for p in positions)
    day_change_value     = sum(
        (p.current_value - (p.current_value / (1 + p.day_change_pct / 100)))
        for p in positions
        if p.current_value is not None and p.day_change_pct is not None
    )
    holdings_count = len(positions)

    total_pnl_pct = (
        round(total_unrealized_pnl / total_invested * 100, 2) if total_invested else None
    )
    day_pnl_pct = (
        round(day_change_value / (total_current - day_change_value) * 100, 2)
        if (total_current - day_change_value) else None
    )

    any_low = any(p.data_confidence == "LOW" for p in positions)
    confidence = "LOW" if any_low else ("HIGH" if positions else "SUPPRESSED")

    return {
        "total_invested":          round(total_invested, 2),
        "total_current_value":     round(total_current, 2),
        "total_unrealized_pnl":    round(total_unrealized_pnl, 2),
        "total_unrealized_pnl_pct": total_pnl_pct,
        "total_realized_pnl_ytd":  round(total_realized_pnl, 2),
        "day_change_value":        round(day_change_value, 2),
        "day_change_pct":          day_pnl_pct,
        "holdings_count":          holdings_count,
        "data_confidence":         confidence,
        "as_of_date":              str(as_of_date) if as_of_date else None,
    }


def stock_allocation(positions: list[Position]) -> list[dict[str, Any]]:
    """Per-position allocation (weight_pct), sorted by weight DESC."""
    total = sum(p.current_value for p in positions if p.current_value is not None)
    rows = []
    for p in positions:
        cv = p.current_value
        rows.append({
            "symbol":     p.symbol,
            "value":      round(cv, 2) if cv is not None else None,
            "weight_pct": round(cv / total * 100, 2) if (cv and total) else None,
        })
    rows.sort(key=lambda r: r["weight_pct"] or 0, reverse=True)
    return rows


def sector_allocation(positions: list[Position]) -> list[dict[str, Any]]:
    """Sector-level allocation — weights sum to 100 % (± 0.1)."""
    total = sum(p.current_value for p in positions if p.current_value is not None)
    sector_values: dict[str, float] = {}
    for p in positions:
        if p.current_value is None:
            continue
        sec = p.sector or "Unknown"
        sector_values[sec] = sector_values.get(sec, 0.0) + p.current_value

    rows = [
        {
            "sector":     sec,
            "value":      round(val, 2),
            "weight_pct": round(val / total * 100, 2) if total else None,
        }
        for sec, val in sector_values.items()
    ]
    rows.sort(key=lambda r: r["weight_pct"] or 0, reverse=True)
    return rows


def market_cap_exposure(positions: list[Position]) -> list[dict[str, Any]]:
    """Market-cap band allocation."""
    total = sum(p.current_value for p in positions if p.current_value is not None)
    band_values: dict[str, float] = {}
    for p in positions:
        if p.current_value is None:
            continue
        band = p.market_cap_band or "UNKNOWN"
        band_values[band] = band_values.get(band, 0.0) + p.current_value

    rows = [
        {
            "band":       band,
            "value":      round(val, 2),
            "weight_pct": round(val / total * 100, 2) if total else None,
        }
        for band, val in band_values.items()
    ]
    rows.sort(key=lambda r: r["weight_pct"] or 0, reverse=True)
    return rows
