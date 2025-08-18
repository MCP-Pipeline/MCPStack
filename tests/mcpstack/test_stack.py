import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP

from MCPStack.core.config import StackConfig
from MCPStack.core.mcp_config_generator.registry import ALL_MCP_CONFIG_GENERATORS
from MCPStack.core.tool.base import BaseTool
from MCPStack.core.utils.exceptions import (
    MCPStackBuildError,
    MCPStackInitializationError,
    MCPStackPresetError,
    MCPStackValidationError,
    MCPStackConfigError,
)
from MCPStack.stack import MCPStackCore
from MCPStack.tools.registry import ALL_TOOLS


@pytest.fixture
def mock_config() -> StackConfig:
    return StackConfig(env_vars={"TEST_ENV": "value"})


@pytest.fixture
def mock_tool() -> BaseTool:
    class MockTool(BaseTool):
        TYPE = "mocktool"
        @classmethod
        def from_dict(cls, params):
            return cls()
        def actions(self):
            pass
        def to_dict(self):
            pass
        def __init__(self):
            super().__init__()
            self.required_env_vars = {}
            self.actions = MagicMock(return_value=[lambda: "test_action"])
            self.to_dict = MagicMock(return_value={"param": "value"})
            self.initialize = MagicMock()
            self.post_load = MagicMock()
    return MockTool()


