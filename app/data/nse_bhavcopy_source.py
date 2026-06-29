"""Real NSE Bhavcopy + MTO delivery adapter (SPEC §8, docs/12 §3, docs/steps/01).

Downloads the authoritative NSE CM Bhavcopy (UDiFF format, equity segment) and the
MTO (Market-wide Position in Delivery) file from the NSE archives.

Capability flags:
  delivery_pct   = True   (MTO file supplies delivery quantity and percentage)
  adjusted       = False  (Bhavcopy supplies raw OHLCV only; adj is our adjuster's job)
  redistribution = False  (pending legal redistribution review; prototype/local only)

NSE URLs
--------
UDiFF Bhavcopy (post-Jan 2020):
  https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{YYYYMMDD}_F_0000.csv.zip

Legacy Bhavcopy (pre-2020):
  https://nsearchives.nseindia.com/content/historical/EQUITIES/{YYYY}/{MON}/cm{DD}{MON}{YYYY}bhav.csv.zip

MTO delivery:
  https://nsearchives.nseindia.com/archives/equities/mto/MT{DDMMYYYY}.DAT

NSE archives require a valid session cookie obtained by first visiting nseindia.com.
The _prime_session() helper does this via a lightweight GET to the NSE home page.

Parsing
-------
UDiFF CSV key columns:
  TradDt / BizDt  — trade/business date (DD-Mon-YYYY)
  TckrSymb        — NSE symbol (e.g. RELIANCE)
  SctySrs         — series (EQ | BE | BL …)
  OpnPric         — open price
  HghPric         — high price
  LwPric          — low price
  ClsgPric        — closing / settlement price
  TtlTradgVol     — total traded volume (shares)
  ISIN            — ISIN

MTO DAT format (comma-separated):
  Record Type,Sr No,Symbol,Series,Total Volume,Deliverable Volume,% Deliverable
  55,1,ABAN,EQ,12345,6789,55.01
"""

from __future__ import annotations

import io
import time
import zipfile
from collections.abc import Iterable
from datetime import date, timedelta
from typing import TYPE_CHECKING

import httpx

from app.data.base import CorpActionRow, DeliveryRow, OHLCRow

if TYPE_CHECKING:
    pass

_CAPS: dict[str, bool] = {
    "adjusted": False,
    "delivery_pct": True,
    "redistribution": False,
}

_NSE_HOME = "https://www.nseindia.com"
_ARCHIVES = "https://nsearchives.nseindia.com"
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
}

# UDiFF format launched Jan 2020; older dates use the legacy format.
_UDIFF_FROM = date(2020, 1, 1)

# Series to include (equity series on NSE CM segment).
_EQUITY_SERIES = {"EQ", "BE", "BL", "BT", "BZ", "GC", "IL"}


class NseBhavcopSource:
    """DataSource backed by NSE CM Bhavcopy (UDiFF) + MTO delivery files.

    Redistribution rights are pending review; local/prototype use only (SPEC §8).
    """

    name = "nse_bhavcopy"

    def supports(self, capability: str) -> bool:
        return _CAPS.get(capability, False)

    # ------------------------------------------------------------------
    # DataSource protocol
    # ------------------------------------------------------------------

    def fetch_history(self, symbols: Iterable[str], period: str = "30d") -> list[OHLCRow]:
        """Download Bhavcopy for each trading day in ``period`` (slow; 1 request/day).

        Intended for short recent windows. For full-history backfill, use the yfinance
        adapter which provides adjusted OHLCV in a single bulk request.
        """
        sym_set = set(symbols)
        days = _period_to_days(period)
        today = date.today()
        rows: list[OHLCRow] = []
        for delta in range(days, 0, -1):
            d = today - timedelta(days=delta)
            if d.weekday() >= 5:  # skip weekends
                continue
            try:
                rows.extend(self.fetch_eod(sym_set, d))
            except Exception:  # noqa: BLE001
                continue  # holiday / file not found → skip silently
        return rows

    def fetch_eod(self, symbols: Iterable[str], session_date: date) -> list[OHLCRow]:
        """Download the Bhavcopy for ``session_date`` and return rows for ``symbols``."""
        sym_set = set(symbols)
        with _nse_client() as client:
            _prime_session(client)
            bhavcopy_bytes = _download_bhavcopy(client, session_date)
        return _parse_bhavcopy(bhavcopy_bytes, sym_set, session_date)

    def fetch_delivery(self, session_date: date) -> list[DeliveryRow] | None:
        """Download the MTO delivery file and return DeliveryRow list."""
        with _nse_client() as client:
            _prime_session(client)
            mto_bytes = _download_mto(client, session_date)
        if mto_bytes is None:
            return None
        return _parse_mto(mto_bytes)

    def fetch_corporate_actions(
        self, symbols: Iterable[str], since: date
    ) -> list[CorpActionRow]:
        # NSE's corporate-action data is on a separate API endpoint; deferred to a
        # future adapter iteration.  For now yfinance remains the corp-action source.
        return []


