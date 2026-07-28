# mcp-app-suite

[![CI](https://github.com/vikasudasi/mcp-app-suite/actions/workflows/ci.yml/badge.svg)](https://github.com/vikasudasi/mcp-app-suite/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Python monorepo for MCP Apps tooling: shared protocol utilities, a local playground CLI, a project scaffolder CLI, and runnable examples.

## Table of Contents

- [Quick Start](#quick-start)
- [Repository Layout](#repository-layout)
- [Architecture](#architecture)
- [Development](#development)

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
make install-all
```

Run checks:

```bash
make lint
make typecheck
make test
```

## Repository Layout

```text
mcp-app-suite/
├── mcp_app_suite_shared/    # Shared MCP protocol + HTML bundling utilities
├── mcp_app_playground/      # CLI: local MCP App playground host
├── mcp_app_scaffolder/      # CLI: MCP App project scaffolder
├── examples/                # CLI: example MCP Apps/demo server entrypoint
├── tests/                   # Test suite
├── pyproject.toml           # Root project + tooling configuration
├── Makefile                 # Local development commands
└── .github/workflows/ci.yml # CI checks
```

## Architecture

- `mcp_app_suite_shared`: foundation layer for JSON-RPC/MCP message handling and HTML asset bundling.
- `mcp_app_playground`: host-oriented command surface for inspecting and rendering MCP Apps.
- `mcp_app_scaffolder`: template-oriented command surface for generating new app projects.
- `examples`: reference apps and demonstrations that validate end-to-end behavior.

All packages are managed from the root `pyproject.toml` using optional dependency groups (`playground`, `scaffolder`, `examples`, `all`) so each tool can be installed independently.

## Development

- `make install`: install base package with dev tooling
- `make install-all`: install all optional tool dependencies with dev tooling
- `make lint`: run Ruff checks
- `make typecheck`: run mypy
- `make test`: run pytest with coverage output
- `make clean`: remove local caches and build artifacts
