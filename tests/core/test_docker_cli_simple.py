"""Profile-based Docker CLI tests for the integrated workflow approach."""
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from MCPStack.cli import StackCLI
from MCPStack.core.config import StackConfig
from MCPStack.stack import MCPStackCore


class TestProfileBasedDockerCLI:
    """Tests for profile-based Docker CLI using integrated workflow approach."""

    def setup_method(self):
        """Set up test environment."""
        self.cli = StackCLI()
        self.runner = CliRunner()

    def test_build_help_includes_docker_options(self):
        """Test that build command help includes Docker options."""
        result = self.runner.invoke(self.cli.app, ["build", "--help"])
        assert result.exit_code == 0
        assert "--build-image" in result.stdout
        assert "--generate-dockerfile" in result.stdout
        assert "--docker-push" in result.stdout
        assert "--config-type" in result.stdout
        assert "--profile" in result.stdout

    @patch('MCPStack.core.profile_manager.ProfileManager.execute_profile')
    def test_build_docker_config_via_profile(self, mock_execute):
        """Test Docker config generation via build-only profile (equivalent to mcpstack docker config)."""
        mock_execute.return_value = Mock(successful=True, results={})
        
        with patch('MCPStack.stack.MCPStackCore.save') as mock_save:
            mock_save.return_value = None

            result = self.runner.invoke(self.cli.app, [
                "build",
                "--profile", "build-only",
                "--config-type", "docker",
                "--presets", "example_preset"
            ])

            assert result.exit_code == 0
            assert "Executing workflow profile 'build-only'" in result.stdout
            mock_execute.assert_called_once()

    @patch('MCPStack.core.profile_manager.ProfileManager.execute_profile')
    def test_build_dockerfile_generation_via_profile(self, mock_execute):
        """Test Dockerfile generation via build-only profile (equivalent to mcpstack docker dockerfile)."""
        mock_execute.return_value = Mock(successful=True, results={})
        
        with patch('MCPStack.stack.MCPStackCore.save') as mock_save:
            mock_save.return_value = None

            result = self.runner.invoke(self.cli.app, [
                "build",
                "--profile", "build-only",
                "--presets", "example_preset",
                "--generate-dockerfile"
            ])

            assert result.exit_code == 0
            assert "Executing workflow profile 'build-only'" in result.stdout
            mock_execute.assert_called_once()

    @patch('MCPStack.core.profile_manager.ProfileManager.execute_profile')
    def test_build_image_via_profile(self, mock_execute):
        """Test Docker image building via build-only profile (equivalent to mcpstack docker build)."""
        mock_execute.return_value = Mock(successful=True, results={})
        
        with patch('MCPStack.stack.MCPStackCore.save') as mock_save:
            mock_save.return_value = None

            result = self.runner.invoke(self.cli.app, [
                "build",
                "--profile", "build-only",
                "--presets", "example_preset",
                "--build-image", "test:latest"
            ])

            assert result.exit_code == 0
            assert "Executing workflow profile 'build-only'" in result.stdout
            mock_execute.assert_called_once()

    @patch('MCPStack.core.profile_manager.ProfileManager.execute_profile')
    def test_build_and_push_via_profile(self, mock_execute):
        """Test full Docker workflow via build-and-push profile."""
        mock_execute.return_value = Mock(successful=True, results={})
        
        with patch('MCPStack.stack.MCPStackCore.save') as mock_save:
            mock_save.return_value = None

            result = self.runner.invoke(self.cli.app, [
                "build",
                "--profile", "build-and-push",
                "--presets", "example_preset",
                "--build-image", "test:latest",
                "--docker-push"
            ])

            assert result.exit_code == 0
            assert "Executing workflow profile 'build-and-push'" in result.stdout
            mock_execute.assert_called_once()

    def test_build_backward_compatibility_without_profile(self):
        """Test that existing build command still works without profile."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('MCPStack.stack.MCPStackCore.build') as mock_build, \
                 patch('MCPStack.stack.MCPStackCore.save') as mock_save:
                mock_build.return_value = {"mcpServers": {"test": {"command": "docker"}}}
                mock_save.return_value = None

                result = self.runner.invoke(self.cli.app, [
                    "build", 
                    "--presets", "example_preset"
                ])
                
                assert result.exit_code == 0
                assert "SUCCESS: Pipeline config saved" in result.stdout
                assert "Executing workflow profile" not in result.stdout
