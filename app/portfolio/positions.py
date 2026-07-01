"""Transaction ledger, FIFO/WAVG reducer, position reconstruction, corp-action synthesizer.

Source of truth: transactions table (docs/16 §1.1–1.5).
- reconstruct_positions() rebuilds current holdings from the ledger.
- fifo_reduce() computes realized P&L under FIFO costing.
- synthesize_corp_action_txns() inserts BONUS/SPLIT ledger rows so cost basis
  stays correct through corp actions (a 1:1 bonus doubles qty, halves avg cost — never
  reads as a 50% loss).

Mode-A discipline: no target / stop / entry / return-forecast fields anywhere.
"""

from __future__ import annotations

import math
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import date
from typing import Any


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class TxnType:
    BUY         = "BUY"
    SELL        = "SELL"
    BONUS       = "BONUS"
    SPLIT       = "SPLIT"
    DIVIDEND    = "DIVIDEND"
    RIGHTS      = "RIGHTS"
    MERGER_IN   = "MERGER_IN"
    MERGER_OUT  = "MERGER_OUT"


@dataclass
class Transaction:
    txn_id:               str
    portfolio_id:         str
    symbol:               str
    exchange:             str
    type:                 str
    quantity:             float
    price:                float
    trade_date:           date
    charges:              float = 0.0
    source:               str   = "MANUAL"
    corp_action_adjusted: bool  = False
    as_of_version:        int   = 1


@dataclass
class Position:
    portfolio_id:         str
    symbol:               str
    exchange:             str
    quantity:             float
    avg_buy_price:        float
    invested_value:       float
    current_value:        float | None     = None
    last_close:           float | None     = None
    prev_close:           float | None     = None
    unrealized_pnl:       float | None     = None
    unrealized_pnl_pct:   float | None     = None
    realized_pnl:         float            = 0.0
    day_change_pct:       float | None     = None
    sector:               str | None       = None
    market_cap_band:      str | None       = None
    as_of_date:           date | None      = None
    data_confidence:      str              = "HIGH"


# ---------------------------------------------------------------------------
# FIFO reducer
# ---------------------------------------------------------------------------

