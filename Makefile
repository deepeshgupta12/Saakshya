# Saakshya local-first orchestration (SPEC §12). Plain targets; Celery/Redis deferred.
.PHONY: install pipeline test lint typecheck clean

VENV ?= .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

install:
	python3 -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt

pipeline:           ## M0: ingest -> (compute -> scan in later milestones)
	$(PY) scripts/run_pipeline.py

test:
	$(VENV)/bin/pytest

lint:
	$(VENV)/bin/ruff check app tests

typecheck:
	$(VENV)/bin/mypy app

clean:
	rm -f data/*.duckdb data/*.duckdb.wal
