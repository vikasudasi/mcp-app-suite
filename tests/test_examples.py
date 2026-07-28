"""Integration tests for the examples demo MCP server.

Starts the demo server in a subprocess, connects via httpx, verifies
the MCP initialize sequence, lists tools with correct schemas, and
verifies resources/read returns HTML for each ui:// resource.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPECTED_TOOLS = {
    "render-mermaid",
    "system-monitor",
    "get-snapshot",
    "query-table",
    "export-csv",
}

EXPECTED_UI_RESOURCES = {
    "ui://mermaid-viewer",
    "ui://system-monitor",
    "ui://data-table",
}

EXPECTED_RESOURCE_LABELS = {
    "ui://mermaid-viewer": "Mermaid",
    "ui://system-monitor": "System Monitor",
    "ui://data-table": "Data Table",
}

MERMAID_RESOURCE_URI = "ui://mermaid-viewer"
SYSTEM_MONITOR_RESOURCE_URI = "ui://system-monitor"
DATA_TABLE_RESOURCE_URI = "ui://data-table"

_TOOL_META_URIS: dict[str, str] = {
    "render-mermaid": MERMAID_RESOURCE_URI,
    "system-monitor": SYSTEM_MONITOR_RESOURCE_URI,
    "get-snapshot": SYSTEM_MONITOR_RESOURCE_URI,
    "query-table": DATA_TABLE_RESOURCE_URI,
    "export-csv": DATA_TABLE_RESOURCE_URI,
}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_initialize_sequence(
    http_client: httpx.AsyncClient, server_process_manager: dict[str, Any],
) -> None:
    """Start the examples server and verify the MCP initialize handshake."""
    info = await server_process_manager["start"]("examples", port=8002)
    url = info["url"]

    # Send initialize request
    init_payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "initialize",
        "params": {
            "protocolVersion": "2026-07-28",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "0.1.0"},
        },
    }
    resp = await http_client.post(f"{url}/session", json=init_payload)
    assert resp.status_code == 200, f"Initialize failed: {resp.text}"
    data = resp.json()
    assert data.get("jsonrpc") == "2.0"
    assert "result" in data, f"No result in initialize response: {data}"
    result = data["result"]
    assert result.get("protocolVersion") == "2026-07-28"
    assert "serverInfo" in result

    # Send initialized notification
    notif_payload = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {},
    }
    await http_client.post(f"{url}/session", json=notif_payload)

    await server_process_manager["stop"]()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_tools_returns_all_five(
    http_client: httpx.AsyncClient, server_process_manager: dict[str, Any]
) -> None:
    """Verify tools/list returns all 5 tools with correct schemas and UI metadata."""
    info = await server_process_manager["start"]("examples", port=8003)
    url = info["url"]

    # Initialize first
    init_payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "initialize",
        "params": {
            "protocolVersion": "2026-07-28",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "0.1.0"},
        },
    }
    await http_client.post(f"{url}/session", json=init_payload)
    notif_payload = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {},
    }
    await http_client.post(f"{url}/session", json=notif_payload)

    # List tools
    list_payload = {
        "jsonrpc": "2.0",
        "id": "2",
        "method": "tools/list",
    }
    resp = await http_client.post(f"{url}/session", json=list_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data, f"No result: {data}"
    tools: list[dict[str, Any]] = data["result"].get("tools", [])
    tool_names = {t["name"] for t in tools}
    assert tool_names == EXPECTED_TOOLS, (
        f"Tools mismatch. Expected {EXPECTED_TOOLS}, got {tool_names}"
    )

    # Check each tool has _meta.ui.resourceUri with correct schema
    for tool in tools:
        name = tool["name"]
        assert "inputSchema" in tool, f"{name} missing inputSchema"
        meta = tool.get("_meta", {})
        ui = meta.get("ui", {})
        assert "resourceUri" in ui, f"{name} missing _meta.ui.resourceUri"
        assert ui["resourceUri"] == _TOOL_META_URIS[name], (
            f"{name}: expected resourceUri {_TOOL_META_URIS[name]}, got {ui['resourceUri']}"
        )

    await server_process_manager["stop"]()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_resources_read_returns_html(
    http_client: httpx.AsyncClient, server_process_manager: dict[str, Any]
) -> None:
    """Verify resources/read returns HTML content for each ui:// resource."""
    info = await server_process_manager["start"]("examples", port=8004)
    url = info["url"]

    # Initialize first
    init_payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "initialize",
        "params": {
            "protocolVersion": "2026-07-28",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "0.1.0"},
        },
    }
    await http_client.post(f"{url}/session", json=init_payload)
    notif_payload = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {},
    }
    await http_client.post(f"{url}/session", json=notif_payload)

    for resource_uri in EXPECTED_UI_RESOURCES:
        read_payload = {
            "jsonrpc": "2.0",
            "id": f"read-{hash(resource_uri)}",
            "method": "resources/read",
            "params": {"uri": resource_uri},
        }
        resp = await http_client.post(f"{url}/session", json=read_payload)
        assert resp.status_code == 200, f"resources/read failed for {resource_uri}: {resp.text}"
        data = resp.json()
        assert "result" in data, f"No result for {resource_uri}: {data}"
        contents = data["result"].get("contents", [])
        assert len(contents) > 0, f"No contents for {resource_uri}"

        # At least one content entry should have text/html
        html_text = None
        for content in contents:
            mime = content.get("mimeType", "")
            text = content.get("text", "")
            if mime.startswith("text/html") or resource_uri.endswith(".html"):
                html_text = text
                break

        if html_text is None and contents:
            # Fallback: use first content with text
            html_text = contents[0].get("text", "")

        assert html_text, f"No HTML text found for {resource_uri}"
        assert "<!doctype html>" in html_text.lower() or "<html" in html_text.lower(), (
            f"Content for {resource_uri} does not appear to be HTML"
        )

    await server_process_manager["stop"]()
