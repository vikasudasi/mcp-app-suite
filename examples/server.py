"""MCP examples demo server with three interactive UI apps."""

from __future__ import annotations

import csv
import io
import json
import shutil
import sqlite3
import subprocess
import tempfile
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import psutil
from jinja2 import Template
from mcp.server.fastmcp import FastMCP

from .html_templates import (
    DATA_TABLE_TEMPLATE,
    MERMAID_VIEWER_TEMPLATE,
    SYSTEM_MONITOR_TEMPLATE,
)

mcp = FastMCP("mcp-app-examples")

MERMAID_RESOURCE_URI = "ui://mermaid-viewer"
SYSTEM_MONITOR_RESOURCE_URI = "ui://system-monitor"
DATA_TABLE_RESOURCE_URI = "ui://data-table"

MERMAID_THEMES = ("default", "dark", "forest", "neutral")
MONITOR_METRICS = ("cpu", "memory", "disk", "processes")

APP_UI_META = {
    "render-mermaid": {
        "ui": {
            "resourceUri": MERMAID_RESOURCE_URI,
            "label": "Mermaid Diagram Viewer",
        }
    },
    "system-monitor": {
        "ui": {
            "resourceUri": SYSTEM_MONITOR_RESOURCE_URI,
            "label": "Real-time System Monitor",
        }
    },
    "get-snapshot": {
        "ui": {
            "resourceUri": SYSTEM_MONITOR_RESOURCE_URI,
            "label": "Real-time System Monitor",
        }
    },
    "query-table": {
        "ui": {
            "resourceUri": DATA_TABLE_RESOURCE_URI,
            "label": "Interactive Data Table",
        }
    },
    "export-csv": {
        "ui": {
            "resourceUri": DATA_TABLE_RESOURCE_URI,
            "label": "Interactive Data Table",
        }
    },
}


def _render_template(template: str, **context: Any) -> str:
    return cast(str, Template(template).render(**context))


def _render_mermaid_svg(code: str, theme: str) -> str:
    """Render Mermaid to SVG via mermaid-cli if available."""
    mmdc = shutil.which("mmdc")
    if not mmdc:
        return ""

    with tempfile.TemporaryDirectory(prefix="mcp-mermaid-") as tmp:
        temp_dir = Path(tmp)
        input_file = temp_dir / "diagram.mmd"
        output_file = temp_dir / "diagram.svg"
        input_file.write_text(code, encoding="utf-8")
        cmd = [
            mmdc,
            "-i",
            str(input_file),
            "-o",
            str(output_file),
            "-t",
            theme,
            "--backgroundColor",
            "transparent",
        ]
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return ""
        if not output_file.exists():
            return ""
        return output_file.read_text(encoding="utf-8")


def _collect_processes(top_n: int = 8) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for proc in psutil.process_iter(attrs=["pid", "name", "cpu_percent", "memory_percent"]):
        info = proc.info
        rows.append(
            {
                "pid": int(info.get("pid", 0)),
                "name": str(info.get("name", "unknown")),
                "cpu_percent": float(info.get("cpu_percent", 0.0) or 0.0),
                "memory_percent": float(info.get("memory_percent", 0.0) or 0.0),
            }
        )
    rows.sort(key=lambda item: (item["cpu_percent"], item["memory_percent"]), reverse=True)
    return rows[:top_n]


def _normalize_metrics(metrics: Iterable[str] | None) -> list[str]:
    if not metrics:
        return list(MONITOR_METRICS)
    normalized = []
    for metric in metrics:
        metric_key = metric.strip().lower()
        if metric_key in MONITOR_METRICS:
            normalized.append(metric_key)
    return normalized or list(MONITOR_METRICS)


def _system_snapshot(metrics: Iterable[str] | None = None) -> dict[str, Any]:
    selected = _normalize_metrics(metrics)
    snapshot: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "metrics": selected,
    }

    if "cpu" in selected:
        snapshot["cpu"] = {
            "percent": psutil.cpu_percent(interval=0.1),
            "count": psutil.cpu_count(logical=True),
        }
    if "memory" in selected:
        memory = psutil.virtual_memory()
        snapshot["memory"] = {
            "percent": memory.percent,
            "used": memory.used,
            "total": memory.total,
        }
    if "disk" in selected:
        disk = psutil.disk_usage("/")
        snapshot["disk"] = {
            "percent": disk.percent,
            "used": disk.used,
            "total": disk.total,
        }
    if "processes" in selected:
        snapshot["processes"] = _collect_processes()

    return snapshot


