"""Tests for token-bucket rate limiter (docs/10 §0.4)."""

from __future__ import annotations

import pytest

from app.api.errors import RateLimitedError
from app.api.ratelimit import RateLimiter


def test_within_limit_passes() -> None:
    rl = RateLimiter()
    for _ in range(5):
        rl.check("127.0.0.1", "read")  # should not raise


def test_over_limit_raises() -> None:
    rl = RateLimiter()
    # Drain the entire bucket.
    settings_capacity = 60  # default api_read_rate_limit
    for _ in range(settings_capacity):
        rl.check("10.0.0.1", "read")
    with pytest.raises(RateLimitedError):
        rl.check("10.0.0.1", "read")


def test_different_ips_are_independent() -> None:
    rl = RateLimiter()
    capacity = 60
    for _ in range(capacity):
        rl.check("1.1.1.1", "read")
    # IP 1.1.1.1 is exhausted; 2.2.2.2 should still pass.
    rl.check("2.2.2.2", "read")


def test_ai_bucket_has_lower_limit() -> None:
    rl = RateLimiter()
    ai_limit = 30
    for _ in range(ai_limit):
        rl.check("127.0.0.1", "ai")
    with pytest.raises(RateLimitedError) as exc_info:
        rl.check("127.0.0.1", "ai")
    assert exc_info.value.details is not None
    assert exc_info.value.details["bucket"] == "ai"
