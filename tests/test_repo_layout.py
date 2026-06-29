"""Repo layout smoke test: every required package/module imports cleanly (docs/steps/01)."""

from __future__ import annotations

import importlib

import pytest

MODULES = [
    "app",
    "app.config",
    "app.storage.duckdb",
    "app.storage.repository",
    "app.data.base",
    "app.data.yfinance_source",
    "app.data.universe",
    "app.data.normalize",
    "app.pipeline.ingest",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_imports(module: str) -> None:
    assert importlib.import_module(module) is not None


def test_app_package_imports() -> None:
    import app

    assert app.__doc__
