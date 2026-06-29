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

    # Storage / data paths.
    duckdb_path: Path = Field(default=REPO_ROOT / "data" / "saakshya.duckdb")
    data_dir: Path = Field(default=REPO_ROOT / "data")
    universe_path: Path = Field(default=REPO_ROOT / "data" / "universe.csv")

    # AI layer (used from M4). Default is the local cheap tier (SPEC §14.4).
    model_version: str = Field(default="claude-haiku-4-5-20251001")

    # Data source selection + fetch window.
    active_data_source: str = Field(default="yfinance")
    history_period: str = Field(default="max")

    def require_anthropic_key(self) -> str:
        """Return the key or fail loud (docs/27 §0.5) — without leaking the value."""
        if not self.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env (see .env.example)."
            )
        return self.anthropic_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor used everywhere (docs/27 §5)."""
    return Settings()
