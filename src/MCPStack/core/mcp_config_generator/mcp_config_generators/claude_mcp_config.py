import json, logging, os, shutil
from pathlib import Path
from beartype import beartype
from beartype.typing import Any, Dict, List, Optional
from MCPStack.core.utils.exceptions import MCPStackValidationError

logger = logging.getLogger(__name__)

@beartype
class ClaudeConfigGenerator:
    @classmethod
    def generate(
        cls, stack,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        module_name: Optional[str] = None,
        pipeline_config_path: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        _command = cls._get_command(command, stack)
        _module_name = cls._get_module_name(module_name, stack)
        _args = cls._get_args(args, stack, _module_name)
        _cwd = cls._get_cwd(cwd, stack)

        if not shutil.which(_command):
            raise MCPStackValidationError(f"Invalid command '{_command}': Not found on PATH.")
        if not os.path.isdir(_cwd):
            raise MCPStackValidationError(f"Invalid cwd '{_cwd}': Directory does not exist.")

        env = stack.config.env_vars.copy()
        if pipeline_config_path:
            env["MCPSTACK_CONFIG_PATH"] = pipeline_config_path

        config = {"mcpServers": {"mcpstack": {"command": _command, "args": _args, "cwd": _cwd, "env": env}}}
        if save_path:
            with open(save_path, "w") as f:
                json.dump(config, f, indent=2)
            logger.info(f"✅ Claude config saved to {save_path}.")
        else:
            path = cls._get_claude_config_path()
            if path:
                existing = {}
                if path.exists():
                    with open(path) as f:
                        existing = json.load(f)
                existing.setdefault("mcpServers", {}).update(config["mcpServers"])
                with open(path, "w") as f:
                    json.dump(existing, f, indent=2)
                logger.info(f"✅ Claude config merged into {path}.")
        return config

    @staticmethod
    def _get_command(command, stack) -> str:
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
        if module_name is not None:
            return module_name
        return stack.config.get_env_var("MCPSTACK_MODULE", "MCPStack.core.server")

    @staticmethod
    def _get_args(args, stack, module_name: str):
        if args is not None:
            return args
        default = ["-m", module_name]
        value = stack.config.get_env_var("MCPSTACK_ARGS", default)
        return value if isinstance(value, list) else default

    @staticmethod
    def _get_cwd(cwd, stack) -> str:
        if cwd is not None:
            return cwd
        return stack.config.get_env_var("MCPSTACK_CWD", os.getcwd())

    @staticmethod
    def _get_claude_config_path():
        home = Path.home()
        paths = [
            home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
            home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
            home / ".config" / "Claude" / "claude_desktop_config.json",
        ]
        return next((p for p in paths if p.parent.exists()), None)
