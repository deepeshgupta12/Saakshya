"""Adapter contract: sources satisfy the Protocol; publish-guard enforced (docs/steps/01)."""

from __future__ import annotations

import pytest

from app.data.base import (
    DataSource,
    PublishGuardError,
    assert_publishable,
    get_source,
)
from app.data.yfinance_source import YFinanceSource


def test_yfinance_satisfies_protocol() -> None:
    source = YFinanceSource()
    assert isinstance(source, DataSource)
    assert source.name == "yfinance"


def test_yfinance_capabilities() -> None:
    source = YFinanceSource()
    assert source.supports("adjusted") is True
    assert source.supports("delivery_pct") is False
    assert source.supports("redistribution") is False
    assert source.supports("nonexistent") is False


def test_publish_guard_blocks_non_redistributable_source() -> None:
    with pytest.raises(PublishGuardError):
        assert_publishable(YFinanceSource())


def test_get_source_resolves_yfinance() -> None:
    assert get_source("yfinance").name == "yfinance"


def test_get_source_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        get_source("not_a_real_source")
