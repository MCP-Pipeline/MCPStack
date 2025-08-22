"""Additional tests for Docker builder to improve coverage."""
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from MCPStack.core.docker.docker_builder import DockerBuilder
from MCPStack.core.utils.exceptions import MCPStackValidationError


class TestDockerBuilderCoverage:
    """Additional tests for Docker builder to improve coverage."""

    def test_build_with_nonexistent_dockerfile(self):
        """Test build with non-existent Dockerfile."""
        with pytest.raises(MCPStackValidationError, match="Dockerfile not found"):
            DockerBuilder.build(
                dockerfile_path=Path("/nonexistent/Dockerfile"),
                image_name="test:latest"
            )

    @patch('subprocess.run')
    def test_build_with_build_args(self, mock_run):
        """Test build with build arguments."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Successfully built abc123"
        mock_run.return_value.stderr = ""

        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile_path = Path(tmpdir) / "Dockerfile"
            dockerfile_path.write_text("FROM python:3.13-slim\n")

            build_args = {"ARG1": "value1", "ARG2": "value2"}
            result = DockerBuilder.build(
                dockerfile_path=dockerfile_path,
                image_name="test:latest",
                build_args=build_args,
                no_cache=True,
                quiet=True
            )

            assert result["success"] is True
            mock_run.assert_called_once()

            call_args = mock_run.call_args[0][0]
            assert "--build-arg" in call_args
            assert "ARG1=value1" in call_args
            assert "ARG2=value2" in call_args
            assert "--no-cache" in call_args
            assert "--quiet" in call_args

    @patch('subprocess.run')
    def test_build_with_custom_context(self, mock_run):
        """Test build with custom context path."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Successfully built abc123"
        mock_run.return_value.stderr = ""

        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile_path = Path(tmpdir) / "Dockerfile"
            dockerfile_path.write_text("FROM python:3.13-slim\n")
            context_path = "/custom/context"

            result = DockerBuilder.build(
                dockerfile_path=dockerfile_path,
                image_name="test:latest",
                context_path=context_path
            )

            assert result["success"] is True
            call_args = mock_run.call_args[0][0]
            assert call_args[-1] == context_path

    @patch('subprocess.run')
    def test_build_subprocess_error(self, mock_run):
        """Test build with subprocess error."""
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["docker", "build"]
        )
        error.stdout = "stdout output"
        error.stderr = "build failed"
        mock_run.side_effect = error

        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile_path = Path(tmpdir) / "Dockerfile"
            dockerfile_path.write_text("FROM python:3.13-slim\n")

            with pytest.raises(MCPStackValidationError, match="Docker build failed"):
                DockerBuilder.build(
                    dockerfile_path=dockerfile_path,
                    image_name="test:latest"
                )

    @patch('subprocess.run')
    def test_build_docker_not_found(self, mock_run):
        """Test build when Docker command is not found."""
        mock_run.side_effect = FileNotFoundError()

        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile_path = Path(tmpdir) / "Dockerfile"
            dockerfile_path.write_text("FROM python:3.13-slim\n")

            with pytest.raises(MCPStackValidationError, match="Docker command not found"):
                DockerBuilder.build(
                    dockerfile_path=dockerfile_path,
                    image_name="test:latest"
                )

    @patch('subprocess.run')
    def test_push_success(self, mock_run):
        """Test successful Docker push."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Successfully pushed"
        mock_run.return_value.stderr = ""

        result = DockerBuilder.push(image_name="test:latest")

        assert result["success"] is True
        assert result["image_name"] == "test:latest"
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "docker" in call_args
        assert "push" in call_args
        assert "test:latest" in call_args

    @patch('subprocess.run')
    def test_push_with_registry(self, mock_run):
        """Test push with registry URL."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Successfully pushed"
        mock_run.return_value.stderr = ""

        result = DockerBuilder.push(
            image_name="myimage:latest",
            registry_url="registry.example.com"
        )

        assert result["success"] is True
        assert result["image_name"] == "registry.example.com/myimage:latest"
        call_args = mock_run.call_args[0][0]
        assert "registry.example.com/myimage:latest" in call_args

    @patch('subprocess.run')
    def test_push_failure(self, mock_run):
        """Test Docker push failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["docker", "push"],
            stderr="push failed"
        )

        with pytest.raises(MCPStackValidationError, match="Docker push failed"):
            DockerBuilder.push(image_name="test:latest")

    @patch('subprocess.run')
    def test_push_docker_not_found(self, mock_run):
        """Test push when Docker command is not found."""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(MCPStackValidationError, match="Docker command not found"):
            DockerBuilder.push(image_name="test:latest")

    @patch('subprocess.run')
    def test_tag_success(self, mock_run):
        """Test successful Docker tag."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""

        result = DockerBuilder.tag(
            source_image="test:latest",
            target_image="test:v1.0"
        )

        assert result["success"] is True
        assert result["source_image"] == "test:latest"
        assert result["target_image"] == "test:v1.0"
        call_args = mock_run.call_args[0][0]
        assert "docker" in call_args
        assert "tag" in call_args
        assert "test:latest" in call_args
        assert "test:v1.0" in call_args

    @patch('subprocess.run')
    def test_tag_failure(self, mock_run):
        """Test Docker tag failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["docker", "tag"],
            stderr="tag failed"
        )

        with pytest.raises(MCPStackValidationError, match="Docker tag failed"):
            DockerBuilder.tag(
                source_image="test:latest",
                target_image="test:v1.0"
            )

    @patch('subprocess.run')
    def test_tag_docker_not_found(self, mock_run):
        """Test tag when Docker command is not found."""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(MCPStackValidationError, match="Docker command not found"):
            DockerBuilder.tag(
                source_image="test:latest",
                target_image="test:v1.0"
            )

    @patch('subprocess.run')
    def test_list_images_success(self, mock_run):
        """Test successful Docker images list."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"Repository":"test","Tag":"latest","ID":"abc123"}\n'
        mock_run.return_value.stderr = ""

        result = DockerBuilder.list_images()

        assert len(result) == 1
        assert result[0]["Repository"] == "test"
        assert result[0]["Tag"] == "latest"
        call_args = mock_run.call_args[0][0]
        assert "docker" in call_args
        assert "images" in call_args
        assert "--format" in call_args
        assert "json" in call_args

    @patch('subprocess.run')
    def test_list_images_with_filter(self, mock_run):
        """Test Docker images list with filter."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"Repository":"test","Tag":"latest","ID":"abc123"}\n'
        mock_run.return_value.stderr = ""

        result = DockerBuilder.list_images(filter_name="test")

        assert len(result) == 1
        call_args = mock_run.call_args[0][0]
        assert "--filter" in call_args
        assert "reference=test" in call_args

    @patch('subprocess.run')
    def test_list_images_invalid_json(self, mock_run):
        """Test Docker images list with invalid JSON."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = 'invalid json\n{"Repository":"test","Tag":"latest"}\n'
        mock_run.return_value.stderr = ""

        result = DockerBuilder.list_images()

        # Should still return the valid JSON entry
        assert len(result) == 1
        assert result[0]["Repository"] == "test"

    @patch('subprocess.run')
    def test_list_images_failure(self, mock_run):
        """Test Docker images list failure."""
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["docker", "images"],
            stderr="list failed"
        )

        with pytest.raises(MCPStackValidationError, match="Failed to list Docker images"):
            DockerBuilder.list_images()

    @patch('subprocess.run')
    def test_list_images_docker_not_found(self, mock_run):
        """Test list images when Docker command is not found."""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(MCPStackValidationError, match="Docker command not found"):
            DockerBuilder.list_images()