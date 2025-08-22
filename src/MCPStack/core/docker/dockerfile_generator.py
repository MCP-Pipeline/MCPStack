"""Dockerfile generation for MCPStack containerization."""
import logging
from pathlib import Path

from beartype import beartype
from beartype.typing import List, Optional

logger = logging.getLogger(__name__)


@beartype
class DockerfileGenerator:
    """Generator for Dockerfiles to containerize MCPStack tools."""

    @classmethod
    def generate(
        cls,
        stack,
        base_image: str = "python:3.13-slim",
        package_name: Optional[str] = None,
        requirements: Optional[List[str]] = None,
        local_package_path: Optional[str] = None,
        cmd: Optional[List[str]] = None,
        workdir: str = "/app",
        expose_port: int = 8000,
    ) -> str:
        """Generate a Dockerfile for the MCPStack configuration.

        Args:
            stack: MCPStackCore instance
            base_image: Base Docker image to use
            package_name: Package to install via pip (e.g., "mcpstack")
            requirements: List of additional requirements to install
            local_package_path: Path to local package for development
            cmd: Custom command to run in container
            workdir: Working directory in container
            expose_port: Port to expose

        Returns:
            String content of the generated Dockerfile
        """
        lines = []
        
        # Base image
        lines.append(f"FROM {base_image}")
        
        # Working directory
        lines.append(f"WORKDIR {workdir}")
        
        # Install system dependencies if needed
        if base_image.startswith("python:") and "slim" in base_image:
            lines.append("RUN apt-get update && apt-get install -y --no-install-recommends \\")
            lines.append("    curl \\")
            lines.append("    && rm -rf /var/lib/apt/lists/*")
        
        # Handle local package installation
        if local_package_path:
            lines.append(f"COPY {local_package_path} {workdir}/mcpstack")
            lines.append(f"RUN pip install -e {workdir}/mcpstack")
        
        # Install package from PyPI
        elif package_name:
            install_cmd = f"RUN pip install {package_name}"
            lines.append(install_cmd)
        
        # Install additional requirements
        if requirements:
            req_str = " ".join(requirements)
            lines.append(f"RUN pip install {req_str}")
        
        # Set environment variables from stack config
        if stack.config.env_vars:
            for key, value in stack.config.env_vars.items():
                lines.append(f"ENV {key}={value}")
        
        # Expose port
        lines.append(f"EXPOSE {expose_port}")
        
        # Default command
        if cmd:
            cmd_str = '["' + '", "'.join(cmd) + '"]'
            lines.append(f"CMD {cmd_str}")
        else:
            lines.append('CMD ["mcpstack-mcp-server"]')
        
        return "\n".join(lines) + "\n"

    @classmethod
    def save(
        cls,
        stack,
        path: Path,
        base_image: str = "python:3.13-slim",
        package_name: Optional[str] = None,
        requirements: Optional[List[str]] = None,
        local_package_path: Optional[str] = None,
        cmd: Optional[List[str]] = None,
        workdir: str = "/app",
        expose_port: int = 8000,
    ) -> None:
        """Generate and save Dockerfile to specified path.

        Args:
            stack: MCPStackCore instance
            path: Path where to save the Dockerfile
            base_image: Base Docker image to use
            package_name: Package to install via pip
            requirements: List of additional requirements
            local_package_path: Path to local package for development
            cmd: Custom command to run in container
            workdir: Working directory in container
            expose_port: Port to expose
        """
        dockerfile_content = cls.generate(
            stack=stack,
            base_image=base_image,
            package_name=package_name,
            requirements=requirements,
            local_package_path=local_package_path,
            cmd=cmd,
            workdir=workdir,
            expose_port=expose_port,
        )
        
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dockerfile_content)
        
        logger.info(f"✅ Dockerfile saved to {path}")

    @classmethod
    def generate_for_tool(
        cls,
        stack,
        tool_name: str,
        base_image: str = "python:3.13-slim",
    ) -> str:
        """Generate a Dockerfile specific to a single tool.

        Args:
            stack: MCPStackCore instance
            tool_name: Name of the specific tool to containerize
            base_image: Base Docker image to use

        Returns:
            String content of the generated Dockerfile
        """
        # Find the specific tool in the stack
        tool = None
        for t in stack.tools:
            if t.__class__.__name__.lower() == tool_name.lower():
                tool = t
                break
        
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found in stack")
        
        # Get tool-specific requirements if available
        requirements = getattr(tool, "requirements", [])
        
        # Get tool-specific environment variables
        tool_env_vars = getattr(tool, "required_env_vars", {})
        
        lines = []
        lines.append(f"FROM {base_image}")
        lines.append("WORKDIR /app")
        
        # Install MCPStack
        lines.append("RUN pip install mcpstack")
        
        # Install tool-specific requirements
        if requirements:
            req_str = " ".join(requirements)
            lines.append(f"RUN pip install {req_str}")
        
        # Set tool-specific environment variables
        for key, default_value in tool_env_vars.items():
            if default_value is not None:
                lines.append(f"ENV {key}={default_value}")
        
        # Set general environment variables from stack
        for key, value in stack.config.env_vars.items():
            lines.append(f"ENV {key}={value}")
        
        lines.append("EXPOSE 8000")
        lines.append('CMD ["mcpstack-mcp-server"]')
        
        return "\n".join(lines) + "\n"