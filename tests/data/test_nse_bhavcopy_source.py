"""NSE Bhavcopy adapter tests — inline CSV fixtures, zero network calls (docs/27 §7.6).

Tests cover:
  1. UDiFF format parsing (post-2020 bhavcopy) → typed OHLCRow list
  2. Legacy format parsing (pre-2020 bhavcopy) → typed OHLCRow list
  3. MTO delivery file parsing → typed DeliveryRow list
  4. Adapter contract: satisfies DataSource protocol; capability flags are correct
  5. Symbol filtering: only requested symbols are returned
  6. Series filtering: only equity series (EQ/BE/…) rows are returned

These tests import only the parser helpers, not the HTTP layer, so they run offline.
"""

from __future__ import annotations

import io
import zipfile
from datetime import date

import pytest

from app.data.base import DataSource
from app.data.nse_bhavcopy_source import (
    NseBhavcopSource,
    _parse_bhavcopy,
    _parse_legacy,
    _parse_mto,
    _parse_udiff,
)

# ---------------------------------------------------------------------------
# Inline test fixtures — minimal but structurally correct NSE data
# ---------------------------------------------------------------------------

# UDiFF format (post-Jan 2020). Columns are the minimum subset needed for parsing.
_UDIFF_CSV = (
    "TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,"
    "TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,"
    "OpnPric,HghPric,LwPric,ClsgPric,LastPric,PrvsClsgPric,TtlTradgVol,TtlTrfVal\n"
    "01-Jan-2024,01-Jan-2024,CM,NSE,EQ,RELIANCE,INE002A01018,"
    "RELIANCE,EQ,NA,NA,0,NA,Reliance Industries,"
    "2500.00,2560.00,2490.00,2540.00,2538.00,2495.00,5000000,12700000000\n"
    "01-Jan-2024,01-Jan-2024,CM,NSE,EQ,TCS,INE467B01029,"
    "TCS,EQ,NA,NA,0,NA,TCS Ltd,"
    "3800.00,3850.00,3790.00,3820.00,3818.00,3795.00,2000000,7640000000\n"
    "01-Jan-2024,01-Jan-2024,CM,NSE,FO,NIFTY,NA,"
    "NIFTY,FU,25-Jan-2024,25-Jan-2024,0,NA,NIFTY,"
    "21500.00,21600.00,21480.00,21550.00,21548.00,21495.00,1000000,215500000000\n"
)

# Legacy format (pre-2020). Columns: SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,...
_LEGACY_CSV = """\
SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,TIMESTAMP,TOTALTRADES,ISIN
RELIANCE,EQ,2500.00,2560.00,2490.00,2540.00,2538.00,2495.00,5000000,12700000000,01-JAN-2019,125000,INE002A01018
INFY,EQ,800.00,820.00,795.00,810.00,808.00,805.00,3000000,2430000000,01-JAN-2019,95000,INE009A01021
INFY,BE,810.00,825.00,800.00,815.00,813.00,808.00,100000,81500000,01-JAN-2019,2000,INE009A01021
"""

# MTO delivery file (record type 55 rows).
_MTO_DAT = """\
55,1,RELIANCE,EQ,5000000,2750000,55.00
55,2,TCS,EQ,2000000,1200000,60.00
55,3,INFY,EQ,3000000,900000,30.00
99,0,,,,,
"""


