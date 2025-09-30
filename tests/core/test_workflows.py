"""Tests for workflow profile management."""

import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from MCPStack.core.workflow import (
    WorkflowRegistry,
    ProfileOrchestrator,
    ExecutionResult,
    ProfileDefinition
)


class TestWorkflowRegistry:
    """Test WorkflowRegistry functionality."""

    def test_load_builtin_profiles(self):
        """Test loading of built-in workflow profiles."""
        registry = WorkflowRegistry()

        # Should have loaded built-in profiles
        profile_names = registry.list_profiles()
        assert "build-and-push" in profile_names
        assert "build-only" in profile_names

    def test_get_profile(self):
        """Test retrieving a specific profile."""
        registry = WorkflowRegistry()

        profile = registry.get_profile("build-and-push")
        assert isinstance(profile, ProfileDefinition)
        assert profile.name == "build-and-push"
        assert profile.config_type == "docker"
        assert "config.generate" in profile.stages
        assert "image.push" in profile.stages
        assert "docker_client" in profile.requires
        assert "registry_auth" in profile.requires

    def test_get_nonexistent_profile(self):
        """Test retrieving a profile that doesn't exist."""
        registry = WorkflowRegistry()
        assert registry.get_profile("nonexistent") is None

    def test_list_profiles_for_config_type(self):
        """Test filtering profiles by config type."""
        registry = WorkflowRegistry()
        docker_profiles = registry.list_profiles_for_config_type("docker")
        assert "build-and-push" in docker_profiles
        assert "build-only" in docker_profiles

        # Test with non-existent config type
        nonexistent_profiles = registry.list_profiles_for_config_type("kubernetes")
        assert len(nonexistent_profiles) == 0

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_discover_external_profiles(self, mock_file, mock_exists):
        """Test discovering external profiles from YAML files."""
        mock_exists.return_value = True

        # Mock YAML content
        yaml_content = """
        name: external-docker
        description: External Docker profile
        config_type: docker
        stages:
          - config.generate
          - image.build
        requires:
          - docker_client
        """

        mock_file.return_value.read.return_value = yaml_content

        # Mock the yaml.safe_load to return parsed content
        with patch('yaml.safe_load') as mock_yaml_load:
            mock_yaml_load.return_value = {
                "name": "external-docker",
                "description": "External Docker profile",
                "config_type": "docker",
                "stages": ["config.generate", "image.build"],
                "requires": ["docker_client"]
            }

            registry = WorkflowRegistry()
            profile = registry.get_profile("external-docker")

            assert profile is not None
            assert profile.name == "external-docker"
            assert profile.config_type == "docker"
            assert profile.description == "External Docker profile"


class TestExecutionResult:
    """Test ExecutionResult functionality."""

    def test_successful_execution(self):
        """Test successful execution result."""
        results = {
            "stage1": "success",
            "stage2": True,
            "stage3": {"status": "ok"}
        }
        execution = ExecutionResult(results)

        assert execution.successful
        assert execution.get_stage_result("stage1") == "success"
        assert execution.get_stage_result("stage2") is True

    def test_failed_execution(self):
        """Test failed execution result."""
        results = {
            "stage1": "success",
            "stage2": Exception("Failed"),
            "stage3": RuntimeError("Error")
        }
        execution = ExecutionResult(results)

        assert not execution.successful

    def test_get_nonexistent_stage_result(self):
        """Test getting result for a stage that doesn't exist."""
        results = {"stage1": "success"}
        execution = ExecutionResult(results)

        assert execution.get_stage_result("nonexistent") is None


