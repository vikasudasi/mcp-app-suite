"""Shared utilities for MCP App suite packages."""

from .html_bundler import bundle_html, inline_css, inline_js
from .mcp_protocol import (
    JsonRpcError,
    parse_jsonrpc_message,
    request_message,
    response_error_message,
    response_success_message,
)

__all__ = [
    "JsonRpcError",
    "bundle_html",
    "inline_css",
    "inline_js",
    "parse_jsonrpc_message",
    "request_message",
    "response_error_message",
    "response_success_message",
]
