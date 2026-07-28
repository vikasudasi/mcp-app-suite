"""MCP Apps Host postMessage bridge.

Implements the @modelcontextprotocol/ext-apps postMessage protocol:
- callServerTool: calls a tool on the connected MCP server
- sendMessage: logs a message (simulates sending a message to the AI host)
- updateModelContext: updates the debug panel with model context
- openLink: opens a URL (in a new tab)
- downloadFile: triggers a file download
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("mcp_app_playground.bridge")


class McpAppsBridge:
    """Handles postMessage events from sandboxed MCP App iframes."""

    def __init__(self, call_tool_fn: Callable[..., Any] | None = None) -> None:
        self._call_tool_fn = call_tool_fn
        self._messages: list[dict[str, Any]] = []
        self._model_context_updates: list[dict[str, Any]] = []

    def set_call_tool_fn(self, fn: Callable[..., Any]) -> None:
        """Set the function to call MCP server tools."""
        self._call_tool_fn = fn

    async def handle_message(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle an incoming postMessage from an MCP App iframe.

        Returns a response dict to send back to the iframe.
        """
        event_type = data.get("type", "")
        event_id = data.get("id", "")
        payload = data.get("payload", {})

        if event_type == "callServerTool":
            return await self._handle_call_server_tool(event_id, payload)
        elif event_type == "sendMessage":
            return self._handle_send_message(event_id, payload)
        elif event_type == "updateModelContext":
            return self._handle_update_model_context(event_id, payload)
        elif event_type == "openLink":
            return self._handle_open_link(event_id, payload)
        elif event_type == "downloadFile":
            return self._handle_download_file(event_id, payload)
        else:
            logger.warning("Unknown postMessage event type: %s", event_type)
            return {
                "type": "response",
                "id": event_id,
                "payload": {"error": f"Unknown event type: {event_type}"},
            }

    async def _handle_call_server_tool(
        self, event_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle callServerTool: calls a tool on the MCP server."""
        tool_name = payload.get("toolName", "")
        arguments = payload.get("arguments", {})

        if not tool_name:
            return {
                "type": "response",
                "id": event_id,
                "payload": {"error": "Missing toolName"},
            }

        if not self._call_tool_fn:
            return {
                "type": "response",
                "id": event_id,
                "payload": {"error": "No MCP server connected"},
            }

        try:
            result = await self._call_tool_fn(tool_name, arguments)
            return {
                "type": "response",
                "id": event_id,
                "payload": {"result": result},
            }
        except Exception as e:
            logger.exception("Tool call failed: %s", tool_name)
            return {
                "type": "response",
                "id": event_id,
                "payload": {"error": str(e)},
            }

    def _handle_send_message(
        self, event_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle sendMessage: logs the message and returns success."""
        role = payload.get("role", "user")
        content = payload.get("content", "")

        message: dict[str, Any] = {"role": role, "content": content}
        self._messages.append(message)
        logger.info("App message (%s): %s", role, content[:200])

        return {
            "type": "response",
            "id": event_id,
            "payload": {"success": True, "messageCount": len(self._messages)},
        }

    def _handle_update_model_context(
        self, event_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle updateModelContext: records for debug panel."""
        context = payload.get("context", {})
        self._model_context_updates.append(context)
        logger.debug("Model context updated: %s", json.dumps(context, indent=2)[:500])

        return {
            "type": "response",
            "id": event_id,
            "payload": {"success": True},
        }

    def _handle_open_link(
        self, event_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle openLink: log the URL that would be opened."""
        url = payload.get("url", "")
        logger.info("App requested to open link: %s", url)
        return {
            "type": "response",
            "id": event_id,
            "payload": {"success": True, "url": url},
        }

    def _handle_download_file(
        self, event_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle downloadFile: log the file download request."""
        filename = payload.get("filename", "download")
        content_type = payload.get("contentType", "application/octet-stream")
        data = payload.get("data", "")

        logger.info(
            "App requested file download: %s (%s, %d bytes)",
            filename,
            content_type,
            len(data),
        )

        return {
            "type": "response",
            "id": event_id,
            "payload": {"success": True, "filename": filename},
        }

    def get_messages(self) -> list[dict[str, Any]]:
        """Get all messages sent by apps."""
        return list(self._messages)

    def get_model_context_updates(self) -> list[dict[str, Any]]:
        """Get all model context updates."""
        return list(self._model_context_updates)

    def get_bridge_client_js(self) -> str:
        """Return JavaScript that runs inside sandboxed iframes for postMessage bridge."""
        return (
            "(function(){'use strict';"
            "var p={};var i=0;"
            "window.__MCP_APPS_BRIDGE__={"
            "callServerTool:function(n,a){return s('callServerTool',"
            "{toolName:n,arguments:a||{}});},"
            "sendMessage:function(r,c){return s('sendMessage',{role:r,content:c});},"
            "updateModelContext:function(c){return s('updateModelContext',{context:c});},"
            "openLink:function(u){return s('openLink',{url:u});},"
            "downloadFile:function(fn,ct,d){return s('downloadFile',"
            "{filename:fn,contentType:ct,data:d});}"
            "};"
            "function s(t,pl){return new Promise(function(rj,re){"
            "var id='m_'+(++i);p[id]={resolve:rj,reject:re};"
            "window.parent.postMessage({type:t,id:id,payload:pl},'*');"
            "setTimeout(function(){if(p[id]){delete p[id];re(new Error('Timeout:'+t));}},30000);"
            "});}"
            "window.addEventListener('message',function(e){"
            "var d=e.data;if(d&&d.type==='response'&&d.id&&p[d.id]){"
            "var x=p[d.id];delete p[d.id];"
            "if(d.payload&&d.payload.error){x.reject(new Error(d.payload.error));}"
            "else{x.resolve(d.payload);}}});"
            "})();"
        )