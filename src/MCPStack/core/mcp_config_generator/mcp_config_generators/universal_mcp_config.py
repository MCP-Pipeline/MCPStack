import json
import logging

from beartype import beartype
from beartype.typing import List, Optional

logger = logging.getLogger(__name__)


@beartype
class UniversalConfigGenerator:
    """Factory for producing an MCP host configuration JSON from a stack, dedicated to universal applications.

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
    ) -> dict:
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
        env = stack.config.env_vars.copy()
        if pipeline_config_path:
            env["MCPSTACK_CONFIG_PATH"] = pipeline_config_path
        config = stack.__dict__.copy()
        config["env_vars"] = env
        if save_path:
            with open(save_path, "w") as f:
                json.dump(config, f, indent=2)
            logger.info(f"✅ Universal config saved to {save_path}.")
        return config
