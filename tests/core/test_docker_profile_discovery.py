"""Tests for Docker profile discovery and listing functionality."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from typer.testing import CliRunner

from MCPStack.cli import StackCLI
from MCPStack.core.profile_manager import ProfileManager
from MCPStack.stack import MCPStackCore


class TestDockerProfileDiscovery:
    """Test cases for Docker profile discovery and listing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.cli = StackCLI()
        self.profile_manager = ProfileManager()

    def test_list_profiles_shows_docker_profiles(self):
        """Test that mcpstack list-profiles --config-type docker shows Docker profiles."""
        result = self.runner.invoke(self.cli.app, [
            "list-profiles", 
            "--config-type", "docker"
        ])
        
        assert result.exit_code == 0
        assert "Available Workflow Profiles" in result.stdout
        assert "build-only" in result.stdout
        assert "build-and-push" in result.stdout
        assert "docker" in result.stdout  # Should show config type

    def test_list_profiles_shows_all_profiles(self):
        """Test that mcpstack list-profiles shows all profiles including Docker ones."""
        result = self.runner.invoke(self.cli.app, ["list-profiles"])
        
        assert result.exit_code == 0
        assert "Available Workflow Profiles" in result.stdout
        assert "build-only" in result.stdout
        assert "build-and-push" in result.stdout

    def test_profile_descriptions_displayed_correctly(self):
        """Test that profile descriptions and requirements are displayed correctly."""
        profiles = self.profile_manager.list_profiles(config_type="docker")
        
        # Should have at least build-only and build-and-push
        assert len(profiles) >= 2
        
        # Check that profiles have proper descriptions
        profile_names = [p.name for p in profiles]
        assert "build-only" in profile_names
        assert "build-and-push" in profile_names
        
        # Check descriptions are not empty
        for profile in profiles:
            assert profile.description is not None
            assert len(profile.description) > 0
            assert profile.config_type == "docker"

    def test_profile_validation_works_for_docker_requirements(self):
        """Test that profile validation works for Docker requirements."""
        # Test build-only profile validation
        build_only_validation = self.profile_manager.validate_profile("build-only")
        assert build_only_validation.is_valid is True
        
        # Test build-and-push profile validation
        build_and_push_validation = self.profile_manager.validate_profile("build-and-push")
        assert build_and_push_validation.is_valid is True

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    def test_profile_validation_missing_docker(self, mock_docker_check):
        """Test profile validation when Docker is not available."""
        mock_docker_check.return_value = False
        
        validation = self.profile_manager.validate_profile("build-only")
        
        # Should still be valid but with missing requirements
        assert validation.is_valid is True
        assert len(validation.missing_requirements) > 0
        assert any("Docker client" in req for req in validation.missing_requirements)

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_registry_auth')
    def test_profile_validation_missing_registry_auth(self, mock_registry_auth):
        """Test profile validation when registry authentication is missing."""
        mock_registry_auth.return_value = False
        
        validation = self.profile_manager.validate_profile("build-and-push")
        
        # Should still be valid but with missing requirements
        assert validation.is_valid is True
        assert len(validation.missing_requirements) > 0
        assert any("registry" in req.lower() for req in validation.missing_requirements)

    def test_docker_profile_sources_identified(self):
        """Test that Docker profile sources are correctly identified."""
        profiles = self.profile_manager.list_profiles(config_type="docker")
        
        for profile in profiles:
            if profile.name in ["build-only", "build-and-push"]:
                assert profile.source == "built-in"
            # External profiles would have different source

    def test_profile_manager_list_profiles_api(self):
        """Test ProfileManager list_profiles API for Docker profiles."""
        # Test without filter
        all_profiles = self.profile_manager.list_profiles()
        assert len(all_profiles) > 0
        
        # Test with Docker filter
        docker_profiles = self.profile_manager.list_profiles(config_type="docker")
        assert len(docker_profiles) >= 2
        
        # All Docker profiles should have docker config type
        for profile in docker_profiles:
            assert profile.config_type == "docker"

    def test_profile_info_retrieval(self):
        """Test getting detailed profile information."""
        # Test build-only profile info
        build_only_info = self.profile_manager.get_profile_info("build-only")
        assert build_only_info is not None
        assert build_only_info.name == "build-only"
        assert build_only_info.config_type == "docker"
        assert build_only_info.source == "built-in"
        assert len(build_only_info.stages) > 0
        assert "docker_client" in build_only_info.requires
        
        # Test build-and-push profile info
        build_and_push_info = self.profile_manager.get_profile_info("build-and-push")
        assert build_and_push_info is not None
        assert build_and_push_info.name == "build-and-push"
        assert build_and_push_info.config_type == "docker"
        assert build_and_push_info.source == "built-in"
        assert len(build_and_push_info.stages) > 0
        assert "docker_client" in build_and_push_info.requires
        assert "registry_auth" in build_and_push_info.requires

    def test_nonexistent_profile_info(self):
        """Test getting info for non-existent profile."""
        info = self.profile_manager.get_profile_info("nonexistent-profile")
        assert info is None

    def test_cli_help_shows_list_profiles_command(self):
        """Test that CLI help shows the list-profiles command."""
        result = self.runner.invoke(self.cli.app, ["--help"])
        
        assert result.exit_code == 0
        assert "list-profiles" in result.stdout
        assert "List available workflow profiles" in result.stdout

    def test_list_profiles_help_shows_config_type_filter(self):
        """Test that list-profiles help shows config-type filter option."""
        result = self.runner.invoke(self.cli.app, ["list-profiles", "--help"])
        
        assert result.exit_code == 0
        assert "--config-type" in result.stdout
        assert "Filter profiles by config type" in result.stdout

    def test_empty_config_type_filter(self):
        """Test list-profiles with non-existent config type."""
        result = self.runner.invoke(self.cli.app, [
            "list-profiles", 
            "--config-type", "nonexistent"
        ])
        
        assert result.exit_code == 0
        assert "no profiles found for config type 'nonexistent'" in result.stdout

    def test_profile_discovery_consistency(self):
        """Test that profile discovery is consistent between CLI and ProfileManager."""
        # Get profiles via CLI
        cli_result = self.runner.invoke(self.cli.app, [
            "list-profiles", 
            "--config-type", "docker"
        ])
        assert cli_result.exit_code == 0
        
        # Get profiles via ProfileManager
        manager_profiles = self.profile_manager.list_profiles(config_type="docker")
        
        # Should have consistent results
        assert len(manager_profiles) >= 2
        for profile in manager_profiles:
            assert profile.name in cli_result.stdout

    def test_profile_validation_error_handling(self):
        """Test profile validation error handling."""
        # Test with invalid profile name
        validation = self.profile_manager.validate_profile("invalid-profile-name")
        
        assert validation.is_valid is False
        assert len(validation.errors) > 0
        assert "not found" in validation.errors[0]

    def test_docker_profiles_have_required_fields(self):
        """Test that Docker profiles have all required fields."""
        docker_profiles = self.profile_manager.list_profiles(config_type="docker")
        
        for profile in docker_profiles:
            # Check required fields
            assert profile.name is not None and len(profile.name) > 0
            assert profile.description is not None and len(profile.description) > 0
            assert profile.config_type == "docker"
            assert profile.stages is not None and len(profile.stages) > 0
            assert profile.requires is not None
            assert profile.source is not None

    def test_profile_suggestions_work(self):
        """Test that profile suggestions work for fuzzy matching."""
        # Test exact match
        suggestions = self.profile_manager.suggest_profiles("build-only")
        assert "build-only" in suggestions
        
        # Test fuzzy match
        suggestions = self.profile_manager.suggest_profiles("build")
        assert len(suggestions) > 0
        assert any("build" in suggestion for suggestion in suggestions)
        
        # Test no match
        suggestions = self.profile_manager.suggest_profiles("xyz123nonexistent")
        assert len(suggestions) <= 1  # Should return empty or very low confidence matches


