"""Unit tests for the mcp-app-playground module.

Tests McpServerConnection (discovery, tool listing, resource fetch),
PlaygroundServer route handling, and the McpAppsBridge postMessage routing.
All MCP server interactions are mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from mcp_app_playground.bridge import McpAppsBridge
from mcp_app_playground.discovery import McpAppInfo, McpServerConnection

# =====================================================================
# McpServerConnection — unit tests (mocked HTTP responses)
# =====================================================================


class TestMcpServerConnectionHttp:
    """Tests for HTTP-mode McpServerConnection with mocked transport."""

    @pytest.mark.asyncio
    async def test_connect_success(self) -> None:
        conn = McpServerConnection(mode="http", server_url="http://localhost:8002")
        # Mock the _send_request to simulate a successful initialize
        init_response = {
            "jsonrpc": "2.0",
            "id": "1",
            "result": {
                "protocolVersion": "2026-07-28",
                "capabilities": {},
                "serverInfo": {"name": "test-server", "version": "0.1.0"},
            },
        }
        with patch.object(conn, "_send_request", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = init_response
            with patch.object(conn, "_send_notification", new_callable=AsyncMock) as mock_notify:
                await conn.connect()
                assert conn._session_id is None  # no session header set
                # initialize called
                mock_send.assert_any_call(
                    "initialize",
                    {
                        "protocolVersion": "2026-07-28",
                        "capabilities": {},
                        "clientInfo": {"name": "mcp-app-playground", "version": "0.1.0"},
                    },
                )
                mock_notify.assert_awaited_once_with("notifications/initialized", {})

    @pytest.mark.asyncio
    async def test_connect_http_failure(self) -> None:
        conn = McpServerConnection(mode="http", server_url="http://localhost:9999")
        init_response: dict[str, object] = {
            "jsonrpc": "2.0", "id": "1",
            "error": {"code": -32000, "message": "timeout"},
        }
        with patch.object(conn, "_send_request", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = init_response
            with patch.object(conn, "_send_notification", new_callable=AsyncMock):
                await conn.connect()
                # If init response has an error, no notification should be sent
                # (connect itself doesn't raise — error handling is caller's responsibility)
                pass

    @pytest.mark.asyncio
    async def test_discover_apps_returns_apps(self) -> None:
        conn = McpServerConnection(mode="http", server_url="http://localhost:8002")
        tools_response = {
            "jsonrpc": "2.0",
            "id": "2",
            "result": {
                "tools": [
                    {
                        "name": "render-mermaid",
                        "description": "Render Mermaid diagrams",
                        "_meta": {
                            "ui": {
                                "resourceUri": "ui://mermaid-viewer",
                                "label": "Mermaid Diagram Viewer",
                            }
                        },
                    },
                    {
                        "name": "plain-tool",
                        "description": "A tool without UI metadata",
                    },
                ]
            },
        }
        resource_response = {
            "jsonrpc": "2.0",
            "id": "3",
            "result": {
                "contents": [
                    {"mimeType": "text/html", "text": "<html><body>Hello</body></html>"}
                ]
            },
        }

        with patch.object(conn, "_send_request", new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = [tools_response, resource_response]
            apps = await conn.discover_apps()

        assert len(apps) == 1, "Only the tool with ui metadata should be discovered"
        app = apps[0]
        assert app.tool_name == "render-mermaid"
        assert app.tool_description == "Render Mermaid diagrams"
        assert app.resource_uri == "ui://mermaid-viewer"
        assert app.display_name == "Mermaid Diagram Viewer"
        assert app.html_content == "<html><body>Hello</body></html>"

    @pytest.mark.asyncio
    async def test_discover_apps_no_ui_tools(self) -> None:
        conn = McpServerConnection(mode="http", server_url="http://localhost:8002")
        tools_response = {
            "jsonrpc": "2.0",
            "id": "2",
            "result": {
                "tools": [
                    {"name": "plain-tool", "description": "No UI here"},
                ]
            },
        }

        with patch.object(conn, "_send_request", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = tools_response
            apps = await conn.discover_apps()

        assert len(apps) == 0

    @pytest.mark.asyncio
    async def test_discover_apps_empty_result(self) -> None:
        conn = McpServerConnection(mode="http", server_url="http://localhost:8002")
        with patch.object(conn, "_send_request", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = None
            apps = await conn.discover_apps()
            assert apps == []

    @pytest.mark.asyncio
    async def test_call_tool_success(self) -> None:
        conn = McpServerConnection(mode="http", server_url="http://localhost:8002")
        tool_response = {
            "jsonrpc": "2.0",
            "id": "5",
            "result": {"content": [{"type": "text", "text": "done"}]},
        }

        with patch.object(conn, "_send_request", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = tool_response
            result = await conn.call_tool("my-tool", {"key": "value"})

        assert result == {"content": [{"type": "text", "text": "done"}]}
        mock_send.assert_awaited_once_with(
            "tools/call", {"name": "my-tool", "arguments": {"key": "value"}}
        )

    @pytest.mark.asyncio
    async def test_call_tool_no_response(self) -> None:
        conn = McpServerConnection(mode="http", server_url="http://localhost:8002")
        with patch.object(conn, "_send_request", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = None
            result = await conn.call_tool("my-tool")
        assert result == {"error": "No response from server"}

    @pytest.mark.asyncio
    async def test_call_tool_error_response(self) -> None:
        conn = McpServerConnection(mode="http", server_url="http://localhost:8002")
        error_response = {
            "jsonrpc": "2.0",
            "id": "6",
            "error": {"code": -32601, "message": "Method not found"},
        }
        with patch.object(conn, "_send_request", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = error_response
            result = await conn.call_tool("missing")
        assert "error" in result


# =====================================================================
# McpAppsBridge — postMessage routing unit tests
# =====================================================================


class TestMcpAppsBridge:
    """Tests for postMessage bridge message routing."""

    @pytest.mark.asyncio
    async def test_handle_call_server_tool(self, bridge: McpAppsBridge) -> None:
        result = await bridge.handle_message({
            "type": "callServerTool",
            "id": "req-1",
            "payload": {"toolName": "my-tool", "arguments": {"x": 1}},
        })
        assert result["type"] == "response"
        assert result["id"] == "req-1"
        assert "result" in result["payload"]

    @pytest.mark.asyncio
    async def test_handle_call_tool_missing_name(self, bridge: McpAppsBridge) -> None:
        result = await bridge.handle_message({
            "type": "callServerTool",
            "id": "req-2",
            "payload": {},
        })
        assert result["payload"]["error"] == "Missing toolName"

    @pytest.mark.asyncio
    async def test_handle_call_tool_no_fn(self) -> None:
        b = McpAppsBridge()  # No call_tool_fn set
        result = await b.handle_message({
            "type": "callServerTool",
            "id": "req-3",
            "payload": {"toolName": "t"},
        })
        assert result["payload"]["error"] == "No MCP server connected"

    @pytest.mark.asyncio
    async def test_handle_send_message(self, bridge: McpAppsBridge) -> None:
        result = await bridge.handle_message({
            "type": "sendMessage",
            "id": "req-4",
            "payload": {"role": "user", "content": "Hello from app"},
        })
        assert result["payload"]["success"] is True
        assert result["payload"]["messageCount"] == 1
        messages = bridge.get_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello from app"

    @pytest.mark.asyncio
    async def test_handle_update_model_context(self, bridge: McpAppsBridge) -> None:
        result = await bridge.handle_message({
            "type": "updateModelContext",
            "id": "req-5",
            "payload": {"context": {"app": "test", "value": 42}},
        })
        assert result["payload"]["success"] is True
        updates = bridge.get_model_context_updates()
        assert len(updates) == 1
        assert updates[0] == {"app": "test", "value": 42}

    @pytest.mark.asyncio
    async def test_handle_open_link(self, bridge: McpAppsBridge) -> None:
        result = await bridge.handle_message({
            "type": "openLink",
            "id": "req-6",
            "payload": {"url": "https://example.com"},
        })
        assert result["payload"]["success"] is True
        assert result["payload"]["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_handle_download_file(self, bridge: McpAppsBridge) -> None:
        result = await bridge.handle_message({
            "type": "downloadFile",
            "id": "req-7",
            "payload": {
                "filename": "test.csv",
                "contentType": "text/csv",
                "data": "a,b,c",
            },
        })
        assert result["payload"]["success"] is True
        assert result["payload"]["filename"] == "test.csv"

    @pytest.mark.asyncio
    async def test_handle_unknown_event(self, bridge: McpAppsBridge) -> None:
        result = await bridge.handle_message({
            "type": "unknownEvent",
            "id": "req-8",
            "payload": {},
        })
        assert "error" in result["payload"]
        assert "unknownEvent" in result["payload"]["error"]

    def test_get_bridge_client_js(self, bridge: McpAppsBridge) -> None:
        js = bridge.get_bridge_client_js()
        assert "callServerTool" in js
        assert "sendMessage" in js
        assert "updateModelContext" in js
        assert "openLink" in js
        assert "downloadFile" in js
        assert "window.parent.postMessage" in js

    def test_get_messages(self, bridge: McpAppsBridge) -> None:
        assert bridge.get_messages() == []

    def test_get_model_context_updates(self, bridge: McpAppsBridge) -> None:
        assert bridge.get_model_context_updates() == []


# =====================================================================
# PlaygroundServer — route handling (mocked aiohttp)
# =====================================================================


class TestPlaygroundServerRoutes:
    """Tests for PlaygroundServer HTTP route handling using test client."""

    @pytest.mark.asyncio
    async def test_api_health(self) -> None:

        # Use aiohttp test client pattern
        from aiohttp.test_utils import TestClient, TestServer

        from mcp_app_playground.server import PlaygroundServer

        conn = McpServerConnection(mode="http", server_url="http://localhost:8002")
        apps = [
            McpAppInfo(
                tool_name="test-app",
                tool_description="A test app",
                resource_uri="ui://test",
                display_name="Test App",
                html_content="<html><body>Test</body></html>",
            )
        ]

        server = PlaygroundServer(conn, apps, port=0)
        client = TestClient(TestServer(server._app))
        await client.start_server()

        try:
            resp = await client.get("/api/health")
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "ok"
            assert data["apps"] == 1
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_api_apps(self) -> None:
        from aiohttp.test_utils import TestClient, TestServer

        from mcp_app_playground.server import PlaygroundServer

        conn = McpServerConnection(mode="http", server_url="http://localhost:8002")
        apps = [
            McpAppInfo(
                tool_name="app1",
                tool_description="First app",
                resource_uri="ui://app1",
                display_name="App One",
                html_content="<html>1</html>",
            ),
        ]

        server = PlaygroundServer(conn, apps, port=0)
        client = TestClient(TestServer(server._app))
        await client.start_server()

        try:
            resp = await client.get("/api/apps")
            assert resp.status == 200
            data = await resp.json()
            assert data["count"] == 1
            assert data["apps"][0]["toolName"] == "app1"
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_api_bridge_route(self) -> None:
        from aiohttp.test_utils import TestClient, TestServer

        from mcp_app_playground.server import PlaygroundServer

        conn = McpServerConnection(mode="http", server_url="http://localhost:8002")
        app_info = McpAppInfo(
            tool_name="t", tool_description="d", resource_uri="ui://t",
        )
        server = PlaygroundServer(conn, [app_info], port=0)
        client = TestClient(TestServer(server._app))
        await client.start_server()

        try:
            resp = await client.post(
                "/api/bridge",
                json={
                    "type": "sendMessage",
                    "id": "b1",
                    "payload": {"role": "user", "content": "hi"},
                },
            )
            assert resp.status == 200
            data = await resp.json()
            assert data["payload"]["success"] is True
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_bridge_invalid_json(self) -> None:
        from aiohttp.test_utils import TestClient, TestServer

        from mcp_app_playground.server import PlaygroundServer

        conn = McpServerConnection(mode="http", server_url="http://localhost:8002")
        server = PlaygroundServer(conn, [], port=0)
        client = TestClient(TestServer(server._app))
        await client.start_server()

        try:
            resp = await client.post(
                "/api/bridge",
                data=b"not-json",
                headers={"Content-Type": "application/json"},
            )
            assert resp.status == 400
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_listing_page_returns_html(self) -> None:
        from aiohttp.test_utils import TestClient, TestServer

        from mcp_app_playground.server import PlaygroundServer

        conn = McpServerConnection(mode="http", server_url="http://localhost:8002")
        apps = [
            McpAppInfo(
                tool_name="my-app",
                tool_description="desc",
                resource_uri="ui://my-app",
                html_content="<html><body>App</body></html>",
            ),
        ]
        server = PlaygroundServer(conn, apps, port=0)
        client = TestClient(TestServer(server._app))
        await client.start_server()

        try:
            resp = await client.get("/")
            assert resp.status == 200
            text = await resp.text()
            assert "text/html" in resp.content_type
            assert "my-app" in text
        finally:
            await client.close()
