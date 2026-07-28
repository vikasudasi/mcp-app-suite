import os
import tempfile
from pathlib import Path

from typer.testing import CliRunner

from mcp_app_scaffolder.cli import app

runner = CliRunner()


def test_default_python_scaffold_layout_and_wiring() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        prev_cwd = Path.cwd()
        temp_path = Path(temp_dir)
        try:
            os.chdir(temp_path)
            result = runner.invoke(app, ["my-app"])
        finally:
            os.chdir(prev_cwd)
        assert result.exit_code == 0

        root = temp_path / "my-app"
        assert (root / "pyproject.toml").exists()
        assert (root / "server.py").exists()
        assert (root / "README.md").exists()
        assert (root / "ui").exists()
        assert (root / "ui" / "index.html").exists()
        assert (root / "ui" / "package.json").exists()
        assert (root / "ui" / "vite.config.js").exists()
        assert (root / "ui" / "src" / "main.js").exists()

        server_text = (root / "server.py").read_text(encoding="utf-8")
        assert "_meta=TOOL_META" in server_text
        assert '"resourceUri": "ui://app/index.html"' in server_text

        ui_js = (root / "ui" / "src" / "main.js").read_text(encoding="utf-8")
        assert 'from "@modelcontextprotocol/ext-apps"' in ui_js
        assert "postMessage" in ui_js


def test_python_simple_demo_generates_single_file_ui_counter() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        prev_cwd = Path.cwd()
        temp_path = Path(temp_dir)
        try:
            os.chdir(temp_path)
            result = runner.invoke(app, ["counter-app", "--simple", "--demo"])
        finally:
            os.chdir(prev_cwd)
        assert result.exit_code == 0

        root = temp_path / "counter-app"
        assert (root / "server.py").exists()
        assert not (root / "ui").exists()

        server_text = (root / "server.py").read_text(encoding="utf-8")
        assert "<!doctype html>" in server_text
        assert "increment" in server_text
        assert "decrement" in server_text
        assert 'from "@modelcontextprotocol/ext-apps"' in server_text
        assert "window.parent.postMessage" in server_text


def test_node_template_supported() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        prev_cwd = Path.cwd()
        temp_path = Path(temp_dir)
        try:
            os.chdir(temp_path)
            result = runner.invoke(app, ["node-app", "--template", "node"])
        finally:
            os.chdir(prev_cwd)
        assert result.exit_code == 0

        root = temp_path / "node-app"
        assert (root / "package.json").exists()
        assert (root / "server.js").exists()
        assert (root / "ui" / "src" / "main.js").exists()


def test_refuses_existing_directory() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        prev_cwd = Path.cwd()
        temp_path = Path(temp_dir)
        try:
            os.chdir(temp_path)
            Path("existing").mkdir()
            result = runner.invoke(app, ["existing"])
        finally:
            os.chdir(prev_cwd)
        assert result.exit_code != 0
        assert "Refusing to overwrite" in result.output