class TestMCPStackCore:
    def test_init_default(self) -> None:
        stack = MCPStackCore()
        assert isinstance(stack.config, StackConfig)
        assert stack.tools == []
        assert stack.mcp is None
        assert stack._mcp_config_generators == ALL_MCP_CONFIG_GENERATORS
        assert not stack._built

    def test_init_with_params(self, mock_config: StackConfig) -> None:
        mock_mcp = MagicMock(spec=FastMCP)
        stack = MCPStackCore(config=mock_config, mcp=mock_mcp)
        assert stack.config == mock_config
        assert stack.mcp == mock_mcp

    def test_with_config(self, mock_config: StackConfig) -> None:
        stack = MCPStackCore()
        new_stack = stack.with_config(mock_config)
        assert new_stack != stack
        assert new_stack.config == mock_config
        assert new_stack.tools == stack.tools
        assert new_stack.mcp == stack.mcp

    def test_with_tool(self, mock_tool: BaseTool) -> None:
        stack = MCPStackCore()
        new_stack = stack.with_tool(mock_tool)
        assert new_stack != stack
        assert new_stack.tools == [mock_tool]
        assert new_stack.config == stack.config
        assert new_stack.mcp == stack.mcp

    def test_with_tools(self, mock_tool: BaseTool) -> None:
        stack = MCPStackCore()
        new_stack = stack.with_tools([mock_tool, mock_tool])
        assert new_stack != stack
        assert len(new_stack.tools) == 2
        assert new_stack.config == stack.config
        assert new_stack.mcp == stack.mcp

    @patch("MCPStack.core.preset.registry.ALL_PRESETS", {"test_preset": MagicMock()})
    def test_with_preset_success(self) -> None:
        mock_preset_class = MagicMock()
        mock_preset_stack = MagicMock(spec=MCPStackCore)
        mock_preset_stack.tools = [MagicMock(spec=BaseTool)]
        mock_preset_stack.config = MagicMock(spec=StackConfig)
        mock_preset_stack.mcp = MagicMock(spec=FastMCP)
        mock_preset_class.create.return_value = mock_preset_stack
        with patch.dict("MCPStack.core.preset.registry.ALL_PRESETS", {"test_preset": mock_preset_class}):
            stack = MCPStackCore()
            new_stack = stack.with_preset("test_preset")
            assert new_stack != stack
            assert new_stack.tools == mock_preset_stack.tools
            assert new_stack.config == mock_preset_stack.config
            assert new_stack.mcp == mock_preset_stack.mcp

    def test_with_preset_unknown(self) -> None:
        stack = MCPStackCore()
        with pytest.raises(MCPStackPresetError, match="Unknown preset"):
            stack.with_preset("unknown")

    def test_build_success(self, mock_tool: BaseTool) -> None:
        with patch.dict(ALL_MCP_CONFIG_GENERATORS, {"test": MagicMock()}):
            mock_generator = ALL_MCP_CONFIG_GENERATORS["test"]
            mock_generator.generate.return_value = {"config": "test"}
            mock_mcp = MagicMock(spec=FastMCP)
            mock_mcp.tool.return_value = lambda x: x
            stack = MCPStackCore(mcp=mock_mcp).with_tool(mock_tool)
            result = stack.build(type="test")
            assert result == {"config": "test"}
            assert stack._built
            mock_tool.initialize.assert_called_once()
            mock_generator.generate.assert_called_once()

    def test_build_no_tools(self) -> None:
        stack = MCPStackCore()
        with pytest.raises(MCPStackValidationError):
            stack.build()

    def test_build_validation_failure(self, mock_tool: BaseTool) -> None:
        mock_tool.required_env_vars = {"MISSING": None}
        with pytest.raises(MCPStackConfigError):
            stack = MCPStackCore().with_tool(mock_tool)
            stack.build()

    def test_build_unknown_type(self) -> None:
        stack = MCPStackCore()
        with pytest.raises(MCPStackValidationError):
            stack.build(type="unknown")

    def test_run_not_built(self) -> None:
        stack = MCPStackCore()
        with pytest.raises(MCPStackBuildError, match="Call .build()"):
            stack.run()

    def test_run_no_mcp(self) -> None:
        stack = MCPStackCore()
        stack._built = True
        with pytest.raises(MCPStackInitializationError, match="MCP not initialized"):
            stack.run()

    def test_run_success(self, mock_tool: BaseTool) -> None:
        mock_mcp = MagicMock(spec=FastMCP)
        stack = MCPStackCore(mcp=mock_mcp).with_tool(mock_tool)
        stack._built = True
        with patch.object(stack, "_teardown_tools") as mock_teardown:
            stack.run()
            mock_mcp.run.assert_called_once()
            mock_teardown.assert_called_once()

    def test_run_exception(self, mock_tool: BaseTool) -> None:
        mock_mcp = MagicMock(spec=FastMCP)
        mock_mcp.run.side_effect = Exception("Run failed")
        stack = MCPStackCore(mcp=mock_mcp).with_tool(mock_tool)
        stack._built = True
        with patch.object(stack, "_teardown_tools") as mock_teardown:
            with pytest.raises(Exception, match="Run failed"):
                stack.run()
            mock_teardown.assert_called_once()

    def test_save_not_built(self) -> None:
        stack = MCPStackCore()
        with pytest.raises(MCPStackBuildError, match="Call .build()"):
            stack.save("test.json")

    def test_save_success(self, tmp_path: Path, mock_tool: BaseTool) -> None:
        path = tmp_path / "config.json"
        stack = MCPStackCore().with_tool(mock_tool)
        stack._built = True
        stack.save(str(path))
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
        assert "config" in data
        assert "tools" in data
        assert len(data["tools"]) == 1

    def test_load_success(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        data = {
            "config": {"log_level": "INFO", "env_vars": {}},
            "tools": [{"type": "mocktool", "params": {"param": "value"}}],
        }
        with open(path, "w") as f:
            json.dump(data, f)
        with patch.dict(ALL_TOOLS, {"mocktool": MagicMock()}):
            mock_tool_cls = ALL_TOOLS["mocktool"]
            mock_tool = MagicMock(spec=BaseTool)
            mock_tool_cls.from_dict.return_value = mock_tool
            stack = MCPStackCore.load(str(path))
            assert isinstance(stack, MCPStackCore)
            assert stack._built
            mock_tool.post_load.assert_called_once()

    def test_load_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            MCPStackCore.load("nonexistent.json")

    def test_load_unknown_tool(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        data = {
            "config": {"log_level": "INFO", "env_vars": {}},
            "tools": [{"type": "unknown", "params": {}}],
        }
        with open(path, "w") as f:
            json.dump(data, f)
        with pytest.raises(MCPStackValidationError, match="Unknown tool type"):
            MCPStackCore.load(str(path))

    def test_teardown_tools(self, mock_tool: BaseTool) -> None:
        mock_backend = MagicMock()
        mock_tool.backends = {"test": mock_backend}
        stack = MCPStackCore().with_tool(mock_tool)
        stack._teardown_tools()
        mock_backend.teardown.assert_called_once()

    def test_post_load(self, mock_tool: BaseTool) -> None:
        stack = MCPStackCore().with_tool(mock_tool)
        stack._post_load()
        mock_tool.post_load.assert_called_once()
        assert stack._built

    def test_generate_config_unknown_type_with_suggestion(self) -> None:
        with patch.dict(ALL_MCP_CONFIG_GENERATORS, {"fastmcp": MagicMock()}):
            stack = MCPStackCore()
            with pytest.raises(MCPStackValidationError) as exc_info:
                stack._generate_config(type="fastmc")
            assert "Unknown config type: fastmc. Did you mean 'fastmcp'?" in str(exc_info.value)
