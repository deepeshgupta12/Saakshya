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
    conn: Any,
    claims: dict[str, Any],
) -> tuple[str, str]:
    """Map Google claims → (user_id, plan).

    Creates user + consent rows on first login for that Google account.
    """
    provider = "google"
    subject  = claims["sub"]
    email    = claims.get("email", "").lower() or None

    # 1. Existing oauth_identities row → return linked user.
    row = conn.execute(
        "SELECT user_id FROM oauth_identities WHERE provider = ? AND subject = ?",
        [provider, subject],
    ).fetchone()
    if row:
        user_row = conn.execute(
            "SELECT user_id, plan FROM users WHERE user_id = ?", [row[0]]
        ).fetchone()
        if user_row:
            return str(user_row[0]), str(user_row[1])

    # 2. Existing user by email → link the identity.
    user_row = None
    if email:
        user_row = conn.execute(
            "SELECT user_id, plan FROM users WHERE email = ?", [email]
        ).fetchone()

    if user_row:
        user_id = str(user_row[0])
        plan    = str(user_row[1])
    else:
        # 3. New user: create account + auto-consent (Google OIDC = implicit consent).
        user_id      = str(uuid.uuid4())
        display_name = claims.get("name") or (email.split("@")[0] if email else "User")
        plan         = "free"
        conn.execute(
            "INSERT INTO users (user_id, email, display_name, plan) VALUES (?, ?, ?, ?)",
            [user_id, email, display_name, plan],
        )
        for consent_type in ("not_advice", "ai_use"):
            conn.execute(
                "INSERT INTO consents (consent_id, user_id, consent_type) VALUES (?, ?, ?)",
                [str(uuid.uuid4()), user_id, consent_type],
            )

    # 4. Insert oauth_identities row (idempotent — UNIQUE constraint guards re-insert).
    conn.execute(
        """
        INSERT OR IGNORE INTO oauth_identities (id, user_id, provider, subject, email)
        VALUES (?, ?, ?, ?, ?)
        """,
        [str(uuid.uuid4()), user_id, provider, subject, email],
    )
    return user_id, plan
