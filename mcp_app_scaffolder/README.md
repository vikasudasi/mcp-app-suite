# mcp-app-scaffolder

**MCP App project scaffolder** — generate new MCP App projects from ready-made templates in seconds.

> Part of the [mcp-app-suite](../README.md) monorepo.

## Problem Statement

Building a new MCP App requires setting up a project with the correct directory structure, server configuration, MCP SDK integration, UI boilerplate with postMessage bridge code, and Vite build tooling. `mcp-app-scaffolder` eliminates all of that setup by generating a complete, ready-to-run project from well-tested Jinja2 templates.

## Installation

```bash
# From the root of the monorepo:
pip install -e '.[scaffolder]'
```

This installs `mcp-app-scaffolder` and its dependencies (jinja2, typer).

## Usage

### Basic Python app (default)

```bash
# Creates a Python project with Vite-based UI structure
mcp-app-scaffolder my-app
```

### Python app with minimal single-file template

```bash
# --simple generates a single-file server with inline HTML (no Vite, no ui/ directory)
mcp-app-scaffolder my-app --simple
```

### Python app with demo counter tool

```bash
# --demo adds a working counter with increment/decrement and postMessage bridge code
mcp-app-scaffolder my-app --demo
```

### Combined: simple + demo

```bash
# Minimal single-file server with a working counter demo
mcp-app-scaffolder my-app --simple --demo
```

### Node/TypeScript app

```bash
# Full Node.js project with Vite-based UI
mcp-app-scaffolder my-app --template node
```

### Node simple + demo

```bash
mcp-app-scaffolder my-app --template node --simple --demo
```

## Flags Reference

| Flag | Default | Description |
|---|---|---|
| `--template python` | `python` | Template family: `python` or `node` |
| `--template node` | `python` | Generates a Node.js/TypeScript project instead of Python |
| `--simple` | `False` | Minimal single-file app — no `ui/` directory, no Vite. HTML is inlined in the server file |
| `--demo` | `False` | Adds a working counter demo tool with increment/decrement operations and postMessage bridge code |

## What Each Template Generates

### Python — Full (default)

```
my-app/
├── pyproject.toml      # Python project config with mcp dependency
├── README.md           # Project documentation
├── server.py           # MCP server with FastMCP, tool definition, resource serving
└── ui/
    ├── package.json    # Node.js dependencies (Vite, @modelcontextprotocol/ext-apps)
    ├── vite.config.js  # Vite build configuration
    ├── index.html      # Entry HTML
    └── src/
        ├── main.js     # App UI logic with postMessage bridge
        └── style.css   # Styling
```

### Python — Simple (`--simple`)

```
my-app/
├── pyproject.toml    # Python project config
├── README.md         # Project documentation
└── server.py         # Self-contained server with inline HTML
```

The server file includes the full App HTML as a Python string — no build step needed.

### Node/TypeScript — Full (`--template node`)

```
my-app/
├── package.json     # Node.js project config with mcp SDK dependency
├── README.md        # Project documentation
├── server.js        # MCP server with @modelcontextprotocol/sdk
└── ui/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.js
        └── style.css
```

### Node/TypeScript — Simple (`--template node --simple`)

```
my-app/
├── package.json    # Node.js project config
├── README.md       # Project documentation
└── server.js       # Self-contained server with inline HTML
```

## Demo Flag

When `--demo` is set, the generated project includes a working **counter tool** (`{app-name}-counter`) with:

- `increment` operation — increases the counter
- `decrement` operation — decreases the counter
- A full HTML UI with a counter display and buttons
- `postMessage` bridge code so the UI can call the server's counter tool
- Server-side state management

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success — project scaffolded |
| `1` | Target directory already exists (Refusing to overwrite) |
| `1` | Invalid template name |

## Cross-Reference

- Use [mcp-app-playground](../mcp_app_playground/README.md) to preview the generated App in a browser without an AI host
- The [examples server](../examples/README.md) provides 3 reference Apps that demonstrate the full MCP Apps pattern
