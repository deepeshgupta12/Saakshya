"""FastAPI application entry-point (docs/09 §4, docs/10).

Start the API server:
    uvicorn app.main:app --reload --port 8000

All endpoints use the standard envelope {data, meta, error} — see app/api/envelope.py.
Rate limits and error handling are wired at the app level.
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.envelope import fail
from app.api.errors import SaakshyaError, generic_error_handler, saakshya_error_handler
from app.api.routers import market, scanners, sectors, stocks
from app.api.routers import auth, watchlists, ai as ai_router
from app.api.routers import news as news_router
from app.api.routers import portfolio as portfolio_router
from app.api.routers import alerts as alerts_router
from app.api.routers import strategies as strategies_router

app = FastAPI(
    title="Saakshya API",
    version="0.8.0",
    description=(
        "Evidence-first Indian equity analytics for NSE/BSE. "
        "Mode A (pure analytics — not investment advice). "
        "See SPEC.md §2 for compliance scope."
    ),
)

# CORS — local-first: allow all origins during dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _attach_request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Attach a per-request ID so error envelopes can be correlated."""
    request.state.request_id = str(uuid.uuid4())[:8]
    response = await call_next(request)
    response.headers["X-Request-Id"] = request.state.request_id
    return response


# Exception handlers — all errors return the standard envelope {data, meta, error}.
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    rid = request.state.request_id if hasattr(request.state, "request_id") else ""
    body = fail(f"HTTP_{exc.status_code}", str(exc.detail), request_id=rid)
    headers = getattr(exc, "headers", None) or {}
    return JSONResponse(status_code=exc.status_code, content=body, headers=headers)


app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(SaakshyaError, saakshya_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, generic_error_handler)

# Routers.
app.include_router(market.router)
app.include_router(scanners.router)
app.include_router(sectors.router)
app.include_router(stocks.router)
app.include_router(auth.router)
app.include_router(watchlists.router)
app.include_router(ai_router.router)
app.include_router(news_router.router)
app.include_router(portfolio_router.router)
app.include_router(alerts_router.router)
app.include_router(strategies_router.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "saakshya-api"}
