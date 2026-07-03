"""Portfolio API endpoints (docs/10 §5, docs/16, step 08).

POST /v1/portfolio/{id}/transactions  — record a transaction
GET  /v1/portfolio/{id}/positions     — current holdings
GET  /v1/portfolio/{id}/overview      — aggregate P&L metrics
GET  /v1/portfolio/{id}/health        — portfolio health score + risk drivers
GET  /v1/portfolio/{id}/ai-summary    — grounded AI portfolio summary
GET  /v1/portfolio/{id}/risk/{symbol} — per-stock risk detail

Polyglot (D-059): portfolios + transactions are MongoDB documents; prices, indicators,
and sector come from the TimescaleDB analytics core. AI audit is written to TimescaleDB.
Mode-A discipline: no SL / target / entry fields anywhere in response bodies.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from pymongo.database import Database

from app.ai.portfolio_summary import (
    PortfolioPayload,
    PortfolioSummary,
    summarize_portfolio,
)
from app.api.deps import AsOfDep, AuthUserDep, DbDep, MongoDep
from app.api.envelope import ok
from app.api.errors import NotFoundError
from app.portfolio.analytics import (
    aggregate_metrics,
    market_cap_exposure,
    sector_allocation,
    stock_allocation,
)
from app.portfolio.positions import Position, Transaction, fifo_reduce
from app.risk.components import compute_health_score, compute_position_risk

router = APIRouter(prefix="/v1/portfolio", tags=["portfolio"])


class TransactionIn(BaseModel):
    symbol:     str
    exchange:   str = "NSE"
    type:       str              # BUY | SELL | BONUS | SPLIT | DIVIDEND
    quantity:   float
    price:      float
    trade_date: str              # ISO date
    charges:    float = 0.0
    source:     str   = "MANUAL"


# ---------------------------------------------------------------------------
# Holdings (MongoDB) + market data (TimescaleDB)
# ---------------------------------------------------------------------------

def _assert_portfolio(portfolio_id: str, user_id: str, mongo: Database) -> None:
    if mongo.portfolios.find_one(
        {"portfolio_id": portfolio_id, "user_id": user_id}, {"portfolio_id": 1}
    ) is None:
        raise NotFoundError(f"Portfolio {portfolio_id!r} not found.")


def _load_transactions(portfolio_id: str, mongo: Database) -> list[Transaction]:
    docs = mongo.transactions.find({"portfolio_id": portfolio_id}).sort("trade_date", 1)
    txns: list[Transaction] = []
    for d in docs:
        td = d["trade_date"]
        txns.append(Transaction(
            txn_id=d["txn_id"], portfolio_id=d["portfolio_id"], symbol=d["symbol"],
            exchange=d.get("exchange", "NSE"), type=d["type"],
            quantity=float(d["quantity"]), price=float(d["price"]),
            trade_date=td if isinstance(td, date) else date.fromisoformat(str(td)[:10]),
            charges=float(d.get("charges", 0.0)), source=d.get("source", "MANUAL"),
            corp_action_adjusted=bool(d.get("corp_action_adjusted", False)),
            as_of_version=int(d.get("as_of_version", 1)),
        ))
    return txns


def _fetch_market_data(symbol: str, as_of: date | None, conn: Any) -> dict[str, Any]:
    """Prices + indicators + sector for a symbol on a date, from TimescaleDB.

    Correctly joins the real schema (stock_master → daily_ohlc / technical_indicators /
    sector_master); the previous single-table daily_ohlc query referenced columns that
    do not exist. Returns {} when the symbol/date has no data.
    """
    if as_of is None:
        return {}
    row = conn.execute(
        """
        SELECT
            ohlc.close_adj                                 AS close_adj,
            sec.name                                       AS sector,
            ti.sma_50, ti.sma_200, ti.atr_14,
            (SELECT close_adj FROM daily_ohlc p
             WHERE p.stock_id = sm.stock_id AND p.session_date < %s AND p.as_of_version = 1
             ORDER BY p.session_date DESC LIMIT 1)         AS prev_close
        FROM stock_master sm
        LEFT JOIN sector_master sec ON sec.sector_id = sm.sector_id
        LEFT JOIN daily_ohlc ohlc ON ohlc.stock_id = sm.stock_id
             AND ohlc.session_date = %s AND ohlc.as_of_version = 1
        LEFT JOIN technical_indicators ti ON ti.stock_id = sm.stock_id
             AND ti.session_date = %s AND ti.as_of_version = 1
        WHERE sm.primary_symbol = %s
        """,
        [as_of, as_of, as_of, symbol],
    ).fetchone()
    if row is None:
        return {}
    return {
        "close_adj":  float(row[0]) if row[0] is not None else None,
        "sector":     str(row[1]) if row[1] else None,
        "sma_50":     float(row[2]) if row[2] is not None else None,
        "sma_200":    float(row[3]) if row[3] is not None else None,
        "atr_14":     float(row[4]) if row[4] is not None else None,
        "prev_close": float(row[5]) if row[5] is not None else None,
    }


def _hydrate_positions(
    portfolio_id: str,
    transactions: list[Transaction],
    conn: Any,
    as_of: date | None,
) -> list[Position]:
    """Build Position list from the transaction ledger + TimescaleDB prices."""
    txns_by_symbol: dict[str, list[Transaction]] = defaultdict(list)
    for txn in transactions:
        txns_by_symbol[txn.symbol].append(txn)

    positions: list[Position] = []
    for symbol, txns in txns_by_symbol.items():
        reduced = fifo_reduce(txns)
        if reduced["quantity"] <= 0:
            continue  # fully sold out

        md          = _fetch_market_data(symbol, as_of, conn)
        last_close  = md.get("close_adj")
        prev_close  = md.get("prev_close")
        sector      = md.get("sector")

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
            if last_close and prev_close
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
            market_cap_band    = None,  # not available from the current schema
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
    mongo:        MongoDep,
    user:         AuthUserDep,
) -> dict[str, Any]:
    """Record a transaction in the portfolio ledger (MongoDB)."""
    _assert_portfolio(portfolio_id, user.user_id, mongo)
    txn_id = f"txn-{uuid.uuid4().hex}"
    mongo.transactions.insert_one({
        "txn_id": txn_id, "portfolio_id": portfolio_id,
        "symbol": body.symbol.upper(), "exchange": body.exchange.upper(),
        "type": body.type.upper(), "quantity": body.quantity, "price": body.price,
        "trade_date": date.fromisoformat(body.trade_date).isoformat(),
        "charges": body.charges, "source": body.source,
        "corp_action_adjusted": False, "as_of_version": 1,
    })
    return ok({"txn_id": txn_id, "portfolio_id": portfolio_id}, data_confidence="high")


@router.get("/{portfolio_id}/positions")
def get_positions(
    portfolio_id: str, conn: DbDep, mongo: MongoDep, as_of: AsOfDep, user: AuthUserDep
) -> dict[str, Any]:
    """Return current open positions with P&L metrics."""
    _assert_portfolio(portfolio_id, user.user_id, mongo)
    positions = _hydrate_positions(portfolio_id, _load_transactions(portfolio_id, mongo), conn, as_of)
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
    portfolio_id: str, conn: DbDep, mongo: MongoDep, as_of: AsOfDep, user: AuthUserDep
) -> dict[str, Any]:
    """Aggregate P&L, allocation, and market-cap exposure."""
    _assert_portfolio(portfolio_id, user.user_id, mongo)
    positions = _hydrate_positions(portfolio_id, _load_transactions(portfolio_id, mongo), conn, as_of)
    agg = aggregate_metrics(positions, as_of)
    return ok(
        {
            "aggregate":         agg,
            "stock_allocation":  stock_allocation(positions),
            "sector_allocation": sector_allocation(positions),
            "cap_exposure":      market_cap_exposure(positions),
        },
        as_of=str(as_of),
        data_confidence=agg.get("data_confidence", "HIGH").lower(),
    )


@router.get("/{portfolio_id}/health")
def get_health(
    portfolio_id: str, conn: DbDep, mongo: MongoDep, as_of: AsOfDep, user: AuthUserDep
) -> dict[str, Any]:
    """Portfolio health score (0–100), band, and risk drivers per position."""
    _assert_portfolio(portfolio_id, user.user_id, mongo)
    positions = _hydrate_positions(portfolio_id, _load_transactions(portfolio_id, mongo), conn, as_of)
    if not positions:
        return ok(
            {"portfolio_health_score": None, "band": None, "drivers": [], "components": []},
            data_confidence="suppressed",
        )
    total_cv    = sum(p.current_value for p in positions if p.current_value) or 1.0
    pos_weights = {p.symbol: (p.current_value or 0) / total_cv * 100 for p in positions}
    sec_weights = _sector_weights(positions)
    micro_small = sum(v for s, v in sec_weights.items()
                      if s in ("MICRO", "SMALL", "MicroCap", "SmallCap"))

    risk_by_symbol: dict[str, Any] = {}
    for p in positions:
        rc = compute_position_risk(
            symbol                 = p.symbol,
            weight_pct             = pos_weights.get(p.symbol, 0.0),
            sector_weight_pct      = sec_weights.get(p.sector or "Unknown", 0.0),
            micro_small_weight_pct = micro_small,
            indicators             = _fetch_market_data(p.symbol, as_of, conn),
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
    return ok({**health, "components": components}, as_of=str(as_of), data_confidence=confidence)


@router.get("/{portfolio_id}/ai-summary")
def get_ai_summary(
    portfolio_id: str, conn: DbDep, mongo: MongoDep, as_of: AsOfDep, user: AuthUserDep
) -> dict[str, Any]:
    """Grounded AI portfolio summary — Mode-A safe, audit-logged to TimescaleDB."""
    _assert_portfolio(portfolio_id, user.user_id, mongo)
    positions = _hydrate_positions(portfolio_id, _load_transactions(portfolio_id, mongo), conn, as_of)
    agg          = aggregate_metrics(positions, as_of)
    sector_alloc = sector_allocation(positions)
    stock_alloc  = stock_allocation(positions)

    events: list[str] = []
    for p in positions:
        if p.data_confidence == "LOW":
            continue
        md    = _fetch_market_data(p.symbol, as_of, conn)
        close = md.get("close_adj")
        if close and md.get("sma_50") and close < md["sma_50"]:
            events.append(f"{p.symbol} closed below its 50-DMA.")
        if close and md.get("sma_200") and close < md["sma_200"]:
            events.append(f"{p.symbol} closed below its 200-DMA.")

    confidence = agg.get("data_confidence", "HIGH")
    payload = PortfolioPayload(
        portfolio_id      = portfolio_id,
        as_of_date        = str(as_of),
        aggregate         = {
            "total_value":    agg.get("total_current_value"),
            "total_pnl":      agg.get("total_unrealized_pnl"),
            "total_pnl_pct":  agg.get("total_unrealized_pnl_pct"),
            "day_change_pct": agg.get("day_change_pct"),
            "holdings_count": agg.get("holdings_count"),
        },
        health            = {},
        top_allocations   = stock_alloc[:5],
        sector_allocation = sector_alloc[:5],
        events            = events,
        data_confidence   = confidence,
    )
    summary: PortfolioSummary = summarize_portfolio(payload, conn=conn)
    return ok(
        {
            "summary":    summary.summary,
            "suppressed": summary.suppressed,
            "degraded":   summary.degraded,
            "audit_id":   summary.audit_id,
        },
        as_of=str(as_of),
        data_confidence=confidence.lower(),
    )


@router.get("/{portfolio_id}/risk/{symbol}")
def get_position_risk(
    portfolio_id: str, symbol: str, conn: DbDep, mongo: MongoDep, as_of: AsOfDep, user: AuthUserDep
) -> dict[str, Any]:
    """Per-stock risk detail with evidence — Mode-A, no SL/target fields."""
    _assert_portfolio(portfolio_id, user.user_id, mongo)
    positions = _hydrate_positions(portfolio_id, _load_transactions(portfolio_id, mongo), conn, as_of)
    sym = symbol.upper()
    pos = next((p for p in positions if p.symbol == sym), None)
    if pos is None:
        raise NotFoundError(f"Position {sym!r} not found in portfolio {portfolio_id!r}.")

    total_cv    = sum(p.current_value or 0 for p in positions) or 1.0
    sec_weights = _sector_weights(positions)
    micro_small = sum(v for s, v in sec_weights.items()
                      if s in ("MICRO", "SMALL", "MicroCap", "SmallCap"))
    rc = compute_position_risk(
        symbol                 = sym,
        weight_pct             = (pos.current_value or 0) / total_cv * 100,
        sector_weight_pct      = sec_weights.get(pos.sector or "Unknown", 0.0),
        micro_small_weight_pct = micro_small,
        indicators             = _fetch_market_data(sym, as_of, conn),
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

def _sector_weights(positions: list[Position]) -> dict[str, float]:
    total = sum(p.current_value or 0 for p in positions) or 1.0
    sw: dict[str, float] = {}
    for p in positions:
        sec = p.sector or "Unknown"
        sw[sec] = sw.get(sec, 0.0) + (p.current_value or 0) / total * 100
    return sw
