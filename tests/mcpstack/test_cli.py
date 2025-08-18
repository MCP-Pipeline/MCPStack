from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from MCPStack.cli import StackCLI
import MCPStack.core.preset.registry as preset_registry
from MCPStack.core.config import StackConfig

runner = CliRunner()
app = StackCLI().app


def _strip_ansi(text: str) -> str:
    import re
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


class TestMCPStackCLI:
    def test_version(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "MCPStack CLI Version" in result.stdout

    def test_list_presets(self) -> None:
        result = runner.invoke(app, ["list-presets"])
        print(f"-----------> DEBUG: {result.stdout}")
        assert result.exit_code == 0
        assert "Available Presets" in result.stdout

    def test_list_tools(self) -> None:
        result = runner.invoke(app, ["list-tools"])
        assert result.exit_code == 0
        assert "Available Tools" in result.stdout

    @patch("MCPStack.cli.MCPStackCore.run")
    @patch("MCPStack.cli.MCPStackCore.build")
    @patch("MCPStack.cli.MCPStackCore.save")
    def test_run_with_preset(self, mock_save: MagicMock, mock_build: MagicMock, mock_run: MagicMock) -> None:
        with patch("MCPStack.core.preset.registry.ALL_PRESETS", {"example_preset": MagicMock()}):
            mock_preset_class = preset_registry.ALL_PRESETS["example_preset"]
            mock_preset_stack = MagicMock()
            mock_preset_stack.config = StackConfig()
            mock_preset_stack.mcp = None
            mock_preset_stack.tools = []
            mock_preset_class.configure_mock(**{"create.return_value": mock_preset_stack})
            result = runner.invoke(app, ["run", "--presets", "example_preset"])
            assert result.exit_code == 0
            output = _strip_ansi(result.stdout)
            assert "Applying preset 'example_preset'" in output
            mock_build.assert_called_once()
            mock_save.assert_called_once()
            mock_run.assert_called_once()

    def test_search_presets(self) -> None:
        result = runner.invoke(app, ["search", "example", "--type", "presets"])
        assert result.exit_code == 0
        assert "Presets matches" in result.stdout

    def test_search_invalid_type(self) -> None:
        result = runner.invoke(app, ["search", "query", "--type", "invalid"])
        assert result.exit_code != 0
        assert "Invalid type" in result.stdout

    def test_tools_help(self) -> None:
        result = runner.invoke(app, ["tools", "--help"])
        assert result.exit_code == 0
        assert "Tool-specific subcommands" in result.stdout

    def test_run_with_invalid_preset(self) -> None:
        result = runner.invoke(app, ["run", "--presets", "invalid_preset"])
        assert result.exit_code != 0
        output = _strip_ansi(result.output)
        assert "Unknown preset" in output

    @patch("MCPStack.cli.MCPStackCore.load")
    def test_build_success_fastmcp(self, mock_load: MagicMock) -> None:
        # Build with default config type; use existing pipeline path scenario
        mock_stack = MagicMock()
        mock_load.return_value = mock_stack
        result = runner.invoke(app, ["build", "--config-type", "fastmcp", "--pipeline", "some.json"])
        # build subcommand should succeed (it catches exceptions and exits 1 otherwise)
        assert result.exit_code == 0

    @patch("MCPStack.core.mcp_config_generator.mcp_config_generators.claude_mcp_config.ClaudeConfigGenerator.generate")
    def test_build_success_claude(self, mock_generate: MagicMock) -> None:
        mock_generate.return_value = {"mcpServers": {"mcpstack": {}}}
        result = runner.invoke(app, ["build", "--config-type", "claude"])
        assert result.exit_code == 0
        output = _strip_ansi(result.stdout)
        assert "Pipeline config saved" in output

    @patch("MCPStack.core.mcp_config_generator.mcp_config_generators.universal_mcp_config.UniversalConfigGenerator.generate")
    def test_build_success_universal(self, mock_generate: MagicMock) -> None:
        mock_generate.return_value = {"mcpServers": {"mcpstack": {}}}
        result = runner.invoke(app, ["build", "--config-type", "universal"])
        assert result.exit_code == 0
        output = _strip_ansi(result.stdout)
        assert "Pipeline config saved" in output

    @patch("MCPStack.core.mcp_config_generator.mcp_config_generators.fast_mcp_config.FastMCPConfigGenerator.generate")
    def test_build_script_failure(self, mock_generate: MagicMock) -> None:
        mock_generate.side_effect = Exception("Build failed")
        result = runner.invoke(app, ["build"])
        assert result.exit_code != 0
        output = _strip_ansi(result.output)
        assert "Build failed" in output

    def test_add_tool_unknown(self) -> None:
        result = runner.invoke(app, ["pipeline", "unknown"])
        assert result.exit_code != 0
        assert "Unknown tool" in result.output

