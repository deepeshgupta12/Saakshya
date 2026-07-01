"""Tests for FIFO reducer, corp-action synthesizer, position reconstruction."""

from __future__ import annotations

from datetime import date

import pytest

from app.portfolio.positions import (
    Position,
    Transaction,
    TxnType,
    fifo_reduce,
    synthesize_corp_action_txns,
)

_PID = "port-001"
_SYM = "INFY"


def _txn(type_: str, qty: float, price: float, day: int = 1, charges: float = 0.0) -> Transaction:
    return Transaction(
        txn_id      = f"txn-{type_}-{day}",
        portfolio_id= _PID,
        symbol      = _SYM,
        exchange    = "NSE",
        type        = type_,
        quantity    = qty,
        price       = price,
        trade_date  = date(2024, 1, day),
        charges     = charges,
    )


class TestFifoReduce:
    def test_single_buy(self):
        txns = [_txn(TxnType.BUY, 10, 1000.0)]
        r    = fifo_reduce(txns)
        assert r["quantity"]      == 10.0
        assert r["avg_buy_price"] == 1000.0
        assert r["invested_value"] == 10_000.0
        assert r["realized_pnl"]  == 0.0

    def test_partial_sell_fifo_realized(self):
        txns = [
            _txn(TxnType.BUY,  10, 1000.0, day=1),
            _txn(TxnType.SELL,  4, 1200.0, day=5),
        ]
        r = fifo_reduce(txns)
        assert r["quantity"] == 6.0
        # Realized P&L = 4 × (1200 − 1000) = 800
        assert abs(r["realized_pnl"] - 800.0) < 0.01

    def test_full_sell_zero_position(self):
        txns = [
            _txn(TxnType.BUY,  5, 500.0, day=1),
            _txn(TxnType.SELL, 5, 600.0, day=2),
        ]
        r = fifo_reduce(txns)
        assert r["quantity"] == 0.0
        assert abs(r["realized_pnl"] - 500.0) < 0.01

    def test_fifo_ordering_multiple_buy_lots(self):
        txns = [
            _txn(TxnType.BUY,  5,  900.0, day=1),
            _txn(TxnType.BUY,  5, 1100.0, day=3),
            _txn(TxnType.SELL, 5, 1000.0, day=5),
        ]
        r = fifo_reduce(txns)
        assert r["quantity"] == 5.0
        # FIFO: sells the 900-lot first. Realized = 5 × (1000 − 900) = 500
        assert abs(r["realized_pnl"] - 500.0) < 0.01

    def test_bonus_halves_avg_cost(self):
        txns = [
            _txn(TxnType.BUY,  10, 500.0, day=1),
            # 1:1 bonus → extra 10 shares, price=0
            _txn(TxnType.BONUS, 10, 0.0, day=10),
        ]
        r = fifo_reduce(txns)
        assert r["quantity"] == 20.0
        # Avg cost halved: 10 × 500 / 20 = 250
        assert abs(r["avg_buy_price"] - 250.0) < 0.01

    def test_split_doubles_qty_halves_price(self):
        txns = [
            _txn(TxnType.BUY,   5, 1000.0, day=1),
            # 1:2 split → factor=2 in price field
            _txn(TxnType.SPLIT, 0,    2.0, day=10),
        ]
        r = fifo_reduce(txns)
        assert r["quantity"] == 10.0
        assert abs(r["avg_buy_price"] - 500.0) < 0.01

    def test_charges_included_in_cost_basis(self):
        txns = [_txn(TxnType.BUY, 10, 1000.0, charges=100.0)]
        r    = fifo_reduce(txns)
        # cost per share = (1000 + 100/10) = 1010
        assert abs(r["avg_buy_price"] - 1010.0) < 0.01

    def test_dividend_no_quantity_change(self):
        txns = [
            _txn(TxnType.BUY,       10, 500.0, day=1),
            _txn(TxnType.DIVIDEND,   0,  20.0, day=5),  # ₹20 cash
        ]
        r = fifo_reduce(txns)
        assert r["quantity"] == 10.0
        assert r["avg_buy_price"] == 500.0

    def test_empty_transactions(self):
        r = fifo_reduce([])
        assert r["quantity"]       == 0.0
        assert r["realized_pnl"]   == 0.0

    def test_merger_out_consumes_lots(self):
        txns = [
            _txn(TxnType.BUY,       10,  800.0, day=1),
            _txn(TxnType.MERGER_OUT, 10, 1000.0, day=15),
        ]
        r = fifo_reduce(txns)
        assert r["quantity"] == 0.0
        assert abs(r["realized_pnl"] - 2000.0) < 0.01  # 10 × (1000 − 800)


class TestSynthesizeCorpActions:
    def test_bonus_generates_transaction(self):
        buy_txn = _txn(TxnType.BUY, 10, 500.0, day=1)
        # Corp action: 1:1 bonus on ex_date 2024-01-15
        corp_actions = [{
            "action_type": "bonus",
            "ex_date":    date(2024, 1, 15),
            "ratio_from": 1,
            "ratio_to":   1,
        }]
        synth = synthesize_corp_action_txns(
            portfolio_id  = _PID,
            symbol        = _SYM,
            exchange      = "NSE",
            corp_actions  = corp_actions,
            existing_txns = [buy_txn],
        )
        assert len(synth) == 1
        assert synth[0].type == TxnType.BONUS
        assert synth[0].corp_action_adjusted is True

    def test_no_corp_action_before_first_buy(self):
        buy_txn = _txn(TxnType.BUY, 10, 500.0, day=10)  # bought day=10
        corp_actions = [{
            "action_type": "bonus",
            "ex_date":    date(2024, 1, 5),   # ex_date BEFORE first buy
            "ratio_from": 1,
            "ratio_to":   1,
        }]
        synth = synthesize_corp_action_txns(
            portfolio_id  = _PID,
            symbol        = _SYM,
            exchange      = "NSE",
            corp_actions  = corp_actions,
            existing_txns = [buy_txn],
        )
        assert len(synth) == 0  # skipped because ex_date < first buy

    def test_empty_corp_actions(self):
        buy_txn = _txn(TxnType.BUY, 10, 500.0, day=1)
        synth   = synthesize_corp_action_txns(_PID, _SYM, "NSE", [], [buy_txn])
        assert synth == []
