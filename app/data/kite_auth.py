"""Zerodha Kite Connect daily token management (D-058, docs/12 §3.2).

Kite's ``access_token`` expires at ~06:00 IST the next day (regulatory requirement,
docs/connect/v3/user) and must be regenerated via a login. This module provides that in
two flavours, tried in order:

  1. **Automated TOTP login (primary, unattended)** — scripts the full Kite web login
     (user id + password + a programmatically-generated TOTP) to obtain a
     ``request_token`` with zero human interaction, then exchanges it for the day's
     ``access_token``. Suitable for the overnight EOD pipeline / cron.
  2. **Browser callback (fallback)** — opens the Kite login URL in a browser and runs a
     tiny local HTTP server on the registered redirect (``127.0.0.1:8000/kite/callback``)
     to capture the ``request_token`` after the user authorises. Used when Zerodha forces
     a manual re-auth (e.g. new-device / password reset).

The resolved token is cached in-process and written back to ``.env`` (``KITE_ACCESS_TOKEN``)
so subsequent runs the same day reuse it without another login.

Secrets (password / TOTP secret / api secret) are read from settings only and are never
logged. NOTHING here places orders — Mode A, EOD only.
"""

from __future__ import annotations

import logging
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from app.config import get_settings

log = logging.getLogger(__name__)

_KITE_LOGIN_HOST = "https://kite.zerodha.com"
_ENV_TOKEN_KEY = "KITE_ACCESS_TOKEN"


class KiteAuthError(RuntimeError):
    """Raised when neither the automated nor the callback login could obtain a token."""


def ensure_access_token(*, force: bool = False) -> str:
    """Return a valid Kite ``access_token`` for today.

    Uses the token already in settings/.env if present (``force=False``); otherwise
    tries automated TOTP login, then the browser callback. On success the token is
    persisted to ``.env`` and returned.
    """
    cfg = get_settings()
    if not force and cfg.kite_access_token:
        return cfg.kite_access_token

    api_key, api_secret = cfg.require_kite_api()

    request_token: str | None = None
    try:
        request_token = _automated_request_token()
        log.info("[kite_auth] obtained request_token via automated TOTP login")
    except Exception as exc:  # noqa: BLE001 — fall back to the interactive flow
        log.warning("[kite_auth] automated login failed (%s); falling back to browser", exc)

    if request_token is None:
        request_token = _callback_request_token(api_key)
        log.info("[kite_auth] obtained request_token via browser callback")

    access_token = _exchange_request_token(api_key, api_secret, request_token)
    _persist_token(access_token)
    # Refresh the cached settings so the new token is visible this process.
    get_settings.cache_clear()  # type: ignore[attr-defined]
    return access_token


# ---------------------------------------------------------------------------
# 1. Automated TOTP login (unattended)
# ---------------------------------------------------------------------------

def _automated_request_token() -> str:
    """Drive the Kite web login end-to-end with TOTP and return a ``request_token``.

    Requires KITE_USER_ID / KITE_PASSWORD / KITE_TOTP_SECRET in the environment.
    """
    import httpx  # noqa: PLC0415
    import pyotp  # noqa: PLC0415

    cfg = get_settings()
    if not (cfg.kite_user_id and cfg.kite_password and cfg.kite_totp_secret):
        raise KiteAuthError(
            "Automated login needs KITE_USER_ID, KITE_PASSWORD and KITE_TOTP_SECRET."
        )
    api_key, _ = cfg.require_kite_api()

    verify: object = cfg.kite_ca_bundle or True  # supply proxy CA, never disable
    with httpx.Client(follow_redirects=False, timeout=30.0, verify=verify) as client:
        # Step 1 — password login → request_id
        r1 = client.post(
            f"{_KITE_LOGIN_HOST}/api/login",
            data={"user_id": cfg.kite_user_id, "password": cfg.kite_password},
        )
        r1.raise_for_status()
        request_id = r1.json()["data"]["request_id"]

        # Step 2 — TOTP 2FA
        totp = pyotp.TOTP(cfg.kite_totp_secret).now()
        r2 = client.post(
            f"{_KITE_LOGIN_HOST}/api/twofa",
            data={
                "user_id": cfg.kite_user_id,
                "request_id": request_id,
                "twofa_value": totp,
                "twofa_type": "totp",
            },
        )
        r2.raise_for_status()

        # Step 3 — hit the Connect login URL; Kite 302-redirects to our redirect_url
        # with ?request_token=... appended. We capture it from the Location header.
        return _follow_to_request_token(client, api_key)