def _make_zip(csv_content: str, filename: str = "bhavcopy.csv") -> bytes:
    """Wrap CSV content in a zip archive as the NSE server does."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(filename, csv_content)
    return buf.getvalue()


SESSION_DATE = date(2024, 1, 1)


# ---------------------------------------------------------------------------
# UDiFF parsing
# ---------------------------------------------------------------------------

def test_udiff_parses_equity_rows() -> None:
    """UDiFF CSV → OHLCRow list with correct prices; FO (futures) row excluded."""
    header = _UDIFF_CSV.splitlines()[0].split(",")
    rows = _parse_udiff(header, _UDIFF_CSV.splitlines()[1:], set(), SESSION_DATE)

    # Only EQ/equity-series rows (RELIANCE, TCS). FO row (NIFTY) is excluded.
    symbols = {r.symbol for r in rows}
    assert "RELIANCE" in symbols
    assert "TCS" in symbols
    assert "NIFTY" not in symbols


def test_udiff_parses_correct_prices() -> None:
    """RELIANCE UDiFF row → open/high/low/close map correctly."""
    header = _UDIFF_CSV.splitlines()[0].split(",")
    rows = _parse_udiff(header, _UDIFF_CSV.splitlines()[1:], {"RELIANCE"}, SESSION_DATE)
    assert len(rows) == 1
    r = rows[0]
    assert r.open_raw == pytest.approx(2500.0)
    assert r.high_raw == pytest.approx(2560.0)
    assert r.low_raw == pytest.approx(2490.0)
    assert r.close_raw == pytest.approx(2540.0)
    assert r.volume == 5000000
    assert r.source == "nse_bhavcopy"
    assert r.is_adjusted is False
    assert r.adj_factor == pytest.approx(1.0)


def test_udiff_symbol_filter_applies() -> None:
    """Only the requested symbols are returned."""
    header = _UDIFF_CSV.splitlines()[0].split(",")
    rows = _parse_udiff(header, _UDIFF_CSV.splitlines()[1:], {"TCS"}, SESSION_DATE)
    assert all(r.symbol == "TCS" for r in rows)
    assert len(rows) == 1


def test_parse_bhavcopy_zip_udiff() -> None:
    """_parse_bhavcopy correctly unzips and dispatches to the UDiFF parser."""
    zip_bytes = _make_zip(_UDIFF_CSV)
    rows = _parse_bhavcopy(zip_bytes, {"RELIANCE", "TCS"}, SESSION_DATE)
    symbols = {r.symbol for r in rows}
    assert symbols == {"RELIANCE", "TCS"}


# ---------------------------------------------------------------------------
# Legacy format parsing
# ---------------------------------------------------------------------------

def test_legacy_parses_equity_rows() -> None:
    """Legacy CSV → RELIANCE (EQ) and INFY (EQ + BE) parsed; BE also included."""
    header = _LEGACY_CSV.splitlines()[0].split(",")
    rows = _parse_legacy(header, _LEGACY_CSV.splitlines()[1:], set(), date(2019, 1, 1))
    symbols = [r.symbol for r in rows]
    assert "RELIANCE" in symbols
    assert "INFY" in symbols


def test_legacy_parses_correct_prices() -> None:
    """RELIANCE legacy row → prices correct."""
    header = _LEGACY_CSV.splitlines()[0].split(",")
    rows = _parse_legacy(header, _LEGACY_CSV.splitlines()[1:], {"RELIANCE"}, date(2019, 1, 1))
    assert len(rows) == 1
    r = rows[0]
    assert r.close_raw == pytest.approx(2540.0)
    assert r.open_raw == pytest.approx(2500.0)


# ---------------------------------------------------------------------------
# MTO delivery parsing
# ---------------------------------------------------------------------------

def test_mto_parses_delivery_rows() -> None:
    """MTO DAT → DeliveryRow for record-55 equity lines; record-99 footer excluded."""
    rows = _parse_mto(_MTO_DAT.encode())
    symbols = {r.symbol for r in rows}
    assert "RELIANCE" in symbols
    assert "TCS" in symbols
    assert "INFY" in symbols


def test_mto_delivery_quantities() -> None:
    """RELIANCE delivery qty and pct parse correctly."""
    rows = _parse_mto(_MTO_DAT.encode())
    rel = next(r for r in rows if r.symbol == "RELIANCE")
    assert rel.delivery_qty == 2750000
    assert rel.delivery_pct == pytest.approx(55.0)


def test_mto_footer_row_excluded() -> None:
    """Record type 99 (footer) is not included in output."""
    rows = _parse_mto(_MTO_DAT.encode())
    assert all(r.delivery_qty > 0 for r in rows)
    assert len(rows) == 3  # RELIANCE, TCS, INFY only


# ---------------------------------------------------------------------------
# Adapter contract
# ---------------------------------------------------------------------------

def test_nse_bhavcopy_satisfies_protocol() -> None:
    """NseBhavcopSource satisfies the DataSource protocol."""
    source = NseBhavcopSource()
    assert isinstance(source, DataSource)
    assert source.name == "nse_bhavcopy"


def test_nse_bhavcopy_capability_flags() -> None:
    """delivery_pct=True, adjusted=False, redistribution=False (pending review)."""
    source = NseBhavcopSource()
    assert source.supports("delivery_pct") is True
    assert source.supports("adjusted") is False
    assert source.supports("redistribution") is False
    assert source.supports("unknown_cap") is False


def test_nse_bhavcopy_publish_guard() -> None:
    """Publish-guard must reject the bhavcopy source (redistribution=False)."""
    from app.data.base import PublishGuardError, assert_publishable
    with pytest.raises(PublishGuardError):
        assert_publishable(NseBhavcopSource())


def test_get_source_resolves_nse_bhavcopy() -> None:
    """get_source('nse_bhavcopy') returns a NseBhavcopSource instance."""
    from app.data.base import get_source
    source = get_source("nse_bhavcopy")
    assert source.name == "nse_bhavcopy"
    assert isinstance(source, NseBhavcopSource)


# ---------------------------------------------------------------------------
# corp_actions (returns empty list — NSE corp-action API deferred)
# ---------------------------------------------------------------------------

def test_nse_bhavcopy_fetch_corporate_actions_returns_empty() -> None:
    source = NseBhavcopSource()
    result = source.fetch_corporate_actions(["RELIANCE", "TCS"], since=date(2020, 1, 1))
    assert result == []
