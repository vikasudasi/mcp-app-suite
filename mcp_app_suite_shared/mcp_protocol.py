"""Minimal JSON-RPC 2.0 helpers used by MCP-facing tools."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

JSONRPC_VERSION = "2.0"


@dataclass(slots=True)
class JsonRpcError(Exception):
    """JSON-RPC error payload model."""

    code: int
    message: str
    data: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data is not None:
            payload["data"] = self.data
        return payload


def request_message(
    method: str,
    params: dict[str, Any] | list[Any] | None = None,
    request_id: str | int | None = None,
) -> dict[str, Any]:
    """Build a JSON-RPC request object."""
    message: dict[str, Any] = {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id if request_id is not None else str(uuid4()),
        "method": method,
    }
    if params is not None:
        message["params"] = params
    return message


def notification_message(
    method: str,
    params: dict[str, Any] | list[Any] | None = None,
) -> dict[str, Any]:
    """Build a JSON-RPC notification object."""
    message: dict[str, Any] = {"jsonrpc": JSONRPC_VERSION, "method": method}
    if params is not None:
        message["params"] = params
    return message


def response_success_message(request_id: str | int, result: Any) -> dict[str, Any]:
    """Build a JSON-RPC success response object."""
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}


def response_error_message(
    request_id: str | int | None,
    code: int,
    message: str,
    data: Any | None = None,
) -> dict[str, Any]:
    """Build a JSON-RPC error response object."""
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "error": JsonRpcError(code=code, message=message, data=data).to_dict(),
    }


def parse_jsonrpc_message(raw_message: str | bytes | dict[str, Any]) -> dict[str, Any]:
    """Parse and validate a JSON-RPC message from text, bytes, or dictionary."""
    if isinstance(raw_message, bytes):
        raw_message = raw_message.decode("utf-8")

    if isinstance(raw_message, str):
        parsed: Any = json.loads(raw_message)
    elif isinstance(raw_message, dict):
        parsed = raw_message
    else:
        raise TypeError("raw_message must be str, bytes, or dict")

    if not isinstance(parsed, dict):
        raise ValueError("JSON-RPC message must decode to an object")

    if parsed.get("jsonrpc") != JSONRPC_VERSION:
        raise ValueError("Invalid or missing jsonrpc version")

    has_method = "method" in parsed
    has_result = "result" in parsed
    has_error = "error" in parsed

    if has_method and ("id" not in parsed or parsed["id"] is None):
        raise ValueError("Requests must include a non-null id")
    if has_result and has_error:
        raise ValueError("Response cannot contain both result and error")
    if not has_method and not has_result and not has_error:
        raise ValueError("Message must be request/notification or response")

    return parsed
