"""Tests for build-and-push profile functionality."""

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


class TestBuildAndPushProfileFunctionality:
    """Test cases for build-and-push profile functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.cli = StackCLI()
        self.profile_manager = ProfileManager()

    def test_build_and_push_profile_exists(self):
        """Test that build-and-push profile is available."""
        profiles = self.profile_manager.list_profiles(config_type="docker")
        profile_names = [p.name for p in profiles]
        
        assert "build-and-push" in profile_names
        
        # Get detailed info about the profile
        profile_info = self.profile_manager.get_profile_info("build-and-push")
        assert profile_info is not None
        assert profile_info.name == "build-and-push"
        assert profile_info.config_type == "docker"
        assert profile_info.source == "built-in"

    def test_build_and_push_profile_stages(self):
        """Test that build-and-push profile has correct stages including push."""
        profile_info = self.profile_manager.get_profile_info("build-and-push")
        
        assert profile_info is not None
        assert len(profile_info.stages) > 0
        
        # Check that it includes expected stages
        stage_names = []
        for stage in profile_info.stages:
            if isinstance(stage, str):
                stage_names.append(stage)
            elif isinstance(stage, dict) and "stage" in stage:
                stage_names.append(stage["stage"])
        
        # Should include config generation, dockerfile generation, image building, and push
        assert any("config" in stage for stage in stage_names)
        assert any("dockerfile" in stage for stage in stage_names)
        assert any("image" in stage for stage in stage_names)
        assert any("push" in stage for stage in stage_names)

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_registry_auth')
    @patch('MCPStack.core.docker.DockerBuilder.push')
    @patch('MCPStack.core.docker.DockerBuilder.build')
    @patch('MCPStack.core.docker.DockerfileGenerator.generate')
    def test_complete_workflow_including_push(self, mock_dockerfile_gen, mock_build, mock_push, mock_registry_auth, mock_docker_check):
        """Test that build-and-push profile executes complete workflow including registry push."""
        mock_docker_check.return_value = True
        mock_registry_auth.return_value = True
        mock_dockerfile_gen.return_value = "FROM python:3.11\nCOPY . /app\nWORKDIR /app"
        mock_build.return_value = {"success": True, "image_name": "test-app:latest"}
        mock_push.return_value = {"success": True, "image_name": "test-app:latest"}
        
        result = self.runner.invoke(self.cli.app, [
            "build",
            "--profile", "build-and-push",
            "--presets", "example_preset",
            "--build-image", "test-app:latest",
            "--docker-push"
        ])
        
        # Should execute the profile
        assert "Executing workflow profile 'build-and-push'" in result.stdout
        
        # All stages should be called
        mock_dockerfile_gen.assert_called()
        mock_build.assert_called()
        mock_push.assert_called()

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_registry_auth')
    def test_stages_execute_in_correct_order(self, mock_registry_auth, mock_docker_check):
        """Test that build-and-push profile stages execute in correct order."""
        mock_docker_check.return_value = True
        mock_registry_auth.return_value = True
        
        profile_info = self.profile_manager.get_profile_info("build-and-push")
        assert profile_info is not None
        
        # Verify stage order: config -> dockerfile -> build -> push
        stage_names = []
        for stage in profile_info.stages:
            if isinstance(stage, str):
                stage_names.append(stage)
            elif isinstance(stage, dict) and "stage" in stage:
                stage_names.append(stage["stage"])
        
        # Find indices of key stages
        config_idx = next((i for i, stage in enumerate(stage_names) if "config" in stage), -1)
        dockerfile_idx = next((i for i, stage in enumerate(stage_names) if "dockerfile" in stage), -1)
        build_idx = next((i for i, stage in enumerate(stage_names) if "image" in stage and "build" in stage), -1)
        push_idx = next((i for i, stage in enumerate(stage_names) if "push" in stage), -1)
        
        # Verify order
        assert config_idx < dockerfile_idx, "Config generation should come before dockerfile generation"
        assert dockerfile_idx < build_idx, "Dockerfile generation should come before image building"
        assert build_idx < push_idx, "Image building should come before push"

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_registry_auth')
    def test_error_handling_missing_registry_auth(self, mock_registry_auth, mock_docker_check):
        """Test error handling when registry authentication is missing."""
        mock_docker_check.return_value = True
        mock_registry_auth.return_value = False
        
        validation = self.profile_manager.validate_profile("build-and-push")
        
        # Should still be valid but with missing requirements
        assert validation.is_valid is True
        assert len(validation.missing_requirements) > 0
        assert any("registry" in req.lower() for req in validation.missing_requirements)

    def test_build_and_push_profile_validation(self):
        """Test that build-and-push profile passes validation."""
        validation = self.profile_manager.validate_profile("build-and-push")
        
        assert validation.is_valid is True
        assert len(validation.errors) == 0

    def test_build_and_push_profile_requirements(self):
        """Test that build-and-push profile has correct requirements."""
        profile_info = self.profile_manager.get_profile_info("build-and-push")
        
        assert profile_info is not None
        assert "docker_client" in profile_info.requires
        assert "registry_auth" in profile_info.requires

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_registry_auth')
    def test_build_and_push_profile_cli_integration(self, mock_registry_auth, mock_docker_check):
        """Test build-and-push profile integration with CLI command."""
        mock_docker_check.return_value = True
        mock_registry_auth.return_value = True
        
        # Test that the profile is recognized and processed
        result = self.runner.invoke(self.cli.app, [
            "build",
            "--profile", "build-and-push",
            "--presets", "example_preset"
        ])
        
        # Should recognize the profile and attempt execution
        assert "Executing workflow profile 'build-and-push'" in result.stdout
        assert "Using docker config type for profile execution" in result.stdout

    @patch('MCPStack.core.workflow.ProfileOrchestrator.execute_workflow')
    def test_build_and_push_profile_execution_success(self, mock_execute):
        """Test successful execution of build-and-push profile."""
        # Mock successful execution result
        mock_result = Mock()
        mock_result.successful = True
        mock_result.results = {
            "config.generate": "completed",
            "dockerfile.generate": "completed", 
            "image.build": "completed",
            "image.push": "completed"
        }
        mock_execute.return_value = mock_result
        
        mock_stack = Mock()
        
        result = self.profile_manager.execute_profile("build-and-push", mock_stack)
        
        assert result.successful is True
        assert "config.generate" in result.results
        assert "dockerfile.generate" in result.results
        assert "image.build" in result.results
        assert "image.push" in result.results

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_registry_auth')
    @patch('MCPStack.core.docker.DockerBuilder.push')
    @patch('MCPStack.core.docker.DockerBuilder.build')
    @patch('MCPStack.core.docker.DockerfileGenerator.generate')
    def test_registry_url_parameter_handling(self, mock_dockerfile_gen, mock_build, mock_push, mock_registry_auth, mock_docker_check):
        """Test that registry URL parameter is properly handled in build-and-push profile."""
        mock_docker_check.return_value = True
        mock_registry_auth.return_value = True
        mock_dockerfile_gen.return_value = "FROM python:3.11"
        mock_build.return_value = {"success": True, "image_name": "my-registry.com/my-app:v1.0"}
        mock_push.return_value = {"success": True, "image_name": "my-registry.com/my-app:v1.0"}
        
        result = self.runner.invoke(self.cli.app, [
            "build",
            "--profile", "build-and-push",
            "--presets", "example_preset",
            "--build-image", "my-app:v1.0",
            "--docker-registry-url", "my-registry.com",
            "--docker-push"
        ])
        
        # Should execute successfully
        assert "Executing workflow profile 'build-and-push'" in result.stdout
        
        # All stages should be called
        mock_dockerfile_gen.assert_called()
        mock_build.assert_called()
        mock_push.assert_called()

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    def test_build_and_push_profile_error_handling(self, mock_docker_check):
        """Test error handling in build-and-push profile execution."""
        mock_docker_check.return_value = True
        
        # Test with invalid preset to trigger error
        result = self.runner.invoke(self.cli.app, [
            "build",
            "--profile", "build-and-push",
            "--presets", "nonexistent_preset"
        ])
        
        assert result.exit_code == 1
        assert "Unknown preset: nonexistent_preset" in result.stdout

    def test_build_and_push_includes_push_stage(self):
        """Test that build-and-push profile includes push stage (unlike build-only)."""
        profile_info = self.profile_manager.get_profile_info("build-and-push")
        
        assert profile_info is not None
        
        # Check that push stage is included
        stage_names = []
        for stage in profile_info.stages:
            if isinstance(stage, str):
                stage_names.append(stage)
            elif isinstance(stage, dict) and "stage" in stage:
                stage_names.append(stage["stage"])
        
        # Should include push stage
        assert any("push" in stage for stage in stage_names)


class TestBuildAndPushProfileComparison:
    """Test that build-and-push profile produces equivalent results to removed commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.cli = StackCLI()
        self.profile_manager = ProfileManager()

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_registry_auth')
    @patch('MCPStack.core.docker.DockerBuilder.push')
    @patch('MCPStack.core.docker.DockerBuilder.build')
    @patch('MCPStack.core.docker.DockerfileGenerator.generate')
    def test_complete_workflow_equivalence(self, mock_dockerfile_gen, mock_build, mock_push, mock_registry_auth, mock_docker_check):
        """Test that build-and-push profile workflow is equivalent to sequential removed commands."""
        mock_docker_check.return_value = True
        mock_registry_auth.return_value = True
        expected_dockerfile = "FROM python:3.11\nCOPY . /app\nWORKDIR /app\nRUN pip install -r requirements.txt"
        mock_dockerfile_gen.return_value = expected_dockerfile
        mock_build.return_value = {"success": True, "image_name": "test-app:latest"}
        mock_push.return_value = {"success": True, "image_name": "test-app:latest"}
        
        # Test profile-based complete workflow
        result = self.runner.invoke(self.cli.app, [
            "build",
            "--profile", "build-and-push",
            "--presets", "example_preset",
            "--build-image", "test-app:latest",
            "--docker-push"
        ])
        
        # Should execute successfully
        assert "Executing workflow profile 'build-and-push'" in result.stdout
        
        # All operations should be called in sequence
        mock_dockerfile_gen.assert_called()
        mock_build.assert_called()
        mock_push.assert_called()

    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_docker_available')
    @patch('MCPStack.core.workflow.ProfileOrchestrator._check_registry_auth')
    def test_profile_validation_comprehensive(self, mock_registry_auth, mock_docker_check):
        """Test comprehensive validation of build-and-push profile."""
        mock_docker_check.return_value = True
        mock_registry_auth.return_value = True
        
        validation = self.profile_manager.validate_profile("build-and-push")
        
        # Should be valid with all requirements met
        assert validation.is_valid is True
        assert len(validation.errors) == 0
        assert len(validation.missing_requirements) == 0

    def test_profile_comparison_with_build_only(self):
        """Test that build-and-push profile differs from build-only by including push stage."""
        build_only_info = self.profile_manager.get_profile_info("build-only")
        build_and_push_info = self.profile_manager.get_profile_info("build-and-push")
        
        assert build_only_info is not None
        assert build_and_push_info is not None
        
        # build-and-push should have more stages than build-only
        assert len(build_and_push_info.stages) > len(build_only_info.stages)
        
        # build-and-push should have registry_auth requirement that build-only doesn't
        assert "registry_auth" in build_and_push_info.requires
        assert "registry_auth" not in build_only_info.requires