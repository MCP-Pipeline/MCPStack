import logging
import os
from pathlib import Path
from beartype import beartype
from beartype.typing import Any, Dict, List, Optional
from .utils.logging import setup_logging
from .utils.exceptions import MCPStackConfigError

logger = logging.getLogger(__name__)

@beartype
class StackConfig:
    def __init__(self, log_level: str = "INFO", env_vars: Optional[Dict[str, str]] = None) -> None:
        self.log_level = log_level
        self.env_vars = env_vars or {}
        self._set_paths()
        self._apply_config()

    def to_dict(self) -> Dict[str, Any]:
        return {"log_level": self.log_level, "env_vars": self.env_vars.copy()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StackConfig":
        return cls(log_level=data.get("log_level", "INFO"), env_vars=data.get("env_vars", {}))

    def get_env_var(self, key: str, default: Optional[Any] = None, raise_if_missing: bool = False) -> Any:
        value = self.env_vars.get(key, os.getenv(key, default))
        if value is None and raise_if_missing:
            raise MCPStackConfigError(f"Missing required env var: {key}")
        logger.debug(f"Accessed env var '{key}': {'[set]' if value else '[unset]'}")
        return value or ""

    def validate_for_tools(self, tools: List) -> None:
        errors = []
        for tool in tools:
            for req_key, req_default in getattr(tool, "required_env_vars", {}).items():
                try:
                    self.get_env_var(req_key, default=req_default, raise_if_missing=req_default is None)
                except Exception as e:
                    errors.append(f"{tool.__class__.__name__}: {e}")
        if errors:
            raise MCPStackConfigError("\n".join(errors))
        logger.info(f"Validated config for {len(tools)} tools.")

    def merge_env(self, new_env: Dict[str, str], prefix: str = "") -> None:
        for key, value in new_env.items():
            prefixed_key = f"{prefix}{key}" if prefix else key
            if prefixed_key in self.env_vars and self.env_vars[prefixed_key] != value:
                raise MCPStackConfigError(f"Env conflict: {prefixed_key} ({self.env_vars[prefixed_key]} vs {value})")
            self.env_vars[prefixed_key] = value

    def _set_paths(self) -> None:
        self.project_root = self._get_project_root()
        self.data_dir = self._get_data_dir()
        self.databases_dir = self.data_dir / "databases"
        self.raw_files_dir = self.data_dir / "raw_files"

    def _get_project_root(self) -> Path:
        package_root = Path(__file__).resolve().parents[3]
        return package_root if (package_root / "pyproject.toml").exists() else Path.home()

    def _get_data_dir(self) -> Path:
        data_dir_str = self.get_env_var("MCPSTACK_DATA_DIR")
        return Path(data_dir_str) if data_dir_str else self.project_root / "mcpstack_data"

    def _apply_config(self) -> None:
        try:
            setup_logging(level=self.log_level)
        except Exception as e:
            raise MCPStackConfigError("Invalid log level", details=str(e))
        for k, v in self.env_vars.items():
            os.environ[k] = v
