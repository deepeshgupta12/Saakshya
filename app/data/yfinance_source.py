"""yfinance EOD source — the M0 local prototype (SPEC §8, §12 / docs/12 §3).

PROTOTYPE-ONLY: not a licensed feed, no delivery %, no commercial redistribution
(``supports("redistribution") is False``). yfinance auto-adjustment is a prototyping
convenience, NOT the production engine — the real corporate-action adjuster is the
first-class workstream in milestone M1 (SPEC §6.1).

Fetch strategy: try the ``yfinance`` library first; if it returns nothing (Yahoo's
cookie/crumb flow is frequently rate-limited / bot-blocked), fall back to Yahoo's public
chart endpoint directly via httpx — which returns OHLCV + adjusted close as plain JSON.
"""

from __future__ import annotations

import time
from collections.abc import Iterable
from datetime import date, datetime, timezone
from typing import Any

import httpx
import pandas as pd
import yfinance as yf

from app.data.base import CorpActionRow, DeliveryRow, OHLCRow

_CAPS: dict[str, bool] = {
    "adjusted": True,
    "delivery_pct": False,   # yfinance has no delivery %; downstream marks it neutral, not 0
    "redistribution": False,  # prototype-only
}

_CHART_HOSTS = ("query1.finance.yahoo.com", "query2.finance.yahoo.com")
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
# Map our period strings to valid Yahoo chart `range` values.
_VALID_RANGES = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}


class YFinanceSource:
    """``DataSource`` implementation backed by yfinance (.NS / .BO tickers)."""

    name = "yfinance"

    def supports(self, capability: str) -> bool:
        return _CAPS.get(capability, False)

    def fetch_history(self, symbols: Iterable[str], period: str = "max") -> list[OHLCRow]:
        rows: list[OHLCRow] = []
        for symbol in symbols:
            rows.extend(self._fetch_one(symbol, period))
        return rows

    def fetch_eod(self, symbols: Iterable[str], session_date: date) -> list[OHLCRow]:
        return [r for r in self.fetch_history(symbols, "5d") if r.session_date == session_date]

    def fetch_delivery(self, session_date: date) -> list[DeliveryRow] | None:
        return None  # not available from yfinance

    def fetch_corporate_actions(
        self, symbols: Iterable[str], since: date
    ) -> list[CorpActionRow]:
        """Pull splits and dividends from yfinance for the given tickers since ``since``."""
        rows: list[CorpActionRow] = []
        for symbol in symbols:
            rows.extend(self._fetch_actions_for(symbol, since))
        return rows

    def _fetch_actions_for(self, symbol: str, since: date) -> list[CorpActionRow]:
        try:
            ticker = yf.Ticker(symbol)
            splits = ticker.splits      # pd.Series: {Timestamp → new/old ratio}
            dividends = ticker.dividends  # pd.Series: {Timestamp → dividend amount}
        except Exception:  # noqa: BLE001
            return []

        out: list[CorpActionRow] = []

        for ts, factor in splits.items():
            try:
                ex_d = ts.date()
            except AttributeError:
                ex_d = ts
            if ex_d < since or float(factor) <= 0:
                continue
            # yfinance factor = new_shares / old_shares (e.g. 2.0 for 2-for-1 split).
            # Store as ratio_from=1, ratio_to=factor so event_factor = 1/factor (price halves).
            out.append(CorpActionRow(
                symbol=symbol,
                action_type="split",
                ex_date=ex_d,
                ratio_from=1.0,
                ratio_to=float(factor),
                source="yfinance",
            ))

        for ts, amount in dividends.items():
            try:
                ex_d = ts.date()
            except AttributeError:
                ex_d = ts
            if ex_d < since:
                continue
            out.append(CorpActionRow(
                symbol=symbol,
                action_type="dividend",
                ex_date=ex_d,
                dividend_amount=float(amount),
                source="yfinance",
            ))

        return out

    def _fetch_one(self, symbol: str, period: str) -> list[OHLCRow]:
        rows = self._fetch_via_library(symbol, period)
        if rows:
            return rows
        return self._fetch_via_chart_api(symbol, period)

    # --- primary path: the yfinance library -----------------------------
    def _fetch_via_library(self, symbol: str, period: str) -> list[OHLCRow]:
        try:
            ticker = yf.Ticker(symbol)
            raw = ticker.history(period=period, auto_adjust=False, actions=False)
            if raw.empty:
                return []
            adj = ticker.history(period=period, auto_adjust=True, actions=False)
        except Exception:  # noqa: BLE001 — fall back to the chart API on any library error
            return []

        out: list[OHLCRow] = []
        for ts, r in raw.iterrows():
            close_raw = _f(r["Close"])
            if close_raw is None:
                continue
            a = adj.loc[ts] if ts in adj.index else None
            if a is not None and _f(a["Close"]) is not None:
                close_adj = _f(a["Close"]) or close_raw
                factor = (close_adj / close_raw) if close_raw else 1.0
                o, h, lo = _f(a["Open"]), _f(a["High"]), _f(a["Low"])
                is_adjusted = True
            else:
                close_adj, factor, is_adjusted = close_raw, 1.0, False
                o, h, lo = _f(r["Open"]), _f(r["High"]), _f(r["Low"])
            out.append(
                _row(
                    symbol, ts.date(),
                    _f(r["Open"]) or close_raw, _f(r["High"]) or close_raw,
                    _f(r["Low"]) or close_raw, close_raw,
                    o or close_adj, h or close_adj, lo or close_adj, close_adj,
                    int(r["Volume"]) if not pd.isna(r["Volume"]) else 0,
                    is_adjusted, factor,
                )
            )
        return out

    # --- fallback: Yahoo public chart endpoint --------------------------
    def _fetch_via_chart_api(self, symbol: str, period: str) -> list[OHLCRow]:
        rng = period if period in _VALID_RANGES else "max"
        params = {
            "range": rng,
            "interval": "1d",
            "events": "div,splits",
            "includeAdjustedClose": "true",
        }
        payload = None
        for host in _CHART_HOSTS:
            url = f"https://{host}/v8/finance/chart/{symbol}"
            try:
                resp = httpx.get(url, params=params, headers={"User-Agent": _UA}, timeout=20.0)
            except httpx.HTTPError:
                continue
            if resp.status_code == 429:
                time.sleep(1.0)
                continue
            if resp.status_code == 200:
                payload = resp.json()
                break
        if not payload:
            return []
        return _parse_chart(symbol, payload)


