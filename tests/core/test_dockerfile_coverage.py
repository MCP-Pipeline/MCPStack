"""Additional tests for Dockerfile generator to improve coverage."""
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from MCPStack.core.config import StackConfig
from MCPStack.core.docker.dockerfile_generator import DockerfileGenerator
from MCPStack.stack import MCPStackCore


class TestDockerfileGeneratorCoverage:
    """Additional tests for Dockerfile generator to improve coverage."""

    def test_generate_with_non_slim_base_image(self):
        """Test Dockerfile generation with non-slim base image."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        dockerfile_content = DockerfileGenerator.generate(
            stack=stack,
            base_image="python:3.13",  # Not slim
            package_name="mcpstack"
        )
        
        # Should not include apt-get commands for non-slim images
        assert "apt-get" not in dockerfile_content
        assert "FROM python:3.13" in dockerfile_content

    def test_generate_with_non_python_base_image(self):
        """Test Dockerfile generation with non-Python base image."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        dockerfile_content = DockerfileGenerator.generate(
            stack=stack,
            base_image="ubuntu:20.04",
            package_name="mcpstack"
        )
        
        # Should not include apt-get commands for non-Python images
        assert "apt-get" not in dockerfile_content
        assert "FROM ubuntu:20.04" in dockerfile_content

    def test_generate_with_custom_workdir_and_port(self):
        """Test Dockerfile generation with custom workdir and port."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        dockerfile_content = DockerfileGenerator.generate(
            stack=stack,
            base_image="python:3.13-slim",
            package_name="mcpstack",
            workdir="/custom/app",
            expose_port=9000
        )
        
        assert "WORKDIR /custom/app" in dockerfile_content
        assert "EXPOSE 9000" in dockerfile_content

    def test_generate_without_package_or_local_path(self):
        """Test Dockerfile generation without package or local path."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        dockerfile_content = DockerfileGenerator.generate(
            stack=stack,
            base_image="python:3.13-slim",
            requirements=["requests", "pandas"]
        )
        
        # Should only install requirements
        assert "RUN pip install requests pandas" in dockerfile_content
        assert "pip install mcpstack" not in dockerfile_content

    def test_generate_for_tool_success(self):
        """Test generate_for_tool with existing tool."""
        from MCPStack.core.tool.base import BaseTool
        
        # Create a proper tool class that inherits from BaseTool
        class TestTool(BaseTool):
            def __init__(self):
                super().__init__()
                self.requirements = ["requests>=2.25.0"]
                self.required_env_vars = {"API_KEY": "default_key", "DEBUG": None}
            
            def initialize(self):
                pass
            
            def actions(self):
                return []
            
            def to_dict(self):
                return {}
            
            @classmethod
            def from_dict(cls, params):
                return cls()
        
        mock_tool = TestTool()
        
        config = StackConfig(env_vars={"CUSTOM_VAR": "custom_value"})
        stack = MCPStackCore(config).with_tool(mock_tool)
        
        dockerfile_content = DockerfileGenerator.generate_for_tool(
            stack=stack,
            tool_name="testtool"
        )
        
        assert "FROM python:3.13-slim" in dockerfile_content
        assert "RUN pip install mcpstack" in dockerfile_content
        assert "RUN pip install requests>=2.25.0" in dockerfile_content
        assert "ENV API_KEY=default_key" in dockerfile_content
        assert "ENV CUSTOM_VAR=custom_value" in dockerfile_content
        # DEBUG should not be set since it has None as default
        assert "ENV DEBUG=" not in dockerfile_content

    def test_generate_for_tool_not_found(self):
        """Test generate_for_tool with non-existent tool."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        with pytest.raises(ValueError, match="Tool 'nonexistent' not found"):
            DockerfileGenerator.generate_for_tool(
                stack=stack,
                tool_name="nonexistent"
            )

    def test_generate_for_tool_no_requirements(self):
        """Test generate_for_tool with tool that has no requirements."""
        from MCPStack.core.tool.base import BaseTool
        
        class SimpleTool(BaseTool):
            def initialize(self):
                pass
            
            def actions(self):
                return []
            
            def to_dict(self):
                return {}
            
            @classmethod
            def from_dict(cls, params):
                return cls()
        
        mock_tool = SimpleTool()
        
        config = StackConfig()
        stack = MCPStackCore(config).with_tool(mock_tool)
        
        dockerfile_content = DockerfileGenerator.generate_for_tool(
            stack=stack,
            tool_name="simpletool"
        )
        
        assert "FROM python:3.13-slim" in dockerfile_content
        assert "RUN pip install mcpstack" in dockerfile_content
        # Should not try to install additional requirements
        lines = dockerfile_content.split('\n')
        pip_install_lines = [line for line in lines if "pip install" in line and "mcpstack" not in line]
        assert len(pip_install_lines) == 0

    def test_save_creates_parent_directories(self):
        """Test that save creates parent directories."""
        config = StackConfig()
        stack = MCPStackCore(config)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "nested" / "dir" / "Dockerfile"
            
            DockerfileGenerator.save(
                stack=stack,
                path=nested_path,
                package_name="mcpstack"
            )
            
            assert nested_path.exists()
            assert nested_path.parent.exists()
            content = nested_path.read_text()
            assert "FROM python:3.13-slim" in content

    def test_generate_with_all_options(self):
        """Test Dockerfile generation with all options."""
        config = StackConfig(env_vars={"VAR1": "value1", "VAR2": "value2"})
        stack = MCPStackCore(config)
        
        dockerfile_content = DockerfileGenerator.generate(
            stack=stack,
            base_image="python:3.11-slim",
            package_name="custom-package",
            requirements=["requests", "pandas"],
            local_package_path="/src/package",
            cmd=["python", "-m", "custom.server", "--port", "8080"],
            workdir="/custom/workdir",
            expose_port=8080
        )
        
        expected_lines = [
            "FROM python:3.11-slim",
            "WORKDIR /custom/workdir",
            "COPY /src/package /custom/workdir/mcpstack",
            "RUN pip install -e /custom/workdir/mcpstack",
            # Note: custom-package is not installed when local_package_path is provided
            "RUN pip install requests pandas",
            "ENV VAR1=value1",
            "ENV VAR2=value2",
            "EXPOSE 8080",
            'CMD ["python", "-m", "custom.server", "--port", "8080"]'
        ]
        
        for line in expected_lines:
            assert line in dockerfile_content