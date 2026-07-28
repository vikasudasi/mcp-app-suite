"""CLI for generating MCP App starter projects."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from jinja2 import Environment, PackageLoader

app = typer.Typer(
    name="mcp-app-scaffolder",
    help="Generate MCP App starter projects.",
    add_completion=False,
)


class TemplateType(StrEnum):
    """Supported scaffold template families."""

    python = "python"
    node = "node"


@dataclass(frozen=True, slots=True)
class GeneratedFile:
    """Maps an output file path to a template path."""

    output_path: str
    template_path: str


def _slugify(name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return normalized or "mcp-app"


def _module_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return cleaned or "mcp_app"


def _display_name(name: str) -> str:
    parts = [part for part in re.split(r"[-_\s]+", name) if part]
    return " ".join(part.capitalize() for part in parts) or "MCP App"


def _jinja_env() -> Environment:
    return Environment(
        loader=PackageLoader("mcp_app_scaffolder", "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def _manifest(template: TemplateType, simple: bool) -> list[GeneratedFile]:
    if template is TemplateType.python:
        if simple:
            return [
                GeneratedFile("pyproject.toml", "python/simple/pyproject.toml.j2"),
                GeneratedFile("README.md", "python/simple/README.md.j2"),
                GeneratedFile("server.py", "python/simple/server.py.j2"),
            ]
        return [
            GeneratedFile("pyproject.toml", "python/full/pyproject.toml.j2"),
            GeneratedFile("README.md", "python/full/README.md.j2"),
            GeneratedFile("server.py", "python/full/server.py.j2"),
            GeneratedFile("ui/package.json", "python/full/ui/package.json.j2"),
            GeneratedFile("ui/vite.config.js", "python/full/ui/vite.config.js.j2"),
            GeneratedFile("ui/index.html", "python/full/ui/index.html.j2"),
            GeneratedFile("ui/src/main.js", "python/full/ui/src/main.js.j2"),
            GeneratedFile("ui/src/style.css", "python/full/ui/src/style.css.j2"),
        ]

    if simple:
        return [
            GeneratedFile("package.json", "node/simple/package.json.j2"),
            GeneratedFile("README.md", "node/simple/README.md.j2"),
            GeneratedFile("server.js", "node/simple/server.js.j2"),
        ]
    return [
        GeneratedFile("package.json", "node/full/package.json.j2"),
        GeneratedFile("README.md", "node/full/README.md.j2"),
        GeneratedFile("server.js", "node/full/server.js.j2"),
        GeneratedFile("ui/package.json", "node/full/ui/package.json.j2"),
        GeneratedFile("ui/vite.config.js", "node/full/ui/vite.config.js.j2"),
        GeneratedFile("ui/index.html", "node/full/ui/index.html.j2"),
        GeneratedFile("ui/src/main.js", "node/full/ui/src/main.js.j2"),
        GeneratedFile("ui/src/style.css", "node/full/ui/src/style.css.j2"),
    ]


def _write_scaffold(
    project_dir: Path, template: TemplateType, simple: bool, demo: bool
) -> None:
    env = _jinja_env()
    app_slug = _slugify(project_dir.name)
    module_name = _module_name(project_dir.name)
    display_name = _display_name(project_dir.name)
    tool_name = f"{app_slug}-counter" if demo else f"{app_slug}-hello"

    context = {
        "app_name": project_dir.name,
        "app_slug": app_slug,
        "app_display_name": display_name,
        "module_name": module_name,
        "tool_name": tool_name,
        "demo": demo,
        "simple": simple,
    }

    for item in _manifest(template=template, simple=simple):
        rendered = env.get_template(item.template_path).render(**context)
        target = project_dir / item.output_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")


@app.command()
def scaffold(
    project_name: Annotated[str, typer.Argument(help="Directory name for the new app.")],
    template: Annotated[
        TemplateType, typer.Option("--template", help="Scaffold template family.")
    ] = TemplateType.python,
    simple: Annotated[
        bool, typer.Option("--simple", help="Generate minimal single-file app (no Vite UI).")
    ] = False,
    demo: Annotated[
        bool,
        typer.Option(
            "--demo",
            help="Generate a working counter demo tool with increment/decrement behavior.",
        ),
    ] = False,
) -> None:
    """Generate a new MCP App project scaffold."""
    project_dir = Path(project_name).resolve()
    if project_dir.exists():
        raise typer.BadParameter(
            f"Refusing to overwrite existing path: {project_dir}", param_hint="project_name"
        )

    project_dir.mkdir(parents=True, exist_ok=False)
    _write_scaffold(project_dir=project_dir, template=template, simple=simple, demo=demo)
    typer.echo(f"Created MCP App scaffold at {project_dir}")


def main() -> None:
    """Run the scaffolder CLI."""
    app(prog_name="mcp-app-scaffolder")


if __name__ == "__main__":
    main()
