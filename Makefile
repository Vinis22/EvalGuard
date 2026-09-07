.PHONY: install test lint run clean

VENV ?= .venv
PYTHON ?= python

install:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/Scripts/pip install -e ".[dev]" || $(VENV)/bin/pip install -e ".[dev]"

test:
	pytest -v

run:
	evalguard run examples/config.yaml

clean:
	rm -rf reports .pytest_cache **/__pycache__ *.egg-info
