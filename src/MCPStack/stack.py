import json, logging, os
from beartype import beartype
from beartype.typing import Any, List, Optional, Union
from fastmcp import FastMCP
from thefuzz import process

from MCPStack.core.config import StackConfig
from MCPStack.core.mcp_config_generator.registry import ALL_MCP_CONFIG_GENERATORS
from MCPStack.core.tool.base import BaseTool
from MCPStack.tools.registry import ALL_TOOLS
from MCPStack.core.utils.exceptions import MCPStackBuildError, MCPStackPresetError, MCPStackValidationError, MCPStackInitializationError
import re

logger = logging.getLogger(__name__)

@beartype
class MCPStackCore:
    def __init__(self, config: Optional[StackConfig] = None, mcp: Optional[FastMCP] = None) -> None:
        self.config = config or StackConfig()
        self.tools: list[BaseTool] = []
        self.mcp = mcp
        self._mcp_config_generators = ALL_MCP_CONFIG_GENERATORS
        self._built = False

    def with_config(self, config: StackConfig) -> "MCPStackCore":
        new = MCPStackCore(config=config, mcp=self.mcp)
        new.tools = self.tools[:]
        return new

    def with_tool(self, tool: BaseTool) -> "MCPStackCore":
        new = MCPStackCore(config=self.config, mcp=self.mcp)
        new.tools = [*self.tools, tool]
        return new

    def with_tools(self, tools: List[BaseTool]) -> "MCPStackCore":
        new = MCPStackCore(config=self.config, mcp=self.mcp)
        new.tools = self.tools + tools
        return new

    def with_preset(self, preset_name: str, **kwargs: Any) -> "MCPStackCore":
        from MCPStack.core.preset.registry import ALL_PRESETS
        if preset_name not in ALL_PRESETS:
            available = list(ALL_PRESETS.keys())
            best, score = process.extractOne(preset_name, available) or (None, 0)
            suggestion = f" Did you mean '{best}'?" if score >= 80 else ""
            raise MCPStackPresetError(f"Unknown preset: {preset_name}.{suggestion}")
        preset_class = ALL_PRESETS[preset_name]
        config = kwargs.pop("config", self.config)
        preset_stack = preset_class.create(config=config, **kwargs)  # type: ignore
        merged_tools = self.tools + preset_stack.tools
        new = MCPStackCore(config=preset_stack.config, mcp=preset_stack.mcp or self.mcp)
        new.tools = merged_tools
        return new

    def build(
        self,
        type: str = "fastmcp",
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        module_name: Optional[str] = None,
        pipeline_config_path: Optional[str] = None,
        save_path: Optional[str] = None,
    ) -> Union[dict, str]:
        self._validate()
        self._initialize_mcp()
        self._initialize_tools()
        self._register_actions()
        self._built = True
        return self._generate_config(
            type, command=command, args=args, cwd=cwd, module_name=module_name,
            pipeline_config_path=pipeline_config_path, save_path=save_path,
        )

    def run(self) -> None:
        if not self._built:
            raise MCPStackBuildError("Call .build() before .run()")
        if not self.mcp:
            raise MCPStackInitializationError("MCP not initialized")
        logger.info("Starting MCP server...")
        try:
            self.mcp.run()  # type: ignore
        finally:
            self._teardown_tools()
            logger.info("MCP server shutdown complete.")

    def save(self, path: str) -> None:
        if not self._built:
            raise MCPStackBuildError("Call .build() before .save()")

        def to_snake_case(name: str) -> str:
            return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

        data = {
            "config": self.config.to_dict(),
            "tools": [
                {
                    "type": to_snake_case(tool.__class__.__name__),
                    "params": tool.to_dict(),
                }
                for tool in self.tools
            ],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
        logger.info(f"✅ Saved pipeline config to {path}.")

    @classmethod
    def load(cls, path: str) -> "MCPStackCore":
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config not found: {path}")
        with open(path) as f:
            data = json.load(f)
        config = StackConfig.from_dict(data["config"])
        instance = cls(config=config)
        for tool_data in data.get("tools", []):
            tool_type = tool_data["type"]
            if tool_type not in ALL_TOOLS:
                raise MCPStackValidationError(f"Unknown tool type: {tool_type}")
            tool_cls = ALL_TOOLS[tool_type]
            tool = tool_cls.from_dict(tool_data["params"])  # type: ignore
            instance = instance.with_tool(tool)
        instance._post_load()
        instance._built = True
        logger.info(f"Pipeline loaded from {path}")
        return instance

    def _validate(self) -> None:
        if not self.tools:
            raise MCPStackValidationError("At least one tool must be added.")
        self.config.validate_for_tools(self.tools)

    def _initialize_mcp(self) -> None:
        if not self.mcp:
            self.mcp = FastMCP("mcpstack")

    def _initialize_tools(self) -> None:
        for tool in self.tools:
            tool.initialize()

    def _register_actions(self) -> None:
        actions = [action for tool in self.tools for action in tool.actions()]
        for action in actions:
            self.mcp.tool()(action)  # type: ignore

    def _generate_config(self, type: str, **kwargs) -> Union[dict, str]:
        if type not in self._mcp_config_generators:
            available = list(self._mcp_config_generators.keys())
            best, score = process.extractOne(type, available) or (None, 0)
            suggestion = f" Did you mean '{best}'?" if score >= 80 else ""
            raise MCPStackValidationError(f"Unknown config type: {type}.{suggestion}")
        generator_class = self._mcp_config_generators[type]
        return generator_class.generate(self, **kwargs)  # type: ignore

    def _teardown_tools(self) -> None:
        for tool in self.tools:
            if hasattr(tool, "backends"):
                for backend in getattr(tool, "backends", {}).values():
                    try:
                        if hasattr(backend, "teardown"):
                            backend.teardown()
                    except Exception:
                        pass

    def _post_load(self) -> None:
        for tool in self.tools:
            tool.post_load()
        if self.mcp:
            self._register_actions()
        self._built = True
