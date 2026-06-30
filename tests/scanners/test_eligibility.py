"""Tests for scanners/eligibility.py (docs/02 §Tests)."""

from __future__ import annotations

from app.scanners.eligibility import check_eligibility


def _default_kwargs() -> dict:
    return dict(
        status="listed",
        close_adj=100.0,
        median_tv_20d=5.0,
        candle_count=250,
        has_quarantined_candle=False,
        corp_action_reconciled=True,
    )


def test_eligible_passes() -> None:
    result = check_eligibility(**_default_kwargs())
    assert result.eligible is True
    assert result.reason is None


def test_delisted_excluded() -> None:
    kw = _default_kwargs()
    kw["status"] = "delisted"
    result = check_eligibility(**kw)
    assert result.eligible is False
    assert "delisted" in (result.reason or "")


def test_penny_stock_excluded() -> None:
    kw = _default_kwargs()
    kw["close_adj"] = 9.0
    result = check_eligibility(**kw)
    assert result.eligible is False
    assert "close_adj" in (result.reason or "")


def test_illiquid_excluded() -> None:
    kw = _default_kwargs()
    kw["median_tv_20d"] = 0.5
    result = check_eligibility(**kw)
    assert result.eligible is False
    assert "median_tv" in (result.reason or "")


def test_insufficient_candles_excluded() -> None:
    kw = _default_kwargs()
    kw["candle_count"] = 30
    result = check_eligibility(**kw)
    assert result.eligible is False


def test_quarantined_candle_excluded() -> None:
    kw = _default_kwargs()
    kw["has_quarantined_candle"] = True
    result = check_eligibility(**kw)
    assert result.eligible is False
    assert "quarantined" in (result.reason or "")


def test_unreconciled_corp_action_excluded() -> None:
    kw = _default_kwargs()
    kw["corp_action_reconciled"] = False
    result = check_eligibility(**kw)
    assert result.eligible is False
    assert "reconcil" in (result.reason or "").lower()


def test_no_median_tv_passes() -> None:
    """When median_tv_20d is None (unknown), the check is skipped."""
    kw = _default_kwargs()
    kw["median_tv_20d"] = None
    result = check_eligibility(**kw)
    assert result.eligible is True


def test_require_200d_needs_200_candles() -> None:
    kw = _default_kwargs()
    kw["candle_count"] = 150
    result = check_eligibility(**kw, require_200d=True)
    assert result.eligible is False
    assert "200" in (result.reason or "")


def test_require_200d_with_200_candles_passes() -> None:
    kw = _default_kwargs()
    kw["candle_count"] = 200
    result = check_eligibility(**kw, require_200d=True)
    assert result.eligible is True