# ------------------------------------------------------------------
# HTTP helpers
# ------------------------------------------------------------------

def _nse_client() -> httpx.Client:
    return httpx.Client(headers=_HEADERS, timeout=30.0, follow_redirects=True)


def _prime_session(client: httpx.Client) -> None:
    """Visit the NSE home page to acquire a valid session cookie."""
    try:
        client.get(_NSE_HOME)
        time.sleep(0.5)
        # Secondary request to the live-market page refreshes the cookie.
        client.get(f"{_NSE_HOME}/market-data/live-equity-market")
        time.sleep(0.5)
    except httpx.HTTPError:
        pass  # best-effort; the archive request may still succeed


# ------------------------------------------------------------------
# Bhavcopy download + parse
# ------------------------------------------------------------------

def _bhavcopy_url(session_date: date) -> str:
    if session_date >= _UDIFF_FROM:
        # UDiFF format: BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip
        return (
            f"{_ARCHIVES}/content/cm/"
            f"BhavCopy_NSE_CM_0_0_0_{session_date:%Y%m%d}_F_0000.csv.zip"
        )
    # Legacy format: cm{DD}{MON}{YYYY}bhav.csv.zip
    mon = session_date.strftime("%b").upper()
    yr = session_date.strftime("%Y")
    dd = session_date.strftime("%d")
    return (
        f"{_ARCHIVES}/content/historical/EQUITIES/{yr}/{mon}/"
        f"cm{dd}{mon}{yr}bhav.csv.zip"
    )


def _download_bhavcopy(client: httpx.Client, session_date: date) -> bytes:
    url = _bhavcopy_url(session_date)
    resp = client.get(url)
    resp.raise_for_status()
    return resp.content


def _parse_bhavcopy(
    zip_bytes: bytes, symbols: set[str], session_date: date
) -> list[OHLCRow]:
    """Extract the CSV from the zip and parse into OHLCRow list (equity series only)."""
    rows: list[OHLCRow] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        csv_name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        raw_text = zf.read(csv_name).decode("utf-8", errors="replace")

    lines = raw_text.splitlines()
    if not lines:
        return rows

    # Detect UDiFF vs legacy by checking the header row.
    header_row = lines[0].strip().split(",")
    header = [h.strip().strip('"') for h in header_row]

    if "TckrSymb" in header:
        rows = _parse_udiff(header, lines[1:], symbols, session_date)
    else:
        rows = _parse_legacy(header, lines[1:], symbols, session_date)

    return rows


def _parse_udiff(
    header: list[str], data_lines: list[str], symbols: set[str], session_date: date
) -> list[OHLCRow]:
    """Parse NSE UDiFF format (post-Jan 2020)."""
    idx: dict[str, int] = {col: i for i, col in enumerate(header)}

    def _get(cols: list[str], key: str) -> str:
        i = idx.get(key)
        return cols[i].strip().strip('"') if i is not None and i < len(cols) else ""

    rows: list[OHLCRow] = []
    for line in data_lines:
        cols = line.split(",")
        if len(cols) < 5:
            continue
        series = _get(cols, "SctySrs")
        if series not in _EQUITY_SERIES:
            continue
        symbol = _get(cols, "TckrSymb")
        if symbols and symbol not in symbols:
            continue

        open_p = _flt(_get(cols, "OpnPric"))
        high_p = _flt(_get(cols, "HghPric"))
        low_p = _flt(_get(cols, "LwPric"))
        close_p = _flt(_get(cols, "ClsgPric"))
        if close_p is None:
            continue
        open_p = open_p or close_p
        high_p = high_p or close_p
        low_p = low_p or close_p

        vol_str = _get(cols, "TtlTradgVol")
        volume = int(float(vol_str)) if vol_str else 0

        rows.append(OHLCRow(
            symbol=symbol,
            session_date=session_date,
            open_raw=open_p,
            high_raw=high_p,
            low_raw=low_p,
            close_raw=close_p,
            open_adj=open_p,
            high_adj=high_p,
            low_adj=low_p,
            close_adj=close_p,
            volume=volume,
            is_adjusted=False,
            adj_factor=1.0,
            source="nse_bhavcopy",
        ))
    return rows


