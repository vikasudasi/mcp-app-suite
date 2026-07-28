"""aiohttp HTTP server for the MCP App playground."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from aiohttp import web

from mcp_app_playground.bridge import McpAppsBridge
from mcp_app_playground.discovery import McpServerConnection

logger = logging.getLogger("mcp_app_playground.server")

HERE = Path(__file__).parent
TEMPLATES_DIR = HERE / "templates"


class PlaygroundServer:
    """Manages the aiohttp server that serves the MCP App playground UI."""

    def __init__(
        self,
        server_connection: McpServerConnection,
        apps: list[Any],
        *,
        port: int = 3691,
        debug: bool = False,
        watch: bool = False,
    ) -> None:
        self._connection = server_connection
        self._apps = apps
        self._port = port
        self._debug = debug
        self._watch = watch
        self._app = web.Application()
        self._runner: web.AppRunner | None = None
        self._bridge = McpAppsBridge(call_tool_fn=self._connection.call_tool)
        self._rpc_log: list[dict[str, Any]] = []

        # Set up routes
        self._app.router.add_get("/", self._handle_listing)
        self._app.router.add_get("/mcp-apps/{tool_name}/", self._handle_app_view)
        self._app.router.add_post("/api/bridge", self._handle_bridge)
        self._app.router.add_get("/api/apps", self._handle_api_apps)
        self._app.router.add_get("/api/debug", self._handle_api_debug)
        self._app.router.add_get("/api/health", self._handle_health)
        self._app.router.add_get("/static/debug.js", self._handle_debug_js)

    def _render_template(self, template_name: str, **kwargs: Any) -> str:
        """Render a Jinja2 template with context."""
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        template = env.get_template(template_name)
        return template.render(**kwargs)

    def _get_listing_html(self) -> str:
        """Render the listing page with all discovered apps."""
        apps_data = []
        for app in self._apps:
            apps_data.append({
                "name": app.display_name or app.tool_name,
                "tool_name": app.tool_name,
                "description": app.tool_description,
            })

        listing_html = self._render_template(
            "listing.html",
            apps=apps_data,
            num_apps=len(apps_data),
            connected=True,
            port=self._port,
            version="0.1.0",
        )

        # Inject bridge JS + debug JS
        bridge_js = self._bridge.get_bridge_client_js()
        bridge_script = f"<script>{bridge_js}</script>"
        debug_script = ""
        if self._debug:
            debug_script = '<script src="/static/debug.js"></script>'

        listing_html = listing_html.replace("</body>", f"{bridge_script}\n{debug_script}\n</body>")
        return listing_html

    async def _handle_listing(self, request: web.Request) -> web.Response:
        """Serve the main listing page."""
        html = self._get_listing_html()
        return web.Response(text=html, content_type="text/html")

    async def _handle_app_view(self, request: web.Request) -> web.Response:
        """Serve a single MCP App in a sandboxed iframe page."""
        tool_name = request.match_info["tool_name"]
        app = next((a for a in self._apps if a.tool_name == tool_name), None)

        if not app or not app.html_content:
            return web.Response(
                text=f"<html><body><h1>App '{tool_name}' not found</h1></body></html>",
                content_type="text/html",
                status=404,
            )

        page = self._render_app_page(app)
        return web.Response(text=page, content_type="text/html")

    def _escape_srcdoc(self, html_text: str) -> str:
        """Escape HTML for use in srcdoc attribute."""
        return (
            html_text.replace("&", "&amp;")
            .replace("\u2028", "\\u2028")
            .replace("\u2029", "\\u2029")
        )

    def _render_app_page(self, app: Any) -> str:
        """Render a full page for a single MCP App with bridge proxy."""
        bridge_js = self._bridge.get_bridge_client_js()
        escaped_content = self._escape_srcdoc(app.html_content)
        safe_name = app.display_name or app.tool_name

        css_block = (
            "*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}"
            "body{background:#fff;overflow:hidden;}"
            ".error-overlay{display:none;position:fixed;top:0;left:0;right:0;"
            "background:#f85149;color:#fff;padding:.75rem 1rem;font-size:.85rem;z-index:999;}"
        )
        js_block = (
            "var appFrame=document.getElementById('app-frame');"
            "window.addEventListener('message',function(e){"
            "if(e.source===appFrame.contentWindow){"
            "var d=e.data;if(d&&d.type){"
            "fetch('/api/bridge',{method:'POST',headers:{'Content-Type':'application/json'},"
            "body:JSON.stringify(d)}).then(function(r){return r.json();})"
            ".then(function(r){appFrame.contentWindow.postMessage(r,'*');})"
            ".catch(function(e){appFrame.contentWindow.postMessage("
            "{type:'response',id:d.id,payload:{error:e.message}},'*');});}}});"
            "appFrame.onerror=function(){"
            "document.getElementById('error').style.display='block';"
            "document.getElementById('error').textContent='Failed to load app content';};"
        )
        return (
            f"<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\">"
            f"<title>{safe_name} - MCP App</title><style>{css_block}</style></head>"
            f"<body><div id=\"error\" class=\"error-overlay\"></div>"
            f"<iframe id=\"app-frame\" srcdoc=\"{escaped_content}\""
            f" sandbox=\"allow-scripts allow-same-origin allow-forms allow-popups\""
            f" allow=\"clipboard-read;clipboard-write\"></iframe><script>{bridge_js}</script>"
            f"<script>{js_block}</script></body></html>"
        )

    async def _handle_bridge(self, request: web.Request) -> web.Response:
        """Handle postMessage bridge API calls."""
        try:
            data = await request.json()
        except json.JSONDecodeError:
            return web.json_response({"error": "Invalid JSON"}, status=400)

        self._rpc_log.append({
            "direction": "in",
            "data": data,
            "timestamp": datetime.now().isoformat(),
        })

        try:
            result = await self._bridge.handle_message(data)
            self._rpc_log.append({
                "direction": "out",
                "data": result,
                "timestamp": datetime.now().isoformat(),
            })
            return web.json_response(result)
        except Exception as e:
            logger.exception("Bridge error")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_api_apps(self, request: web.Request) -> web.Response:
        """Return the list of apps as JSON."""
        apps_data = []
        for app in self._apps:
            apps_data.append({
                "toolName": app.tool_name,
                "displayName": app.display_name or app.tool_name,
                "description": app.tool_description,
                "resourceUri": app.resource_uri,
                "hasContent": app.html_content is not None,
            })
        return web.json_response({"apps": apps_data, "count": len(apps_data)})

    async def _handle_api_debug(self, request: web.Request) -> web.Response:
        """Return the debug/RPC log as JSON."""
        return web.json_response({
            "rpcLog": self._rpc_log[-200:],
            "messages": self._bridge.get_messages()[-100:],
            "modelContextUpdates": self._bridge.get_model_context_updates()[-50:],
        })

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({"status": "ok", "apps": len(self._apps)})

    async def _handle_debug_js(self, request: web.Request) -> web.Response:
        """Serve the debug panel JavaScript."""
        js = """