def fifo_reduce(transactions: list[Transaction]) -> dict[str, Any]:
    """Reduce a sorted list of transactions to current holdings and realized P&L.

    Returns:
        {
            "quantity": float,
            "avg_buy_price": float,
            "invested_value": float,
            "realized_pnl": float,
            "lots": list of (qty, price) — remaining buy lots (FIFO queue),
        }

    Supports BUY, SELL, BONUS, SPLIT, DIVIDEND, RIGHTS, MERGER_IN, MERGER_OUT.
    - BONUS (ratio_from=1, ratio_to=1 → 1:1): doubles qty, halves cost per share.
    - SPLIT (e.g. 1:2 → for each 1 share, you get 2 shares total): multiplies qty,
      divides cost per share accordingly.
    """
    lots: deque[list[float]] = deque()   # [quantity, cost_per_share]
    realized_pnl  = 0.0

    sorted_txns = sorted(transactions, key=lambda t: t.trade_date)

    for txn in sorted_txns:
        t = txn.type

        if t == TxnType.BUY or t == TxnType.MERGER_IN or t == TxnType.RIGHTS:
            cost_per_share = (txn.price + txn.charges / txn.quantity) if txn.quantity else txn.price
            lots.append([txn.quantity, cost_per_share])

        elif t == TxnType.SELL or t == TxnType.MERGER_OUT:
            remaining = txn.quantity
            proceeds  = txn.price * txn.quantity - txn.charges
            cost_consumed = 0.0
            while remaining > 0 and lots:
                lot_qty, lot_price = lots[0]
                consume = min(lot_qty, remaining)
                cost_consumed += consume * lot_price
                remaining   -= consume
                lots[0][0]  -= consume
                if lots[0][0] <= 1e-9:
                    lots.popleft()
            realized_pnl += proceeds - cost_consumed

        elif t == TxnType.BONUS:
            # ratio_from:ratio_to stored in txn.price as ratio_to/ratio_from
            # txn.quantity holds the *extra* shares added (not the new total).
            # For a 1:1 bonus, quantity = existing qty, price = 0.
            extra_qty = txn.quantity
            if extra_qty > 0 and lots:
                total_qty = sum(l[0] for l in lots) + extra_qty
                total_cost = sum(l[0] * l[1] for l in lots)
                if total_qty > 0:
                    new_avg = total_cost / total_qty
                    new_lots: deque[list[float]] = deque()
                    for lot in lots:
                        proportion = (lot[0] / (total_qty - extra_qty)) if total_qty > extra_qty else 0
                        new_lots.append([lot[0] + proportion * extra_qty, new_avg])
                    lots = new_lots

        elif t == TxnType.SPLIT:
            # txn.price holds the split factor (new_qty / old_qty).
            # E.g. a 1:2 split → factor=2 → each lot quantity×2, price÷2.
            factor = txn.price if txn.price > 0 else 1.0
            for lot in lots:
                lot[1] = lot[1] / factor
                lot[0] = lot[0] * factor

        elif t in (TxnType.DIVIDEND,):
            pass  # Cash dividend — no quantity or avg-cost effect

    # Reconstruct summary from remaining lots
    total_qty   = sum(l[0] for l in lots)
    total_cost  = sum(l[0] * l[1] for l in lots)
    avg_price   = total_cost / total_qty if total_qty > 0 else 0.0
    invested    = total_qty * avg_price

    return {
        "quantity":      round(total_qty, 6),
        "avg_buy_price": round(avg_price, 4),
        "invested_value": round(invested, 2),
        "realized_pnl":  round(realized_pnl, 2),
        "lots":          [[round(l[0], 6), round(l[1], 4)] for l in lots],
    }


# ---------------------------------------------------------------------------
# Corp-action transaction synthesizer
# ---------------------------------------------------------------------------

def synthesize_corp_action_txns(
    portfolio_id: str,
    symbol:       str,
    exchange:     str,
    corp_actions: list[dict[str, Any]],  # from corporate_actions master
    existing_txns: list[Transaction],
) -> list[Transaction]:
    """Synthesize BONUS/SPLIT/DIVIDEND transactions from the corporate_actions master.

    Only synthesizes actions whose ex_date is *after* the first BUY in existing_txns.
    Returns only the *new* synthetic transactions (caller deduplicates by trade_date+type).
    """
    if not existing_txns:
        return []

    first_buy = min(
        (t.trade_date for t in existing_txns if t.type == TxnType.BUY),
        default=None,
    )
    if first_buy is None:
        return []

    existing_dates_types = {(t.trade_date, t.type) for t in existing_txns
                            if t.source == "CORP_ACTION"}

    synth: list[Transaction] = []
    for ca in corp_actions:
        ex_date     = ca.get("ex_date")
        action_type = ca.get("action_type", "")
        if not ex_date or ex_date <= first_buy:
            continue

        if action_type == "bonus":
            ratio_from = ca.get("ratio_from") or 1.0
            ratio_to   = ca.get("ratio_to")   or 1.0
            key = (ex_date, TxnType.BONUS)
            if key in existing_dates_types:
                continue
            # extra_qty = existing_qty × (ratio_to / ratio_from)
            # We record as a synthetic BUY at 0 price; FIFO reducer treats type=BONUS specially.
            # Quantity is the ratio_to/ratio_from factor used to scale existing lots.
            synth.append(Transaction(
                txn_id=str(uuid.uuid4()),
                portfolio_id=portfolio_id,
                symbol=symbol,
                exchange=exchange,
                type=TxnType.BONUS,
                quantity=ratio_to / ratio_from,   # extra shares per existing share
                price=0.0,
                trade_date=ex_date,
                source="CORP_ACTION",
                corp_action_adjusted=True,
            ))

        elif action_type == "split":
            ratio_from = ca.get("ratio_from") or 1.0
            ratio_to   = ca.get("ratio_to")   or 1.0
            key = (ex_date, TxnType.SPLIT)
            if key in existing_dates_types:
                continue
            factor = ratio_to / ratio_from   # new_qty / old_qty
            synth.append(Transaction(
                txn_id=str(uuid.uuid4()),
                portfolio_id=portfolio_id,
                symbol=symbol,
                exchange=exchange,
                type=TxnType.SPLIT,
                quantity=0.0,          # quantity not used for splits
                price=factor,          # factor encoded in price field
                trade_date=ex_date,
                source="CORP_ACTION",
                corp_action_adjusted=True,
            ))

        elif action_type == "dividend":
            key = (ex_date, TxnType.DIVIDEND)
            if key in existing_dates_types:
                continue
            synth.append(Transaction(
                txn_id=str(uuid.uuid4()),
                portfolio_id=portfolio_id,
                symbol=symbol,
                exchange=exchange,
                type=TxnType.DIVIDEND,
                quantity=0.0,
                price=ca.get("dividend_amount") or 0.0,
                trade_date=ex_date,
                source="CORP_ACTION",
                corp_action_adjusted=True,
            ))

    return synth


