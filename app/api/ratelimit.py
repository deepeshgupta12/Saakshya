"""Token-bucket rate limiter (docs/10 §0.4, docs/09 §5.3).

In-process implementation — no Redis needed for local-first MVP.
Config-driven via Settings.api_read_rate_limit / api_ai_rate_limit.
Buckets are keyed by (client_ip, bucket_name).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import Request

from app.api.errors import RateLimitedError
from app.config import get_settings


@dataclass
class _Bucket:
    capacity: float
    tokens:   float
    refill_rate: float       # tokens / second
    last:     float = field(default_factory=time.monotonic)

    def _refill(self) -> None:
        now  = time.monotonic()
        diff = now - self.last
        self.tokens = min(self.capacity, self.tokens + diff * self.refill_rate)
        self.last   = now

    def consume(self) -> bool:
        """Consume one token. Returns True if allowed, False if throttled."""
        self._refill()
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class RateLimiter:
    """Thread-safe in-process token-bucket rate limiter."""

    def __init__(self) -> None:
        settings = get_settings()
        self._configs: dict[str, tuple[float, float]] = {
            "read": (
                float(settings.api_read_rate_limit),
                float(settings.api_read_rate_limit) / 60.0,
            ),
            "ai": (
                float(settings.api_ai_rate_limit),
                float(settings.api_ai_rate_limit) / 60.0,
            ),
            "auth": (
                float(settings.api_auth_rate_limit),
                float(settings.api_auth_rate_limit) / 60.0,
            ),
        }
        self._buckets: dict[tuple[str, str], _Bucket] = defaultdict(
            lambda: _Bucket(capacity=0, tokens=0, refill_rate=0)
        )
        self._lock = threading.Lock()

    def _get_or_create(self, key: tuple[str, str]) -> _Bucket:
        if key not in self._buckets:
            bucket_name = key[1]
            cap, rate = self._configs.get(bucket_name, (60, 1))
            self._buckets[key] = _Bucket(capacity=cap, tokens=cap, refill_rate=rate)
        return self._buckets[key]

    def check(self, client_ip: str, bucket: str = "read") -> None:
        """Raise RateLimitedError if the client is over the per-minute limit."""
        key = (client_ip, bucket)
        with self._lock:
            b = self._get_or_create(key)
            allowed = b.consume()
        if not allowed:
            raise RateLimitedError(
                "Rate limit exceeded. Retry after 60 s.",
                details={"bucket": bucket},
            )


_limiter = RateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract best-effort client IP from the request."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(request: Request, bucket: str = "read") -> None:
    """Enforce the named token bucket — call directly or use the typed deps below."""
    _limiter.check(get_client_ip(request), bucket)


def read_rate_limit_dep(request: Request) -> None:
    """FastAPI dependency for read-endpoint rate limiting."""
    rate_limit(request, "read")


def ai_rate_limit_dep(request: Request) -> None:
    """FastAPI dependency for AI-endpoint rate limiting (stricter bucket)."""
    rate_limit(request, "ai")


def auth_rate_limit_dep(request: Request) -> None:
    """FastAPI dependency for auth-endpoint rate limiting (10 req/min per IP)."""
    rate_limit(request, "auth")
