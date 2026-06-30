"""Compliance guardrail: no prohibited/buy-lean phrasing in any scanner output.

Covers all four scanners — momentum, volume_breakout, rsi, moving_average.
Any field in ScannerResult or the AI payload is checked (docs/13 §8, SPEC §3.3, §5).
"""

from __future__ import annotations

import json
from datetime import date

from app.scanners.moving_average import run_ma_scanner
from app.scanners.momentum import run_momentum_scanner
from app.scanners.rsi import run_rsi_scanner
from app.scanners.schema import ScannerResult
from app.scanners.volume_breakout import run_volume_breakout_scanner

# Always-prohibited patterns (CLAUDE.md §3, SPEC §3.3).
_PROHIBITED = [
    "buy now", "sell now", "buy the breakout", "buy the dip",
    "guaranteed", "sure-shot", "risk-free", "multibagger",
    "best stock", "must invest", "assured target", "confirmed target",
    "entry price", "stop loss", "sl:", "target price", "buy this",
    "add to", "book profit", "cut loss",
]


def _all_text(r: ScannerResult) -> str:
    """Collect all user-visible text from a scanner result."""
    parts: list[str] = [
        r.scanner, r.symbol,
        r.data_confidence, r.validation_status, r.weights_version,
        *r.reasons,
        *r.signal_tags,
        *r.risk_flags,
        json.dumps(r.facts),
        json.dumps(r.sub_scores),
        json.dumps(r.ai_payload()),
    ]
    return " ".join(str(p) for p in parts).lower()


def _check_no_prohibited(results: list[ScannerResult], scanner_name: str) -> None:
    for r in results:
        text = _all_text(r)
        for phrase in _PROHIBITED:
            assert phrase not in text, (
                f"[{scanner_name}] Prohibited phrase '{phrase}' found in "
                f"{r.symbol} result: ...{text}..."
            )


# ---------------------------------------------------------------------------
# Momentum scanner
# ---------------------------------------------------------------------------

def test_momentum_no_prohibited_language() -> None:
    universe = {
        1: {"symbol": "ALPHA", "ret_21d": 0.05, "ret_63d": 0.20, "ret_126d": 0.35,
            "rel_strength_63d": 0.10, "rsi_14": 60.0, "close_adj": 500.0,
            "sma_50": 460.0, "atr_14": 12.0},
        2: {"symbol": "BETA", "ret_21d": 0.08, "ret_63d": 0.25, "ret_126d": 0.40,
            "rel_strength_63d": 0.15, "rsi_14": 72.0, "close_adj": 1200.0,
            "sma_50": 1000.0, "atr_14": 40.0},
    }
    results = run_momentum_scanner(universe, date(2024, 1, 31))
    _check_no_prohibited(results, "momentum")


# ---------------------------------------------------------------------------
# Volume breakout scanner
# ---------------------------------------------------------------------------

def test_volume_breakout_no_prohibited_language() -> None:
    universe = {
        1: {"symbol": "GAMMA", "volume_ratio_20": 3.5, "delivery_pct": 58.0,
            "delivery_pct_20d_mean": 40.0, "delivery_pct_20d_std": 8.0,
            "price_change_pct": 4.2},
        2: {"symbol": "DELTA", "volume_ratio_20": 2.2,
            "delivery_pct": None, "delivery_pct_20d_mean": None,
            "delivery_pct_20d_std": None, "price_change_pct": 1.5},
    }
    results = run_volume_breakout_scanner(universe, date(2024, 1, 31))
    _check_no_prohibited(results, "volume_breakout")


def test_volume_breakout_delivery_missing_neutral_not_zero() -> None:
    """Missing delivery data → DATA_INCOMPLETE flag, not delivery_z=0."""
    universe = {
        1: {"symbol": "NODATA", "volume_ratio_20": 3.0,
            "delivery_pct": None, "delivery_pct_20d_mean": None,
            "delivery_pct_20d_std": None, "price_change_pct": 2.0},
    }
    results = run_volume_breakout_scanner(universe, date(2024, 1, 31))
    assert any("DATA_INCOMPLETE" in r.risk_flags for r in results)
    for r in results:
        assert "delivery_z" not in r.facts


# ---------------------------------------------------------------------------
# RSI scanner
# ---------------------------------------------------------------------------

def test_rsi_no_prohibited_language() -> None:
    universe = {
        1: {"symbol": "RSI1", "rsi_14": 58.0},   # BULLISH_BAND
        2: {"symbol": "RSI2", "rsi_14": 75.0},   # OVERBOUGHT
        3: {"symbol": "RSI3", "rsi_14": 25.0},   # OVERSOLD
    }
    results = run_rsi_scanner(universe, date(2024, 1, 31))
    _check_no_prohibited(results, "rsi")


def test_rsi_overbought_flag_not_buy_lean() -> None:
    """RSI_OVERBOUGHT must flag risk — not suggest selling."""
    universe = {1: {"symbol": "OVB", "rsi_14": 75.0}}
    results = run_rsi_scanner(universe, date(2024, 1, 31))
    assert len(results) == 1
    r = results[0]
    assert "RSI_OVERBOUGHT" in r.risk_flags
    text = _all_text(r)
    assert "sell" not in text
    assert "exit" not in text


# ---------------------------------------------------------------------------
# Moving average scanner
# ---------------------------------------------------------------------------

def test_ma_no_prohibited_language() -> None:
    universe = {
        1: {"symbol": "MA1", "close_adj": 1715.0, "sma_20": 1680.0,
            "sma_50": 1640.0, "sma_200": 1555.0, "slope_50": 0.018},
        2: {"symbol": "MA2", "close_adj": 900.0, "sma_20": 920.0,
            "sma_50": 950.0, "sma_200": 980.0, "slope_50": -0.01},
    }
    results = run_ma_scanner(universe, date(2024, 1, 31))
    _check_no_prohibited(results, "moving_average")


def test_ma_stacked_bullish_tag_is_descriptive() -> None:
    """MA_STACKED_BULLISH tag must appear; output is descriptive not directive."""
    universe = {
        1: {"symbol": "STK", "close_adj": 1715.0, "sma_20": 1680.0,
            "sma_50": 1640.0, "sma_200": 1555.0, "slope_50": 0.018},
    }
    results = run_ma_scanner(universe, date(2024, 1, 31))
    assert len(results) == 1
    assert "MA_STACKED_BULLISH" in results[0].signal_tags
    text = _all_text(results[0])
    assert "buy" not in text


def test_extended_from_ma_flag() -> None:
    """Price > 15% above 50-DMA → EXTENDED_FROM_MA flag."""
    universe = {
        1: {"symbol": "EXT", "close_adj": 1200.0, "sma_20": 1100.0,
            "sma_50": 1000.0, "sma_200": 900.0, "slope_50": 0.02},
    }
    results = run_ma_scanner(universe, date(2024, 1, 31))
    assert any("EXTENDED_FROM_MA" in r.risk_flags for r in results)