class TestProfileOrchestrator:
    """Test ProfileOrchestrator functionality."""

    @pytest.fixture
    def mock_registry(self):
        """Create a mock workflow registry."""
        registry = MagicMock()
        profile = ProfileDefinition(
            name="test-profile",
            description="Test profile",
            config_type="docker",
            stages=["config.generate", "image.build"],
            requires=["docker_client"]
        )
        registry.get_profile.return_value = profile
        return registry

    @patch('subprocess.run')
    def test_validate_requirements_success(self, mock_subprocess, mock_registry):
        """Test successful requirement validation."""
        mock_subprocess.return_value = MagicMock(returncode=0)

        orchestrator = ProfileOrchestrator()
        orchestrator.registry = mock_registry

        profile = ProfileDefinition(
            name="test",
            description="Test",
            config_type="docker",
            stages=[],
            requires=["docker_client"]
        )

        # Should not raise exception
        orchestrator._validate_requirements(profile)

    def test_validate_requirements_docker_missing(self, mock_registry):
        """Test validation when Docker is not available."""
        orchestrator = ProfileOrchestrator()
        orchestrator.registry = mock_registry

        profile = ProfileDefinition(
            name="test",
            description="Test",
            config_type="docker",
            stages=[],
            requires=["docker_client"]
        )

        with patch.object(orchestrator, '_check_docker_available', return_value=False):
            with pytest.raises(RuntimeError, match="Docker client is required"):
                orchestrator._validate_requirements(profile)

    @pytest.fixture
    def mock_stack_context(self):
        """Create a mock stack context."""
        stack = MagicMock()
        stack.build.return_value = {"mcpServers": {"test": {"command": "docker"}}}
        return stack

    def test_execute_config_stage(self, mock_stack_context, mock_registry):
        """Test executing a config stage."""
        orchestrator = ProfileOrchestrator()
        orchestrator.registry = mock_registry

        result = orchestrator._execute_stage("config", "generate", mock_stack_context, {})
        mock_stack_context.build.assert_called_once()

    def test_execute_dockerfile_stage(self, mock_stack_context, mock_registry):
        """Test executing a dockerfile stage."""
        orchestrator = ProfileOrchestrator()
        orchestrator.registry = mock_registry

        with patch('MCPStack.core.docker.dockerfile_generator.DockerfileGenerator.save') as mock_save:
            mock_save.return_value = "/path/to/dockerfile"

            result = orchestrator._execute_stage("dockerfile", "generate", mock_stack_context, 
                                               {"dockerfile_path": "Dockerfile"})

            mock_save.assert_called_once()

    def test_execute_image_stage_build(self, mock_registry):
        """Test executing an image build stage."""
        orchestrator = ProfileOrchestrator()

        with patch('MCPStack.core.docker.docker_builder.DockerBuilder.build') as mock_build:
            mock_build.return_value = "Successfully built image"

            result = orchestrator._execute_stage("image", "build", None, {},
                                               image_name="test:latest",
                                               build_args={"KEY": "VALUE"})

            mock_build.assert_called_once_with(
                dockerfile_path=Path("Dockerfile"),
                image_name="test:latest",
                build_args={"KEY": "VALUE"}
            )

    def test_execute_image_stage_push(self, mock_registry):
        """Test executing an image push stage."""
        orchestrator = ProfileOrchestrator()

        with patch('MCPStack.core.docker.docker_builder.DockerBuilder.push') as mock_push:
            mock_push.return_value = "Successfully pushed"

            result = orchestrator._execute_stage("image", "push", None, {},
                                               image_name="test:latest",
                                               registry_url="registry.io")

            mock_push.assert_called_once_with(
                image_name="test:latest",
                registry_url="registry.io"
            )

    def test_execute_unknown_component(self, mock_registry):
        """Test executing a stage with unknown component."""
        orchestrator = ProfileOrchestrator()

        with pytest.raises(ValueError, match="Unknown workflow component: unknown"):
            orchestrator._execute_stage("unknown", "operation", None, {})

    def test_docker_availability_check(self):
        """Test checking Docker availability."""
        orchestrator = ProfileOrchestrator()

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert orchestrator._check_docker_available()

            mock_run.return_value = MagicMock(returncode=1)
            assert not orchestrator._check_docker_available()

    @patch('subprocess.run')
    def test_docker_availability_check_exception(self, mock_run):
        """Test Docker availability check when subprocess raises exception."""
        orchestrator = ProfileOrchestrator()

        mock_run.side_effect = Exception("Command not found")

        assert not orchestrator._check_docker_available()


class TestProfileIntegration:
    """Integration tests for workflow profiles."""

    def test_full_workflow_execution(self):
        """Test executing a complete workflow profile."""
        orchestrator = ProfileOrchestrator()

        mock_stack = MagicMock()
        mock_stack.build.return_value = {"mcpServers": {"test": {"command": "docker"}}}

        with patch.object(orchestrator, '_validate_requirements'):
            with patch.object(orchestrator, '_execute_stage') as mock_execute:
                mock_execute.side_effect = ["config_ok", "dockerfile_ok", "build_ok", "push_ok"]

                result = orchestrator.execute_workflow(
                    "build-and-push",
                    mock_stack,
                    image_name="test:latest"
                )

                assert result.successful
                assert mock_execute.call_count == 4  # All stages executed

    def test_workflow_execution_with_failure(self):
        """Test workflow execution when a stage fails."""
        orchestrator = ProfileOrchestrator()

        mock_stack = MagicMock()
        mock_stack.build.return_value = {"mcpServers": {"test": {"command": "docker"}}}

        with patch.object(orchestrator, '_validate_requirements'):
            with patch.object(orchestrator, '_execute_stage') as mock_execute:
                mock_execute.side_effect = ["config_ok", Exception("Docker failed")]

                result = orchestrator.execute_workflow(
                    "build-and-push",
                    mock_stack,
                    image_name="test:latest"
                )

                assert not result.successful
                assert isinstance(result.get_stage_result("dockerfile.generate"), Exception)

    def test_invalid_profile_execution(self):
        """Test executing a profile that doesn't exist."""
        orchestrator = ProfileOrchestrator()

        with pytest.raises(ValueError, match="Workflow profile 'nonexistent' not found"):
            orchestrator.execute_workflow("nonexistent", None)
