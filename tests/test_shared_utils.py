from pathlib import Path

from mcp_app_suite_shared.html_bundler import bundle_html, inline_css, inline_js
from mcp_app_suite_shared.mcp_protocol import (
    parse_jsonrpc_message,
    request_message,
    response_error_message,
    response_success_message,
)


def test_request_and_response_messages() -> None:
    request = request_message(method="tools/list", params={"cursor": "abc"}, request_id="req-1")
    assert request["jsonrpc"] == "2.0"
    assert request["method"] == "tools/list"
    assert request["id"] == "req-1"

    success = response_success_message("req-1", {"tools": []})
    assert success == {"jsonrpc": "2.0", "id": "req-1", "result": {"tools": []}}

    error = response_error_message("req-1", -32601, "Method not found")
    assert error["error"]["code"] == -32601
    assert error["error"]["message"] == "Method not found"


def test_parse_jsonrpc_message() -> None:
    raw = '{"jsonrpc":"2.0","id":"1","method":"ping"}'
    parsed = parse_jsonrpc_message(raw)
    assert parsed["method"] == "ping"
    assert parsed["id"] == "1"


def test_html_inlining_and_bundling(tmp_path: Path) -> None:
    base_html = "<html><head></head><body><h1>Hi</h1></body></html>"
    with_css = inline_css(base_html, "h1 { color: red; }")
    assert "<style>" in with_css

    with_js = inline_js(base_html, "console.log('hello')")
    assert "<script>" in with_js

    css_file = tmp_path / "app.css"
    js_file = tmp_path / "app.js"
    css_file.write_text("body { margin: 0; }", encoding="utf-8")
    js_file.write_text("window.loaded = true;", encoding="utf-8")

    bundled = bundle_html(base_html, css_files=[css_file], js_files=[js_file])
    assert "margin: 0" in bundled
    assert "window.loaded = true" in bundled
