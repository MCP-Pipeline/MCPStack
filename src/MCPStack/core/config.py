import logging
import os
from pathlib import Path

from beartype import beartype
from beartype.typing import Any, Dict, List, Optional

from .utils.exceptions import MCPStackConfigError
from .utils.logging import setup_logging

logger = logging.getLogger(__name__)


@beartype
class StackConfig:
    """Configuration container for MCPStack.

    Holds logging configuration, environment variables, and computed paths used
    by tools and the MCP server.

    !!! note "Scope"
        Stores env vars and I/O paths used by tools and the MCP server.

    Args:
        log_level: Logging level name (e.g., `"INFO"`, `"DEBUG"`).
        env_vars: Mapping of environment variables to set/merge.

    Attributes:
        log_level (str): Active logging level.
        env_vars (dict[str, str]): Environment variables tracked by the stack.
        project_root (Path): Detected project root (see `_get_project_root()`).
        data_dir (Path): Base data directory (see `_get_data_dir()`).
        databases_dir (Path): `data_dir / "databases"`.
        raw_files_dir (Path): `data_dir / "raw_files"`.

    !!! tip "When is logging applied?"
        Logging is initialized and `env_vars` exported to `os.environ` during
        construction via :meth:`_apply_config`.
    """

    def __init__(
        self, log_level: str = "INFO", env_vars: Optional[Dict[str, str]] = None
    ) -> None:
        self.log_level = log_level
        self.env_vars = env_vars or {}
        self._set_paths()
        self._apply_config()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the configuration to a plain dictionary.

        Returns:
            dict: A shallow copy with `log_level` and `env_vars`.

        !!! example
            ```python
            cfg = StackConfig()
            payload = cfg.to_dict()
            ```
        """
        return {"log_level": self.log_level, "env_vars": self.env_vars.copy()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StackConfig":
        """Construct a :class:`StackConfig` from a mapping.

        Args:
            data: A mapping containing optional keys `log_level` and `env_vars`.

        Returns:
            StackConfig: New instance populated from `data`.

        !!! tip
            Missing keys default to `log_level="INFO"` and an empty `env_vars`.
        """
        return cls(
            log_level=data.get("log_level", "INFO"), env_vars=data.get("env_vars", {})
        )

    def get_env_var(
        self, key: str, default: Optional[Any] = None, raise_if_missing: bool = False
    ) -> Any:
        """Retrieve an environment variable with fallback and validation.

        Lookup order: `self.env_vars[key]` → `os.getenv(key)` → `default`.

        Args:
            key: Environment variable name.
            default: Value to return if not found in config or process env.
            raise_if_missing: If `True`, raise when the final value is `None`.

        Returns:
            Any: The resolved value, or `""` if the resolved value is falsy.

        Raises:
            MCPStackConfigError: If `raise_if_missing=True` and no value found.

        !!! note
            A debug log is emitted indicating whether the key was set or unset.
        """
        value = self.env_vars.get(key, os.getenv(key, default))
        if value is None and raise_if_missing:
            raise MCPStackConfigError(f"Missing required env var: {key}")
        logger.debug(f"Accessed env var '{key}': {'[set]' if value else '[unset]'}")
        return value or ""

    def validate_for_tools(self, tools: List) -> None:
        """Ensure all tools' required environment variables are present.

        Inspects each tool's `required_env_vars` (a mapping of `name -> default`)
        and verifies that values are available via :meth:`get_env_var`. When a
        default is `None`, the key is considered **required**.

        Args:
            tools: Iterable of tool instances to validate against this config.

        Raises:
            MCPStackConfigError: Aggregated errors if any requirement is missing.

        !!! failure "Common pitfalls"
            * No value provided for a required key (`default=None`).
            * Typos in environment variable names.
            * Forgot to merge preset/tool-provided env.
        """
        errors = []
        for tool in tools:
            for req_key, req_default in getattr(tool, "required_env_vars", {}).items():
                try:
                    self.get_env_var(
                        req_key,
                        default=req_default,
                        raise_if_missing=req_default is None,
                    )
                except Exception as e:
                    errors.append(f"{tool.__class__.__name__}: {e}")
        if errors:
            raise MCPStackConfigError("\n".join(errors))
        logger.info(f"Validated config for {len(tools)} tools.")

    def merge_env(self, new_env: Dict[str, str], prefix: str = "") -> None:
        """Merge environment variables with optional key prefix and conflict checks.

        Args:
            new_env: Mapping to merge into `env_vars`.
            prefix: String to preprend to each key (namespacing).

        Raises:
            MCPStackConfigError: If a key exists with a **different** value.

        !!! tip "Namespacing"
            Use `prefix` (e.g., `"MYTOOL_"`) to avoid collisions between tools.
        """
        for key, value in new_env.items():
            prefixed_key = f"{prefix}{key}" if prefix else key
            if prefixed_key in self.env_vars and self.env_vars[prefixed_key] != value:
                raise MCPStackConfigError(
                    f"Env conflict: {prefixed_key} ({self.env_vars[prefixed_key]} vs {value})"
                )
            self.env_vars[prefixed_key] = value

    def _set_paths(self) -> None:
        """Compute and cache commonly used directories on disk.

        Side effects:
            Sets `project_root`, `data_dir`, `databases_dir`, and `raw_files_dir`.

        !!! note
            Paths are derived once at initialization; adjust env and rebuild the
            config if your directory layout changes at runtime.
        """
        self.project_root = self._get_project_root()
        self.data_dir = self._get_data_dir()
        self.databases_dir = self.data_dir / "databases"
        self.raw_files_dir = self.data_dir / "raw_files"

    def _get_project_root(self) -> Path:
        """Infer the project root.

        Returns:
            Path: Directory containing `pyproject.toml` if found by traversing
            up from this file; otherwise the user's home directory.

        !!! tip
            Useful for resolving default data directories during local dev.
        """
        package_root = Path(__file__).resolve().parents[3]
        return (
            package_root if (package_root / "pyproject.toml").exists() else Path.home()
        )

    def _get_data_dir(self) -> Path:
        """Resolve the base data directory.

        Resolution order:
            1. `MCPSTACK_DATA_DIR` from config/env (if set)
            2. `project_root / "mcpstack_data"`

        Returns:
            Path: The resolved data directory.
        """
        data_dir_str = self.get_env_var("MCPSTACK_DATA_DIR")
        return (
            Path(data_dir_str) if data_dir_str else self.project_root / "mcpstack_data"
        )

    def _apply_config(self) -> None:
        """Apply logging configuration and export env vars to the process.

        Side effects:
            * Initializes logging via :func:`setup_logging` using `log_level`.
            * Writes keys from `env_vars` into `os.environ`.

        Raises:
            MCPStackConfigError: If the logging level is invalid.

        !!! warning "Global process state"
            Exporting `env_vars` updates `os.environ` for the current process
            and its children. Avoid unintentional overrides by using distinct
            prefixes when merging from multiple sources.
        """
        try:
            setup_logging(level=self.log_level)
        except Exception as e:
            raise MCPStackConfigError("Invalid log level", details=str(e)) from e
        for k, v in self.env_vars.items():
            os.environ[k] = v
