"""Prompt registry: maps prompt_id → (version, filename, model_tier, content_hash).

A change to a prompt file requires:
  1. Rename the file to bump the version (e.g. stock_summary.v2.txt).
  2. Update the registry entry below with the new version, filename, and hash.
This is enforced by get_prompt() and tested in tests/ai/test_registry.py.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent / "prompts"

# Registry format: prompt_id -> (version, filename, model_tier, sha256_of_file_bytes)
# To update a prompt: rename file, bump version, recompute sha256, update here.
_REGISTRY: dict[str, tuple[str, str, str, str]] = {
    "stock_summary": (
        "v1",
        "stock_summary.v1.txt",
        "cheap",
        "ab0aa65363a862a044b87cb2de0eca55efe8944c8f78fa0dff66f62eebbfeea5",
    ),
    "market_brief": (
        "v1",
        "market_brief.v1.txt",
        "cheap",
        "770faa4c11c6f93a0014f4a5681ccb3e1ed20d824c61c5c789fe3f8763f8b5bc",
    ),
    "scanner_explain": (
        "v1",
        "scanner_explain.v1.txt",
        "cheap",
        "458da252f0b5d4025045f90a389b79d45c13dd4d85f8a53bc8e118ae1142a85f",
    ),
    "portfolio_summary": (
        "v1",
        "portfolio_summary.v1.txt",
        "cheap",
        "ed62f49130a7ca0f0aa9e744ad2ab44908830a9cc17a4252dc443cd4e2bed4d7",
    ),
}


def get_prompt(prompt_id: str) -> tuple[str, str, str]:
    """Return (text, version, model_tier) for a registered prompt_id.

    Raises KeyError for unknown prompt_id.
    Raises RuntimeError if the file has changed without a version bump.
    """
    if prompt_id not in _REGISTRY:
        raise KeyError(f"Unknown prompt_id: {prompt_id!r}. Available: {list(_REGISTRY)}")

    version, filename, model_tier, expected_hash = _REGISTRY[prompt_id]
    path = _PROMPTS_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    content = path.read_bytes()
    actual_hash = hashlib.sha256(content).hexdigest()

    if actual_hash != expected_hash:
        raise RuntimeError(
            f"Prompt file '{filename}' has been modified without a version bump.\n"
            f"  Expected SHA-256: {expected_hash}\n"
            f"  Actual  SHA-256: {actual_hash}\n"
            f"Rename the file (e.g. '{filename.replace('v1', 'v2')}'), "
            f"update _REGISTRY with the new version and hash."
        )

    return content.decode("utf-8"), version, model_tier


def list_prompts() -> list[dict[str, str]]:
    """Return metadata for all registered prompts (for admin / introspection)."""
    return [
        {"prompt_id": pid, "version": v, "filename": f, "model_tier": t}
        for pid, (v, f, t, _) in _REGISTRY.items()
    ]
