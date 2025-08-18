import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from MCPStack.core.config import StackConfig
from MCPStack.core.tool.base import BaseTool
from MCPStack.core.utils.exceptions import MCPStackConfigError


@pytest.fixture
def temp_env_vars():
    """Fixture to temporarily set environment variables."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


class TestStackConfig:
    """Tests for StackConfig class."""

    def test_init_default(self):
        """Test default initialization."""
        config = StackConfig()
        assert config.log_level == "INFO"
        assert config.env_vars == {}
        assert isinstance(config.project_root, Path)
        assert isinstance(config.data_dir, Path)
        assert isinstance(config.databases_dir, Path)
        assert isinstance(config.raw_files_dir, Path)

    def test_init_with_params(self):
        """Test initialization with parameters."""
        env_vars = {"TEST_KEY": "value"}
        config = StackConfig(log_level="DEBUG", env_vars=env_vars)
        assert config.log_level == "DEBUG"
        assert config.env_vars == env_vars

    def test_to_dict(self):
        """Test to_dict method."""
        config = StackConfig(env_vars={"KEY": "value"})
        data = config.to_dict()
        assert data["log_level"] == "INFO"
        assert data["env_vars"] == {"KEY": "value"}

    def test_from_dict(self):
        """Test from_dict class method."""
        data = {"log_level": "DEBUG", "env_vars": {"KEY": "value"}}
        config = StackConfig.from_dict(data)
        assert config.log_level == "DEBUG"
        assert config.env_vars == {"KEY": "value"}

    def test_get_env_var(self, temp_env_vars):
        """Test get_env_var method."""
        os.environ["TEST_ENV"] = "env_value"
        config = StackConfig(env_vars={"CONFIG_KEY": "config_value"})
        assert config.get_env_var("TEST_ENV") == "env_value"
        assert config.get_env_var("CONFIG_KEY") == "config_value"
        assert config.get_env_var("MISSING", default="default") == "default"

    def test_get_env_var_raise_if_missing(self):
        """Test get_env_var raises if missing and required."""
        config = StackConfig()
        with pytest.raises(MCPStackConfigError, match="Missing required env var"):
            config.get_env_var("MISSING", raise_if_missing=True)

    def test_validate_for_tools_success(self):
        """Test validate_for_tools method success."""
        class Tool(BaseTool):
            def actions(self): return []
            def to_dict(self): return {}
            @classmethod
            def from_dict(cls, params): return cls()

        mock_tool = Tool()
        mock_tool.__class__.__name__ = "TestTool"
        mock_tool.required_env_vars = {"REQUIRED": None}
        config = StackConfig(env_vars={"REQUIRED": "value"})
        config.validate_for_tools([mock_tool])

    def test_validate_for_tools_error(self):
        """Test validate_for_tools raises on error."""
        class Tool(BaseTool):
            def actions(self): return []
            def to_dict(self): return {}
            @classmethod
            def from_dict(cls, params): return cls()

        mock_tool = Tool()
        mock_tool.__class__.__name__ = "TestTool"
        mock_tool.required_env_vars = {"FAKE_MISSING": None}
        config = StackConfig(env_vars={})
        with pytest.raises(MCPStackConfigError):
            config.validate_for_tools([mock_tool])

    def test_merge_env(self):
        """Test merge_env method."""
        config = StackConfig(env_vars={"EXISTING": "old"})
        new_env = {"NEW": "value"}
        config.merge_env(new_env)
        assert config.env_vars["NEW"] == "value"
        assert config.env_vars["EXISTING"] == "old"

    def test_merge_env_conflict(self):
        """Test merge_env raises on conflict."""
        config = StackConfig(env_vars={"KEY": "old"})
        with pytest.raises(MCPStackConfigError, match="Env conflict"):
            config.merge_env({"KEY": "new"})

    @patch("MCPStack.core.config.Path.home")
    def test_project_root_fallback(self, mock_home):
        """Test project root fallback to home."""
        mock_home.return_value = Path("/home/user")
        with patch("pathlib.Path.exists", return_value=False):
            config = StackConfig()
            assert config.project_root == Path("/home/user")

    def test_invalid_log_level(self):
        """Test invalid log level raises error."""
        with pytest.raises(MCPStackConfigError, match="Invalid log level"):
            StackConfig(log_level="INVALID")

    def test_get_data_dir_with_env(self, temp_env_vars):
        """Test _get_data_dir uses env var when set."""
        os.environ["MCPSTACK_DATA_DIR"] = "/custom/data"
        config = StackConfig()
        assert config._get_data_dir() == Path("/custom/data")