def _col(idx_map: dict[str, int], cols: list[str], key: str, fallback: str = "") -> str:
    i = idx_map.get(key)
    return cols[i] if i is not None and i < len(cols) else fallback


def _parse_legacy(
    header: list[str], data_lines: list[str], symbols: set[str], session_date: date
) -> list[OHLCRow]:
    """Parse NSE legacy Bhavcopy format (pre-2020).

    Legacy columns: SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,...
    """
    idx: dict[str, int] = {col.strip(): i for i, col in enumerate(header)}
    rows: list[OHLCRow] = []
    for line in data_lines:
        cols = [c.strip() for c in line.split(",")]
        if len(cols) < 8:
            continue
        series_i = idx.get("SERIES", 1)
        series = cols[series_i] if series_i < len(cols) else ""
        if series not in _EQUITY_SERIES:
            continue
        sym_i = idx.get("SYMBOL", 0)
        symbol = cols[sym_i] if sym_i < len(cols) else ""
        if symbols and symbol not in symbols:
            continue

        close_p = _flt(_col(idx, cols, "CLOSE"))
        if close_p is None:
            continue
        open_p = _flt(_col(idx, cols, "OPEN")) or close_p
        high_p = _flt(_col(idx, cols, "HIGH")) or close_p
        low_p = _flt(_col(idx, cols, "LOW")) or close_p
        vol_str = _col(idx, cols, "TOTTRDQTY")
        volume = int(float(vol_str)) if vol_str else 0

        rows.append(OHLCRow(
            symbol=symbol,
            session_date=session_date,
            open_raw=open_p,
            high_raw=high_p,
            low_raw=low_p,
            close_raw=close_p,
            open_adj=open_p,
            high_adj=high_p,
            low_adj=low_p,
            close_adj=close_p,
            volume=volume,
            is_adjusted=False,
            adj_factor=1.0,
            source="nse_bhavcopy",
        ))
    return rows


# ------------------------------------------------------------------
# MTO delivery download + parse
# ------------------------------------------------------------------

def _mto_url(session_date: date) -> str:
    # MT{DDMMYYYY}.DAT — e.g. MT02012024.DAT for 2024-01-02
    return f"{_ARCHIVES}/archives/equities/mto/MT{session_date:%d%m%Y}.DAT"


def _download_mto(client: httpx.Client, session_date: date) -> bytes | None:
    url = _mto_url(session_date)
    try:
        resp = client.get(url)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.content
    except httpx.HTTPError:
        return None


def _parse_mto(dat_bytes: bytes) -> list[DeliveryRow]:
    """Parse NSE MTO delivery file into DeliveryRow list.

    Format (comma-separated):
      Record Type,Sr No,Symbol,Series,Total Volume,Deliverable Volume,% Deliverable
      55,1,ABAN,EQ,12345,6789,55.01
    """
    rows: list[DeliveryRow] = []
    text = dat_bytes.decode("utf-8", errors="replace")
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 7:
            continue
        if parts[0] != "55":  # only equity delivery records
            continue
        symbol = parts[2].strip()
        series = parts[3].strip()
        if series not in _EQUITY_SERIES:
            continue
        try:
            total_vol = int(float(parts[4]))
            delivery_qty = int(float(parts[5]))
            delivery_pct = float(parts[6])
        except (ValueError, IndexError):
            continue
        if total_vol <= 0:
            continue
        rows.append(DeliveryRow(
            symbol=symbol,
            session_date=date.today(),  # caller merges with the correct session_date
            delivery_qty=delivery_qty,
            delivery_pct=delivery_pct,
        ))
    return rows


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------

def _flt(value: str) -> float | None:
    try:
        v = float(value)
        return v if v == v else None  # reject NaN
    except (ValueError, TypeError):
        return None


def _period_to_days(period: str) -> int:
    """Convert a period string to calendar days (generous upper bound for weekday filtering)."""
    period = period.strip().lower()
    mapping = {
        "1d": 3, "5d": 10, "1mo": 40, "3mo": 95, "6mo": 185,
        "1y": 370, "2y": 740, "5y": 1850, "10y": 3700, "ytd": 370, "max": 3700,
    }
    return mapping.get(period, 40)
