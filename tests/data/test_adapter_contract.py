"""Adapter contract: KiteSource satisfies the Protocol; publish-guard enforced (D-058)."""

from __future__ import annotations

from datetime import date

import pytest

from app.data.base import (
    DataSource,
    PublishGuardError,
    assert_publishable,
    get_source,
)
from app.data.kite_source import KiteSource, _normalize_symbol, _period_start


def test_kite_satisfies_protocol() -> None:
    source = KiteSource()
    assert isinstance(source, DataSource)
    assert source.name == "kite"


def test_kite_capabilities() -> None:
    source = KiteSource()
    # Kite historical candles are unadjusted, carry no delivery %, and are not
    # licensed for commercial redistribution.
    assert source.supports("adjusted") is False
    assert source.supports("delivery_pct") is False
    assert source.supports("redistribution") is False
    assert source.supports("nonexistent") is False


def test_kite_has_no_corp_action_feed() -> None:
    # Kite Connect exposes no corporate-action API (documented gap, docs/12 §3.4).
    assert KiteSource().fetch_corporate_actions(["RELIANCE"], since=date(2000, 1, 1)) == []
    assert KiteSource().fetch_delivery(date(2026, 6, 30)) is None


def test_publish_guard_blocks_non_redistributable_source() -> None:
    with pytest.raises(PublishGuardError):
        assert_publishable(KiteSource())


def test_get_source_resolves_kite() -> None:
    assert get_source("kite").name == "kite"


def test_get_source_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        get_source("not_a_real_source")


def test_normalize_symbol_strips_legacy_and_prefix_forms() -> None:
    assert _normalize_symbol("RELIANCE") == "RELIANCE"
    assert _normalize_symbol("RELIANCE.NS") == "RELIANCE"
    assert _normalize_symbol("NSE:RELIANCE") == "RELIANCE"
    assert _normalize_symbol(" reliance.bo ") == "RELIANCE"


def test_period_start_parsing() -> None:
    assert _period_start("max") == date(2000, 1, 1)
    assert _period_start("5y") < date.today()
    # nonsense period falls back to the max window
    assert _period_start("garbage") == date(2000, 1, 1)
