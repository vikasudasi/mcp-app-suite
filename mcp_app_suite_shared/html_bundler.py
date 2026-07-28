"""Helpers for inlining CSS/JS into HTML documents."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def inline_css(html: str, css_text: str) -> str:
    """Inline CSS into an HTML document."""
    style_block = f"<style>\n{css_text}\n</style>"
    if "</head>" in html:
        return html.replace("</head>", f"{style_block}\n</head>", 1)
    return f"{style_block}\n{html}"


def inline_js(html: str, js_text: str) -> str:
    """Inline JavaScript into an HTML document."""
    script_block = f"<script>\n{js_text}\n</script>"
    if "</body>" in html:
        return html.replace("</body>", f"{script_block}\n</body>", 1)
    return f"{html}\n{script_block}"


def _read_files(paths: Iterable[str | Path], base_path: str | Path | None = None) -> list[str]:
    base = Path(base_path) if base_path is not None else Path(".")
    content: list[str] = []
    for path in paths:
        file_path = Path(path)
        if not file_path.is_absolute():
            file_path = base / file_path
        content.append(file_path.read_text(encoding="utf-8"))
    return content


def bundle_html(
    html: str,
    css_files: Iterable[str | Path] | None = None,
    js_files: Iterable[str | Path] | None = None,
    base_path: str | Path | None = None,
) -> str:
    """Inline CSS and JS file content into HTML."""
    bundled = html
    if css_files:
        for css_text in _read_files(css_files, base_path=base_path):
            bundled = inline_css(bundled, css_text)
    if js_files:
        for js_text in _read_files(js_files, base_path=base_path):
            bundled = inline_js(bundled, js_text)
    return bundled
