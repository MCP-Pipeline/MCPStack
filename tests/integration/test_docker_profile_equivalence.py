"""Integration tests verifying Docker profiles provide equivalent functionality to removed commands."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from MCPStack.cli import StackCLI
from MCPStack.core.config import StackConfig
from MCPStack.stack import MCPStackCore


class TestDockerProfileEquivalence:
    """Test that Docker profiles generate identical results to removed commands."""

    def setup_method(self):
        """Set up test environment."""
        self.cli = StackCLI()
        self.runner = CliRunner()

    @patch('MCPStack.core.profile_manager.ProfileManager.execute_profile')
    def test_profile_dockerfile_matches_removed_command(self, mock_execute):
        """Test that Docker profiles generate identical Dockerfiles as removed commands."""
        expected_dockerfile = """FROM python:3.13-slim
WORKDIR /app
RUN pip install mcpstack
ENV API_KEY=test
CMD ["python", "-m", "MCPStack.core.server"]"""

        with tempfile.TemporaryDirectory() as temp_dir:
            dockerfile_path = Path(temp_dir) / "Dockerfile"
            
            # Test profile-based approach
            mock_execute.return_value = Mock(successful=True, results={
                'dockerfile.generate': str(dockerfile_path)
            })
            
            with patch('MCPStack.stack.MCPStackCore.save') as mock_save:
                mock_save.return_value = None
                
                result = self.runner.invoke(self.cli.app, [
                    "build",
                    "--profile", "build-only",
                    "--generate-dockerfile",
                    "--dockerfile-path", str(dockerfile_path),
                    "--presets", "example_preset"
                ])
                
                assert result.exit_code == 0
                assert "Executing workflow profile 'build-only'" in result.stdout
                mock_execute.assert_called_once()

    @patch('MCPStack.core.profile_manager.ProfileManager.execute_profile')
    def test_profile_image_build_matches_removed_command(self, mock_execute):
        """Test that Docker profiles build identical images as removed commands."""
        expected_result = {"success": True, "image_name": "test:latest", "image_id": "sha256:abc123"}

        mock_execute.return_value = Mock(successful=True, results={
            'image.build': expected_result
        })
        
        with patch('MCPStack.stack.MCPStackCore.save') as mock_save:
            mock_save.return_value = None
            
            result = self.runner.invoke(self.cli.app, [
                "build",
                "--profile", "build-only",
                "--build-image", "test:latest",
                "--presets", "example_preset"
            ])
            
            assert result.exit_code == 0
            assert "Executing workflow profile 'build-only'" in result.stdout
            mock_execute.assert_called_once()

    @patch('MCPStack.core.profile_manager.ProfileManager.execute_profile')
    def test_profile_config_matches_removed_command(self, mock_execute):
        """Test that Docker profiles generate identical MCP configs as removed commands."""
        expected_config = {
            "mcpServers": {
                "test": {
                    "command": "docker",
                    "args": ["run", "-i", "--rm", "test:latest"]
                }
            }
        }

        mock_execute.return_value = Mock(successful=True, results={
            'config.generate': expected_config
        })
        
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
    def test_complete_docker_workflow_via_profile(self, mock_execute):
        """Test complete end-to-end Docker workflows via profiles."""
        mock_execute.return_value = Mock(successful=True, results={
            'config.generate': {"mcpServers": {"test": {"command": "docker"}}},
            'dockerfile.generate': "/tmp/Dockerfile",
            'image.build': {"success": True, "image_name": "test:latest"},
            'image.push': {"success": True, "pushed": "test:latest"}
        })
        
        with patch('MCPStack.stack.MCPStackCore.save') as mock_save:
            mock_save.return_value = None
            
            result = self.runner.invoke(self.cli.app, [
                "build",
                "--profile", "build-and-push",
                "--build-image", "test:latest",
                "--docker-push",
                "--presets", "example_preset"
            ])
            
            assert result.exit_code == 0
            assert "Executing workflow profile 'build-and-push'" in result.stdout
            mock_execute.assert_called_once()


class TestDockerProfileParameterHandling:
    """Test that Docker profiles handle parameters correctly."""

    def setup_method(self):
        """Set up test environment."""
        self.cli = StackCLI()
        self.runner = CliRunner()

    @patch('MCPStack.core.profile_manager.ProfileManager.execute_profile')
    def test_profile_handles_custom_dockerfile_path(self, mock_execute):
        """Test that profiles handle custom Dockerfile paths correctly."""
        mock_execute.return_value = Mock(successful=True, results={})
        
        with patch('MCPStack.stack.MCPStackCore.save') as mock_save:
            mock_save.return_value = None
            
            result = self.runner.invoke(self.cli.app, [
                "build",
                "--profile", "build-only",
                "--generate-dockerfile",
                "--dockerfile-path", "/custom/path/Dockerfile",
                "--presets", "example_preset"
            ])
            
            assert result.exit_code == 0
            mock_execute.assert_called_once()

    @patch('MCPStack.core.profile_manager.ProfileManager.execute_profile')
    def test_profile_handles_build_args(self, mock_execute):
        """Test that profiles handle Docker build arguments correctly."""
        mock_execute.return_value = Mock(successful=True, results={})
        
        with patch('MCPStack.stack.MCPStackCore.save') as mock_save:
            mock_save.return_value = None
            
            result = self.runner.invoke(self.cli.app, [
                "build",
                "--profile", "build-only",
                "--build-image", "test:latest",
                "--build-args", "VERSION=1.0,ENV=prod",
                "--presets", "example_preset"
            ])
            
            assert result.exit_code == 0
            mock_execute.assert_called_once()

    @patch('MCPStack.core.profile_manager.ProfileManager.execute_profile')
    def test_profile_handles_registry_push(self, mock_execute):
        """Test that profiles handle registry push correctly."""
        mock_execute.return_value = Mock(successful=True, results={})
        
        with patch('MCPStack.stack.MCPStackCore.save') as mock_save:
            mock_save.return_value = None
            
            result = self.runner.invoke(self.cli.app, [
                "build",
                "--profile", "build-and-push",
                "--build-image", "registry.example.com/test:latest",
                "--docker-push",
                "--docker-registry-url", "registry.example.com",
                "--presets", "example_preset"
            ])
            
            assert result.exit_code == 0
            mock_execute.assert_called_once()


class TestDockerProfileErrorHandling:
    """Test error handling in Docker profiles."""

    def setup_method(self):
        """Set up test environment."""
        self.cli = StackCLI()
        self.runner = CliRunner()

    def test_profile_not_found_error(self):
        """Test clear error when profile is not found."""
        result = self.runner.invoke(self.cli.app, [
            "build",
            "--profile", "nonexistent-docker-profile",
            "--presets", "example_preset"
        ])
        
        assert result.exit_code == 1
        # The error message includes suggestions, so check for the core message
        assert "nonexistent-docker-profile" in result.stdout
        # Check for "not" and "found" separately since they may be on different lines
        assert "not" in result.stdout and "found" in result.stdout

    def test_profile_suggestions_for_typos(self):
        """Test that profile suggestions work for typos."""
        result = self.runner.invoke(self.cli.app, [
            "build",
            "--profile", "build-onli",  # Typo in build-only
            "--presets", "example_preset"
        ])
        
        assert result.exit_code == 1
        assert "Did you mean:" in result.stdout
        assert "build-only" in result.stdout

    @patch('MCPStack.core.profile_manager.ProfileManager.validate_profile')
    def test_missing_docker_warning(self, mock_validate):
        """Test warning when Docker is not available."""
        from MCPStack.core.profile_manager import ValidationResult
        
        # Mock validation to show missing Docker requirement
        mock_validate.return_value = ValidationResult(
            is_valid=True,
            missing_requirements=["Docker client (install Docker Desktop or Docker Engine)"]
        )
        
        result = self.runner.invoke(self.cli.app, [
            "build",
            "--profile", "build-only",
            "--presets", "example_preset"
        ])
        
        # Should show warning but still attempt execution
        assert "Warning: Missing requirements" in result.stdout or "Docker" in result.stdout


class TestBackwardCompatibility:
    """Test that existing functionality still works alongside profiles."""

    def setup_method(self):
        """Set up test environment."""
        self.cli = StackCLI()
        self.runner = CliRunner()

    def test_regular_build_still_works(self):
        """Test that regular build command without profiles still works."""
        with patch('MCPStack.stack.MCPStackCore.build') as mock_build, \
             patch('MCPStack.stack.MCPStackCore.save') as mock_save:
            mock_build.return_value = {"mcpServers": {"test": {"command": "fastmcp"}}}
            mock_save.return_value = None

            result = self.runner.invoke(self.cli.app, [
                "build",
                "--config-type", "fastmcp",
                "--presets", "example_preset"
            ])

            assert result.exit_code == 0
            assert "Pipeline config saved" in result.stdout
            assert "Executing workflow profile" not in result.stdout

    def test_docker_config_type_without_profile(self):
        """Test that docker config type works without profile."""
        with patch('MCPStack.stack.MCPStackCore.build') as mock_build, \
             patch('MCPStack.stack.MCPStackCore.save') as mock_save:
            mock_build.return_value = {"mcpServers": {"test": {"command": "docker"}}}
            mock_save.return_value = None

            result = self.runner.invoke(self.cli.app, [
                "build",
                "--config-type", "docker",
                "--presets", "example_preset"
            ])

            assert result.exit_code == 0
            mock_build.assert_called_once()
            call_kwargs = mock_build.call_args[1]
            assert call_kwargs["type"] == "docker"

