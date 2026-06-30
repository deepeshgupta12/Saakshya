"""LLM provider abstraction (docs/14 §3, SPEC §9, D-027).

Default: OllamaProvider using qwen2.5:7b-instruct via the local Ollama server.
Alternative: AnthropicProvider (Claude Haiku / premium) — requires ANTHROPIC_API_KEY.

Swapping providers touches no business logic; only get_default_provider() changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import httpx

from app.config import get_settings


@dataclass
class LLMResult:
    text:       str
    model_id:   str
    tokens_in:  int
    tokens_out: int
    cost_usd:   float


@runtime_checkable
class LLMProvider(Protocol):
    def complete(
        self,
        *,
        prompt_id:      str,
        prompt_version: str,
        system:         str,
        payload_json:   str,
        model_tier:     str,
    ) -> LLMResult: ...


class OllamaProvider:
    """Local Ollama provider via the OpenAI-compatible endpoint (D-027).

    Uses httpx (already in requirements); no extra dependency needed.
    cost_usd is always 0.0 for local inference.
    """

    def __init__(
        self,
        base_url:      str | None = None,
        model_cheap:   str | None = None,
        model_premium: str | None = None,
    ) -> None:
        cfg = get_settings()
        self._base_url = (base_url or cfg.ai_ollama_base_url).rstrip("/")
        self._models: dict[str, str] = {
            "cheap":   model_cheap   or cfg.ai_ollama_model_cheap,
            "premium": model_premium or cfg.ai_ollama_model_premium,
        }

    def complete(
        self,
        *,
        prompt_id:      str,
        prompt_version: str,
        system:         str,
        payload_json:   str,
        model_tier:     str = "cheap",
    ) -> LLMResult:
        model_id = self._models.get(model_tier, self._models["cheap"])

        resp = httpx.post(
            f"{self._base_url}/v1/chat/completions",
            json={
                "model": model_id,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": payload_json},
                ],
                "temperature": 0.1,   # factual grounding favours low temperature
                "max_tokens":  512,
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.json()

        text  = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return LLMResult(
            text=text,
            model_id=model_id,
            tokens_in=int(usage.get("prompt_tokens", 0)),
            tokens_out=int(usage.get("completion_tokens", 0)),
            cost_usd=0.0,
        )


class AnthropicProvider:
    """Anthropic provider (Claude Haiku cheap / premium).  Requires ANTHROPIC_API_KEY."""

    def __init__(
        self,
        model_cheap:   str = "claude-haiku-4-5-20251001",
        model_premium: str = "claude-sonnet-4-6",
    ) -> None:
        self._models: dict[str, str] = {
            "cheap":   model_cheap,
            "premium": model_premium,
        }

    def complete(
        self,
        *,
        prompt_id:      str,
        prompt_version: str,
        system:         str,
        payload_json:   str,
        model_tier:     str = "cheap",
    ) -> LLMResult:
        import anthropic  # noqa: PLC0415

        cfg      = get_settings()
        api_key  = cfg.require_anthropic_key()
        client   = anthropic.Anthropic(api_key=api_key)
        model_id = self._models.get(model_tier, self._models["cheap"])

        msg = client.messages.create(
            model=model_id,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": payload_json}],
        )
        first = msg.content[0] if msg.content else None
        text  = first.text if hasattr(first, "text") else ""
        return LLMResult(
            text=text,
            model_id=model_id,
            tokens_in=msg.usage.input_tokens,
            tokens_out=msg.usage.output_tokens,
            cost_usd=0.0,
        )


def get_default_provider() -> LLMProvider:
    """Return the configured default provider.

    Set SAAKSHYA_AI_PROVIDER=anthropic to switch to Claude (requires API key).
    Default: OllamaProvider (local, no API key, qwen2.5:7b-instruct).
    """
    cfg = get_settings()
    if cfg.ai_provider == "anthropic":
        return AnthropicProvider()
    return OllamaProvider()