# ---------------------------------------------------------------------------
# Position reconstruction
# ---------------------------------------------------------------------------

def reconstruct_positions(
    portfolio_id: str,
    txns_by_symbol: dict[str, list[Transaction]],
    prices: dict[str, dict[str, Any]],   # symbol → {close_adj, prev_close, session_date}
    stock_master: dict[str, dict[str, Any]] | None = None,
) -> list[Position]:
    """Reconstruct positions from the transaction ledger for a portfolio.

    Args:
        txns_by_symbol: {symbol: sorted list of Transaction}
        prices:         {symbol: {"close_adj": float, "prev_close": float|None, "date": date|None}}
        stock_master:   {symbol: {"sector": str|None, "market_cap_band": str|None}}

    Returns:
        List of Position with current_value and P&L hydrated where prices available.
        data_confidence is LOW when close_adj is missing.
    """
    positions: list[Position] = []
    sm = stock_master or {}

    for symbol, txns in txns_by_symbol.items():
        if not txns:
            continue

        reduced = fifo_reduce(txns)
        qty = reduced["quantity"]
        if qty <= 1e-9:
            continue   # fully sold out

        avg_price    = reduced["avg_buy_price"]
        invested_val = reduced["invested_value"]
        realized_pnl = reduced["realized_pnl"]

        price_info       = prices.get(symbol, {})
        last_close       = price_info.get("close_adj")
        prev_close       = price_info.get("prev_close")
        as_of_date       = price_info.get("date")

        if last_close is None:
            data_conf = "LOW"
            current_val = None
            unrealized  = None
            unr_pct     = None
            day_chg_pct = None
        else:
            data_conf   = "HIGH"
            current_val = round(qty * last_close, 2)
            unrealized  = round(current_val - invested_val, 2)
            unr_pct     = round(unrealized / invested_val * 100, 2) if invested_val else None
            day_chg_pct = (
                round((last_close - prev_close) / prev_close * 100, 2)
                if prev_close and prev_close > 0 else None
            )

        meta = sm.get(symbol, {})
        positions.append(Position(
            portfolio_id      = portfolio_id,
            symbol            = symbol,
            exchange          = txns[0].exchange,
            quantity          = qty,
            avg_buy_price     = avg_price,
            invested_value    = invested_val,
            current_value     = current_val,
            last_close        = last_close,
            prev_close        = prev_close,
            unrealized_pnl    = unrealized,
            unrealized_pnl_pct= unr_pct,
            realized_pnl      = realized_pnl,
            day_change_pct    = day_chg_pct,
            sector            = meta.get("sector"),
            market_cap_band   = meta.get("market_cap_band"),
            as_of_date        = as_of_date,
            data_confidence   = data_conf,
        ))

    return positions
