"""Simplified Docker CLI tests."""
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from MCPStack.cli import StackCLI
from MCPStack.core.config import StackConfig
from MCPStack.stack import MCPStackCore


class TestDockerCLIBasic:
    """Basic Docker CLI tests without complex mocking."""

    def setup_method(self):
        """Set up test environment."""
        self.cli = StackCLI()
        self.runner = CliRunner()

    def test_docker_help_command(self):
        """Test that Docker commands are available."""
        result = self.runner.invoke(self.cli.app, ["docker", "--help"])
        assert result.exit_code == 0
        assert "docker-dockerfile" in result.stdout
        assert "docker-build" in result.stdout
        assert "docker-config" in result.stdout

    def test_build_stack_from_options_empty(self):
        """Test _build_stack_from_options with no options."""
        stack = self.cli._build_stack_from_options(None, None)
        assert isinstance(stack, MCPStackCore)
        assert len(stack.tools) == 0

    def test_build_stack_from_options_nonexistent_pipeline(self):
        """Test _build_stack_from_options with non-existent pipeline."""
        with pytest.raises(FileNotFoundError):
            self.cli._build_stack_from_options("/nonexistent/pipeline.json", None)

    def test_docker_dockerfile_help(self):
        """Test Docker dockerfile command help."""
        result = self.runner.invoke(self.cli.app, ["docker", "docker-dockerfile", "--help"])
        assert result.exit_code == 0
        assert "Generate Dockerfile" in result.stdout

    def test_docker_build_help(self):
        """Test Docker build command help."""
        result = self.runner.invoke(self.cli.app, ["docker", "docker-build", "--help"])
        assert result.exit_code == 0
        assert "Build Docker image" in result.stdout

    def test_docker_config_help(self):
        """Test Docker config command help."""
        result = self.runner.invoke(self.cli.app, ["docker", "docker-config", "--help"])
        assert result.exit_code == 0
        assert "Generate Claude Desktop config" in result.stdout