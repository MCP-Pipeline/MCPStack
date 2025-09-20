import os
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from MCPStack.core.config import StackConfig
from MCPStack.core.mcp_config_generator.mcp_config_generators.claude_mcp_config import (
    ClaudeConfigGenerator,
)
from MCPStack.core.mcp_config_generator.mcp_config_generators.docker_mcp_config import (
    DockerMCPConfigGenerator,
)
from MCPStack.core.mcp_config_generator.mcp_config_generators.fast_mcp_config import (
    FastMCPConfigGenerator,
)
from MCPStack.core.utils.exceptions import MCPStackValidationError
from MCPStack.stack import MCPStackCore


@pytest.fixture
def mock_stack() -> MCPStackCore:
    """Fixture for mock MCPStack instance."""
    config = StackConfig(env_vars={"TEST_ENV": "value"})
    return MCPStackCore(config=config)


class TestClaudeConfigGenerator:
    """Tests for ClaudeConfigGenerator."""

    @patch("shutil.which", return_value="/usr/bin/python")
    @patch("os.path.isdir", return_value=True)
    @patch(
        "MCPStack.core.mcp_config_generator.mcp_config_generators.claude_mcp_config.ClaudeConfigGenerator._get_claude_config_path"
    )
    def test_generate_with_defaults(
        self,
        mock_get_path: MagicMock,
        mock_isdir: MagicMock,
        mock_which: MagicMock,
        mock_stack: MCPStackCore,
    ) -> None:
        """Test generating config with defaults."""
        mock_get_path.return_value = None
        config = ClaudeConfigGenerator.generate(mock_stack)
        assert isinstance(config, dict)
        assert "mcpServers" in config
        assert "mcpstack" in config["mcpServers"]
        server = config["mcpServers"]["mcpstack"]
        assert server["command"].endswith("python") or server["command"].endswith("python.exe")
        assert server["args"] == ["-m", "MCPStack.core.server"]
        assert os.path.isdir(server["cwd"])
        assert "TEST_ENV" in server["env"]

    @patch("shutil.which", return_value=None)
    def test_invalid_command_raises_error(
        self, mock_which: MagicMock, mock_stack: MCPStackCore
    ) -> None:
        """Test invalid command raises error."""
        with pytest.raises(MCPStackValidationError, match="Invalid command"):
            ClaudeConfigGenerator.generate(mock_stack, command="/invalid/python")

    @patch("os.path.isdir", return_value=False)
    def test_invalid_cwd_raises_error(
        self, mock_isdir: MagicMock, mock_stack: MCPStackCore
    ) -> None:
        """Test invalid cwd raises error."""
        with pytest.raises(MCPStackValidationError, match="Invalid cwd"):
            ClaudeConfigGenerator.generate(mock_stack, cwd="/invalid/dir")

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("json.dump")
    @patch(
        "MCPStack.core.mcp_config_generator.mcp_config_generators.claude_mcp_config.ClaudeConfigGenerator._get_claude_config_path"
    )
    @patch("pathlib.Path.exists")
    def test_merge_with_existing_config(
        self,
        mock_exists: MagicMock,
        mock_get_path: MagicMock,
        mock_dump: MagicMock,
        mock_load: MagicMock,
        mock_open_file: MagicMock,
        mock_stack: MCPStackCore,
        tmp_path: Path,
    ) -> None:
        """Test merging with existing Claude config."""
        mock_path = tmp_path / "claude_config.json"
        mock_get_path.return_value = mock_path
        mock_exists.return_value = True
        mock_load.return_value = {"mcpServers": {"existing": {}}}
        _config = ClaudeConfigGenerator.generate(mock_stack)
        mock_dump.assert_called_once()
        dumped_config = mock_dump.call_args[0][0]
        assert "existing" in dumped_config["mcpServers"]
        assert "mcpstack" in dumped_config["mcpServers"]

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_to_custom_path(
        self,
        mock_dump: MagicMock,
        mock_open_file: MagicMock,
        mock_stack: MCPStackCore,
        tmp_path: Path,
    ) -> None:
        """Test saving to custom path."""
        save_path = tmp_path / "custom.json"
        config = ClaudeConfigGenerator.generate(mock_stack, save_path=str(save_path))
        mock_dump.assert_called_once_with(config, mock_open_file(), indent=2)


class TestFastMCPConfigGenerator:
    """Tests for FastMCPConfigGenerator."""

    @patch("shutil.which", return_value="/usr/bin/python")
    @patch("os.path.isdir", return_value=True)
    def test_generate_with_defaults(
        self, mock_isdir: MagicMock, mock_which: MagicMock, mock_stack: MCPStackCore
    ) -> None:
        """Test generating config with defaults."""
        config = FastMCPConfigGenerator.generate(mock_stack)
        assert isinstance(config, dict)
        assert "mcpServers" in config
        assert "mcpstack" in config["mcpServers"]
        server = config["mcpServers"]["mcpstack"]
        assert server["command"].endswith("python") or server["command"].endswith("python.exe")
        assert server["args"] == ["-m", "MCPStack.core.server"]
        assert os.path.isdir(server["cwd"])
        assert "TEST_ENV" in server["env"]

    @patch("shutil.which", return_value=None)
    def test_invalid_command_raises_error(
        self, mock_which: MagicMock, mock_stack: MCPStackCore
    ) -> None:
        """Test invalid command raises error."""
        with pytest.raises(MCPStackValidationError, match="Invalid command"):
            FastMCPConfigGenerator.generate(mock_stack, command="/invalid/python")

    @patch("os.path.isdir", return_value=False)
    def test_invalid_cwd_raises_error(
        self, mock_isdir: MagicMock, mock_stack: MCPStackCore
    ) -> None:
        """Test invalid cwd raises error."""
        with pytest.raises(MCPStackValidationError, match="Invalid cwd"):
            FastMCPConfigGenerator.generate(mock_stack, cwd="/invalid/dir")

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_to_custom_path(
        self,
        mock_dump: MagicMock,
        mock_open_file: MagicMock,
        mock_stack: MCPStackCore,
        tmp_path: Path,
    ) -> None:
        """Test saving to custom path."""
        save_path = tmp_path / "custom.json"
        config = FastMCPConfigGenerator.generate(mock_stack, save_path=str(save_path))
        mock_dump.assert_called_once_with(config, mock_open_file(), indent=2)


