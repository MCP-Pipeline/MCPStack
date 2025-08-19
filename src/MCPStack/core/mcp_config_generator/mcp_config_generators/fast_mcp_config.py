import json
import logging
import os
import shutil
from pathlib import Path

from beartype import beartype
from beartype.typing import Any, Dict, List, Optional

from MCPStack.core.utils.exceptions import MCPStackValidationError

logger = logging.getLogger(__name__)


@beartype
class FastMCPConfigGenerator:
    """Factory for producing an MCP host configuration JSON from a stack dedicated to FastMCP.

    !!! note "Deterministic"

        Reads from environment and `StackConfig`; does not mutate the stack.
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
    ) -> Dict[str, Any]:
        """Create the configuration mapping and optionally persist it to disk.

        !!! tip "Use with CLI"

            The `mcpstack build` command calls into this method.

        Args:
          stack: An `MCPStackCore` instance.
          command (str | None): Executable used to launch the server; defaults to the active Python.
          args (List[str] | None): Arguments for the command; defaults to `['-m', module_name]`.
          cwd (str | None): Working directory for the server process.
          module_name (str | None): Python module to run when using `-m`.
          pipeline_config_path (str | None): Path to the pipeline JSON produced by `stack.save()`.
          save_path (str | None): If set, write the config JSON here.

        Returns:
          dict: Configuration mapping suitable for MCP-compatible hosts.

        Raises:
          MCPStackValidationError: If `command` or `cwd` are invalid (FastMCP variant).
        """
        _command = cls._get_command(command, stack)
        _module_name = cls._get_module_name(module_name, stack)
        _args = cls._get_args(args, stack, _module_name)
        _cwd = cls._get_cwd(cwd, stack)

        if not shutil.which(_command):
            raise MCPStackValidationError(
                f"Invalid command '{_command}': Not found on PATH."
            )
        if not os.path.isdir(_cwd):
            raise MCPStackValidationError(
                f"Invalid cwd '{_cwd}': Directory does not exist."
            )

        env = stack.config.env_vars.copy()
        if pipeline_config_path:
            env["MCPSTACK_CONFIG_PATH"] = pipeline_config_path

        config = {
            "mcpServers": {
                "mcpstack": {
                    "command": _command,
                    "args": _args,
                    "cwd": _cwd,
                    "env": env,
                }
            }
        }
        if save_path:
            with open(save_path, "w") as f:
                json.dump(config, f, indent=2)
            logger.info(f"✅ FastMCP config saved to {save_path}.")
        return config

    @staticmethod
    def _get_command(command, stack) -> str:
        """Resolve `command` from explicit args, env, or sensible defaults."""
        if command is not None:
            return command
        if "VIRTUAL_ENV" in os.environ:
            venv_python = Path(os.environ["VIRTUAL_ENV"]) / "bin" / "python"
            if venv_python.exists():
                return str(venv_python)
        default_python = shutil.which("python") or shutil.which("python3") or "python"
        return stack.config.get_env_var("MCPSTACK_COMMAND", default_python)

    @staticmethod
    def _get_module_name(module_name, stack) -> str:
        """Resolve `module_name` from explicit args, env, or sensible defaults."""
        if module_name is not None:
            return module_name
        return stack.config.get_env_var("MCPSTACK_MODULE", "MCPStack.core.server")

    @staticmethod
    def _get_args(args, stack, module_name: str):
        """Resolve `args` from explicit args, env, or sensible defaults."""
        if args is not None:
            return args
        default = ["-m", module_name]
        value = stack.config.get_env_var("MCPSTACK_ARGS", default)
        return value if isinstance(value, list) else default

    @staticmethod
    def _get_cwd(cwd, stack) -> str:
        """Resolve `cwd` from explicit args, env, or sensible defaults."""
        if cwd is not None:
            return cwd
        return stack.config.get_env_var("MCPSTACK_CWD", os.getcwd())
