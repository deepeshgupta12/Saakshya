"""Zerodha Kite Connect EOD source — the sole market-data adapter (D-058, docs/12 §3).

Implements the ``DataSource`` Protocol from ``app.data.base`` so indicators, scanners and
AI depend only on the seam, never on Kite. Uses the official ``kiteconnect`` SDK:

  - ``instruments("NSE")``      → the instrument master (tradingsymbol → instrument_token).
  - ``historical_data(token, from, to, "day")`` → daily OHLCV, chunked to respect Kite's
    per-request span, throttled to Kite's historical rate limit (~3 req/s).

Capabilities (honest declaration):
  - ``adjusted``: **False** — Kite historical candles are NOT split/bonus-adjusted. Our
    first-class corp-action adjuster (M1) applies adjustments; see fetch_corporate_actions.
  - ``delivery_pct``: **False** — the historical API carries no delivery quantity.
  - ``redistribution``: **False** — Kite data is licensed for the authenticated user; the
    publish-guard keeps commercial redistribution blocked until a redistribution licence
    is in force (SPEC §8).

Corporate actions: Kite Connect exposes **no** corporate-action API, so
``fetch_corporate_actions`` returns ``[]``. Until a corp-action feed is added, series are
stored unadjusted (a documented gap, docs/12 §3.4) — never silently mis-adjusted.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from datetime import date, datetime, timedelta

from app.config import get_settings
from app.data.base import CorpActionRow, DeliveryRow, OHLCRow

log = logging.getLogger(__name__)

_CAPS: dict[str, bool] = {
    "adjusted": False,
    "delivery_pct": False,
    "redistribution": False,
}

# Kite historical rate limit is ~3 req/s; ~0.34s between calls stays under it.
_RATE_LIMIT_SLEEP_S = 0.34
_MAX_HISTORY_START = date(2000, 1, 1)


class KiteSource:
    """``DataSource`` implementation backed by Zerodha Kite Connect."""

    name = "kite"

    def __init__(self, access_token: str | None = None) -> None:
        self._access_token = access_token
        self._kite: object | None = None
        self._token_by_symbol: dict[str, int] | None = None

    # --- capabilities ----------------------------------------------------
    def supports(self, capability: str) -> bool:
        return _CAPS.get(capability, False)

    # --- public DataSource surface --------------------------------------
    def fetch_history(self, symbols: Iterable[str], period: str = "max") -> list[OHLCRow]:
        start = _period_start(period)
        end = _today_ist()
        rows: list[OHLCRow] = []
        for symbol in symbols:
            rows.extend(self._fetch_one(symbol, start, end))
        return rows

    def fetch_eod(self, symbols: Iterable[str], session_date: date) -> list[OHLCRow]:
        # Pull a short window around the date and filter (handles holidays/weekends).
        window_start = session_date - timedelta(days=7)
        rows: list[OHLCRow] = []
        for symbol in symbols:
            rows.extend(self._fetch_one(symbol, window_start, session_date))
        return [r for r in rows if r.session_date == session_date]

    def fetch_delivery(self, session_date: date) -> list[DeliveryRow] | None:
        return None  # not available from the Kite historical API

    def fetch_corporate_actions(
        self, symbols: Iterable[str], since: date
    ) -> list[CorpActionRow]:
        # Kite Connect exposes no corporate-action endpoint (docs/12 §3.4).
        return []

    # --- internals -------------------------------------------------------
    def _client(self) -> object:
        """Lazily build an authenticated KiteConnect client."""
        if self._kite is not None:
            return self._kite

        cfg = get_settings()
        # Corporate-proxy CA: kiteconnect uses `requests`, which honours these env vars.
        if cfg.kite_ca_bundle:
            import os  # noqa: PLC0415

            os.environ.setdefault("REQUESTS_CA_BUNDLE", cfg.kite_ca_bundle)
            os.environ.setdefault("SSL_CERT_FILE", cfg.kite_ca_bundle)

        from kiteconnect import KiteConnect  # noqa: PLC0415

        api_key, _ = cfg.require_kite_api()
        token = self._access_token or cfg.kite_access_token
        if not token:
            # No token yet — run the daily login flow (automated → browser fallback).
            from app.data.kite_auth import ensure_access_token  # noqa: PLC0415

            token = ensure_access_token()
        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(token)
        self._kite = kite
        return kite

    def _instrument_map(self) -> dict[str, int]:
        """tradingsymbol → instrument_token for the configured exchange (cached)."""
        if self._token_by_symbol is not None:
            return self._token_by_symbol
        cfg = get_settings()
        kite = self._client()
        instruments = kite.instruments(cfg.kite_exchange)  # type: ignore[attr-defined]
        self._token_by_symbol = {
            str(i["tradingsymbol"]): int(i["instrument_token"]) for i in instruments
        }
        log.info(
            "[kite] loaded %d %s instruments", len(self._token_by_symbol), cfg.kite_exchange
        )
        return self._token_by_symbol

    def _fetch_one(self, symbol: str, start: date, end: date) -> list[OHLCRow]:
        tradingsymbol = _normalize_symbol(symbol)
        token = self._instrument_map().get(tradingsymbol)
        if token is None:
            log.warning("[kite] no instrument_token for %s — skipping", tradingsymbol)
            return []

        kite = self._client()
        cfg = get_settings()
        out: list[OHLCRow] = []
        chunk = timedelta(days=cfg.kite_history_chunk_days)
        cur = start
        while cur <= end:
            chunk_end = min(cur + chunk, end)
            try:
                # Kite expects 'yyyy-mm-dd hh:mm:ss' (docs/connect/v3/historical).
                candles = kite.historical_data(  # type: ignore[attr-defined]
                    token,
                    f"{cur} 00:00:00",
                    f"{chunk_end} 23:59:59",
                    "day",
                )
            except Exception:  # noqa: BLE001 — fail-soft per chunk; log and continue
                log.exception("[kite] historical_data failed for %s %s..%s",
                              tradingsymbol, cur, chunk_end)
                candles = []
            for c in candles:
                row = _to_ohlc_row(symbol, c)
                if row is not None:
                    out.append(row)
            time.sleep(_RATE_LIMIT_SLEEP_S)
            cur = chunk_end + timedelta(days=1)
        return out


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _normalize_symbol(symbol: str) -> str:
    """Map our seam symbols to a Kite tradingsymbol.

    Accepts ``RELIANCE``, ``RELIANCE.NS`` (legacy yfinance form), or ``NSE:RELIANCE``.
    """
    s = symbol.strip().upper()
    if ":" in s:
        s = s.split(":", 1)[1]
    if s.endswith(".NS") or s.endswith(".BO"):
        s = s[:-3]
    return s


def _to_ohlc_row(symbol: str, candle: dict[str, object]) -> OHLCRow | None:
    close = _f(candle.get("close"))
    if close is None:
        return None
    o = _f(candle.get("open")) or close
    h = _f(candle.get("high")) or close
    lo = _f(candle.get("low")) or close
    vol = candle.get("volume")
    session = candle.get("date")
    if isinstance(session, datetime):
        session_date = session.date()
    elif isinstance(session, date):
        session_date = session
    else:
        return None
    # Kite candles are unadjusted → raw == adj, is_adjusted=False, factor 1.0.
    return OHLCRow(
        symbol=symbol,
        session_date=session_date,
        open_raw=o, high_raw=h, low_raw=lo, close_raw=close,
        open_adj=o, high_adj=h, low_adj=lo, close_adj=close,
        volume=int(vol) if isinstance(vol, (int, float)) else 0,
        is_adjusted=False,
        adj_factor=1.0,
        source="kite",
    )


def _period_start(period: str) -> date:
    """Translate a period string ('max', '5y', '1y', ...) to a start date."""
    p = period.strip().lower()
    if p == "max":
        return _MAX_HISTORY_START
    if p.endswith("y") and p[:-1].isdigit():
        return _today_ist() - timedelta(days=365 * int(p[:-1]))
    if p.endswith("mo") and p[:-2].isdigit():
        return _today_ist() - timedelta(days=30 * int(p[:-2]))
    return _MAX_HISTORY_START


def _today_ist() -> date:
    """Today's date in IST (Kite sessions are IST; UTC+5:30)."""
    from datetime import timezone

    return (datetime.now(tz=timezone.utc) + timedelta(hours=5, minutes=30)).date()


def _f(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
