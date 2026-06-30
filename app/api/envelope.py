"""Standard response envelope (docs/10 §0.1–0.2, docs/27 §3.3).

Every 2xx response from a Saakshya endpoint is wrapped in:
  { "data": <T>, "meta": { as_of, data_confidence, ... }, "error": null }

Errors use:
  { "data": null, "meta": { request_id }, "error": { code, message, ... } }
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PageMeta(BaseModel):
    limit:  int
    offset: int
    total:  int


class Meta(BaseModel):
    as_of:            str | None = None
    data_confidence:  str | None = None        # high | medium | low | suppressed
    source:           str | None = None
    is_adjusted:      bool       = True
    generated_at:     str        = ""
    request_id:       str        = ""
    cache:            str | None = None        # hit | miss | degraded
    page:             PageMeta | None = None


class ErrorDetail(BaseModel):
    code:      str
    message:   str
    details:   dict[str, Any] | None = None
    retriable: bool = False


class Envelope(BaseModel, Generic[T]):
    data:  T | None       = None
    meta:  Meta
    error: ErrorDetail | None = None


def _now_utc() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def ok(
    data: Any,
    *,
    as_of: str | None = None,
    data_confidence: str | None = "high",
    source: str | None = None,
    is_adjusted: bool = True,
    request_id: str = "",
    cache: str | None = None,
    page: PageMeta | None = None,
) -> dict[str, Any]:
    """Build a successful envelope dict (serialised directly by FastAPI)."""
    return {
        "data": data,
        "meta": {
            "as_of":           as_of,
            "data_confidence": data_confidence,
            "source":          source,
            "is_adjusted":     is_adjusted,
            "generated_at":    _now_utc(),
            "request_id":      request_id,
            "cache":           cache,
            "page":            page.model_dump() if page else None,
        },
        "error": None,
    }


def fail(
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    retriable: bool = False,
    request_id: str = "",
) -> dict[str, Any]:
    """Build an error envelope dict."""
    return {
        "data": None,
        "meta": {"request_id": request_id, "generated_at": _now_utc()},
        "error": {
            "code":      code,
            "message":   message,
            "details":   details,
            "retriable": retriable,
        },
    }