def _parse_chart(symbol: str, payload: dict[str, Any]) -> list[OHLCRow]:
    result = (payload.get("chart") or {}).get("result")
    if not result:
        return []
    block = result[0]
    timestamps = block.get("timestamp") or []
    meta = block.get("meta") or {}
    gmtoffset = int(meta.get("gmtoffset") or 0)
    quote = ((block.get("indicators") or {}).get("quote") or [{}])[0]
    adjclose_list = ((block.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose")

    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    out: list[OHLCRow] = []
    for i, ts in enumerate(timestamps):
        close_raw = _f(_at(closes, i))
        if close_raw is None:
            continue
        adj_close = _f(_at(adjclose_list, i)) if adjclose_list else None
        close_adj = adj_close if adj_close is not None else close_raw
        factor = (close_adj / close_raw) if close_raw else 1.0
        open_raw = _f(_at(opens, i)) or close_raw
        high_raw = _f(_at(highs, i)) or close_raw
        low_raw = _f(_at(lows, i)) or close_raw
        session_date = datetime.fromtimestamp(ts + gmtoffset, tz=timezone.utc).date()
        out.append(
            _row(
                symbol, session_date, open_raw, high_raw, low_raw, close_raw,
                open_raw * factor, high_raw * factor, low_raw * factor, close_adj,
                int(_f(_at(volumes, i)) or 0), adj_close is not None, factor,
            )
        )
    return out


def _row(
    symbol: str, session_date: date,
    o_raw: float, h_raw: float, l_raw: float, c_raw: float,
    o_adj: float, h_adj: float, l_adj: float, c_adj: float,
    volume: int, is_adjusted: bool, factor: float,
) -> OHLCRow:
    return OHLCRow(
        symbol=symbol, session_date=session_date,
        open_raw=o_raw, high_raw=h_raw, low_raw=l_raw, close_raw=c_raw,
        open_adj=o_adj, high_adj=h_adj, low_adj=l_adj, close_adj=c_adj,
        volume=volume, is_adjusted=is_adjusted, adj_factor=factor, source="yfinance",
    )


def _at(seq: list[object], i: int) -> object:
    return seq[i] if i < len(seq) else None


def _f(value: object) -> float | None:
    """Coerce a cell to float, returning None for NaN/missing (fail-soft per row)."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
