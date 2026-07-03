"""Compute full indicator set per symbol and persist to technical_indicators (docs/02 §4).

Reads adjusted OHLCV from the repository, runs all core indicators and returns,
then bulk-inserts into technical_indicators with as_of_version propagation.
vwap is left NULL — EOD-only, V7 intraday milestone (docs/13 §3.5).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from app.indicators.core import (
    adx_14 as compute_adx,
    atr,
    bollinger,
    compute_rsi,
    ema,
    macd,
    pivots,
    sma,
    stoch_rsi,
)
from app.indicators.returns import relative_strength, total_return, volume_ratio_20
from app.storage.repository import OhlcBar, Repository

_INDICATOR_VERSION = 1

_IND_COLS = (
    "stock_id, session_date, indicator_version, as_of_version, "
    "rsi_14, sma_20, sma_50, sma_200, ema_21, atr_14, "
    "macd_line, macd_signal, bb_upper, bb_mid, bb_lower, "
    "adx_14, stoch_rsi_k, stoch_rsi_d, "
    '"pivot", pivot_r1, pivot_r2, pivot_s1, pivot_s2, '
    "vwap, ret_5d, ret_21d, ret_63d, ret_126d, volume_ratio_20, rel_strength_63d"
)

_IND_PLACEHOLDERS = ", ".join(["%s"] * 30)

_IND_UPDATE = (
    "rsi_14=excluded.rsi_14, sma_20=excluded.sma_20, sma_50=excluded.sma_50, "
    "sma_200=excluded.sma_200, ema_21=excluded.ema_21, atr_14=excluded.atr_14, "
    "macd_line=excluded.macd_line, macd_signal=excluded.macd_signal, "
    "bb_upper=excluded.bb_upper, bb_mid=excluded.bb_mid, bb_lower=excluded.bb_lower, "
    "adx_14=excluded.adx_14, stoch_rsi_k=excluded.stoch_rsi_k, "
    'stoch_rsi_d=excluded.stoch_rsi_d, "pivot"=excluded."pivot", '
    "pivot_r1=excluded.pivot_r1, pivot_r2=excluded.pivot_r2, "
    "pivot_s1=excluded.pivot_s1, pivot_s2=excluded.pivot_s2, "
    "vwap=excluded.vwap, ret_5d=excluded.ret_5d, ret_21d=excluded.ret_21d, "
    "ret_63d=excluded.ret_63d, ret_126d=excluded.ret_126d, "
    "volume_ratio_20=excluded.volume_ratio_20, "
    "rel_strength_63d=excluded.rel_strength_63d, computed_at=now()"
)


@dataclass
class ComputeSummary:
    stocks_processed: int = 0
    rows_written: int = 0
    errors: list[str] = field(default_factory=list)


def _nullify(val: object) -> float | None:
    """Convert NaN/None to Python None; else return float (safe for DB binding)."""
    if val is None:
        return None
    try:
        f = float(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _to_list(s: pd.Series) -> list[float | None]:
    return [_nullify(v) for v in s.tolist()]


def compute_all(
    repo: Repository,
    as_of_version: int = 1,
    benchmark_symbol: str = "^NSEI",
) -> ComputeSummary:
    """Compute and persist indicators for every listed stock in the repository."""
    summary = ComputeSummary()
    rows = repo._conn.execute(
        "SELECT stock_id FROM stock_master WHERE status='listed'"
    ).fetchall()
    stock_ids = [int(r[0]) for r in rows]

    bench_close = _load_bench(repo, benchmark_symbol)

    for stock_id in stock_ids:
        try:
            n = _compute_stock(repo, stock_id, as_of_version, bench_close)
            summary.rows_written += n
            summary.stocks_processed += 1
        except Exception as exc:  # noqa: BLE001
            summary.errors.append(f"stock_id={stock_id}: {exc}")

    return summary


def _load_bench(repo: Repository, symbol: str) -> pd.Series:
    """Load benchmark (Nifty 50) adjusted closes as a date-indexed pd.Series."""
    raw = repo._conn.execute(
        "SELECT session_date, close FROM index_ohlc WHERE index_symbol=%s "
        "ORDER BY session_date ASC",
        [symbol],
    ).fetchall()
    if not raw:
        return pd.Series(dtype=float)
    idx = pd.DatetimeIndex([pd.Timestamp(r[0]) for r in raw])
    return pd.Series([float(r[1]) for r in raw], index=idx)


def _compute_stock(
    repo: Repository,
    stock_id: int,
    as_of_version: int,
    bench_close: pd.Series,
) -> int:
    bars: list[OhlcBar] = repo.get_all_bars(stock_id, as_of_version)
    if len(bars) < 2:
        return 0

    dates: list[date] = [b.session_date for b in bars]
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in dates])
    close = pd.Series([b.close_adj for b in bars], index=idx)
    high  = pd.Series([b.high_adj  for b in bars], index=idx)
    low_s = pd.Series([b.low_adj   for b in bars], index=idx)
    vol   = pd.Series([float(b.volume) for b in bars], index=idx)

    # Core indicators
    rsi14_s        = compute_rsi(close)
    sma20_s        = sma(close, 20)
    sma50_s        = sma(close, 50)
    sma200_s       = sma(close, 200)
    ema21_s        = ema(close, 21)
    atr14_s        = atr(high, low_s, close)
    macd_l_s, macd_sig_s = macd(close)
    bb_up_s, bb_mid_s, bb_lo_s = bollinger(close)
    adx14_s        = compute_adx(high, low_s, close)
    sk_s, sd_s     = stoch_rsi(close)
    piv_d          = pivots(high, low_s, close)

    # Returns and volume
    ret5_s    = total_return(close, 5)
    ret21_s   = total_return(close, 21)
    ret63_s   = total_return(close, 63)
    ret126_s  = total_return(close, 126)
    volr20_s  = volume_ratio_20(vol)

    # Relative strength vs benchmark (63d); NEUTRAL if benchmark not available
    if not bench_close.empty:
        bench_aligned = bench_close.reindex(close.index, method="ffill")
        rs63_s = relative_strength(close, bench_aligned, 63)
    else:
        rs63_s = pd.Series([np.nan] * len(close), index=idx)

    # Convert all series to plain lists to avoid per-row iloc overhead
    rsi14_l   = _to_list(rsi14_s)
    sma20_l   = _to_list(sma20_s)
    sma50_l   = _to_list(sma50_s)
    sma200_l  = _to_list(sma200_s)
    ema21_l   = _to_list(ema21_s)
    atr14_l   = _to_list(atr14_s)
    macd_l_l  = _to_list(macd_l_s)
    macd_s_l  = _to_list(macd_sig_s)
    bb_up_l   = _to_list(bb_up_s)
    bb_mid_l  = _to_list(bb_mid_s)
    bb_lo_l   = _to_list(bb_lo_s)
    adx14_l   = _to_list(adx14_s)
    sk_l      = _to_list(sk_s)
    sd_l      = _to_list(sd_s)
    piv_l     = _to_list(piv_d["pivot"])
    piv_r1_l  = _to_list(piv_d["pivot_r1"])
    piv_r2_l  = _to_list(piv_d["pivot_r2"])
    piv_s1_l  = _to_list(piv_d["pivot_s1"])
    piv_s2_l  = _to_list(piv_d["pivot_s2"])
    ret5_l    = _to_list(ret5_s)
    ret21_l   = _to_list(ret21_s)
    ret63_l   = _to_list(ret63_s)
    ret126_l  = _to_list(ret126_s)
    volr20_l  = _to_list(volr20_s)
    rs63_l    = _to_list(rs63_s)

    params: list[list[object]] = []
    for i, d in enumerate(dates):
        params.append([
            stock_id, d, _INDICATOR_VERSION, as_of_version,
            rsi14_l[i], sma20_l[i], sma50_l[i], sma200_l[i], ema21_l[i], atr14_l[i],
            macd_l_l[i], macd_s_l[i], bb_up_l[i], bb_mid_l[i], bb_lo_l[i],
            adx14_l[i], sk_l[i], sd_l[i],
            piv_l[i], piv_r1_l[i], piv_r2_l[i], piv_s1_l[i], piv_s2_l[i],
            None,           # vwap: NULL in EOD mode (V7)
            ret5_l[i], ret21_l[i], ret63_l[i], ret126_l[i], volr20_l[i], rs63_l[i],
        ])

    # psycopg's Connection has no executemany(); use a cursor (matches Repository).
    with repo._conn.cursor() as cur:
        cur.executemany(
            f"INSERT INTO technical_indicators ({_IND_COLS}) VALUES ({_IND_PLACEHOLDERS}) "
            f"ON CONFLICT (stock_id, session_date, indicator_version, as_of_version) "
            f"DO UPDATE SET {_IND_UPDATE}",
            params,
        )
    return len(params)
