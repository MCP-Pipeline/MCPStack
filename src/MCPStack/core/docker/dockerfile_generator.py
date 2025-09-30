import logging
from pathlib import Path

from beartype import beartype
from beartype.typing import List, Optional

logger = logging.getLogger(__name__)


# Environment variables that should NOT be copied to containers
EXCLUDED_ENV_VARS = {
    # Windows system paths with spaces
    'PROGRAMFILES', 'PROGRAMFILES(X86)', 'PROGRAMDATA', 'PROGRAMW6432',
    'COMMONPROGRAMFILES', 'COMMONPROGRAMFILES(X86)', 'COMMONPROGRAMW6432',
    'WINDIR', 'SYSTEMROOT', 'SYSTEMDRIVE', 'APPDATA', 'LOCALAPPDATA',
    'USERPROFILE', 'HOMEPATH', 'TEMP', 'TMP', 'PUBLIC',

    # User identity and system info
    'USERNAME', 'USERDOMAIN', 'COMPUTERNAME', 'USERDNSDOMAIN',
    'SESSIONNAME', 'LOGONSERVER', 'HOMEDRIVE', 'HOMESHARE',

    # Process and shell variables
    'PATH', 'PATHEXT', 'PSMODULEPATH', 'PSHOMEDRIVE', 'PSHOMEPATH',
    'CMDPROMPT', 'PROMPT', 'SHELL', 'BASH_ENV', 'ENV',

    # Linux-specific system paths (prevent conflicts)
    'LD_LIBRARY_PATH', 'PYTHONPATH', 'PKG_CONFIG_PATH',
    'MANPATH', 'INFOPATH', 'XDG_CONFIG_DIRS',

    # Host-specific network and display
    'DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY',
    'SSH_AUTH_SOCK', 'SSH_AGENT_PID',
}


def _should_include_env_var(key: str, value: str) -> bool:
    """Determine if an environment variable should be included in the Dockerfile.

    Args:
        key: Environment variable name
        value: Environment variable value

    Returns:
        True if the variable should be included in the container
    """
    if key.upper() in EXCLUDED_ENV_VARS:
        return False

    if key.upper().startswith(('MCPSTACK_', 'MCP_')):
        return True

    key_lower = key.lower()
    value_lower = value.lower()

    if any(keyword in key_lower for keyword in ['api_key', 'auth', 'token', 'secret', 'key']):
        return True

    if any(keyword in key_lower for keyword in ['tool', 'server', 'config', 'port', 'host', 'debug', 'env']):
        return True

    if any(keyword in value_lower for keyword in ['config', '.json', '.yaml', 'http', '://', '/api/', '.txt', '.log']):
        return True

    if ('_config' in value_lower or
        '_path' in value_lower or
        '_endpoints' in value_lower or
        key.lower().endswith(('_path', '_config', '_file', '_log'))):
        return True

    if any(ide_keyword in key.upper() for ide_keyword in ['VSCODE_', 'BUNDLED_', '_ADAPTER_ENDPOINTS']):
        return False

    if len(value) < 100 and not any(char in value for char in ['\\', '/', ':', ';']) and value.replace('_', '').replace('-', '').replace('.', '').isalnum():
        return True

    return False


def _sanitize_env_value(value: str) -> str:
    """Sanitize environment variable values for Dockerfile usage.

    Args:
        value: Raw environment variable value

    Returns:
        Properly quoted value safe for Dockerfile ENV statements
    """
    if any(char in value for char in [' ', '\\', '"', "'"]):
        escaped_value = value.replace('"', '\\"')
        return f'"{escaped_value}"'

    return value


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
        
        lines.append(f"FROM {base_image}")
        
        lines.append(f"WORKDIR {workdir}")
        
        if base_image.startswith("python:") and "slim" in base_image:
            lines.append("RUN apt-get update && apt-get install -y --no-install-recommends \\")
            lines.append("    curl \\")
            lines.append("    && rm -rf /var/lib/apt/lists/*")
        
        if local_package_path:
            import os
            files_to_copy = ["pyproject.toml", "LICENSE"]
            if os.path.exists("README.md"):
                files_to_copy.append("README.md")
            copy_command = f"COPY {' '.join(files_to_copy)} /app/"
            lines.append(copy_command)
            lines.append("COPY src/ /app/src/")
            lines.append("RUN pip install .")

        elif package_name:
            install_cmd = f"RUN pip install {package_name}"
            lines.append(install_cmd)

        if requirements:
            req_str = " ".join(requirements)
            lines.append(f"RUN pip install {req_str}")

        lines.append("COPY mcpstack_pipeline.json /app/mcpstack-config.json")
        
        if not cmd:  # Only set if using default MCPStack server command
            lines.append(f'ENV MCPSTACK_CONFIG_PATH={workdir}/mcpstack-config.json')
            lines.append('ENV MCPSTACK_COMMAND=python3')

        if stack.config.env_vars:
            for key, value in stack.config.env_vars.items():
                if _should_include_env_var(key, value):
                    sanitized_value = _sanitize_env_value(value)
                    lines.append(f"ENV {key}={sanitized_value}")

        lines.append(f"EXPOSE {expose_port}")

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
        
        logger.info(f"Dockerfile saved to {path}")

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
        tool = None
        for t in stack.tools:
            if t.__class__.__name__.lower() == tool_name.lower():
                tool = t
                break
        
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found in stack")
        
        requirements = getattr(tool, "requirements", [])
        
        tool_env_vars = getattr(tool, "required_env_vars", {})
        
        lines = []
        lines.append(f"FROM {base_image}")
        lines.append("WORKDIR /app")
        
        lines.append("RUN pip install mcpstack")
        
        if requirements:
            req_str = " ".join(requirements)
            lines.append(f"RUN pip install {req_str}")
        
        for key, default_value in tool_env_vars.items():
            if default_value is not None and _should_include_env_var(key, str(default_value)):
                sanitized_value = _sanitize_env_value(str(default_value))
                lines.append(f"ENV {key}={sanitized_value}")

        for key, value in stack.config.env_vars.items():
            if _should_include_env_var(key, value):
                sanitized_value = _sanitize_env_value(value)
                lines.append(f"ENV {key}={sanitized_value}")
        
        lines.append("EXPOSE 8000")
        lines.append('CMD ["mcpstack-mcp-server"]')
        
        return "\n".join(lines) + "\n"

