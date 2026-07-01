"""Portfolio API endpoints (docs/10 §5, docs/16, step 08).

POST /v1/portfolio/{id}/transactions  — record a transaction
GET  /v1/portfolio/{id}/positions     — current holdings
GET  /v1/portfolio/{id}/overview      — aggregate P&L metrics
GET  /v1/portfolio/{id}/health        — portfolio health score + risk drivers
GET  /v1/portfolio/{id}/ai-summary    — grounded AI portfolio summary
GET  /v1/portfolio/{id}/risk/{symbol} — per-stock risk detail

Mode-A discipline: no SL / target / entry fields anywhere in response bodies.
All AI output is grounded and audit-logged (docs/14 §7).
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.ai.portfolio_summary import (
    PortfolioPayload,
    PortfolioSummary,
    is_suppressed,
    summarize_portfolio,
)
from app.api.deps import AsOfDep, AuthUserDep, DbDep
from app.api.envelope import ok
from app.api.errors import NotFoundError
from app.portfolio.analytics import (
    aggregate_metrics,
    market_cap_exposure,
    sector_allocation,
    stock_allocation,
)
from app.portfolio.positions import Position, Transaction, TxnType, fifo_reduce
from app.risk.components import compute_health_score, compute_position_risk

router = APIRouter(prefix="/v1/portfolio", tags=["portfolio"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class TransactionIn(BaseModel):
    symbol:    str
    exchange:  str = "NSE"
    type:      str              # BUY | SELL | BONUS | SPLIT | DIVIDEND
    quantity:  float
    price:     float
    trade_date: str             # ISO date
    charges:   float = 0.0
    source:    str   = "MANUAL"


# ---------------------------------------------------------------------------
# Helpers: load transactions + positions from DB
# ---------------------------------------------------------------------------

def _load_transactions(portfolio_id: str, conn: Any) -> list[Transaction]:
    rows = conn.execute(
        "SELECT txn_id, portfolio_id, symbol, exchange, type, "
        "quantity, price, trade_date, charges, source, corp_action_adjusted, as_of_version "
        "FROM transactions WHERE portfolio_id = ? ORDER BY trade_date",
        [portfolio_id],
    ).fetchall()
    return [
        Transaction(
            txn_id=r[0], portfolio_id=r[1], symbol=r[2], exchange=r[3],
            type=r[4], quantity=float(r[5]), price=float(r[6]),
            trade_date=r[7] if isinstance(r[7], date) else date.fromisoformat(str(r[7])),
            charges=float(r[8]), source=r[9],
            corp_action_adjusted=bool(r[10]), as_of_version=int(r[11]),
        )
        for r in rows
    ]


def _hydrate_positions(
    portfolio_id: str,
    transactions: list[Transaction],
    conn: Any,
    as_of: date | None,
) -> list[Position]:
    """Build Position list from transaction ledger + daily_ohlc prices."""
    from collections import defaultdict

    txns_by_symbol: dict[str, list[Transaction]] = defaultdict(list)
    for txn in transactions:
        txns_by_symbol[txn.symbol].append(txn)

    positions: list[Position] = []
    for symbol, txns in txns_by_symbol.items():
        reduced = fifo_reduce(txns)
        if reduced["quantity"] <= 0:
            continue  # fully sold out

        # Fetch market data
        price_row = None
        if as_of is not None:
            price_row = conn.execute(
                "SELECT close_adj, close, prev_close, sma_50, sma_200, atr_14, "
                "sector, market_cap_band "
                "FROM daily_ohlc WHERE symbol = ? AND session_date = ?",
                [symbol, as_of],
            ).fetchone()

        close_adj   = float(price_row[0]) if price_row and price_row[0] else None
        close       = float(price_row[1]) if price_row and price_row[1] else None
        prev_close  = float(price_row[2]) if price_row and price_row[2] else None
        last_close  = close_adj or close
        sector      = str(price_row[6]) if price_row and price_row[6] else None
        cap_band    = str(price_row[7]) if price_row and price_row[7] else None

        qty         = reduced["quantity"]
        avg_price   = reduced["avg_buy_price"]
        current_val = round(qty * last_close, 2) if last_close else None
        unrealized  = round(current_val - reduced["invested_value"], 2) if current_val else None
        unrealized_pct = (
            round(unrealized / reduced["invested_value"] * 100, 2)
            if unrealized is not None and reduced["invested_value"]
            else None
        )
        day_chg_pct = (
            round((last_close - prev_close) / prev_close * 100, 2)
            if last_close and prev_close and prev_close
            else None
        )

        positions.append(Position(
            portfolio_id       = portfolio_id,
            symbol             = symbol,
            exchange           = txns[0].exchange,
            quantity           = qty,
            avg_buy_price      = avg_price,
            invested_value     = reduced["invested_value"],
            current_value      = current_val,
            last_close         = last_close,
            prev_close         = prev_close,
            unrealized_pnl     = unrealized,
            unrealized_pnl_pct = unrealized_pct,
            realized_pnl       = reduced["realized_pnl"],
            day_change_pct     = day_chg_pct,
            sector             = sector,
            market_cap_band    = cap_band,
            as_of_date         = as_of,
            data_confidence    = "LOW" if last_close is None else "HIGH",
        ))

    return positions


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/{portfolio_id}/transactions", status_code=201)
def add_transaction(
    portfolio_id: str,
    body:         TransactionIn,
    conn:         DbDep,
    user:         AuthUserDep,
) -> dict[str, Any]:
    """Record a transaction in the portfolio ledger."""
    # Validate portfolio belongs to this user
    row = conn.execute(
        "SELECT portfolio_id FROM portfolios WHERE portfolio_id = ? AND user_id = ?",
        [portfolio_id, user.user_id],
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Portfolio {portfolio_id!r} not found.")

    txn_id = f"txn-{uuid.uuid4().hex}"
    conn.execute(
        "INSERT INTO transactions "
        "(txn_id, portfolio_id, symbol, exchange, type, quantity, price, "
        "trade_date, charges, source) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            txn_id, portfolio_id, body.symbol.upper(), body.exchange.upper(),
            body.type.upper(), body.quantity, body.price,
            date.fromisoformat(body.trade_date), body.charges, body.source,
        ],
    )
    return ok({"txn_id": txn_id, "portfolio_id": portfolio_id}, data_confidence="high")


@router.get("/{portfolio_id}/positions")
def get_positions(
    portfolio_id: str,
    conn:         DbDep,
    as_of:        AsOfDep,
    user:         AuthUserDep,
) -> dict[str, Any]:
    """Return current open positions with P&L metrics."""
    _assert_portfolio(portfolio_id, user.user_id, conn)
    transactions = _load_transactions(portfolio_id, conn)
    positions    = _hydrate_positions(portfolio_id, transactions, conn, as_of)

    data = [
        {
            "symbol":             p.symbol,
            "exchange":           p.exchange,
            "quantity":           p.quantity,
            "avg_buy_price":      p.avg_buy_price,
            "invested_value":     p.invested_value,
            "current_value":      p.current_value,
            "last_close":         p.last_close,
            "unrealized_pnl":     p.unrealized_pnl,
            "unrealized_pnl_pct": p.unrealized_pnl_pct,
            "realized_pnl":       p.realized_pnl,
            "day_change_pct":     p.day_change_pct,
            "sector":             p.sector,
            "market_cap_band":    p.market_cap_band,
            "data_confidence":    p.data_confidence,
        }
        for p in positions
    ]
    confidence = "low" if any(p.data_confidence == "LOW" for p in positions) else "high"
    return ok(data, as_of=str(as_of), data_confidence=confidence)


@router.get("/{portfolio_id}/overview")
def get_overview(
    portfolio_id: str,
    conn:         DbDep,
    as_of:        AsOfDep,
    user:         AuthUserDep,
) -> dict[str, Any]:
    """Aggregate P&L, allocation, and market-cap exposure."""
    _assert_portfolio(portfolio_id, user.user_id, conn)
    transactions = _load_transactions(portfolio_id, conn)
    positions    = _hydrate_positions(portfolio_id, transactions, conn, as_of)

    agg       = aggregate_metrics(positions, as_of)
    stock_alloc  = stock_allocation(positions)
    sector_alloc = sector_allocation(positions)
    cap_alloc    = market_cap_exposure(positions)

    confidence = agg.get("data_confidence", "HIGH").lower()
    return ok(
        {
            "aggregate":         agg,
            "stock_allocation":  stock_alloc,
            "sector_allocation": sector_alloc,
            "cap_exposure":      cap_alloc,
        },
        as_of=str(as_of),
        data_confidence=confidence,
    )


@router.get("/{portfolio_id}/health")
def get_health(
    portfolio_id: str,
    conn:         DbDep,
    as_of:        AsOfDep,
    user:         AuthUserDep,
) -> dict[str, Any]:
    """Portfolio health score (0–100), band, and risk drivers per position."""
    _assert_portfolio(portfolio_id, user.user_id, conn)
    transactions = _load_transactions(portfolio_id, conn)
    positions    = _hydrate_positions(portfolio_id, transactions, conn, as_of)

    if not positions:
        return ok(
            {"portfolio_health_score": None, "band": None, "drivers": [], "components": []},
            data_confidence="suppressed",
        )

    total_cv = sum(p.current_value for p in positions if p.current_value) or 1.0
    pos_weights  = {p.symbol: (p.current_value or 0) / total_cv * 100 for p in positions}
    sec_weights  = _sector_weights(positions)
    micro_small  = sum(
        v for s, v in sec_weights.items()
        if s in ("MICRO", "SMALL", "MicroCap", "SmallCap")
    )

    risk_by_symbol: dict[str, Any] = {}
    for p in positions:
        indicators = _fetch_indicators(p.symbol, as_of, conn)
        rc = compute_position_risk(
            symbol                = p.symbol,
            weight_pct            = pos_weights.get(p.symbol, 0.0),
            sector_weight_pct     = sec_weights.get(p.sector or "Unknown", 0.0),
            micro_small_weight_pct= micro_small,
            indicators            = indicators,
        )
        risk_by_symbol[p.symbol] = rc

    health = compute_health_score(
        risk_components_by_symbol = risk_by_symbol,
        position_weights_pct      = pos_weights,
        sector_weights_pct        = sec_weights,
        micro_small_weight_pct    = micro_small,
    )

    components = [
        {
            "symbol":                    sym,
            "concentration_risk":        rc.concentration_risk,
            "sector_concentration_risk": rc.sector_concentration_risk,
            "volatility_risk":           rc.volatility_risk,
            "technical_breakdown_risk":  rc.technical_breakdown_risk,
            "news_risk":                 rc.news_risk,
            "cap_exposure_risk":         rc.cap_exposure_risk,
            "evidence":                  rc.evidence,
        }
        for sym, rc in risk_by_symbol.items()
    ]

    confidence = "low" if any(p.data_confidence == "LOW" for p in positions) else "high"
    return ok(
        {**health, "components": components},
        as_of=str(as_of),
        data_confidence=confidence,
    )


@router.get("/{portfolio_id}/ai-summary")
def get_ai_summary(
    portfolio_id: str,
    conn:         DbDep,
    as_of:        AsOfDep,
    user:         AuthUserDep,
) -> dict[str, Any]:
    """Grounded AI portfolio summary — Mode-A safe, audit-logged."""
    _assert_portfolio(portfolio_id, user.user_id, conn)
    transactions = _load_transactions(portfolio_id, conn)
    positions    = _hydrate_positions(portfolio_id, transactions, conn, as_of)

    agg          = aggregate_metrics(positions, as_of)
    sector_alloc = sector_allocation(positions)
    stock_alloc  = stock_allocation(positions)

    # Gather factual events from tech-breakdown risk for the payload
    events: list[str] = []
    for p in positions:
        if p.data_confidence == "LOW":
            continue
        indicators = _fetch_indicators(p.symbol, as_of, conn)
        close  = indicators.get("close_adj") or indicators.get("close")
        sma_50 = indicators.get("sma_50")
        sma_200= indicators.get("sma_200")
        if close and sma_50 and close < sma_50:
            events.append(f"{p.symbol} closed below its 50-DMA.")
        if close and sma_200 and close < sma_200:
            events.append(f"{p.symbol} closed below its 200-DMA.")

    confidence = agg.get("data_confidence", "HIGH")

    payload = PortfolioPayload(
        portfolio_id     = portfolio_id,
        as_of_date       = str(as_of),
        aggregate        = {
            "total_value":     agg.get("total_current_value"),
            "total_pnl":       agg.get("total_unrealized_pnl"),
            "total_pnl_pct":   agg.get("total_unrealized_pnl_pct"),
            "day_change_pct":  agg.get("day_change_pct"),
            "holdings_count":  agg.get("holdings_count"),
        },
        health           = {},   # health endpoint has it; AI summary uses a lightweight call
        top_allocations  = stock_alloc[:5],
        sector_allocation= sector_alloc[:5],
        events           = events,
        data_confidence  = confidence,
    )

    summary: PortfolioSummary = summarize_portfolio(payload, conn=conn)

    return ok(
        {
            "summary":     summary.summary,
            "suppressed":  summary.suppressed,
            "degraded":    summary.degraded,
            "audit_id":    summary.audit_id,
        },
        as_of=str(as_of),
        data_confidence=confidence.lower(),
    )


@router.get("/{portfolio_id}/risk/{symbol}")
def get_position_risk(
    portfolio_id: str,
    symbol:       str,
    conn:         DbDep,
    as_of:        AsOfDep,
    user:         AuthUserDep,
) -> dict[str, Any]:
    """Per-stock risk detail with evidence — Mode-A, no SL/target fields."""
    _assert_portfolio(portfolio_id, user.user_id, conn)
    transactions = _load_transactions(portfolio_id, conn)
    positions    = _hydrate_positions(portfolio_id, transactions, conn, as_of)

    sym = symbol.upper()
    pos = next((p for p in positions if p.symbol == sym), None)
    if pos is None:
        raise NotFoundError(f"Position {sym!r} not found in portfolio {portfolio_id!r}.")

    total_cv    = sum(p.current_value or 0 for p in positions) or 1.0
    sec_weights = _sector_weights(positions)
    micro_small = sum(
        v for s, v in sec_weights.items()
        if s in ("MICRO", "SMALL", "MicroCap", "SmallCap")
    )

    indicators = _fetch_indicators(sym, as_of, conn)
    rc = compute_position_risk(
        symbol                = sym,
        weight_pct            = (pos.current_value or 0) / total_cv * 100,
        sector_weight_pct     = sec_weights.get(pos.sector or "Unknown", 0.0),
        micro_small_weight_pct= micro_small,
        indicators            = indicators,
    )

    return ok(
        {
            "symbol":                    rc.symbol,
            "concentration_risk":        rc.concentration_risk,
            "sector_concentration_risk": rc.sector_concentration_risk,
            "volatility_risk":           rc.volatility_risk,
            "technical_breakdown_risk":  rc.technical_breakdown_risk,
            "news_risk":                 rc.news_risk,
            "cap_exposure_risk":         rc.cap_exposure_risk,
            "evidence":                  rc.evidence,
        },
        as_of=str(as_of),
        data_confidence="low" if pos.data_confidence == "LOW" else "high",
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _assert_portfolio(portfolio_id: str, user_id: str, conn: Any) -> None:
    row = conn.execute(
        "SELECT portfolio_id FROM portfolios WHERE portfolio_id = ? AND user_id = ?",
        [portfolio_id, user_id],
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Portfolio {portfolio_id!r} not found.")


def _sector_weights(positions: list[Position]) -> dict[str, float]:
    total = sum(p.current_value or 0 for p in positions) or 1.0
    sw: dict[str, float] = {}
    for p in positions:
        sec = p.sector or "Unknown"
        sw[sec] = sw.get(sec, 0.0) + (p.current_value or 0) / total * 100
    return sw


def _fetch_indicators(symbol: str, as_of: date | None, conn: Any) -> dict[str, Any]:
    if as_of is None:
        return {}
    row = conn.execute(
        "SELECT close_adj, close, sma_50, sma_200, atr_14 "
        "FROM daily_ohlc WHERE symbol = ? AND session_date = ?",
        [symbol, as_of],
    ).fetchone()
    if row is None:
        return {}
    return {
        "close_adj": float(row[0]) if row[0] else None,
        "close":     float(row[1]) if row[1] else None,
        "sma_50":    float(row[2]) if row[2] else None,
        "sma_200":   float(row[3]) if row[3] else None,
        "atr_14":    float(row[4]) if row[4] else None,
    }
