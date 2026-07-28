"""MCP server connection and tool/app discovery."""

from __future__ import annotations

import asyncio
import base64
import json
import shlex
from dataclasses import dataclass, field
from typing import Any, cast

import httpx

from mcp_app_suite_shared.mcp_protocol import request_message

MCP_JSONRPC_VERSION = "2.0"


@dataclass
class McpAppInfo:
    """Metadata about a discovered MCP App."""

    tool_name: str
    tool_description: str
    resource_uri: str
    display_name: str = ""
    html_content: str | None = None


@dataclass
class McpServerConnection:
    """Manages a connection to an MCP server over stdio or Streamable HTTP."""

    mode: str  # "stdio" or "http"
    command: str | None = None
    server_url: str | None = None
    _process: asyncio.subprocess.Process | None = field(default=None, repr=False)
    _http_client: httpx.AsyncClient | None = field(default=None, repr=False)
    _session_id: str | None = None
    _request_id: int = 0
    _base_url: str = ""

    async def connect(self) -> None:
        """Establish the connection to the MCP server."""
        if self.mode == "stdio":
            if not self.command:
                raise ValueError("stdio mode requires a command")
            args = shlex.split(self.command)
            self._process = await asyncio.create_subprocess_exec(
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            init_response = await self._send_request(
                "initialize",
                {
                    "protocolVersion": "2026-07-28",
                    "capabilities": {},
                    "clientInfo": {"name": "mcp-app-playground", "version": "0.1.0"},
                },
            )
            if init_response and "result" in init_response:
                await self._send_notification("notifications/initialized", {})
        else:
            if not self.server_url:
                raise ValueError("HTTP mode requires a server_url")
            self._http_client = httpx.AsyncClient(timeout=30.0)
            self._base_url = self.server_url.rstrip("/")
            init_response = await self._send_request(
                "initialize",
                {
                    "protocolVersion": "2026-07-28",
                    "capabilities": {},
                    "clientInfo": {"name": "mcp-app-playground", "version": "0.1.0"},
                },
            )
            if init_response and "result" in init_response:
                await self._send_notification("notifications/initialized", {})

    async def _read_stdio_line(self) -> dict[str, Any] | None:
        """Read one JSON-RPC line from the stdio subprocess stdout."""
        if not self._process or not self._process.stdout:
            return None
        line = await self._process.stdout.readline()
        if not line:
            return None
        raw = line.decode("utf-8").strip()
        if not raw:
            return None
        return cast("dict[str, Any]", json.loads(raw))

    async def _send_request(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Send a JSON-RPC request and wait for the response."""
        self._request_id += 1
        req_id = str(self._request_id)
        message = request_message(method, params, request_id=req_id)

        if self.mode == "stdio":
            if not self._process or not self._process.stdin:
                raise RuntimeError("stdio process not connected")
            line = json.dumps(message) + "\n"
            self._process.stdin.write(line.encode("utf-8"))
            await self._process.stdin.drain()
            response = await self._read_stdio_line()
            while response is not None and response.get("id") != req_id:
                response = await self._read_stdio_line()
            return response
        else:
            if not self._http_client:
                raise RuntimeError("HTTP client not initialized")
            headers: dict[str, str] = {"Content-Type": "application/json"}
            if self._session_id:
                headers["Mcp-Session-Id"] = self._session_id
            url = f"{self._base_url}/session"

            try:
                resp = await self._http_client.post(
                    url, json=message, headers=headers
                )
                resp.raise_for_status()
                data: dict[str, Any] = cast(
                    "dict[str, Any]", resp.json()
                )

                if "Mcp-Session-Id" in resp.headers:
                    self._session_id = resp.headers["Mcp-Session-Id"]

                return data
            except httpx.HTTPError as e:
                raise RuntimeError(f"HTTP request failed: {e}") from e

    async def _send_notification(
        self, method: str, params: dict[str, Any] | None = None
    ) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        from mcp_app_suite_shared.mcp_protocol import notification_message

        message = notification_message(method, params)
        if self.mode == "stdio":
            if not self._process or not self._process.stdin:
                raise RuntimeError("stdio process not connected")
            line = json.dumps(message) + "\n"
            self._process.stdin.write(line.encode("utf-8"))
            await self._process.stdin.drain()
        else:
            if not self._http_client:
                return
            headers: dict[str, str] = {"Content-Type": "application/json"}
            if self._session_id:
                headers["Mcp-Session-Id"] = self._session_id
            url = f"{self._base_url}/session"
            try:
                await self._http_client.post(url, json=message, headers=headers)
            except httpx.HTTPError:
                pass

    async def discover_apps(self) -> list[McpAppInfo]:
        """Discover MCP Apps by listing tools and filtering for those with ui resource URIs."""
        response = await self._send_request("tools/list")
        if not response or "result" not in response:
            return []

        tools: list[dict[str, Any]] = response["result"].get("tools", [])
        apps: list[McpAppInfo] = []

        for tool in tools:
            resource_uri: str = ""
            meta: Any = tool.get("_meta", {}) or {}
            if isinstance(meta, dict):
                meta_ui: Any = meta.get("ui", {})
                if isinstance(meta_ui, dict):
                    resource_uri = str(meta_ui.get("resourceUri", "") or "")

            if resource_uri:
                html_content = await self._fetch_resource(resource_uri)
                apps.append(
                    McpAppInfo(
                        tool_name=str(tool["name"]),
                        tool_description=str(tool.get("description", "")),
                        resource_uri=resource_uri,
                        display_name=str(
                            cast("dict[str, Any]", meta.get("ui", {})).get("label", tool["name"])
                        ),
                        html_content=html_content,
                    )
                )

        return apps

    async def _fetch_resource(self, uri: str) -> str | None:
        """Fetch HTML content from a resource URI via resources/read."""
        try:
            response = await self._send_request("resources/read", {"uri": uri})
            if response and "result" in response:
                contents: list[Any] = response["result"].get("contents", [])
                for content in contents:
                    mime_type = str(content.get("mimeType", ""))
                    if mime_type.startswith("text/html") or uri.endswith(".html"):
                        text = content.get("text", "")
                        if text:
                            return str(text)
                        blob = content.get("blob", "")
                        if blob:
                            return base64.b64decode(str(blob)).decode("utf-8")
                for content in contents:
                    text = content.get("text", "")
                    if text:
                        return str(text)
            return None
        except Exception:
            return None

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Call a tool on the connected MCP server."""
        response = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments or {},
        })
        if response and "result" in response:
            result: dict[str, Any] = cast("dict[str, Any]", response["result"])
            return result
        if response and "error" in response:
            return {"error": response["error"]}
        return {"error": "No response from server"}

    async def close(self) -> None:
        """Close the connection."""
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except (TimeoutError, ProcessLookupError):
                try:
                    self._process.kill()
                except ProcessLookupError:
                    pass
            self._process = None
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None