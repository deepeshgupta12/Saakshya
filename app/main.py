"""FastAPI application entry-point (docs/09 §4, docs/10).

Start the API server:
    uvicorn app.main:app --reload --port 8000

All endpoints use the standard envelope {data, meta, error} — see app/api/envelope.py.
Rate limits and error handling are wired at the app level.
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import SaakshyaError, generic_error_handler, saakshya_error_handler
from app.api.routers import market, scanners, sectors, stocks
from app.api.routers import auth, watchlists, ai as ai_router

app = FastAPI(
    title="Saakshya API",
    version="0.7.0",
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


# Exception handlers — convert SaakshyaError + uncaught exceptions to envelope format.
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


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "saakshya-api"}
