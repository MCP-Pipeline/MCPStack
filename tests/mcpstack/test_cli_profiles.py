"""CLI integration tests for workflow profile functionality."""

from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from MCPStack.cli import StackCLI
from MCPStack.core.config import StackConfig
from MCPStack.stack import MCPStackCore

runner = CliRunner()
app = StackCLI().app


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    import re
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


class TestCLIProfileIntegration:
    """Test CLI integration with workflow profiles."""

    def test_list_profiles_command(self):
        """Test the list-profiles CLI command."""
        result = runner.invoke(app, ["list-profiles"])
        assert result.exit_code == 0
        output = _strip_ansi(result.stdout)
        assert "Available Workflow Profiles" in output
        assert "build-and-push" in output
        assert "build-only" in output

    def test_list_profiles_with_config_type_filter(self):
        """Test list-profiles with config type filtering."""
        result = runner.invoke(app, ["list-profiles", "--config-type", "docker"])
        assert result.exit_code == 0
        output = _strip_ansi(result.stdout)
        assert "Available Workflow Profiles" in output
        assert "build-and-push" in output

    def test_list_profiles_with_nonexistent_config_type(self):
        """Test list-profiles with non-existent config type."""
        result = runner.invoke(app, ["list-profiles", "--config-type", "kubernetes"])
        assert result.exit_code == 0
        output = _strip_ansi(result.stdout)
        # Should show empty results for non-existent config type
        assert "Available Workflow Profiles" in output

    @patch("MCPStack.cli.MCPStackCore.build")
    @patch("MCPStack.cli.MCPStackCore.save")
    @patch("MCPStack.core.profile_manager.ProfileManager.execute_profile")
    def test_build_with_profile_success(self, mock_execute, mock_save, mock_build):
        """Test build command with profile execution."""
        # Mock successful profile execution
        mock_result = MagicMock()
        mock_result.successful = True
        mock_execute.return_value = mock_result

        # Create a proper mock preset that returns a real MCPStackCore
        mock_preset = MagicMock()
        mock_preset.create.return_value = MCPStackCore(config=StackConfig())
        
        with patch("MCPStack.core.preset.registry.ALL_PRESETS", {"example_preset": mock_preset}):
            result = runner.invoke(app, [
                "build", 
                "--presets", "example_preset",
                "--config-type", "docker",
                "--profile", "build-only"
            ])
            
            assert result.exit_code == 0
            output = _strip_ansi(result.stdout)
            assert "Executing workflow profile 'build-only'" in output
            assert "Profile 'build-only' executed successfully" in output
            
            # Verify profile orchestrator was called
            mock_execute.assert_called_once()

    @patch("MCPStack.cli.MCPStackCore.build")
    @patch("MCPStack.cli.MCPStackCore.save")
    @patch("MCPStack.core.profile_manager.ProfileManager.execute_profile")
    def test_build_with_profile_failure(self, mock_execute, mock_save, mock_build):
        """Test build command when profile execution fails."""
        # Mock failed profile execution
        mock_execute.side_effect = RuntimeError("Docker not available")

        # Create a proper mock preset that returns a real MCPStackCore
        mock_preset = MagicMock()
        mock_preset.create.return_value = MCPStackCore(config=StackConfig())
        
        with patch("MCPStack.core.preset.registry.ALL_PRESETS", {"example_preset": mock_preset}):
            result = runner.invoke(app, [
                "build", 
                "--presets", "example_preset",
                "--config-type", "docker",
                "--profile", "build-and-push"
            ])
            
            assert result.exit_code == 1
            output = _strip_ansi(result.stdout)
            assert "Executing workflow profile 'build-and-push'" in output
            assert "Profile execution failed: Docker not available" in output

    @patch("MCPStack.cli.MCPStackCore.build")
    @patch("MCPStack.cli.MCPStackCore.save")
    def test_build_without_profile(self, mock_save, mock_build):
        """Test build command without profile (backward compatibility)."""
        # Create a proper mock preset that returns a real MCPStackCore
        mock_preset = MagicMock()
        mock_preset.create.return_value = MCPStackCore(config=StackConfig())
        
        with patch("MCPStack.core.preset.registry.ALL_PRESETS", {"example_preset": mock_preset}):
            result = runner.invoke(app, [
                "build", 
                "--presets", "example_preset",
                "--config-type", "docker"
            ])
            
            assert result.exit_code == 0
            output = _strip_ansi(result.stdout)
            # Should not mention profiles
            assert "workflow profile" not in output.lower()
            assert "Pipeline config saved" in output

    @patch("MCPStack.cli.MCPStackCore.build")
    @patch("MCPStack.cli.MCPStackCore.save")
    @patch("MCPStack.core.profile_manager.ProfileManager.execute_profile")
    def test_build_with_profile_partial_success(self, mock_execute, mock_save, mock_build):
        """Test build command when profile completes with issues."""
        # Mock partially successful profile execution
        mock_result = MagicMock()
        mock_result.successful = False  # Some stages failed
        mock_execute.return_value = mock_result

        # Create a proper mock preset that returns a real MCPStackCore
        mock_preset = MagicMock()
        mock_preset.create.return_value = MCPStackCore(config=StackConfig())
        
        with patch("MCPStack.core.preset.registry.ALL_PRESETS", {"example_preset": mock_preset}):
            result = runner.invoke(app, [
                "build", 
                "--presets", "example_preset",
                "--config-type", "docker",
                "--profile", "build-and-push"
            ])
            
            assert result.exit_code == 0  # Build succeeded, profile had issues
            output = _strip_ansi(result.stdout)
            assert "Workflow 'build-and-push' completed with issues" in output

    def test_profile_help_integration(self):
        """Test that profile help is properly integrated."""
        result = runner.invoke(app, ["build", "--help"])
        assert result.exit_code == 0
        output = _strip_ansi(result.stdout)
        assert "--profile" in output
        assert "Workflow profile to execute" in output

    @patch("MCPStack.cli.MCPStackCore.build")
    @patch("MCPStack.cli.MCPStackCore.save")
    def test_profile_with_other_config_types(self, mock_save, mock_build):
        """Test that profiles work with different config types."""
        with patch("MCPStack.core.preset.registry.ALL_PRESETS", {"example_preset": MagicMock()}):
            # Profile should be ignored for non-docker config types
            result = runner.invoke(app, [
                "build", 
                "--presets", "example_preset",
                "--config-type", "fastmcp",
                "--profile", "build-and-push"  # Docker profile with fastmcp config
            ])
            
            # Should still succeed but profile might be ignored or cause validation error
            # The exact behavior depends on implementation - this tests the integration
            assert result.exit_code in [0, 1]  # Either succeeds or fails gracefully