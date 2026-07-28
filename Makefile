PYTHON ?= python3
PIP := $(PYTHON) -m pip

.PHONY: install install-all test lint clean typecheck

install:
	$(PIP) install -e .
	$(PIP) install pytest pytest-cov ruff mypy

install-all:
	$(PIP) install -e ".[all]"
	$(PIP) install pytest pytest-cov ruff mypy

test:
	pytest --cov=mcp_app_suite_shared --cov=mcp_app_playground --cov=mcp_app_scaffolder --cov=examples --cov-report=term-missing

lint:
	ruff check .

typecheck:
	mypy .

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache
	rm -rf .coverage coverage.xml htmlcov
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
