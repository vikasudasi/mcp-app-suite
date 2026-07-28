"""CLI entrypoint for the examples demo MCP server."""

from __future__ import annotations

import typer

from .server import run_server

app = typer.Typer(
    no_args_is_help=True,
    help="MCP examples demo server (Mermaid, monitor, and data table).",
)


@app.command("run")
def run(
    host: str = typer.Option("127.0.0.1", help="Host interface to bind."),
    port: int = typer.Option(8002, help="Port to listen on."),
) -> None:
    """Run the examples MCP server over Streamable HTTP."""
    run_server(host=host, port=port)


def main() -> None:
    """Entrypoint used by the console script."""
    app()


if __name__ == "__main__":
    main()
