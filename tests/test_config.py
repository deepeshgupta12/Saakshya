"""Settings load + fail-loud behavior (docs/27 §0.5, §5)."""

from __future__ import annotations

import pytest

from app.config import Settings


def test_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.model_version == "claude-haiku-4-5-20251001"
    assert settings.active_data_source == "yfinance"
    assert settings.history_period == "max"


def test_require_anthropic_key_fails_loud() -> None:
    settings = Settings(_env_file=None, anthropic_api_key=None)
    with pytest.raises(RuntimeError):
        settings.require_anthropic_key()


def test_require_anthropic_key_does_not_leak_value() -> None:
    settings = Settings(_env_file=None, anthropic_api_key=None)
    try:
        settings.require_anthropic_key()
    except RuntimeError as exc:
        assert "ANTHROPIC_API_KEY" in str(exc)  # names the var, never a value


def test_require_anthropic_key_ok() -> None:
    settings = Settings(_env_file=None, anthropic_api_key="sk-test-123")
    assert settings.require_anthropic_key() == "sk-test-123"
