"""Shared test fixtures for the mcp-app-suite test suite."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio

from mcp_app_playground.bridge import McpAppsBridge

# ---------------------------------------------------------------------------
# Fixtures: temp project / working directory
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_project_dir() -> Generator[Path, None, None]:
    """Yield a temporary directory suitable for scaffolding a project."""
    with tempfile.TemporaryDirectory(prefix="mcp-test-") as tmp:
        cwd = Path.cwd()
        os.chdir(tmp)
        try:
            yield Path(tmp)
        finally:
            os.chdir(cwd)


# ---------------------------------------------------------------------------
# Fixtures: async HTTP client
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an httpx AsyncClient for connecting to test MCP servers."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        yield client


# ---------------------------------------------------------------------------
# Helpers: start / stop a subprocess-based MCP server
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def server_process_manager() -> AsyncGenerator[dict[str, Any], None]:
    """Manage lifecycle of a child MCP server process.

    Yields a dict with helpers:
        start(module_path, port) -- starts a server and returns its info
        stop() -- terminates the server
    """
    running: dict[str, Any] = {}

    async def _start(server_script: str, port: int = 8002) -> dict[str, Any]:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            server_script,
            "--port",
            str(port),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        running["process"] = proc
        running["port"] = port
        running["url"] = f"http://127.0.0.1:{port}"

        # Wait for the server to be ready (up to 15 seconds)
        for _attempt in range(30):
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    resp = await client.get(f"http://127.0.0.1:{port}/health")
                    if resp.status_code == 200:
                        return running
            except (httpx.ConnectError, httpx.TimeoutException):
                await asyncio.sleep(0.5)
        raise RuntimeError(
            f"Server on port {port} did not start within 15 seconds"
        )

    async def _stop() -> None:
        proc = running.get("process")
        if proc and proc.returncode is None:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except (TimeoutError, ProcessLookupError):
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
        running.clear()

    manager: dict[str, Any] = {"start": _start, "stop": _stop}
    try:
        yield manager
    finally:
        await _stop()


# ---------------------------------------------------------------------------
# Fixtures: mock MCP server (in-process using httpx mock / aiohttp)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def mock_mcp_server() -> AsyncGenerator[dict[str, Any], None]:
    """Yield a dict of mock MCP server responses for unit tests.

    Returns:
        respond_to: callable to register a response for a method
        responses: dict of registered responses
    """
    responses: dict[str, list[dict[str, Any]]] = {}

    def respond_to(method: str, response: dict[str, Any]) -> None:
        responses.setdefault(method, []).append(response)

    mock: dict[str, Any] = {
        "respond_to": respond_to,
        "responses": responses,
    }
    yield mock


# ---------------------------------------------------------------------------
# Fixtures: McpAppsBridge
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def bridge() -> McpAppsBridge:
    """Provide an McpAppsBridge instance for unit testing postMessage routing."""
    b = McpAppsBridge()

    async def fake_call_tool(name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": f"called {name}"}]}

    b.set_call_tool_fn(fake_call_tool)
    return b