(function(){'use strict';var s=document.createElement('div');
s.id='mcp-debug-sidebar';s.innerHTML=
'<style>'+
'#mcp-debug-sidebar{position:fixed;top:0;right:0;width:400px;height:100vh;'+
'background:#1a1d27;border-left:1px solid #2d3347;z-index:10000;'+
'display:flex;flex-direction:column;font-family:SF Mono,Fira Code,monospace;'+
'font-size:12px;color:#e1e4e8;transform:translateX(100%);'+
'transition:transform 0.3s ease;}'+
'#mcp-debug-sidebar.open{transform:translateX(0);}'+
'#mcp-debug-toggle{position:fixed;top:10px;right:10px;z-index:10001;'+
'background:#238636;color:#fff;border:none;border-radius:6px;'+
'padding:6px 12px;cursor:pointer;font-size:12px;font-family:inherit;}'+
'#mcp-debug-sidebar .header{padding:12px;border-bottom:1px solid #2d3347;'+
'display:flex;justify-content:space-between;align-items:center;}'+
'#mcp-debug-sidebar .content{flex:1;overflow-y:auto;padding:8px;}'+
'#mcp-debug-sidebar .entry{padding:6px 8px;border-bottom:1px solid #2d3347;'+
'word-break:break-all;line-height:1.4;}'+
'#mcp-debug-sidebar .entry .dir-in{color:#58a6ff;}'+
'#mcp-debug-sidebar .entry .dir-out{color:#3fb950;}'+
'#mcp-debug-sidebar .entry .time{color:#8b949e;font-size:10px;}'+
'#mcp-debug-sidebar .clear-btn{background:transparent;border:1px solid #2d3347;'+
'color:#8b949e;cursor:pointer;border-radius:4px;padding:2px 8px;font-size:11px;}'+
'</style>'+
'<div class="header"><h3>\\ud83d\\udd0d Debug</h3>'+
'<button class="clear-btn" onclick="'+
"var e=document.getElementById('mcp-debug-entries');e.innerHTML='';"+
'">Clear</button></div>'+
'<div class="content" id="mcp-debug-entries">'+
'<div class="entry" style="color:#8b949e">Waiting for bridge activity...</div></div>';
document.body.appendChild(s);
var t=document.createElement('button');
t.id='mcp-debug-toggle';
t.textContent='\\ud83d\\udc1e Debug';
t.onclick=function(){s.classList.toggle('open');};
document.body.appendChild(t);
var c=0;
setInterval(function(){
fetch('/api/debug').then(function(r){return r.json();}).then(function(d){
var l=d.rpcLog||[];
if(l.length>c){var e=document.getElementById('mcp-debug-entries');
for(var i=c;i<l.length;i++){var x=l[i];
var dv=document.createElement('div');dv.className='entry';
var dir=x.direction==='in'?'\\u2192':'\\u2190';
var dc=x.direction==='in'?'dir-in':'dir-out';
var ts=x.timestamp?x.timestamp.slice(11,19):'';
dv.innerHTML='<span class=\"'+dc+'\">'+dir+'</span> <span class=\"time\">'+ts+'</span> '+
JSON.stringify(x.data).slice(0,200);
e.appendChild(dv);e.scrollTop=e.scrollHeight;}
c=l.length;}}).catch(function(){});},2000);})();
"""
        return web.Response(text=js, content_type="application/javascript")

    async def start(self) -> None:
        """Start the aiohttp server."""
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "0.0.0.0", self._port)
        await site.start()
        logger.info("Playground server started on http://0.0.0.0:%d", self._port)

    async def stop(self) -> None:
        """Stop the server."""
        if self._runner:
            await self._runner.cleanup()
            self._runner = None

    @property
    def port(self) -> int:
        return self._port