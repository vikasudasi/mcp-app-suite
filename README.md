# mcp-app-suite

[![CI](https://github.com/vikasudasi/mcp-app-suite/actions/workflows/ci.yml/badge.svg)](https://github.com/vikasudasi/mcp-app-suite/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Python monorepo for MCP Apps tooling: shared protocol utilities, a local playground CLI, a project scaffolder CLI, and runnable example apps.

## Table of Contents

- [Quick Start](#quick-start)
- [Repository Layout](#repository-layout)
- [Architecture](#architecture)
- [MCP Apps Protocol Background](#mcp-apps-protocol-background)
- [Tools Overview](#tools-overview)
- [Development](#development)
- [Links](#links)

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[all]'
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
├── tests/                   # Test suite (unit + integration)
├── pyproject.toml           # Root project + tooling configuration
├── Makefile                 # Local development commands
└── .github/workflows/ci.yml # CI checks
```

## Architecture

The suite is organized as a **layered monorepo** with four packages:

| Package | Role | Dependencies |
|---|---|---|
| `mcp_app_suite_shared` | **Foundation layer** — JSON-RPC 2.0 helpers, HTML/CSS/JS bundling utilities | None |
| `mcp_app_playground` | **Host layer** — connects to any MCP server, discovers App tools, renders HTML UIs in sandboxed iframes with a full postMessage bridge | `shared`, aiohttp, httpx, jinja2, typer, rich |
| `mcp_app_scaffolder` | **Template layer** — generates new MCP App projects from Jinja2 templates (Python or Node) | jinja2, typer |
| `examples` | **Reference layer** — demo MCP server with 3 interactive apps (Mermaid viewer, system monitor, data table) | mcp (FastMCP), typer |

**How they compose:**

```
┌─────────────────────────────────────────────────────┐
│                  examples/                           │
│   MCP server with 3 interactive HTML Apps            │
└──────────────┬──────────────────────────────┬────────┘
               │ serves ui:// resources        │ scaffold new projects
               ▼                              ▼
┌──────────────────────────┐   ┌──────────────────────────┐
│ mcp_app_playground/      │   │ mcp_app_scaffolder/      │
│ Preview MCP Apps in      │   │ Generate new MCP App     │
│ browser sandboxed iframe │   │ projects (Python/Node)   │
└──────────┬───────────────┘   └──────────┬───────────────┘
           │ both use shared protocol      │
           ▼                              ▼
┌─────────────────────────────────────────────────────────┐
│                 mcp_app_suite_shared/                    │
│        JSON-RPC helpers, HTML bundling utilities         │
└─────────────────────────────────────────────────────────┘
```

All packages are managed from the root `pyproject.toml` using optional dependency groups (`playground`, `scaffolder`, `examples`, `all`) so each tool can be installed independently.

## MCP Apps Protocol Background

[MCP Apps](https://modelcontextprotocol.io/extensions/apps) (shipped July 28, 2026) is an extension to the Model Context Protocol that allows MCP servers to render **interactive HTML user interfaces** inside AI conversations. The HTML is served via `resources/read` at `ui://` URIs, and tools advertise their associated UI through `_meta.ui.resourceUri` metadata.

Key protocol concepts:

- **Discovery** — Tools advertise HTML UIs via `_meta.ui.resourceUri` metadata in `tools/list` responses
- **Resource serving** — HTML content is served through `resources/read` at `ui://` URIs
- **Host role** — The AI host (or the playground) connects to the server, discovers App tools, fetches the HTML resources, renders them in sandboxed iframes
- **postMessage bridge** — A JavaScript bridge provides 5 host operations: `callServerTool`, `sendMessage`, `updateModelContext`, `openLink`, and `downloadFile`
- **Transport** — Uses Streamable HTTP (the 2026-07-28 RC spec) for stateless communication

The playground in this suite acts as a standalone **MCP Apps Host** — it performs the full lifecycle: discovery → resource fetch → initialize → interactive → teardown.

## Tools Overview

### mcp-app-playground

Local MCP App preview playground. Connects to any MCP server, discovers Apps, and renders them in a browser with sandboxed iframes and a full postMessage bridge.

```bash
pip install -e '.[playground]'
mcp-app-playground --server http://localhost:8002
# or
mcp-app-playground --stdio --command "python my_server.py"
```

See [mcp_app_playground/README.md](mcp_app_playground/README.md) for full documentation.

### mcp-app-scaffolder

Generates new MCP App projects from templates (Python or Node/TypeScript, simple or Vite-based, with optional demo counter tool).

```bash
pip install -e '.[scaffolder]'
mcp-app-scaffolder my-app --template python --demo
```

See [mcp_app_scaffolder/README.md](mcp_app_scaffolder/README.md) for full documentation.

### examples

Demo MCP server with three interactive Apps: a Mermaid diagram viewer, a real-time system monitor, and an interactive data table.

```bash
pip install -e '.[examples]'
mcp-app-examples run
```

See [examples/README.md](examples/README.md) for full documentation.

## Development

```bash
# Install base + dev tooling
make install

# Install everything
make install-all

# Run linter (Ruff)
make lint

# Run type checker (mypy)
make typecheck

# Run tests (unit only by default)
make test

# Run all tests including integration
pytest -m integration

# Clean up
make clean
```

**Code quality gates** (as enforced in CI):
1. `make lint` — Ruff checks (E, F, I, B, UP)
2. `make typecheck` — mypy with strict settings
3. `pytest -m 'not integration'` — unit tests with coverage
4. `pytest -m integration` — integration tests

## Links

- [@modelcontextprotocol/ext-apps SDK](https://www.npmjs.com/package/@modelcontextprotocol/ext-apps) — JavaScript Apps Extensions SDK
- [MCP 2026-07-28 Specification](https://spec.modelcontextprotocol.io/2026-07-28/) — Core MCP spec
- [MCP Apps Protocol](https://modelcontextprotocol.io/extensions/apps) — Apps protocol documentation
- [FastMCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) — Python MCP server SDK
- [GitHub Repository](https://github.com/vikasudasi/mcp-app-suite)
