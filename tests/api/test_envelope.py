"""Tests for standard response envelope (docs/10 §0.1–0.2)."""

from __future__ import annotations

from app.api.envelope import PageMeta, fail, ok


def test_ok_shape() -> None:
    result = ok({"key": "value"}, as_of="2024-01-02", data_confidence="high")
    assert result["data"] == {"key": "value"}
    assert result["error"] is None
    assert result["meta"]["as_of"] == "2024-01-02"
    assert result["meta"]["data_confidence"] == "high"
    assert result["meta"]["generated_at"]  # non-empty


def test_ok_with_page_meta() -> None:
    page = PageMeta(limit=50, offset=0, total=123)
    result = ok([], page=page)
    assert result["meta"]["page"]["total"] == 123
    assert result["meta"]["page"]["limit"] == 50


def test_ok_defaults() -> None:
    result = ok(None)
    assert result["data"] is None
    assert result["meta"]["is_adjusted"] is True
    assert result["meta"]["data_confidence"] == "high"


def test_fail_shape() -> None:
    result = fail("NOT_FOUND", "Symbol not found", request_id="abc123")
    assert result["data"] is None
    assert result["error"]["code"] == "NOT_FOUND"
    assert result["error"]["message"] == "Symbol not found"
    assert result["error"]["retriable"] is False
    assert result["meta"]["request_id"] == "abc123"


def test_fail_retriable() -> None:
    result = fail("RATE_LIMITED", "Too fast", retriable=True)
    assert result["error"]["retriable"] is True


def test_fail_with_details() -> None:
    result = fail("VALIDATION_ERROR", "Bad param", details={"field": "limit"})
    assert result["error"]["details"]["field"] == "limit"
