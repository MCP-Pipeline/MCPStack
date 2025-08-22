"""Integration tests for Docker containerization workflow."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from MCPStack.core.config import StackConfig
from MCPStack.core.docker import DockerBuilder, DockerConfigGenerator, DockerfileGenerator
from MCPStack.stack import MCPStackCore


class TestDockerIntegration:
    """Integration tests for the complete Docker workflow."""

    def test_complete_docker_workflow(self):
        """Test the complete workflow from stack to Docker config."""
        # Create a stack with environment variables
        config = StackConfig(env_vars={
            "API_KEY": "test_key",
            "DEBUG": "true"
        })
        stack = MCPStackCore(config)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Step 1: Generate Dockerfile
            dockerfile_path = tmpdir_path / "Dockerfile"
            DockerfileGenerator.save(
                stack=stack,
                path=dockerfile_path,
                base_image="python:3.13-slim",
                package_name="mcpstack"
            )
            
            # Verify Dockerfile was created
            assert dockerfile_path.exists()
            dockerfile_content = dockerfile_path.read_text()
            assert "FROM python:3.13-slim" in dockerfile_content
            assert "ENV API_KEY=test_key" in dockerfile_content
            assert "ENV DEBUG=true" in dockerfile_content
            assert "RUN pip install mcpstack" in dockerfile_content
            
            # Step 2: Generate Claude Desktop config
            claude_config_path = tmpdir_path / "claude_desktop_config.json"
            DockerConfigGenerator.save(
                stack=stack,
                image_name="mcpstack:test",
                server_name="test_server",
                save_path=str(claude_config_path),
                volumes=["/host/data:/app/data"],
                ports=["8000:8000"]
            )
            
            # Verify Claude config was created
            assert claude_config_path.exists()
            with open(claude_config_path) as f:
                claude_config = json.load(f)
            
            assert "mcpServers" in claude_config
            assert "test_server" in claude_config["mcpServers"]
            server_config = claude_config["mcpServers"]["test_server"]
            
            assert server_config["command"] == "docker"
            assert "mcpstack:test" in server_config["args"]
            assert "-v" in server_config["args"]
            assert "/host/data:/app/data" in server_config["args"]
            assert "-p" in server_config["args"]
            assert "8000:8000" in server_config["args"]
            assert server_config["env"]["API_KEY"] == "test_key"
            assert server_config["env"]["DEBUG"] == "true"

    @patch('subprocess.run')
    def test_docker_build_integration(self, mock_run):
        """Test Docker build integration."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Successfully built abc123\nSuccessfully tagged mcpstack:test\n"
        mock_run.return_value.stderr = ""
        
        config = StackConfig()
        stack = MCPStackCore(config)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            dockerfile_path = tmpdir_path / "Dockerfile"
            
            # Generate Dockerfile
            DockerfileGenerator.save(
                stack=stack,
                path=dockerfile_path,
                package_name="mcpstack"
            )
            
            # Build Docker image
            result = DockerBuilder.build(
                dockerfile_path=dockerfile_path,
                image_name="mcpstack:test",
                context_path=str(tmpdir_path)
            )
            
            assert result["success"] is True
            assert result["image_name"] == "mcpstack:test"
            mock_run.assert_called_once()
            
            # Verify build command
            call_args = mock_run.call_args[0][0]
            assert "docker" in call_args
            assert "build" in call_args
            assert "-t" in call_args
            assert "mcpstack:test" in call_args
            assert str(tmpdir_path) in call_args

    def test_end_to_end_biomcp_style_example(self):
        """Test end-to-end workflow similar to the biomcp example."""
        config = StackConfig(env_vars={
            "BIO_API_KEY": "test_bio_key"
        })
        stack = MCPStackCore(config)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Generate Dockerfile (equivalent to creating biomcp Dockerfile)
            dockerfile_path = tmpdir_path / "Dockerfile"
            DockerfileGenerator.save(
                stack=stack,
                path=dockerfile_path,
                base_image="python:3.13-slim",
                package_name="mcpstack"  # equivalent to biomcp-python
            )
            
            dockerfile_content = dockerfile_path.read_text()
            expected_lines = [
                "FROM python:3.13-slim",
                "WORKDIR /app",
                "RUN pip install mcpstack",
                "ENV BIO_API_KEY=test_bio_key",
                "EXPOSE 8000",
                'CMD ["mcpstack-mcp-server"]'
            ]
            
            for line in expected_lines:
                assert line in dockerfile_content
            
            # Generate Claude Desktop config (equivalent to editing claude_desktop_config.json)
            claude_config_path = tmpdir_path / "claude_desktop_config.json"
            DockerConfigGenerator.save(
                stack=stack,
                image_name="mcpstack:latest",  # equivalent to biomcp:latest
                server_name="mcpstack",
                save_path=str(claude_config_path)
            )
            
            with open(claude_config_path) as f:
                config_data = json.load(f)
            
            # Verify it matches the biomcp example structure
            expected_config = {
                "mcpServers": {
                    "mcpstack": {
                        "command": "docker",
                        "args": ["run", "-i", "--rm", "mcpstack:latest"],
                        "env": {"BIO_API_KEY": "test_bio_key"}
                    }
                }
            }
            
            assert config_data == expected_config

    def test_docker_config_type_build_integration(self):
        """Test using the 'docker' config type with build()."""
        from MCPStack.tools.hello_world import Hello_World
        
        config = StackConfig(env_vars={
            "TEST_VAR": "test_value"
        })
        stack = MCPStackCore(config).with_tool(Hello_World())
        
        # Test building with docker config type and Docker-specific parameters
        # The MCPStackCore.build() method passes **kwargs to the generator
        docker_config = stack.build(
            type="docker",
            # These parameters are passed to DockerMCPConfigGenerator.generate()
            **{
                "image_name": "mcpstack:integration-test",
                "server_name": "integration_server", 
                "volumes": ["/test:/test"],
                "ports": ["9000:9000"]
            }
        )
        
        assert "mcpServers" in docker_config
        assert "integration_server" in docker_config["mcpServers"]
        
        server_config = docker_config["mcpServers"]["integration_server"]
        assert server_config["command"] == "docker"
        assert "mcpstack:integration-test" in server_config["args"]
        assert "-v" in server_config["args"]
        assert "/test:/test" in server_config["args"]
        assert "-p" in server_config["args"]
        assert "9000:9000" in server_config["args"]
        assert server_config["env"]["TEST_VAR"] == "test_value"