def _follow_to_request_token(client: object, api_key: str) -> str:
    """Walk Kite's redirect chain (session cookies set) until request_token appears."""
    import httpx  # noqa: PLC0415

    assert isinstance(client, httpx.Client)
    url: str | None = f"https://kite.trade/connect/login?api_key={api_key}&v=3"
    for _ in range(10):  # bounded redirect walk
        if url is None:
            break
        resp = client.get(url)
        location = resp.headers.get("location")
        token = _extract_request_token(resp.url.query.decode() if resp.url.query else "")
        if token:
            return token
        if location:
            token = _extract_request_token(urlparse(location).query)
            if token:
                return token
            url = location if location.startswith("http") else None
        else:
            break
    raise KiteAuthError("request_token not found in Kite redirect chain")


def _extract_request_token(query: str) -> str | None:
    values = parse_qs(query).get("request_token")
    return values[0] if values else None


# ---------------------------------------------------------------------------
# 2. Browser callback (interactive fallback)
# ---------------------------------------------------------------------------

class _CallbackHandler(BaseHTTPRequestHandler):
    captured_token: str | None = None

    def do_GET(self) -> None:  # noqa: N802 — required name from BaseHTTPRequestHandler
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/kite/callback"):
            self.send_response(404)
            self.end_headers()
            return
        token = _extract_request_token(parsed.query)
        _CallbackHandler.captured_token = token
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        body = (
            "<h2>Saakshya — Kite login captured.</h2>"
            "<p>You can close this tab and return to the terminal.</p>"
            if token
            else "<h2>No request_token in callback.</h2>"
        )
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, *_args: object) -> None:  # silence default stderr logging
        return


def _callback_request_token(api_key: str, *, timeout_s: float = 300.0) -> str:
    """Open the Kite login URL and capture the request_token via a local server."""
    cfg = get_settings()
    _CallbackHandler.captured_token = None
    server = HTTPServer((cfg.kite_callback_host, cfg.kite_callback_port), _CallbackHandler)
    server.timeout = timeout_s

    login_url = f"https://kite.trade/connect/login?api_key={api_key}&v=3"
    log.info("[kite_auth] opening browser for Kite login: %s", login_url)
    print(f"\n  Log in to Zerodha Kite to authorise Saakshya:\n    {login_url}\n")
    try:
        webbrowser.open(login_url)
    except Exception:  # noqa: BLE001 — headless env; user opens the URL manually
        pass

    thread = threading.Thread(target=_serve_until_token, args=(server,), daemon=True)
    thread.start()
    thread.join(timeout=timeout_s + 5)
    server.server_close()

    if not _CallbackHandler.captured_token:
        raise KiteAuthError("timed out waiting for the Kite login callback")
    return _CallbackHandler.captured_token


def _serve_until_token(server: HTTPServer) -> None:
    while _CallbackHandler.captured_token is None:
        server.handle_request()  # bounded by server.timeout


# ---------------------------------------------------------------------------
# Token exchange + persistence
# ---------------------------------------------------------------------------

def _exchange_request_token(api_key: str, api_secret: str, request_token: str) -> str:
    """Exchange a request_token for today's access_token via the Kite SDK."""
    from kiteconnect import KiteConnect  # noqa: PLC0415

    kite = KiteConnect(api_key=api_key)
    data = kite.generate_session(request_token, api_secret=api_secret)
    token = data["access_token"]
    if not token:
        raise KiteAuthError("Kite generate_session returned no access_token")
    return str(token)


def _persist_token(access_token: str) -> None:
    """Write/replace KITE_ACCESS_TOKEN in .env so same-day runs reuse it."""
    from pathlib import Path  # noqa: PLC0415

    from app.config import REPO_ROOT  # noqa: PLC0415

    env_path: Path = REPO_ROOT / ".env"
    lines: list[str] = []
    found = False
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{_ENV_TOKEN_KEY}="):
                lines.append(f"{_ENV_TOKEN_KEY}={access_token}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"{_ENV_TOKEN_KEY}={access_token}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
