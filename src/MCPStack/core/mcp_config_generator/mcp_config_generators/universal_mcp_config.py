import json, logging
from beartype import beartype
from beartype.typing import List, Optional

logger = logging.getLogger(__name__)

@beartype
class UniversalConfigGenerator:  # pragma: no cover
    @classmethod
    def generate(
        cls, stack,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        module_name: Optional[str] = None,
        pipeline_config_path: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> dict:
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
