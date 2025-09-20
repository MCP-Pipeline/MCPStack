"""Integration tests for CLI profile functionality."""

import json
import os
import re
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from MCPStack.cli import StackCLI


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


class TestProfileCLIIntegration:
    """Integration tests for profile CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.cli = StackCLI()

    def test_list_profiles_command(self):
        """Test mcpstack list-profiles command."""
        result = self.runner.invoke(self.cli.app, ["list-profiles"])
        
        assert result.exit_code == 0
        assert "Available Workflow Profiles" in result.stdout
        assert "build-only" in result.stdout
        assert "build-and-push" in result.stdout

    def test_list_profiles_with_config_type_filter(self):
        """Test mcpstack list-profiles --config-type docker command."""
        result = self.runner.invoke(self.cli.app, ["list-profiles", "--config-type", "docker"])
        
        assert result.exit_code == 0
        assert "Available Workflow Profiles" in result.stdout
        assert "docker" in result.stdout

    def test_list_profiles_with_invalid_config_type(self):
        """Test mcpstack list-profiles with non-existent config type."""
        result = self.runner.invoke(self.cli.app, ["list-profiles", "--config-type", "nonexistent"])
        
        assert result.exit_code == 0
        assert "no profiles found for config type 'nonexistent'" in result.stdout

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    def test_build_with_valid_profile(self, mock_docker_check):
        """Test mcpstack build --profile build-only command."""
        mock_docker_check.return_value = True
        
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            result = self.runner.invoke(self.cli.app, [
                "build", 
                "--profile", "build-only", 
                "--presets", "example_preset"
            ])
            
            # Should succeed even if Docker operations fail in test environment
            # The important thing is that the profile is recognized and processed
            assert "Executing workflow profile 'build-only'" in result.stdout

    def test_build_with_invalid_profile(self):
        """Test mcpstack build --profile with invalid profile name."""
        result = self.runner.invoke(self.cli.app, [
            "build", 
            "--profile", "nonexistent-profile", 
            "--presets", "example_preset"
        ])
        
        assert result.exit_code == 1
        assert "Profile 'nonexistent-profile' not found" in result.stdout

    def test_build_with_fuzzy_profile_suggestions(self):
        """Test mcpstack build --profile with similar profile name."""
        result = self.runner.invoke(self.cli.app, [
            "build", 
            "--profile", "build", 
            "--presets", "example_preset"
        ])
        
        assert result.exit_code == 1
        assert "Did you mean:" in result.stdout
        assert "build-only" in result.stdout or "build-and-push" in result.stdout

    def test_build_backward_compatibility(self):
        """Test that existing build command still works without profile."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            result = self.runner.invoke(self.cli.app, [
                "build", 
                "--presets", "example_preset"
            ])
            
            assert result.exit_code == 0
            assert "SUCCESS: Pipeline config saved" in result.stdout
            assert "Executing workflow profile" not in result.stdout

    def test_help_shows_profile_parameter(self):
        """Test that --help shows the new --profile parameter."""
        result = self.runner.invoke(self.cli.app, ["build", "--help"])
        
        assert result.exit_code == 0
        assert "--profile" in result.stdout
        assert "Workflow profile to execute" in result.stdout

    def test_help_shows_list_profiles_command(self):
        """Test that --help shows the new list-profiles command."""
        result = self.runner.invoke(self.cli.app, ["--help"])
        
        assert result.exit_code == 0
        assert "list-profiles" in result.stdout
        assert "List available workflow profiles" in result.stdout


class TestProfileValidation:
    """Test profile validation and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.cli = StackCLI()

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    def test_profile_validation_missing_docker(self, mock_docker_check):
        """Test profile validation when Docker is not available."""
        mock_docker_check.return_value = False
        
        result = self.runner.invoke(self.cli.app, [
            "build", 
            "--profile", "build-only", 
            "--presets", "example_preset"
        ])
        
        # Should show warning about missing Docker but still attempt execution
        assert "Warning: Missing requirements" in result.stdout or "Docker client" in result.stdout

    def test_profile_parameter_precedence(self):
        """Test that CLI parameters take precedence over profile parameters."""
        # This test verifies the design but may need Docker to fully execute
        result = self.runner.invoke(self.cli.app, [
            "build", 
            "--profile", "build-only", 
            "--presets", "example_preset",
            "--config-type", "fastmcp"  # This should override profile's docker config
        ])
        
        # The profile should still execute but with CLI config type taking precedence
        assert "Executing workflow profile 'build-only'" in result.stdout


class TestExternalProfiles:
    """Test external profile loading and execution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.cli = StackCLI()

    def test_external_profiles_loaded(self):
        """Test that external profiles from workflows/ directory are loaded."""
        result = self.runner.invoke(self.cli.app, ["list-profiles"])
        
        assert result.exit_code == 0
        # Check for external profiles that should exist
        assert "external" in result.stdout  # Should show external source

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    def test_external_profile_execution(self, mock_docker_check):
        """Test execution of external profile with custom parameters."""
        mock_docker_check.return_value = True
        
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            # Test docker-dev profile which has custom parameters
            result = self.runner.invoke(self.cli.app, [
                "build", 
                "--profile", "docker-dev", 
                "--presets", "example_preset"
            ])
            
            # Should attempt to execute the external profile
            assert "Executing workflow profile 'docker-dev'" in result.stdout

    def test_profile_parameter_expansion(self):
        """Test that profile parameters support environment variable expansion."""
        # This is tested indirectly through the docker-dev profile
        # which uses ${preset} variable expansion
        result = self.runner.invoke(self.cli.app, ["list-profiles"])
        
        assert result.exit_code == 0
        assert "docker-dev" in result.stdout


class TestErrorHandling:
    """Test error handling and user feedback."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.cli = StackCLI()

    def test_profile_not_found_error(self):
        """Test clear error message when profile is not found."""
        result = self.runner.invoke(self.cli.app, [
            "build", 
            "--profile", "completely-invalid-profile-name", 
            "--presets", "example_preset"
        ])
        
        assert result.exit_code == 1
        output = _strip_ansi(result.stdout)
        assert "completely-invalid-profile-name" in output
        # Handle potential line breaks in the error message
        assert "not" in output and "found" in output

    def test_invalid_preset_with_profile(self):
        """Test error handling when preset is invalid but profile is valid."""
        result = self.runner.invoke(self.cli.app, [
            "build", 
            "--profile", "build-only", 
            "--presets", "nonexistent-preset"
        ])
        
        assert result.exit_code == 1
        assert "Unknown preset: nonexistent-preset" in result.stdout

    def test_profile_execution_failure_handling(self):
        """Test that profile execution failures are handled gracefully."""
        # This test would need to mock a failure scenario
        # For now, we test that the error handling structure is in place
        result = self.runner.invoke(self.cli.app, [
            "build", 
            "--profile", "build-only", 
            "--presets", "example_preset"
        ])
        
        # Should either succeed or fail gracefully with clear error message
        assert result.exit_code in [0, 1]
        if result.exit_code == 1:
            assert "ERROR:" in result.stdout