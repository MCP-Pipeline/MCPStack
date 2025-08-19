import os
from unittest.mock import Mock, patch

import pytest

from MCPStack.core.utils.exceptions import MCPStackValidationError
from MCPStack.stack import MCPStackCore


class TestMCPServer:
    """Tests for MCP server."""

    def test_server_can_be_imported_as_module(self) -> None:
        """Test that the server can be imported as a module."""
        import MCPStack.core.server

        assert hasattr(MCPStack.core.server, "main")
        assert callable(MCPStack.core.server.main)

    @patch.dict(os.environ, {"MCPSTACK_CONFIG_PATH": "test_config.json"})
    @patch("MCPStack.core.server.MCPStackCore.load")
    def test_main_success(self, mock_load: Mock) -> None:
        """Test main function with valid config."""
        mock_stack = Mock(spec=MCPStackCore)
        mock_load.return_value = mock_stack
        from MCPStack.core.server import main

        main()
        mock_load.assert_called_once_with("test_config.json")
        mock_stack.build.assert_called_once()
        mock_stack.run.assert_called_once()

    @patch.dict(os.environ, clear=True)
    def test_main_no_config_path(self) -> None:
        """Test main raises error when MCPSTACK_CONFIG_PATH is not set."""
        from MCPStack.core.server import main

        with pytest.raises(
            MCPStackValidationError, match="MCPSTACK_CONFIG_PATH env var not set"
        ):
            main()

    @patch.dict(os.environ, {"MCPSTACK_CONFIG_PATH": "invalid.json"})
    @patch("MCPStack.core.server.MCPStackCore.load")
    def test_main_load_failure(self, mock_load: Mock) -> None:
        """Test main handles load failure."""
        mock_load.side_effect = FileNotFoundError("Config not found")
        from MCPStack.core.server import main

        with pytest.raises(FileNotFoundError):
            main()

    @patch.dict(os.environ, {"MCPSTACK_CONFIG_PATH": "test.json"})
    @patch("MCPStack.core.server.MCPStackCore.load")
    def test_main_build_failure(self, mock_load: Mock) -> None:
        """Test main handles build failure."""
        from MCPStack.core.utils.exceptions import MCPStackValidationError

        mock_stack = Mock(spec=MCPStackCore)
        mock_load.return_value = mock_stack
        mock_stack.build.side_effect = MCPStackValidationError("Build failed")
        from MCPStack.core.server import main

        with pytest.raises(MCPStackValidationError):
            main()
