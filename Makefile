PYTHON ?= python3
PIP := $(PYTHON) -m pip

.PHONY: install install-all test test-unit test-integration lint typecheck clean

install:
	$(PIP) install -e .
	$(PIP) install pytest pytest-cov ruff mypy pytest-asyncio

install-all:
	$(PIP) install -e ".[all]"
	$(PIP) install pytest pytest-cov ruff mypy pytest-asyncio

test:
	pytest -m 'not integration' --cov=mcp_app_suite_shared --cov=mcp_app_playground --cov=mcp_app_scaffolder --cov=examples --cov-report=term-missing

test-unit: test

test-integration:
	pytest -m integration

lint:
	ruff check .

typecheck:
	mypy .

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache
	rm -rf .coverage coverage.xml htmlcov
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +