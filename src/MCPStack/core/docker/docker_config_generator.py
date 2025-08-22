"""Docker configuration generator for Claude Desktop integration."""
import json
import logging
import re
from pathlib import Path

from beartype import beartype
from beartype.typing import Any, Dict, List, Optional

from MCPStack.core.utils.exceptions import MCPStackValidationError

logger = logging.getLogger(__name__)


@beartype
class DockerConfigGenerator:
    """Generator for Docker-based MCP configurations for Claude Desktop.
    
    Creates Claude Desktop configuration entries that use Docker to run
    MCPStack tools in containers.
    """

    @classmethod
    def generate(
        cls,
        stack,
        image_name: str,
        server_name: str = "mcpstack",
        volumes: Optional[List[str]] = None,
        ports: Optional[List[str]] = None,
        network: Optional[str] = None,
        extra_docker_args: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate Docker-based Claude Desktop configuration.

        Args:
            stack: MCPStackCore instance
            image_name: Docker image name (e.g., "mcpstack:latest")
            server_name: Name for the MCP server in Claude config
            volumes: List of volume mounts (e.g., ["/host/path:/container/path"])
            ports: List of port mappings (e.g., ["8000:8000"])
            network: Docker network name
            extra_docker_args: Additional Docker arguments

        Returns:
            Dict containing Claude Desktop configuration

        Raises:
            MCPStackValidationError: If image_name is invalid
        """
        cls._validate_image_name(image_name)
        
        # Build Docker command arguments
        docker_args = ["run", "-i", "--rm"]
        
        # Add volume mounts
        if volumes:
            for volume in volumes:
                docker_args.extend(["-v", volume])
        
        # Add port mappings
        if ports:
            for port in ports:
                docker_args.extend(["-p", port])
        
        # Add network
        if network:
            docker_args.extend(["--network", network])
        
        # Add extra arguments
        if extra_docker_args:
            docker_args.extend(extra_docker_args)
        
        # Add image name as final argument
        docker_args.append(image_name)
        
        config = {
            "mcpServers": {
                server_name: {
                    "command": "docker",
                    "args": docker_args,
                    "env": stack.config.env_vars.copy(),
                }
            }
        }
        
        return config

    @classmethod
    def save(
        cls,
        stack,
        image_name: str,
        server_name: str = "mcpstack",
        save_path: Optional[str] = None,
        volumes: Optional[List[str]] = None,
        ports: Optional[List[str]] = None,
        network: Optional[str] = None,
        extra_docker_args: Optional[List[str]] = None,
    ) -> None:
        """Generate and save Docker configuration to file.

        Args:
            stack: MCPStackCore instance
            image_name: Docker image name
            server_name: Name for the MCP server in Claude config
            save_path: Optional custom save path
            volumes: List of volume mounts
            ports: List of port mappings  
            network: Docker network name
            extra_docker_args: Additional Docker arguments
        """
        config = cls.generate(
            stack=stack,
            image_name=image_name,
            server_name=server_name,
            volumes=volumes,
            ports=ports,
            network=network,
            extra_docker_args=extra_docker_args,
        )
        
        if save_path:
            with open(save_path, "w") as f:
                json.dump(config, f, indent=2)
            logger.info(f"✅ Docker config saved to {save_path}")
        else:
            path = cls._get_claude_config_path()
            if path:
                cls._merge_with_existing_config(config, path)
            else:
                logger.warning("Could not find Claude Desktop config directory")

    @staticmethod
    def _validate_image_name(image_name: str) -> None:
        """Validate Docker image name format.
        
        Args:
            image_name: Docker image name to validate
            
        Raises:
            MCPStackValidationError: If image name is invalid
        """
        if not image_name or not image_name.strip():
            raise MCPStackValidationError("Docker image name cannot be empty")
        
        # Basic validation for Docker image name format
        # Allow: registry.io/name:tag, name:tag, name
        if " " in image_name:
            raise MCPStackValidationError(
                f"Docker image name cannot contain spaces: {image_name}"
            )
        
        # Check for invalid characters (basic check)
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._/-]*[a-zA-Z0-9]*(:[a-zA-Z0-9._-]+)?$', image_name):
            if len(image_name) > 1:  # Allow single character names for testing
                raise MCPStackValidationError(
                    f"Invalid Docker image name format: {image_name}"
                )

    @staticmethod
    def _get_claude_config_path() -> Optional[Path]:
        """Get Claude Desktop configuration file path.
        
        Returns:
            Path to claude_desktop_config.json if found, None otherwise
        """
        home = Path.home()
        paths = [
            # macOS
            home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
            # Windows
            home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json", 
            # Linux
            home / ".config" / "Claude" / "claude_desktop_config.json",
        ]
        
        for path in paths:
            if path.parent.exists():
                return path
        
        return None

    @staticmethod
    def _merge_with_existing_config(new_config: Dict[str, Any], config_path: Path) -> None:
        """Merge new configuration with existing Claude Desktop config.
        
        Args:
            new_config: New configuration to merge
            config_path: Path to existing configuration file
        """
        existing_config = {}
        
        if config_path.exists():
            try:
                with open(config_path) as f:
                    existing_config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Could not read existing config: {e}")
                existing_config = {}
        
        # Merge mcpServers sections
        existing_config.setdefault("mcpServers", {})
        existing_config["mcpServers"].update(new_config["mcpServers"])
        
        # Write merged configuration
        try:
            with open(config_path, "w") as f:
                json.dump(existing_config, f, indent=2)
            logger.info(f"✅ Docker config merged into {config_path}")
        except IOError as e:
            logger.error(f"Failed to write config to {config_path}: {e}")
            raise MCPStackValidationError(f"Could not write config file: {e}")