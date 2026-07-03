"""Typed application settings loaded from environment / `.env` (SPEC §12, docs/27 §5).

No module reads ``os.environ`` directly — everything goes through ``get_settings()``.
Secrets (the Anthropic key) are never logged or echoed in error messages.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = parent of the `app/` package.
REPO_ROOT: Path = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application configuration. Field values come from env vars or `.env`."""

    model_config = SettingsConfigDict(
        env_prefix="SAAKSHYA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),  # allow the `model_version` field name
        populate_by_name=True,
    )

    # Secret — read from the unprefixed ANTHROPIC_API_KEY (SPEC §14.4). Optional until M4.
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    # Storage (polyglot, D-059): TimescaleDB = analytics core; MongoDB = user/app docs.
    # Both run locally via docker-compose (D-059). DuckDB retired.
    timescale_url: str = Field(
        default="postgresql://saakshya:saakshya@localhost:5544/saakshya",
        alias="SAAKSHYA_TIMESCALE_URL",
    )
    mongodb_url: str = Field(
        default="mongodb://localhost:27017", alias="SAAKSHYA_MONGODB_URL"
    )
    mongodb_db: str = Field(default="saakshya", alias="SAAKSHYA_MONGODB_DB")
    data_dir: Path = Field(default=REPO_ROOT / "data")
    universe_path: Path = Field(default=REPO_ROOT / "data" / "universe.csv")

    # AI layer — provider + model config (M4, docs/14 §3; D-057 supersedes D-027/D-051).
    # Sole provider: Anthropic Claude (requires ANTHROPIC_API_KEY). Ollama removed —
    # it did not perform reliably on the M1. cheap tier = Haiku for repetitive daily
    # summaries; premium tier = Sonnet for complex synthesis (market brief).
    ai_provider: str = Field(default="anthropic")
    ai_model_cheap: str = Field(default="claude-haiku-4-5-20251001")
    ai_model_premium: str = Field(default="claude-sonnet-4-6")
    ai_daily_call_ceiling: int = Field(default=500)
    ai_max_regen: int = Field(default=2)
    ai_model_tier_default: str = Field(default="cheap")
    # Legacy alias retained for audit records; mirrors the cheap-tier model id.
    model_version: str = Field(default="claude-haiku-4-5-20251001")

    # Data source selection + fetch window. Kite is the sole source (D-058).
    active_data_source: str = Field(default="kite")
    history_period: str = Field(default="max")

    # ── Zerodha Kite Connect (sole market-data source, D-058) ──────────────
    # API credentials from the developers.kite.trade "Connect" app.
    kite_api_key: str | None = Field(default=None, alias="KITE_API_KEY")
    kite_api_secret: str | None = Field(default=None, alias="KITE_API_SECRET")
    # Daily access token — auto-refreshed by app/data/kite_auth.py.
    kite_access_token: str | None = Field(default=None, alias="KITE_ACCESS_TOKEN")
    # Callback flow (fallback): redirect registered on the Kite app.
    kite_redirect_url: str = Field(default="http://127.0.0.1:8000/kite/callback")
    kite_callback_host: str = Field(default="127.0.0.1")
    kite_callback_port: int = Field(default=8000)
    # Automated unattended login (primary flow): TOTP-based 2FA (D-058 option B).
    kite_user_id: str | None = Field(default=None, alias="KITE_USER_ID")
    kite_password: str | None = Field(default=None, alias="KITE_PASSWORD")
    kite_totp_secret: str | None = Field(default=None, alias="KITE_TOTP_SECRET")
    # Historical fetch: daily candles, chunked to respect Kite's per-request span.
    kite_history_chunk_days: int = Field(default=1800)
    kite_exchange: str = Field(default="NSE")
    # Corporate-proxy support: if your network TLS-inspects Kite (e.g. a Sophos/Zscaler
    # appliance re-signs the cert), point this at a PEM bundle that includes the proxy CA.
    # Applied to both the kiteconnect (requests) and kite_auth (httpx) HTTP clients.
    # NEVER disable verification — supply the CA instead.
    kite_ca_bundle: str | None = Field(default=None, alias="KITE_CA_BUNDLE")

    # Auth (M7, docs/23 §1) — HS256 secret for local-first; swap to RS256 in prod.
    # Generated once at init; set SAAKSHYA_SECRET_KEY in .env for persistence.
    secret_key: str = Field(default="dev-local-secret-change-in-prod-32chars!!")

    # OAuth social sign-in (M7 §5) — set GOOGLE_CLIENT_ID to enable Google sign-in.
    google_client_id: str | None = Field(default=None, alias="GOOGLE_CLIENT_ID")

    # API rate limits (requests per minute, per IP/client).
    api_read_rate_limit: int = Field(default=60)   # general read endpoints
    api_ai_rate_limit: int = Field(default=30)     # AI-summary endpoints (stricter)
    api_auth_rate_limit: int = Field(default=10)   # auth endpoints (stricter)

    def require_anthropic_key(self) -> str:
        """Return the key or fail loud (docs/27 §0.5) — without leaking the value."""
        if not self.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env (see .env.example)."
            )
        return self.anthropic_api_key

    def require_kite_api(self) -> tuple[str, str]:
        """Return (api_key, api_secret) or fail loud — without leaking the secret."""
        if not self.kite_api_key or not self.kite_api_secret:
            raise RuntimeError(
                "KITE_API_KEY / KITE_API_SECRET are not set. Add them to your .env "
                "(see .env.example)."
            )
        return self.kite_api_key, self.kite_api_secret


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor used everywhere (docs/27 §5)."""
    return Settings()
