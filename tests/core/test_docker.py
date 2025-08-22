"""Tests for Docker containerization features."""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest

from MCPStack.core.config import StackConfig
from MCPStack.core.docker.docker_config_generator import DockerConfigGenerator
from MCPStack.core.docker.dockerfile_generator import DockerfileGenerator
from MCPStack.core.utils.exceptions import MCPStackValidationError
from MCPStack.stack import MCPStackCore


class TestDockerfileGenerator:
    """Test Dockerfile generation for MCPStack tools."""

    def test_generate_basic_dockerfile(self):
        """Test basic Dockerfile generation."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        dockerfile_content = DockerfileGenerator.generate(
            stack=stack,
            base_image="python:3.13-slim",
            package_name="mcpstack"
        )
        
        expected_lines = [
            "FROM python:3.13-slim",
            "WORKDIR /app",
            "RUN pip install mcpstack",
            "EXPOSE 8000",
            'CMD ["mcpstack-mcp-server"]'
        ]
        
        for line in expected_lines:
            assert line in dockerfile_content

    def test_generate_dockerfile_with_custom_requirements(self):
        """Test Dockerfile generation with custom requirements."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        requirements = ["requests>=2.25.0", "pandas>=1.3.0"]
        dockerfile_content = DockerfileGenerator.generate(
            stack=stack,
            base_image="python:3.11-slim",
            requirements=requirements
        )
        
        assert "FROM python:3.11-slim" in dockerfile_content
        assert "RUN pip install requests>=2.25.0 pandas>=1.3.0" in dockerfile_content

    def test_generate_dockerfile_with_env_vars(self):
        """Test Dockerfile generation with environment variables."""
        config = StackConfig(env_vars={"API_KEY": "test_key", "DEBUG": "true"})
        stack = MCPStackCore(config)
        
        dockerfile_content = DockerfileGenerator.generate(
            stack=stack,
            base_image="python:3.13-slim",
            package_name="mcpstack"
        )
        
        assert "ENV API_KEY=test_key" in dockerfile_content
        assert "ENV DEBUG=true" in dockerfile_content

    def test_generate_dockerfile_with_local_package(self):
        """Test Dockerfile generation for local package development."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        dockerfile_content = DockerfileGenerator.generate(
            stack=stack,
            base_image="python:3.13-slim",
            local_package_path="/local/path/to/mcpstack"
        )
        
        assert "COPY /local/path/to/mcpstack /app/mcpstack" in dockerfile_content
        assert "RUN pip install -e /app/mcpstack" in dockerfile_content

    def test_generate_dockerfile_with_custom_command(self):
        """Test Dockerfile generation with custom command."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        dockerfile_content = DockerfileGenerator.generate(
            stack=stack,
            base_image="python:3.13-slim",
            package_name="mcpstack",
            cmd=["python", "-m", "MCPStack.core.server", "--port", "9000"]
        )
        
        assert 'CMD ["python", "-m", "MCPStack.core.server", "--port", "9000"]' in dockerfile_content

    def test_save_dockerfile(self):
        """Test saving Dockerfile to disk."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile_path = Path(tmpdir) / "Dockerfile"
            
            DockerfileGenerator.save(
                stack=stack,
                path=dockerfile_path,
                base_image="python:3.13-slim",
                package_name="mcpstack"
            )
            
            assert dockerfile_path.exists()
            content = dockerfile_path.read_text()
            assert "FROM python:3.13-slim" in content


class TestDockerConfigGenerator:
    """Test Docker configuration generation for Claude Desktop."""

    def test_generate_docker_config(self):
        """Test basic Docker config generation for Claude Desktop."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        docker_config = DockerConfigGenerator.generate(
            stack=stack,
            image_name="mcpstack:latest"
        )
        
        expected_config = {
            "mcpServers": {
                "mcpstack": {
                    "command": "docker",
                    "args": ["run", "-i", "--rm", "mcpstack:latest"],
                    "env": {}
                }
            }
        }
        
        assert docker_config == expected_config

    def test_generate_docker_config_with_custom_name(self):
        """Test Docker config generation with custom server name."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        docker_config = DockerConfigGenerator.generate(
            stack=stack,
            image_name="custom-mcp:v1.0",
            server_name="custom_mcp"
        )
        
        assert "custom_mcp" in docker_config["mcpServers"]
        assert docker_config["mcpServers"]["custom_mcp"]["args"][-1] == "custom-mcp:v1.0"

    def test_generate_docker_config_with_env_vars(self):
        """Test Docker config generation with environment variables."""
        config = StackConfig(env_vars={"API_KEY": "secret", "DEBUG": "true"})
        stack = MCPStackCore(config)
        
        docker_config = DockerConfigGenerator.generate(
            stack=stack,
            image_name="mcpstack:latest"
        )
        
        expected_env = {"API_KEY": "secret", "DEBUG": "true"}
        assert docker_config["mcpServers"]["mcpstack"]["env"] == expected_env

    def test_generate_docker_config_with_volumes(self):
        """Test Docker config generation with volume mounts."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        volumes = ["/host/data:/app/data", "/host/config:/app/config:ro"]
        docker_config = DockerConfigGenerator.generate(
            stack=stack,
            image_name="mcpstack:latest",
            volumes=volumes
        )
        
        args = docker_config["mcpServers"]["mcpstack"]["args"]
        assert "-v" in args
        assert "/host/data:/app/data" in args
        assert "/host/config:/app/config:ro" in args

    def test_generate_docker_config_with_network(self):
        """Test Docker config generation with custom network."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        docker_config = DockerConfigGenerator.generate(
            stack=stack,
            image_name="mcpstack:latest",
            network="mcp-network"
        )
        
        args = docker_config["mcpServers"]["mcpstack"]["args"]
        assert "--network" in args
        assert "mcp-network" in args

    def test_generate_docker_config_with_ports(self):
        """Test Docker config generation with port mapping."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        ports = ["8000:8000", "9000:9000"]
        docker_config = DockerConfigGenerator.generate(
            stack=stack,
            image_name="mcpstack:latest",
            ports=ports
        )
        
        args = docker_config["mcpServers"]["mcpstack"]["args"]
        assert "-p" in args
        assert "8000:8000" in args
        assert "9000:9000" in args

    def test_save_docker_config(self):
        """Test saving Docker config to file."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "claude_desktop_config.json"
            
            DockerConfigGenerator.save(
                stack=stack,
                image_name="mcpstack:latest",
                save_path=str(config_path)
            )
            
            assert config_path.exists()
            with open(config_path) as f:
                saved_config = json.load(f)
            
            assert "mcpServers" in saved_config
            assert "mcpstack" in saved_config["mcpServers"]

    def test_merge_with_existing_claude_config(self):
        """Test merging Docker config with existing Claude Desktop config."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        existing_config = {
            "mcpServers": {
                "existing_tool": {
                    "command": "python",
                    "args": ["-m", "existing_tool"],
                    "env": {}
                }
            }
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "claude_desktop_config.json"
            
            # Write existing config
            with open(config_path, "w") as f:
                json.dump(existing_config, f)
            
            # Merge new Docker config
            with patch('MCPStack.core.docker.docker_config_generator.DockerConfigGenerator._get_claude_config_path') as mock_path:
                mock_path.return_value = config_path
                
                DockerConfigGenerator.save(
                    stack=stack,
                    image_name="mcpstack:latest"
                )
            
            # Check merged config
            with open(config_path) as f:
                merged_config = json.load(f)
            
            assert "existing_tool" in merged_config["mcpServers"]
            assert "mcpstack" in merged_config["mcpServers"]

    def test_get_claude_config_path_returns_path_or_none(self):
        """Test Claude config path detection returns path or None."""
        # This test just ensures the method runs without error
        # and returns either a valid Path or None
        path = DockerConfigGenerator._get_claude_config_path()
        assert path is None or isinstance(path, Path)

    def test_validate_image_name(self):
        """Test Docker image name validation."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        # Valid image names should work
        valid_names = ["mcpstack:latest", "registry.io/mcpstack:v1.0", "mcpstack"]
        for name in valid_names:
            result = DockerConfigGenerator.generate(stack=stack, image_name=name)
            assert result is not None
        
        # Invalid image names should raise validation error
        invalid_names = ["", "name with spaces"]
        for name in invalid_names:
            with pytest.raises(MCPStackValidationError):
                DockerConfigGenerator.generate(stack=stack, image_name=name)


class TestDockerIntegration:
    """Integration tests for Docker containerization."""

    def test_end_to_end_docker_workflow(self):
        """Test complete Docker workflow from Dockerfile to Claude config."""
        config = StackConfig(env_vars={"TEST_VAR": "test_value"})
        stack = MCPStackCore(config)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            dockerfile_path = tmpdir_path / "Dockerfile"
            config_path = tmpdir_path / "claude_desktop_config.json"
            
            # Generate Dockerfile
            DockerfileGenerator.save(
                stack=stack,
                path=dockerfile_path,
                base_image="python:3.13-slim",
                package_name="mcpstack"
            )
            
            # Generate Claude config
            DockerConfigGenerator.save(
                stack=stack,
                image_name="mcpstack:test",
                save_path=str(config_path)
            )
            
            # Verify both files exist and contain expected content
            assert dockerfile_path.exists()
            assert config_path.exists()
            
            dockerfile_content = dockerfile_path.read_text()
            assert "FROM python:3.13-slim" in dockerfile_content
            assert "ENV TEST_VAR=test_value" in dockerfile_content
            
            with open(config_path) as f:
                claude_config = json.load(f)
            assert claude_config["mcpServers"]["mcpstack"]["args"][-1] == "mcpstack:test"
            assert claude_config["mcpServers"]["mcpstack"]["env"]["TEST_VAR"] == "test_value"

    @patch('subprocess.run')
    def test_docker_build_command_generation(self, mock_run):
        """Test Docker build command generation."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        from MCPStack.core.docker.docker_builder import DockerBuilder
        
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Successfully built abc123"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile_path = Path(tmpdir) / "Dockerfile"
            dockerfile_path.write_text("FROM python:3.13-slim\n")
            
            result = DockerBuilder.build(
                dockerfile_path=dockerfile_path,
                image_name="mcpstack:test",
                context_path=tmpdir
            )
            
            assert result["success"] is True
            mock_run.assert_called_once()
            
            # Verify the docker build command
            call_args = mock_run.call_args[0][0]
            assert "docker" in call_args
            assert "build" in call_args
            assert "-t" in call_args
            assert "mcpstack:test" in call_args