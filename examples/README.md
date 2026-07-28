# mcp-app-examples

**Demo MCP server** with three interactive MCP Apps: a Mermaid diagram viewer, a real-time system monitor, and an interactive data table.

> Part of the [mcp-app-suite](../README.md) monorepo. Use with [mcp-app-playground](../mcp_app_playground/README.md) for local preview.

## Quick Start

```bash
# From the root of the monorepo:
pip install -e '.[examples]'

# Start the server
python -m examples serve
# or
mcp-app-examples run
```

The server starts on `http://127.0.0.1:8002` using Streamable HTTP transport.

### View the Apps

The examples server is designed to be consumed by an **MCP Apps Host**. The easiest way to view the Apps is with the playground:

```bash
# In one terminal:
mcp-app-examples run

# In another terminal:
mcp-app-playground --server http://localhost:8002
```

Then open http://localhost:3691 in your browser.

## Sample Apps

### 1. Mermaid Diagram Viewer

- **Tool:** `render-mermaid`
- **Resource:** `ui://mermaid-viewer`
- **Features:**
  - Editable textarea for Mermaid diagram code
  - Theme selector (default, dark, forest, neutral)
  - Client-side rendering via Mermaid.js (CDN)
  - "Send to Chat" button that sends the diagram code via `sendMessage`
  - Background server-side rendering via `mmdc` (mermaid-cli) when available

```bash
# Trigger via MCP tools/call
curl -X POST http://localhost:8002/session \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"1","method":"tools/call","params":{"name":"render-mermaid","arguments":{"code":"graph TD\\nA-->B","theme":"dark"}}}'
```

### 2. Real-time System Monitor

- **Tools:** `system-monitor`, `get-snapshot`
- **Resource:** `ui://system-monitor`
- **Features:**
  - CPU usage gauge with animated bar
  - Memory usage gauge
  - Disk usage line chart (canvas)
  - Top processes table (PID, name, CPU %, memory %)
  - Configurable polling interval (1–60 seconds)
  - Live updates via `bridge.callServerTool("get-snapshot", ...)`

### 3. Interactive Data Table

- **Tools:** `query-table`, `export-csv`
- **Resource:** `ui://data-table`
- **Features:**
  - In-memory SQLite database with GitHub repo stats (12 repos)
  - Custom SQL query editor (SELECT/CTE only, limit 500 rows)
  - Sortable table columns
  - CSV export via `export-csv` tool
- **Sample data:**
  - `repo` — repository name
  - `language` — primary programming language
  - `stars`, `forks` — GitHub stats
  - `open_issues`, `contributors` — activity metrics
  - `updated_at` — last update date

## Registration: 5 Tools

| Tool | Description | Resource URI |
|---|---|---|
| `render-mermaid` | Render Mermaid diagrams and open the viewer app | `ui://mermaid-viewer` |
| `system-monitor` | Open the real-time system monitoring dashboard | `ui://system-monitor` |
| `get-snapshot` | Return current system metrics (for polling) | `ui://system-monitor` |
| `query-table` | Run a SQL query on sample GitHub stats | `ui://data-table` |
| `export-csv` | Export SQL query results as CSV | `ui://data-table` |

All tools include `_meta.ui.resourceUri` metadata so they are automatically discovered by any MCP Apps Host.

## Connecting via mcp-app-playground

```bash
# Start the examples server
mcp-app-examples run

# In a separate terminal, start the playground pointing at it
mcp-app-playground --server http://localhost:8002 --open
```

The playground will:
1. Connect to the examples server via Streamable HTTP
2. Call `tools/list` and discover all 5 tools with `_meta.ui.resourceUri`
3. Call `resources/read` for each `ui://` resource to fetch the HTML
4. Display a listing page with all 3 Apps
5. Render each App in a sandboxed iframe when clicked
6. Handle bridge messages (`callServerTool`, etc.) between the iframe and the server

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Server failed to start |

## Cross-Reference

- [mcp-app-playground](../mcp_app_playground/README.md) — preview these Apps without an AI host
- [mcp-app-scaffolder](../mcp_app_scaffolder/README.md) — generate your own MCP App projects