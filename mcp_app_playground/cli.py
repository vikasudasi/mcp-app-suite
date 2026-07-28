"""CLI entrypoint for mcp-app-playground.

Usage:
  mcp-app-playground --stdio --command "python my_server.py"
  mcp-app-playground --server http://localhost:8002
  mcp-app-playground --server http://localhost:8002 --watch --debug --open
  mcp-app-playground --stdio --command "uvx mcp-server" --port 8080
"""

from __future__ import annotations

import asyncio
import logging
import signal
import webbrowser

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from mcp_app_playground.discovery import McpServerConnection
from mcp_app_playground.server import PlaygroundServer

app = typer.Typer(
    name="mcp-app-playground",
    help="Local MCP App preview playground - discover and render MCP Apps in your browser.",
    add_completion=False,
)

console = Console()


def setup_logging(debug: bool) -> None:
    """Configure logging with Rich handler."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=debug)],
    )
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


async def _async_main(
    stdio: bool,
    command: str | None,
    server_url: str | None,
    port: int,
    watch: bool,
    debug: bool,
    open_browser: bool,
) -> None:
    """Async main entry point."""
    if not stdio and not server_url:
        console.print("[red]Error:[/] Either --stdio (with --command) or "
                       "--server URL is required.")
        raise typer.Exit(1)

    if stdio and not command:
        console.print("[red]Error:[/] --stdio requires --command to specify "
                       "the server command.")
        raise typer.Exit(1)

    connection = McpServerConnection(
        mode="stdio" if stdio else "http",
        command=command,
        server_url=server_url,
    )

    with console.status("[bold green]Connecting to MCP server..."):
        try:
            await connection.connect()
            console.print("[green]\u2713[/] Connected to MCP server")
        except Exception as e:
            console.print(f"[red]\u2717[/] Failed to connect: {e}")
            raise typer.Exit(1) from e

    with console.status("[bold yellow]Discovering MCP Apps..."):
        try:
            apps = await connection.discover_apps()
            console.print(f"[green]\u2713[/] Discovered {len(apps)} MCP App(s)")
        except Exception as e:
            console.print(f"[red]\u2717[/] Discovery failed: {e}")
            await connection.close()
            raise typer.Exit(1) from e

    if apps:
        table = Table(title="Discovered MCP Apps", title_style="bold cyan")
        table.add_column("Tool", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Resource URI", style="blue")
        table.add_column("Has HTML", style="yellow")

        for app_info in apps:
            table.add_row(
                app_info.tool_name,
                app_info.display_name or app_info.tool_name,
                app_info.resource_uri,
                "\u2713" if app_info.html_content else "\u2717",
            )
        console.print(table)
    else:
        console.print("[yellow]\u26a0[/] No MCP Apps found. Ensure your server "
                       "advertises tools with _meta.ui.resourceUri.")

    server = PlaygroundServer(
        connection, apps, port=port, debug=debug, watch=watch,
    )

    try:
        await server.start()
        console.print(f"\n[bold green]\U0001f680 Playground running at:[/] "
                       f"[blue underline]http://localhost:{port}[/]")
        console.print(f"   [dim]Discovered {len(apps)} MCP App(s)[/]")

        if watch:
            console.print("   [yellow]\U0001f440 Watch mode enabled (hot-reload)[/]")
        if debug:
            console.print("   [cyan]\U0001f50d Debug sidebar enabled[/]")

        if open_browser:
            webbrowser.open(f"http://localhost:{port}")

        console.print("\n[dim]Press Ctrl+C to stop[/]")

        stop_event = asyncio.Event()

        def _signal_handler() -> None:
            stop_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _signal_handler)
            except NotImplementedError:
                pass

        await stop_event.wait()

    except asyncio.CancelledError:
        pass
    finally:
        console.print("\n[yellow]Shutting down...[/]")
        await server.stop()
        await connection.close()
        console.print("[green]\u2713[/] Shutdown complete")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    stdio: bool = typer.Option(
        False, "--stdio", help="Connect via stdio transport",
    ),
    command: str | None = typer.Option(
        None, "--command", "-c",
        help="Command to start the MCP server (required with --stdio)",
    ),
    server: str | None = typer.Option(
        None, "--server", "-s",
        help="Streamable HTTP server URL (e.g. http://localhost:8002)",
    ),
    port: int = typer.Option(
        3691, "--port", "-p",
        help="Port for the playground HTTP server",
        min=1024, max=65535,
    ),
    watch: bool = typer.Option(
        False, "--watch", "-w",
        help="Enable hot-reload for app changes",
    ),
    debug: bool = typer.Option(
        False, "--debug", "-d",
        help="Show debug sidebar with JSON-RPC log",
    ),
    open_browser: bool = typer.Option(
        False, "--open", "-o",
        help="Auto-open browser when ready",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Enable verbose logging",
    ),
) -> None:
    """\U0001f9e9 MCP App Playground - preview MCP Apps in your browser."""
    if ctx.invoked_subcommand is not None:
        return

    setup_logging(verbose or debug)

    try:
        asyncio.run(_async_main(
            stdio=stdio,
            command=command,
            server_url=server,
            port=port,
            watch=watch,
            debug=debug,
            open_browser=open_browser,
        ))
    except KeyboardInterrupt:
        pass
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        if verbose or debug:
            console.print_exception()
        raise typer.Exit(1) from e


@app.command()
def version() -> None:
    """Show the version and exit."""
    console.print("mcp-app-playground v0.1.0")


if __name__ == "__main__":
    app()