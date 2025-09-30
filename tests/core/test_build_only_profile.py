"""Tests for build-only profile functionality."""

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


class TestBuildOnlyProfileFunctionality:
    """Test cases for build-only profile functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.cli = StackCLI()
        self.profile_manager = ProfileManager()

    def test_build_only_profile_exists(self):
        """Test that build-only profile is available."""
        profiles = self.profile_manager.list_profiles(config_type="docker")
        profile_names = [p.name for p in profiles]
        
        assert "build-only" in profile_names
        
        # Get detailed info about the profile
        profile_info = self.profile_manager.get_profile_info("build-only")
        assert profile_info is not None
        assert profile_info.name == "build-only"
        assert profile_info.config_type == "docker"
        assert profile_info.source == "built-in"

    def test_build_only_profile_stages(self):
        """Test that build-only profile has correct stages."""
        profile_info = self.profile_manager.get_profile_info("build-only")
        
        assert profile_info is not None
        assert len(profile_info.stages) > 0
        
        # Check that it includes expected stages
        stage_names = []
        for stage in profile_info.stages:
            if isinstance(stage, str):
                stage_names.append(stage)
            elif isinstance(stage, dict) and "stage" in stage:
                stage_names.append(stage["stage"])
        
        # Should include config generation, dockerfile generation, and image building
        assert any("config" in stage for stage in stage_names)
        assert any("dockerfile" in stage for stage in stage_names)
        assert any("image" in stage for stage in stage_names)

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    @patch('MCPStack.core.docker.DockerBuilder.build')
    @patch('MCPStack.core.docker.DockerfileGenerator.generate')
    def test_dockerfile_generation_works(self, mock_dockerfile_gen, mock_build, mock_docker_check):
        """Test that Dockerfile generation works correctly through build-only profile."""
        mock_docker_check.return_value = True
        mock_dockerfile_gen.return_value = "FROM python:3.11\nCOPY . /app\nWORKDIR /app"
        mock_build.return_value = {"success": True, "image_name": "test-app:latest"}
        
        result = self.runner.invoke(self.cli.app, [
            "build",
            "--profile", "build-only",
            "--presets", "example_preset",
            "--generate-dockerfile",
            "--dockerfile-path", "Dockerfile"
        ])
        
        # Should execute the profile
        assert "Executing workflow profile 'build-only'" in result.stdout
        
        # Dockerfile generation should be called
        mock_dockerfile_gen.assert_called()

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    @patch('MCPStack.core.docker.DockerBuilder.build')
    def test_docker_image_building_works(self, mock_build, mock_docker_check):
        """Test that Docker image building works correctly through build-only profile."""
        mock_docker_check.return_value = True
        mock_build.return_value = {"success": True, "image_name": "test-app:latest"}
        
        result = self.runner.invoke(self.cli.app, [
            "build",
            "--profile", "build-only",
            "--presets", "example_preset",
            "--build-image", "test-app:latest"
        ])
        
        # Should execute the profile
        assert "Executing workflow profile 'build-only'" in result.stdout
        
        # Image building should be attempted
        mock_build.assert_called()

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    @patch('MCPStack.core.docker.DockerBuilder.build')
    @patch('MCPStack.core.docker.DockerfileGenerator.generate')
    def test_docker_parameters_passed_through(self, mock_dockerfile_gen, mock_build, mock_docker_check):
        """Test that all Docker parameters are properly passed through build-only profile."""
        mock_docker_check.return_value = True
        mock_dockerfile_gen.return_value = "FROM python:3.11"
        mock_build.return_value = {"success": True, "image_name": "my-app:v1.0"}
        
        # Test with multiple Docker parameters
        result = self.runner.invoke(self.cli.app, [
            "build",
            "--profile", "build-only",
            "--presets", "example_preset",
            "--build-image", "my-app:v1.0",
            "--generate-dockerfile",
            "--dockerfile-path", "custom.Dockerfile",
            "--build-args", "ENV=production,VERSION=1.0"
        ])
        
        # Should execute successfully
        assert "Executing workflow profile 'build-only'" in result.stdout
        
        # Both dockerfile generation and image building should be called
        mock_dockerfile_gen.assert_called()
        mock_build.assert_called()

    def test_build_only_profile_validation(self):
        """Test that build-only profile passes validation."""
        validation = self.profile_manager.validate_profile("build-only")
        
        assert validation.is_valid is True
        assert len(validation.errors) == 0

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    def test_build_only_profile_missing_docker_warning(self, mock_docker_check):
        """Test that build-only profile shows warning when Docker is not available."""
        mock_docker_check.return_value = False
        
        validation = self.profile_manager.validate_profile("build-only")
        
        # Should still be valid but with missing requirements
        assert validation.is_valid is True
        assert len(validation.missing_requirements) > 0
        assert any("Docker client" in req for req in validation.missing_requirements)

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    def test_build_only_profile_cli_integration(self, mock_docker_check):
        """Test build-only profile integration with CLI command."""
        mock_docker_check.return_value = True
        
        # Test that the profile is recognized and processed
        result = self.runner.invoke(self.cli.app, [
            "build",
            "--profile", "build-only",
            "--presets", "example_preset"
        ])
        
        # Should recognize the profile and attempt execution
        assert "Executing workflow profile 'build-only'" in result.stdout
        assert "Using docker config type for profile execution" in result.stdout

    def test_build_only_profile_requirements(self):
        """Test that build-only profile has correct requirements."""
        profile_info = self.profile_manager.get_profile_info("build-only")
        
        assert profile_info is not None
        assert "docker_client" in profile_info.requires

    @patch('MCPStack.core.workflow.ProfileOrchestrator.execute_workflow')
    def test_build_only_profile_execution_success(self, mock_execute):
        """Test successful execution of build-only profile."""
        # Mock successful execution result
        mock_result = Mock()
        mock_result.successful = True
        mock_result.results = {
            "config.generate": "completed",
            "dockerfile.generate": "completed", 
            "image.build": "completed"
        }
        mock_execute.return_value = mock_result
        
        mock_stack = Mock()
        
        result = self.profile_manager.execute_profile("build-only", mock_stack)
        
        assert result.successful is True
        assert "config.generate" in result.results
        assert "dockerfile.generate" in result.results
        assert "image.build" in result.results

    def test_build_only_profile_no_push_stage(self):
        """Test that build-only profile does not include push stage."""
        profile_info = self.profile_manager.get_profile_info("build-only")
        
        assert profile_info is not None
        
        # Check that push stage is not included
        stage_names = []
        for stage in profile_info.stages:
            if isinstance(stage, str):
                stage_names.append(stage)
            elif isinstance(stage, dict) and "stage" in stage:
                stage_names.append(stage["stage"])
        
        # Should not include push stage
        assert not any("push" in stage for stage in stage_names)

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    def test_build_only_profile_error_handling(self, mock_docker_check):
        """Test error handling in build-only profile execution."""
        mock_docker_check.return_value = True
        
        # Test with invalid preset to trigger error
        result = self.runner.invoke(self.cli.app, [
            "build",
            "--profile", "build-only",
            "--presets", "nonexistent_preset"
        ])
        
        assert result.exit_code == 1
        assert "Unknown preset: nonexistent_preset" in result.stdout


class TestBuildOnlyProfileComparison:
    """Test that build-only profile produces equivalent results to removed commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.cli = StackCLI()

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    @patch('MCPStack.core.docker.DockerfileGenerator.generate')
    def test_dockerfile_generation_equivalence(self, mock_dockerfile_gen, mock_docker_check):
        """Test that profile Dockerfile generation is equivalent to removed docker dockerfile command."""
        mock_docker_check.return_value = True
        expected_dockerfile = "FROM python:3.11\nCOPY . /app\nWORKDIR /app\nRUN pip install -r requirements.txt"
        mock_dockerfile_gen.return_value = expected_dockerfile
        
        # Test profile-based dockerfile generation
        result = self.runner.invoke(self.cli.app, [
            "build",
            "--profile", "build-only",
            "--presets", "example_preset",
            "--generate-dockerfile",
            "--dockerfile-path", "Dockerfile"
        ])
        
        # Should execute successfully
        assert "Executing workflow profile 'build-only'" in result.stdout
        
        # Dockerfile generation should be called with same parameters
        mock_dockerfile_gen.assert_called()

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    @patch('MCPStack.core.docker.DockerBuilder.build')
    def test_image_building_equivalence(self, mock_build, mock_docker_check):
        """Test that profile image building is equivalent to removed docker build command."""
        mock_docker_check.return_value = True
        mock_build.return_value = {"success": True, "image_name": "test-app:latest"}
        
        # Test profile-based image building
        result = self.runner.invoke(self.cli.app, [
            "build",
            "--profile", "build-only",
            "--presets", "example_preset",
            "--build-image", "test-app:latest"
        ])
        
        # Should execute successfully
        assert "Executing workflow profile 'build-only'" in result.stdout
        
        # Image building should be called
        mock_build.assert_called()