def _build_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE github_stats (
            repo TEXT NOT NULL,
            language TEXT NOT NULL,
            stars INTEGER NOT NULL,
            forks INTEGER NOT NULL,
            open_issues INTEGER NOT NULL,
            contributors INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    sample_rows = [
        ("modelcontextprotocol/python-sdk", "Python", 1850, 210, 16, 42, "2026-07-24"),
        ("modelcontextprotocol/typescript-sdk", "TypeScript", 1720, 190, 19, 39, "2026-07-25"),
        ("openai/openai-python", "Python", 27000, 3900, 144, 550, "2026-07-27"),
        ("openai/openai-node", "TypeScript", 12200, 1800, 88, 270, "2026-07-27"),
        ("pallets/flask", "Python", 69700, 16200, 23, 850, "2026-07-22"),
        ("django/django", "Python", 82900, 32800, 334, 2200, "2026-07-26"),
        ("tiangolo/fastapi", "Python", 87900, 7400, 511, 890, "2026-07-26"),
        ("pandas-dev/pandas", "Python", 45200, 19100, 2680, 3300, "2026-07-25"),
        ("numpy/numpy", "Python", 33100, 10600, 2510, 2100, "2026-07-25"),
        ("microsoft/vscode", "TypeScript", 177000, 33300, 9800, 1900, "2026-07-27"),
        ("facebook/react", "JavaScript", 237000, 48800, 1100, 1780, "2026-07-28"),
        ("vuejs/core", "TypeScript", 53000, 9300, 590, 460, "2026-07-27"),
    ]
    conn.executemany(
        """
        INSERT INTO github_stats (
            repo, language, stars, forks, open_issues, contributors, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        sample_rows,
    )
    conn.commit()
    return conn


DB = _build_db()


def _ensure_safe_query(query: str) -> None:
    text = query.strip().lower()
    if not text:
        raise ValueError("Query cannot be empty.")
    if not (text.startswith("select") or text.startswith("with")):
        raise ValueError("Only SELECT/CTE queries are supported in the demo.")
    if ";" in text[:-1]:
        raise ValueError("Multiple statements are not allowed.")


def _query_table(query: str, limit: int) -> tuple[list[str], list[dict[str, Any]]]:
    _ensure_safe_query(query)
    safe_limit = max(1, min(int(limit), 500))
    normalized_query = query.strip().rstrip(";")
    wrapped = f"SELECT * FROM ({normalized_query}) LIMIT ?"
    cursor = DB.execute(wrapped, (safe_limit,))
    rows = cursor.fetchall()
    columns = list(rows[0].keys()) if rows else [desc[0] for desc in cursor.description or []]
    payload_rows = [{col: row[col] for col in columns} for row in rows]
    return columns, payload_rows


@mcp.tool(
    name="render-mermaid",
    description="Render Mermaid diagrams and open the Mermaid viewer app.",
    meta=APP_UI_META["render-mermaid"],
)
def render_mermaid(code: str, theme: str = "default") -> dict[str, Any]:
    if theme not in MERMAID_THEMES:
        raise ValueError(f"theme must be one of: {', '.join(MERMAID_THEMES)}")
    selected_theme = theme
    initial_code = code.strip() or "graph TD\\n  A[Start] --> B{Choice}\\n  B -->|Yes| C[Done]"
    initial_svg = _render_mermaid_svg(initial_code, selected_theme)
    html = _render_template(
        MERMAID_VIEWER_TEMPLATE,
        themes=MERMAID_THEMES,
        selected_theme=selected_theme,
        initial_code=initial_code,
        initial_svg=initial_svg,
    )
    return {
        "resourceUri": MERMAID_RESOURCE_URI,
        "theme": selected_theme,
        "renderedWithMermaidCli": bool(initial_svg),
        "html": html,
    }


@mcp.tool(
    name="system-monitor",
    description="Open a real-time system monitoring dashboard.",
    meta=APP_UI_META["system-monitor"],
)
def system_monitor(interval: int = 5, metrics: list[str] | None = None) -> dict[str, Any]:
    safe_interval = max(1, min(int(interval), 60))
    selected_metrics = _normalize_metrics(metrics)
    snapshot = _system_snapshot(selected_metrics)
    html = _render_template(
        SYSTEM_MONITOR_TEMPLATE,
        interval=safe_interval,
        metrics_json=json.dumps(selected_metrics),
        snapshot_json=json.dumps(snapshot),
    )
    return {
        "resourceUri": SYSTEM_MONITOR_RESOURCE_URI,
        "interval": safe_interval,
        "metrics": selected_metrics,
        "snapshot": snapshot,
        "html": html,
    }


@mcp.tool(
    name="get-snapshot",
    description="Return current system metrics for monitor polling.",
    meta=APP_UI_META["get-snapshot"],
)
def get_snapshot(metrics: list[str] | None = None) -> dict[str, Any]:
    selected_metrics = _normalize_metrics(metrics)
    snapshot = _system_snapshot(selected_metrics)
    return {
        "resourceUri": SYSTEM_MONITOR_RESOURCE_URI,
        "snapshot": snapshot,
    }


@mcp.tool(
    name="query-table",
    description="Run a SQL query on sample GitHub stats and open the data table app.",
    meta=APP_UI_META["query-table"],
)
def query_table(
    query: str = "SELECT * FROM github_stats ORDER BY stars DESC",
    limit: int = 20,
) -> dict[str, Any]:
    columns, rows = _query_table(query, limit)
    html = _render_template(
        DATA_TABLE_TEMPLATE,
        query=query,
        limit=max(1, min(int(limit), 500)),
        columns_json=json.dumps(columns),
        rows_json=json.dumps(rows),
    )
    return {
        "resourceUri": DATA_TABLE_RESOURCE_URI,
        "query": query,
        "limit": max(1, min(int(limit), 500)),
        "columns": columns,
        "rows": rows,
        "html": html,
    }


@mcp.tool(
    name="export-csv",
    description="Export SQL query results as CSV.",
    meta=APP_UI_META["export-csv"],
)
def export_csv(
    query: str = "SELECT * FROM github_stats ORDER BY stars DESC",
    limit: int = 200,
) -> dict[str, Any]:
    columns, rows = _query_table(query, limit)
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    csv_text = buffer.getvalue()
    return {
        "resourceUri": DATA_TABLE_RESOURCE_URI,
        "filename": f"github-stats-{int(time.time())}.csv",
        "csv": csv_text,
        "rowCount": len(rows),
    }


@mcp.resource(MERMAID_RESOURCE_URI)
def mermaid_viewer_resource() -> str:
    return _render_template(
        MERMAID_VIEWER_TEMPLATE,
        themes=MERMAID_THEMES,
        selected_theme="default",
        initial_code="graph TD\\n  API --> Service\\n  Service --> Database",
        initial_svg="",
    )


@mcp.resource(SYSTEM_MONITOR_RESOURCE_URI)
def system_monitor_resource() -> str:
    snapshot = _system_snapshot(_normalize_metrics(None))
    return _render_template(
        SYSTEM_MONITOR_TEMPLATE,
        interval=5,
        metrics_json=json.dumps(list(MONITOR_METRICS)),
        snapshot_json=json.dumps(snapshot),
    )


@mcp.resource(DATA_TABLE_RESOURCE_URI)
def data_table_resource() -> str:
    query = "SELECT * FROM github_stats ORDER BY stars DESC"
    columns, rows = _query_table(query, 20)
    return _render_template(
        DATA_TABLE_TEMPLATE,
        query=query,
        limit=20,
        columns_json=json.dumps(columns),
        rows_json=json.dumps(rows),
    )


def run_server(host: str = "127.0.0.1", port: int = 8002) -> None:
    """Start the examples server over Streamable HTTP."""
    mcp.settings.host = host
    mcp.settings.port = port

    try:
        mcp.run(transport="streamable-http")
    except Exception:
        # Fallback: try stdio if streamable-http is unavailable
        mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()
