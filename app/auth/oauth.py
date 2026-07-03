"""Google OIDC social sign-in handler (docs/23 §1, M7 step 07 task 5).

Flow:
  1. Frontend calls Google Identity Services → receives an id_token (JWT, RS256).
  2. Frontend POSTs id_token to POST /api/auth/oauth/google.
  3. This module validates the id_token against Google's JWKS, extracts claims.
  4. Maps provider subject → oauth_identities → users:
     - Existing identity: return the linked user.
     - New identity for existing email: link to that user, add identity row.
     - Totally new: create user account + auto-consent + identity row.
  5. Issues our JWT access + refresh token pair.

Required env vars:
  GOOGLE_CLIENT_ID — your Google OAuth 2.0 web client ID.

Without GOOGLE_CLIENT_ID the endpoint returns 503 (not configured).
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
from jose import JWTError, jwt as jose_jwt

_GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_GOOGLE_ISSUERS   = {"https://accounts.google.com", "accounts.google.com"}
_jwks_cache: dict[str, Any] | None = None


def _fetch_google_jwks() -> dict[str, Any]:
    """Fetch Google's JWKS (cached per process; re-fetched on unknown kid)."""
    global _jwks_cache
    if _jwks_cache is None:
        resp = httpx.get(_GOOGLE_CERTS_URL, timeout=5.0)
        resp.raise_for_status()
        _jwks_cache = resp.json()
    return _jwks_cache


def validate_google_id_token(id_token: str, client_id: str) -> dict[str, Any]:
    """Validate a Google ID token; return the decoded claims dict.

    Raises ValueError on invalid token, JWTError on signature failure.
    """
    header  = jose_jwt.get_unverified_header(id_token)
    kid     = header.get("kid")
    jwks    = _fetch_google_jwks()

    # Find the matching key; retry once with a fresh JWKS on cache miss.
    matching = [k for k in jwks.get("keys", []) if k.get("kid") == kid]
    if not matching:
        global _jwks_cache
        _jwks_cache = None
        jwks    = _fetch_google_jwks()
        matching = [k for k in jwks.get("keys", []) if k.get("kid") == kid]
    if not matching:
        raise ValueError(f"No matching Google public key for kid={kid!r}")

    pub_key = matching[0]
    claims  = jose_jwt.decode(
        id_token,
        pub_key,
        algorithms=["RS256"],
        audience=client_id,
        issuer=list(_GOOGLE_ISSUERS),
    )
    return claims


def get_or_create_google_user(
    mongo: Any,
    claims: dict[str, Any],
) -> tuple[str, str]:
    """Map Google claims → (user_id, plan) using MongoDB (D-059).

    Creates user + consent docs on first login for that Google account.
    """
    from datetime import datetime, timezone  # noqa: PLC0415

    provider = "google"
    subject  = claims["sub"]
    email    = claims.get("email", "").lower() or None
    now      = datetime.now(tz=timezone.utc)

    # 1. Existing oauth_identities doc → return linked user.
    ident = mongo.oauth_identities.find_one({"provider": provider, "subject": subject}, {"user_id": 1})
    if ident:
        user = mongo.users.find_one({"user_id": ident["user_id"]}, {"user_id": 1, "plan": 1})
        if user:
            return str(user["user_id"]), str(user.get("plan", "free"))

    # 2. Existing user by email → link the identity.
    user = mongo.users.find_one({"email": email}, {"user_id": 1, "plan": 1}) if email else None

    if user:
        user_id = str(user["user_id"])
        plan    = str(user.get("plan", "free"))
    else:
        # 3. New user: create account + auto-consent (Google OIDC = implicit consent).
        user_id      = str(uuid.uuid4())
        display_name = claims.get("name") or (email.split("@")[0] if email else "User")
        plan         = "free"
        mongo.users.insert_one({
            "user_id": user_id, "email": email, "display_name": display_name,
            "plan": plan, "created_at": now, "updated_at": now,
        })
        mongo.consents.insert_many([
            {"consent_id": str(uuid.uuid4()), "user_id": user_id,
             "consent_type": ctype, "granted_at": now}
            for ctype in ("not_advice", "ai_use")
        ])

    # 4. Upsert oauth_identities doc (idempotent — unique (provider, subject) index).
    mongo.oauth_identities.update_one(
        {"provider": provider, "subject": subject},
        {"$setOnInsert": {
            "id": str(uuid.uuid4()), "user_id": user_id,
            "provider": provider, "subject": subject, "email": email, "created_at": now,
        }},
        upsert=True,
    )
    return user_id, plan
