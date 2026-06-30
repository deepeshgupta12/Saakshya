"""Standard error codes and exception classes (docs/10 §0.3)."""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from app.api.envelope import fail


class SaakshyaError(Exception):
    """Base for all API-level errors — maps to the standard error envelope."""

    http_status: int = 500
    code:        str = "INTERNAL"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(SaakshyaError):
    http_status = 404
    code        = "NOT_FOUND"


class DataSuppressedError(SaakshyaError):
    """Critical input missing — value was suppressed, not guessed (SPEC §6.2)."""
    http_status = 422
    code        = "DATA_SUPPRESSED"


class ModeGatedError(SaakshyaError):
    """RA-gated feature; absent until Mode B is in force (docs/10 §14)."""
    http_status = 403
    code        = "MODE_GATED"


class PlanRequiredError(SaakshyaError):
    http_status = 403
    code        = "PLAN_REQUIRED"


class ValidationError(SaakshyaError):
    http_status = 400
    code        = "VALIDATION_ERROR"


class RateLimitedError(SaakshyaError):
    http_status = 429
    code        = "RATE_LIMITED"
    retriable   = True


class PipelineUnavailableError(SaakshyaError):
    http_status = 503
    code        = "PIPELINE_UNAVAILABLE"


# ---------------------------------------------------------------------------
# Exception handlers registered on the FastAPI app
# ---------------------------------------------------------------------------

def _request_id(request: Request) -> str:
    return request.state.request_id if hasattr(request.state, "request_id") else ""


async def saakshya_error_handler(request: Request, exc: SaakshyaError) -> JSONResponse:
    body = fail(
        exc.code,
        exc.message,
        details=exc.details,
        retriable=getattr(exc, "retriable", False),
        request_id=_request_id(request),
    )
    return JSONResponse(status_code=exc.http_status, content=body)


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    body = fail(
        "INTERNAL",
        "An unexpected error occurred.",
        request_id=_request_id(request),
    )
    return JSONResponse(status_code=500, content=body)