class TestDockerMCPConfigGenerator:
    """Tests for DockerMCPConfigGenerator with new Docker building parameters."""

    @patch("MCPStack.core.docker.dockerfile_generator.DockerfileGenerator.save")
    @patch("MCPStack.core.docker.docker_builder.DockerBuilder.build")
    @patch("MCPStack.core.docker.docker_builder.DockerBuilder.push")
    def test_generate_with_dockerfile_generation(
        self,
        mock_push: MagicMock,
        mock_build: MagicMock,
        mock_dockerfile_save: MagicMock,
        mock_stack: MCPStackCore,
    ) -> None:
        """Test generating config with Dockerfile generation."""
        mock_build.return_value = {"success": True}

        config = DockerMCPConfigGenerator.generate(
            mock_stack,
            image_name="test:latest",
            generate_dockerfile=True,
            dockerfile_path="/custom/Dockerfile"
        )

        assert isinstance(config, dict)
        assert "mcpServers" in config
        assert "mcpstack" in config["mcpServers"]
        mock_dockerfile_save.assert_called_once()

    @patch("MCPStack.core.docker.docker_builder.DockerBuilder.build")
    def test_generate_with_image_build(
        self,
        mock_build: MagicMock,
        mock_stack: MCPStackCore,
    ) -> None:
        """Test generating config with Docker image build."""
        mock_build.return_value = {"success": True}

        config = DockerMCPConfigGenerator.generate(
            mock_stack,
            image_name="test:latest",
            build_image="test:v1.0"
        )

        assert isinstance(config, dict)
        mock_build.assert_called_once_with(
            dockerfile_path=Path("Dockerfile"),
            image_name="test:v1.0",
            build_args=None
        )

    @patch("MCPStack.core.docker.docker_builder.DockerBuilder.build")
    @patch("MCPStack.core.docker.docker_builder.DockerBuilder.push")
    def test_generate_with_build_and_push(
        self,
        mock_push: MagicMock,
        mock_build: MagicMock,
        mock_stack: MCPStackCore,
    ) -> None:
        """Test generating config with build and push."""
        mock_build.return_value = {"success": True}
        mock_push.return_value = {"success": True}

        config = DockerMCPConfigGenerator.generate(
            mock_stack,
            image_name="test:latest",
            build_image="test:v1.0",
            docker_push=True,
            docker_registry_url="registry.example.com"
        )

        mock_build.assert_called_once()
        mock_push.assert_called_once_with(
            image_name="test:v1.0",
            registry_url="registry.example.com"
        )

    def test_generate_basic_docker_config(self, mock_stack: MCPStackCore) -> None:
        """Test basic Docker config generation."""
        config = DockerMCPConfigGenerator.generate(
            mock_stack,
            image_name="test:latest",
            server_name="test_server",
            volumes=["/host:/container"],
            ports=["8080:8080"],
            network="test-network"
        )

        assert isinstance(config, dict)
        assert "mcpServers" in config
        assert "test_server" in config["mcpServers"]

        server_config = config["mcpServers"]["test_server"]
        assert server_config["command"] == "docker"
        assert "-v" in server_config["args"]
        assert "/host:/container" in server_config["args"]
        assert "-p" in server_config["args"]
        assert "8080:8080" in server_config["args"]
        assert "--network" in server_config["args"]
        assert "test-network" in server_config["args"]
        assert "test:latest" in server_config["args"]

    def test_generate_with_build_args(self, mock_stack: MCPStackCore) -> None:
        """Test generating config with Docker build arguments."""
        build_args = {"VERSION": "1.0", "ENV": "prod"}

        with patch("MCPStack.core.docker.docker_builder.DockerBuilder.build") as mock_build:
            mock_build.return_value = {"success": True}

            DockerMCPConfigGenerator.generate(
                mock_stack,
                image_name="test:latest",
                build_image="test:latest",
                build_args=build_args
            )

            mock_build.assert_called_once()
            call_kwargs = mock_build.call_args[1]
            assert call_kwargs["build_args"] == build_args

    def test_image_name_validation(self) -> None:
        """Test Docker image name validation."""
        with pytest.raises(MCPStackValidationError):
            DockerMCPConfigGenerator.generate(mock_stack, image_name="")

        with pytest.raises(MCPStackValidationError):
            DockerMCPConfigGenerator.generate(mock_stack, image_name="name with spaces")
