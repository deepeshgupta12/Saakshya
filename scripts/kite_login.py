"""Acquire today's Zerodha Kite access token (D-058, docs/12 §3.3).

Runs the daily login: automated TOTP first (unattended), browser-callback fallback.
On success the token is written to .env (KITE_ACCESS_TOKEN) and reused same-day.

Usage:
    python scripts/kite_login.py            # use cached token if present
    python scripts/kite_login.py --force    # force a fresh login

Prereqs in .env:
    KITE_API_KEY, KITE_API_SECRET                        (always)
    KITE_USER_ID, KITE_PASSWORD, KITE_TOTP_SECRET        (for automated TOTP login)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.data.kite_auth import KiteAuthError, ensure_access_token  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Acquire a Kite access token for today.")
    parser.add_argument("--force", action="store_true", help="force a fresh login")
    args = parser.parse_args()

    try:
        token = ensure_access_token(force=args.force)
    except KiteAuthError as exc:
        print(f"Kite login failed: {exc}")
        sys.exit(1)

    # Never print the full token — just confirm and show a masked tail.
    masked = f"…{token[-4:]}" if len(token) >= 4 else "set"
    print(f"Kite access token acquired ({masked}) and written to .env. Ready to ingest.")


if __name__ == "__main__":
    main()
