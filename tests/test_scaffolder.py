"""Unit tests for the mcp-app-scaffolder CLI.

Tests template rendering for all 4 template variants (python-simple,
python-full, node-simple, node-full), file creation, --simple vs
--demo flags, and existing-directory rejection.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from mcp_app_scaffolder.cli import (
    TemplateType,
    _display_name,
    _jinja_env,
    _manifest,
    _module_name,
    _slugify,
    app,
)

runner = CliRunner()


# =====================================================================
# Utility function tests
# =====================================================================


class TestUtilityFunctions:
    def test_slugify(self) -> None:
        assert _slugify("My Cool App") == "my-cool-app"
        assert _slugify("Hello_World") == "hello-world"
        assert _slugify("special chars!!!") == "special-chars"
        assert _slugify("") == "mcp-app"

    def test_module_name(self) -> None:
        assert _module_name("My App") == "my_app"
        assert _module_name("hello-world") == "hello_world"
        assert _module_name("") == "mcp_app"

    def test_display_name(self) -> None:
        assert _display_name("my-cool-app") == "My Cool App"
        assert _display_name("hello") == "Hello"
        assert _display_name("") == "MCP App"


# =====================================================================
# Manifest generation tests (4 template variants)
# =====================================================================


class TestManifestGeneration:
    """Verify _manifest returns the correct file specs for each variant."""

    def test_python_simple_manifest(self) -> None:
        files = _manifest(TemplateType.python, simple=True)
        paths = {f.output_path for f in files}
        assert "pyproject.toml" in paths
        assert "README.md" in paths
        assert "server.py" in paths
        assert "ui" not in " ".join(paths)  # no ui/ files

    def test_python_full_manifest(self) -> None:
        files = _manifest(TemplateType.python, simple=False)
        paths = {f.output_path for f in files}
        assert "pyproject.toml" in paths
        assert "README.md" in paths
        assert "server.py" in paths
        assert "ui/index.html" in paths
        assert "ui/src/main.js" in paths
        assert "ui/vite.config.js" in paths

    def test_node_simple_manifest(self) -> None:
        files = _manifest(TemplateType.node, simple=True)
        paths = {f.output_path for f in files}
        assert "package.json" in paths
        assert "README.md" in paths
        assert "server.js" in paths
        assert "ui" not in " ".join(paths)

    def test_node_full_manifest(self) -> None:
        files = _manifest(TemplateType.node, simple=False)
        paths = {f.output_path for f in files}
        assert "package.json" in paths
        assert "server.js" in paths
        assert "ui/src/main.js" in paths
        assert "ui/vite.config.js" in paths


# =====================================================================
# Template rendering tests (verify content via Jinja2)
# =====================================================================


class TestTemplateRendering:
    """Render each template variant and verify key content."""

    def _render_template(
        self, template: TemplateType, simple: bool, demo: bool, app_name: str = "my-app",
    ) -> dict[str, str]:
        """Render all templates for a given variant and return {output_path: content}."""
        env = _jinja_env()
        rendered: dict[str, str] = {}
        for item in _manifest(template=template, simple=simple):
            content = env.get_template(item.template_path).render(
                app_name=app_name,
                app_slug=_slugify(app_name),
                app_display_name=_display_name(app_name),
                module_name=_module_name(app_name),
                tool_name=(
                    f"{_slugify(app_name)}-counter" if demo else f"{_slugify(app_name)}-hello"
                ),
                demo=demo,
                simple=simple,
            )
            rendered[item.output_path] = content
        return rendered

    def test_python_simple_no_demo(self) -> None:
        files = self._render_template(TemplateType.python, simple=True, demo=False)
        server = files.get("server.py", "")
        assert "my-app-hello" in server  # default tool name
        assert "import" in server

    def test_python_simple_with_demo(self) -> None:
        files = self._render_template(TemplateType.python, simple=True, demo=True)
        server = files.get("server.py", "")
        assert "my-app-counter" in server
        assert "increment" in server or "counter" in server
        # Demo includes inline HTML with postMessage bridge
        assert "<!doctype html>" in server or "<html" in server

    def test_python_full_no_demo(self) -> None:
        files = self._render_template(TemplateType.python, simple=False, demo=False)
        pyproject = files.get("pyproject.toml", "")
        assert "mcp" in pyproject
        server = files.get("server.py", "")
        assert "my-app-hello" in server
        ui_html = files.get("ui/index.html", "")
        assert "<!doctype html>" in ui_html or "<html" in ui_html
        ui_main = files.get("ui/src/main.js", "")
        assert "postMessage" in ui_main or "__MCP_APPS_BRIDGE__" in ui_main

    def test_python_full_with_demo(self) -> None:
        files = self._render_template(TemplateType.python, simple=False, demo=True)
        server = files.get("server.py", "")
        assert "my-app-counter" in server
        ui_main = files.get("ui/src/main.js", "")
        # Demo UI should have increment/decrement logic
        assert "increment" in ui_main or "counter" in ui_main

    def test_node_simple_no_demo(self) -> None:
        files = self._render_template(TemplateType.node, simple=True, demo=False)
        server = files.get("server.js", "")
        assert "my-app-hello" in server
        assert "require(" in server or "import " in server

    def test_node_simple_with_demo(self) -> None:
        files = self._render_template(TemplateType.node, simple=True, demo=True)
        server = files.get("server.js", "")
        assert "my-app-counter" in server
        assert "increment" in server

    def test_node_full_no_demo(self) -> None:
        files = self._render_template(TemplateType.node, simple=False, demo=False)
        pkg = files.get("package.json", "")
        assert "@modelcontextprotocol/sdk" in pkg or "mcp" in pkg
        server = files.get("server.js", "")
        assert "my-app-hello" in server
        ui_main = files.get("ui/src/main.js", "")
        assert "postMessage" in ui_main or "__MCP_APPS_BRIDGE__" in ui_main

    def test_node_full_with_demo(self) -> None:
        files = self._render_template(TemplateType.node, simple=False, demo=True)
        server = files.get("server.js", "")
        assert "my-app-counter" in server
        ui_main = files.get("ui/src/main.js", "")
        assert "increment" in ui_main or "counter" in ui_main


# =====================================================================
# CLI scaffold file creation tests
# =====================================================================


class TestScaffoldFileCreation:
    """Test that the CLI actually creates files on disk."""

    def test_default_python_creates_files(self) -> None:
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            prev = Path.cwd()
            os.chdir(tmp)
            try:
                result = runner.invoke(app, ["test-app"])
                assert result.exit_code == 0
                root = Path(tmp) / "test-app"
                assert root.is_dir()
                assert (root / "pyproject.toml").is_file()
                assert (root / "server.py").is_file()
                assert (root / "ui" / "index.html").is_file()
                assert (root / "ui" / "src" / "main.js").is_file()
            finally:
                os.chdir(prev)

    def test_python_simple_creates_no_ui_dir(self) -> None:
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            prev = Path.cwd()
            os.chdir(tmp)
            try:
                result = runner.invoke(app, ["simple-app", "--simple"])
                assert result.exit_code == 0
                root = Path(tmp) / "simple-app"
                assert (root / "server.py").is_file()
                assert not (root / "ui").exists()
            finally:
                os.chdir(prev)

    def test_node_full_creates_node_structure(self) -> None:
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            prev = Path.cwd()
            os.chdir(tmp)
            try:
                result = runner.invoke(app, ["node-app", "--template", "node"])
                assert result.exit_code == 0
                root = Path(tmp) / "node-app"
                assert (root / "package.json").is_file()
                assert (root / "server.js").is_file()
                assert (root / "ui" / "src" / "main.js").is_file()
            finally:
                os.chdir(prev)

    def test_node_simple_creates_minimal(self) -> None:
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            prev = Path.cwd()
            os.chdir(tmp)
            try:
                result = runner.invoke(app, ["ns", "--template", "node", "--simple"])
                assert result.exit_code == 0
                root = Path(tmp) / "ns"
                assert (root / "server.js").is_file()
                assert not (root / "ui").exists()
            finally:
                os.chdir(prev)

    def test_demo_flag_adds_tool(self) -> None:
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            prev = Path.cwd()
            os.chdir(tmp)
            try:
                result = runner.invoke(app, ["demo-app", "--demo"])
                assert result.exit_code == 0
                root = Path(tmp) / "demo-app"
                server = (root / "server.py").read_text(encoding="utf-8")
                assert "counter" in server
            finally:
                os.chdir(prev)

    def test_refuses_existing_directory(self) -> None:
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            prev = Path.cwd()
            os.chdir(tmp)
            try:
                Path("existing").mkdir()
                result = runner.invoke(app, ["existing"])
                assert result.exit_code != 0
                assert "Refusing to overwrite" in result.output
            finally:
                os.chdir(prev)

    def test_readme_is_generated(self) -> None:
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            prev = Path.cwd()
            os.chdir(tmp)
            try:
                result = runner.invoke(app, ["docs-test"])
                assert result.exit_code == 0
                root = Path(tmp) / "docs-test"
                readme = (root / "README.md").read_text(encoding="utf-8")
                assert "docs-test" in readme or "Docs Test" in readme or "DocsTest" in readme
            finally:
                os.chdir(prev)