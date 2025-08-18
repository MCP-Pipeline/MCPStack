import json
import os
from pathlib import Path

from typer.testing import CliRunner

from MCPStack.cli import StackCLI
from MCPStack.tools.hello_world import HelloWorld

runner = CliRunner()
app = StackCLI().app


class TestHelloWorldTool:
    def test_actions(self):
        tool = HelloWorld()
        actions = tool.actions()
        names = [fn.__name__ for fn in actions]
        assert "say_hello_world_in_french" in names
        assert "say_hello_world_in_italian" in names
        assert "say_hello_world_in_german" in names
        assert "say_hello_world_in_chinese" in names

    def test_outputs(self):
        tool = HelloWorld()
        assert tool.say_hello_world_in_french() == "Bonjour le monde"
        assert tool.say_hello_world_in_italian() == "Ciao mondo"
        assert tool.say_hello_world_in_german() == "Hallo Welt"
        assert tool.say_hello_world_in_chinese() == "你好，世界"

    def test_tool_cli_mounts_and_configure_status(self, tmp_path: Path, monkeypatch):
        # 1) the tool CLI is mounted under `tools hello_world`
        r_help = runner.invoke(app, ["tools", "hello_world", "--help"])
        assert r_help.exit_code == 0
        out = r_help.stdout
        assert "init" in out
        assert "configure" in out
        assert "status" in out

        # 2) configure writes a valid config JSON
        cfg_path = tmp_path / "hello_world_config.json"
        r_cfg = runner.invoke(
            app,
            [
                "tools",
                "hello_world",
                "configure",
                "--prefix",
                "👋",
                "--languages",
                "french,italian",
                "--output",
                str(cfg_path),
                "--verbose",
            ],
        )
        assert r_cfg.exit_code == 0, r_cfg.stdout
        assert cfg_path.exists()
        cfg = json.loads(cfg_path.read_text())
        assert set(cfg.keys()) == {"env_vars", "tool_params"}
        assert cfg["env_vars"]["MCP_HELLO_PREFIX"] == "👋"
        assert cfg["tool_params"]["allowed_languages"] == ["french", "italian"]

        # 3) status reflects env vars
        monkeypatch.setenv("MCP_HELLO_PREFIX", "✨")
        r_status = runner.invoke(app, ["tools", "hello_world", "status"])
        assert r_status.exit_code == 0
        assert "✨" in r_status.stdout