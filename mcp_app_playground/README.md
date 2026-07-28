# mcp-app-playground

**Local MCP App preview playground** — connect to any MCP server, discover Apps, and render their HTML UIs in sandboxed iframes with a full postMessage bridge.

> Part of the [mcp-app-suite](../README.md) monorepo.

## Problem Statement

MCP Apps (interactive HTML UIs served by MCP servers) normally require an AI host to be viewed. During development, you need to preview and debug your App HTML without an AI host. `mcp-app-playground` fills this gap by acting as a standalone **MCP Apps Host** — it connects to any MCP server, discovers tools with `_meta.ui.resourceUri`, fetches their HTML resources, and renders them in a browser with sandboxed iframes.

## Installation

```bash
# From the root of the monorepo:
pip install -e '.[playground]'
```

This installs `mcp-app-playground` and its dependencies (aiohttp, httpx, jinja2, typer, rich).

## Usage

### Connect via Streamable HTTP (recommended)

```bash
mcp-app-playground --server http://localhost:8002
```

### Connect via stdio

```bash
mcp-app-playground --stdio --command "python my_server.py"
# or with uvx
mcp-app-playground --stdio --command "uvx mcp-server"
```

### With all options

```bash
mcp-app-playground --server http://localhost:8002 \
  --port 8080 \
  --watch \
  --debug \
  --open \
  --verbose
```

Once running, open http://localhost:3691 (or your custom port) in a browser.

## Options Reference

| Flag | Short | Default | Description |
|---|---|---|---|
| `--server URL` | `-s` | — | Streamable HTTP server URL (e.g. `http://localhost:8002`) |
| `--stdio` | — | `False` | Connect via stdio transport (requires `--command`) |
| `--command CMD` | `-c` | — | Command to start the MCP server (required with `--stdio`) |
| `--port PORT` | `-p` | `3691` | Port for the playground HTTP server (1024–65535) |
| `--watch` | `-w` | `False` | Enable hot-reload for app changes |
| `--debug` | `-d` | `False` | Show debug sidebar with JSON-RPC log |
| `--open` | `-o` | `False` | Auto-open browser when ready |
| `--verbose` | `-v` | `False` | Enable verbose logging |

> **Note:** `--server` and `--stdio` are mutually exclusive. One is required.

## Architecture Deep-Dive

The playground implements the full MCP Apps Host protocol in four stages:

### 1. Discovery

On startup, the playground sends `tools/list` to the connected MCP server. It scans each tool's `_meta.ui.resourceUri` metadata — tools with a non-empty URI are identified as MCP Apps. For each discovered App, the URI and display metadata are recorded.

```
mcp-app-playground  ── tools/list ──▶  MCP Server
                   ◀── tools[] ──────
                   ── filters by _meta.ui.resourceUri
```

### 2. Resource Fetch

For each discovered App, the playground sends `resources/read` with the App's `ui://` URI. The response HTML is cached in memory.

```
mcp-app-playground  ── resources/read {"uri": "ui://mermaid-viewer"} ──▶  MCP Server
                   ◀── contents[0].text: "<html>..." ──────────────────
```

### 3. Iframe Render

The playground starts a local HTTP server (aiohttp, port 3691) with routes:

| Route | Description |
|---|---|
| `GET /` | App listing page with cards for each discovered App |
| `GET /mcp-apps/{tool_name}/` | Individual App rendered in a sandboxed iframe |
| `POST /api/bridge` | postMessage bridge endpoint |
| `GET /api/apps` | JSON list of discovered apps |
| `GET /api/debug` | JSON RPC log and bridge messages (debug mode) |
| `GET /api/health` | Health check |

Each App page:
- Creates an `<iframe>` with `srcdoc` containing the App HTML
- Applies `sandbox="allow-scripts allow-same-origin allow-forms allow-popups"`
- Injects the bridge proxy JavaScript
- The proxy relays `postMessage` events between the iframe and the server

### 4. postMessage Bridge

The bridge supports 5 operations defined by the `@modelcontextprotocol/ext-apps` SDK:

| Message Type | Description |
|---|---|
| `callServerTool` | Calls a tool on the connected MCP server and returns the result |
| `sendMessage` | Simulates sending a message to the AI host (logged in debug) |
| `updateModelContext` | Records context updates for the debug panel |
| `openLink` | Opens a URL (logs the request in playground mode) |
| `downloadFile` | Triggers a file download (logs the request) |

The bridge JavaScript injected into each page:
1. Defines `window.__MCP_APPS_BRIDGE__` with all 5 methods
2. Intercepts `postMessage` from the iframe and relays it to the server via `POST /api/bridge`
3. Returns responses back to the iframe via `postMessage`
4. Has a 30-second timeout on all bridge calls

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Missing required flags (`--server` or `--command`) |
| `1` | Connection failure / discovery failure |
| `1` | Runtime error during server startup |

## Cross-Reference

- Use [mcp-app-scaffolder](../mcp_app_scaffolder/README.md) to generate new MCP App projects to preview here
- The [examples](../examples/README.md) server is a quick way to test the playground with real Apps