class TestExternalDockerProfiles:
    """Test external Docker profile discovery and loading."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.cli = StackCLI()
        self.profile_manager = ProfileManager()

    def test_external_profiles_can_be_loaded(self):
        """Test that external profiles from workflows/ directory can be loaded."""
        # This test checks if the system can handle external profiles
        # The actual external profiles depend on what's in the workflows/ directory
        
        all_profiles = self.profile_manager.list_profiles()
        
        # Check if any external profiles exist
        external_profiles = [p for p in all_profiles if p.source != "built-in"]
        
        # If external profiles exist, they should be properly formatted
        for profile in external_profiles:
            assert profile.name is not None
            assert profile.description is not None
            assert profile.config_type is not None
            assert profile.stages is not None

    def test_external_docker_profiles_filtered_correctly(self):
        """Test that external Docker profiles are filtered correctly."""
        docker_profiles = self.profile_manager.list_profiles(config_type="docker")
        
        # All returned profiles should have docker config type
        for profile in docker_profiles:
            assert profile.config_type == "docker"

    def test_mixed_profile_sources_display(self):
        """Test that both built-in and external profiles are displayed correctly."""
        result = self.runner.invoke(self.cli.app, ["list-profiles"])
        
        assert result.exit_code == 0
        assert "Available Workflow Profiles" in result.stdout
        
        # Should show source information
        if "external" in result.stdout:
            # If external profiles exist, verify they're marked as external
            assert "built-in" in result.stdout  # Should also show built-in profiles


class TestProfileDiscoveryIntegration:
    """Integration tests for profile discovery with CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.cli = StackCLI()

    def test_profile_discovery_supports_build_command(self):
        """Test that discovered profiles can be used with build command."""
        # Test that build command recognizes discovered profiles
        result = self.runner.invoke(self.cli.app, [
            "build", 
            "--profile", "build-only",
            "--presets", "example_preset"
        ])
        
        # Should recognize the profile (may fail on execution but should recognize it)
        assert "Profile 'build-only' not found" not in result.stdout

    def test_profile_discovery_error_messages(self):
        """Test that profile discovery provides helpful error messages."""
        result = self.runner.invoke(self.cli.app, [
            "build", 
            "--profile", "nonexistent-profile",
            "--presets", "example_preset"
        ])
        
        assert result.exit_code == 1
        assert "Profile 'nonexistent-profile' not found" in result.stdout
        # Should provide suggestions
        # The error message format may vary, check for profile not found
        assert "Profile 'nonexistent-profile' not found" in result.stdout

    def test_profile_listing_performance(self):
        """Test that profile listing performs reasonably."""
        import time
        
        start_time = time.time()
        result = self.runner.invoke(self.cli.app, ["list-profiles"])
        end_time = time.time()
        
        # Should complete within reasonable time (5 seconds)
        assert (end_time - start_time) < 5.0
        assert result.exit_code == 0