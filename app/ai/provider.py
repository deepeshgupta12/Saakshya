"""LLM provider abstraction (docs/14 §3, SPEC §9; D-057 supersedes D-027/D-051).

Sole provider: AnthropicProvider (Claude Haiku cheap / Claude Sonnet premium) —
requires ANTHROPIC_API_KEY. Ollama was removed (it did not perform reliably on the
M1). The LLMProvider Protocol is retained so tests can inject fakes and so a future
vendor can be added without touching business logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

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


class AnthropicProvider:
    """Anthropic provider (Claude Haiku cheap / Claude Sonnet premium).

    Requires ANTHROPIC_API_KEY. Model ids default to the configured cheap/premium
    tiers (ai_model_cheap / ai_model_premium) so a model bump is a config change.
    """

    def __init__(
        self,
        model_cheap:   str | None = None,
        model_premium: str | None = None,
    ) -> None:
        cfg = get_settings()
        self._models: dict[str, str] = {
            "cheap":   model_cheap   or cfg.ai_model_cheap,
            "premium": model_premium or cfg.ai_model_premium,
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
        from anthropic.types import TextBlock  # noqa: PLC0415
        first = msg.content[0] if msg.content else None
        text  = first.text if isinstance(first, TextBlock) else ""
        return LLMResult(
            text=text,
            model_id=model_id,
            tokens_in=msg.usage.input_tokens,
            tokens_out=msg.usage.output_tokens,
            cost_usd=0.0,
        )


def get_default_provider() -> LLMProvider:
    """Return the default LLM provider — Anthropic Claude (D-057).

    Anthropic is the sole supported provider; ANTHROPIC_API_KEY must be set.
    An unrecognised SAAKSHYA_AI_PROVIDER falls back to Anthropic rather than
    silently disabling AI.
    """
    return AnthropicProvider()
