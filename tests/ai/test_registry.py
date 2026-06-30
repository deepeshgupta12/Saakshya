"""Tests for app/ai/registry.py — prompt versioning and hash enforcement."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.ai.registry import _PROMPTS_DIR, _REGISTRY, get_prompt, list_prompts


class TestGetPrompt:
    def test_valid_prompt_id_returns_text(self) -> None:
        text, version, model_tier = get_prompt("stock_summary")
        assert len(text) > 50
        assert version == "v1"
        assert model_tier == "cheap"

    def test_all_registered_prompts_loadable(self) -> None:
        for pid in _REGISTRY:
            text, version, _ = get_prompt(pid)
            assert len(text) > 0
            assert version

    def test_unknown_prompt_id_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown prompt_id"):
            get_prompt("nonexistent_prompt")

    def test_prompt_ends_with_not_investment_advice(self) -> None:
        for pid in _REGISTRY:
            text, _, _ = get_prompt(pid)
            assert "Not investment advice" in text, f"{pid} missing closing disclaimer"


class TestPromptVersionLocked:
    def test_modified_file_raises_runtime_error(self, tmp_path: Path) -> None:
        pid    = "stock_summary"
        _, filename, _, _ = _REGISTRY[pid]
        src    = _PROMPTS_DIR / filename
        backup = tmp_path / filename

        # Make a backup then modify the live file.
        shutil.copy(src, backup)
        try:
            src.write_bytes(src.read_bytes() + b"\n# unauthorized edit\n")
            with pytest.raises(RuntimeError, match="modified without a version bump"):
                get_prompt(pid)
        finally:
            # Restore the original file.
            shutil.copy(backup, src)

    def test_restored_file_loads_cleanly(self) -> None:
        text, _, _ = get_prompt("stock_summary")
        assert len(text) > 0


class TestListPrompts:
    def test_list_prompts_returns_all_ids(self) -> None:
        prompts = list_prompts()
        ids     = {p["prompt_id"] for p in prompts}
        assert "stock_summary"   in ids
        assert "market_brief"    in ids
        assert "scanner_explain" in ids

    def test_each_entry_has_required_fields(self) -> None:
        for p in list_prompts():
            assert "prompt_id"  in p
            assert "version"    in p
            assert "filename"   in p
            assert "model_tier" in p
