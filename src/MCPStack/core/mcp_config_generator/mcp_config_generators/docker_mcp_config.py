"""Docker MCP configuration generator."""
import logging
from pathlib import Path

from beartype import beartype
from beartype.typing import Any, Dict, List, Optional

from MCPStack.core.docker.docker_config_generator import DockerConfigGenerator

logger = logging.getLogger(__name__)


@beartype
class DockerMCPConfigGenerator:
    """Factory for producing Docker-based MCP host configuration for Claude Desktop.
    
    This generator creates configurations that use Docker to run MCPStack tools
    in containers, following the same pattern as other MCP config generators.
    """

    @classmethod
    def generate(
        cls,
        stack,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        module_name: Optional[str] = None,
        pipeline_config_path: Optional[str] = None,
        save_path: Optional[str] = None,
        image_name: str = "mcpstack:latest",
        server_name: str = "mcpstack",
        volumes: Optional[List[str]] = None,
        ports: Optional[List[str]] = None,
        network: Optional[str] = None,
        extra_docker_args: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate Docker-based MCP configuration.

        Args:
            stack: MCPStackCore instance
            command: Ignored for Docker config (kept for interface compatibility)
            args: Ignored for Docker config (kept for interface compatibility)
            cwd: Ignored for Docker config (kept for interface compatibility)
            module_name: Ignored for Docker config (kept for interface compatibility)
            pipeline_config_path: Optional path to pipeline config (set as env var)
            save_path: Optional path to save the configuration
            image_name: Docker image name to use
            server_name: MCP server name in Claude config
            volumes: Volume mounts for Docker container
            ports: Port mappings for Docker container
            network: Docker network to use
            extra_docker_args: Additional Docker arguments

        Returns:
            Dict containing the Docker-based MCP configuration
        """
        # Generate the Docker configuration
        config = DockerConfigGenerator.generate(
            stack=stack,
            image_name=image_name,
            server_name=server_name,
            volumes=volumes,
            ports=ports,
            network=network,
            extra_docker_args=extra_docker_args,
        )
        
        # Add pipeline config path as environment variable if provided
        if pipeline_config_path:
            config["mcpServers"][server_name]["env"]["MCPSTACK_CONFIG_PATH"] = pipeline_config_path
        
        # Save configuration if path provided
        if save_path:
            DockerConfigGenerator.save(
                stack=stack,
                image_name=image_name,
                server_name=server_name,
                save_path=save_path,
                volumes=volumes,
                ports=ports,
                network=network,
                extra_docker_args=extra_docker_args,
            )
        else:
            # Merge with existing Claude config
            DockerConfigGenerator.save(
                stack=stack,
                image_name=image_name,
                server_name=server_name,
                volumes=volumes,
                ports=ports,
                network=network,
                extra_docker_args=extra_docker_args,
            )
        
        return config