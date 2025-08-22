import json
import logging
import os

from beartype import beartype
from beartype.typing import Any, List, Optional, Union
from fastmcp import FastMCP
from thefuzz import process

from MCPStack.core.config import StackConfig
from MCPStack.core.mcp_config_generator.registry import ALL_MCP_CONFIG_GENERATORS
from MCPStack.core.tool.base import BaseTool
from MCPStack.core.utils.exceptions import (
    MCPStackBuildError,
    MCPStackInitializationError,
    MCPStackPresetError,
    MCPStackValidationError,
)
from MCPStack.tools.registry import ALL_TOOLS

logger = logging.getLogger(__name__)


@beartype
class MCPStackCore:
    """Composable, chainable core for building and running MCPStack MCP tool pipelines.

    Build a pipeline by chaining calls like :meth:`with_tool`, :meth:`with_preset`,
    then invoking :meth:`build` and :meth:`run`.

    !!! tip "Fluent API"
        All `with_*` methods return a **new** `MCPStackCore`, enabling
        clean, stack-like composition without mutating the original.

    !!! note "What happens during `build()`?"
        Tools are validated against the attached :class:`StackConfig`, then
        initialized and their actions registered on the MCP server. No external
        side effects occur before `build()`.

    Attributes:
        config (StackConfig): Configuration object (env vars, paths, etc.).
        tools (list[BaseTool]): Tools staged for initialization/registration.
        mcp (FastMCP | None): Optional pre-initialized MCP server instance.
        _mcp_config_generators (dict[str, Any]): Registry of config generators.
        _built (bool): Whether the stack has been successfully built.

    Examples:
        ```python
        from MCPStack.core.config import StackConfig
        from MCPStack.example_tools import MyTool

        stack = (
            MCPStackCore(StackConfig())
            .with_tool(MyTool(...))
            .build(type="fastmcp")
        )

        # Optionally save the config to a file
        stack.save("my_pipeline_config.json")

        # Optionally start serving (may block depending on host)
        # stack.run()
        ```
    """

    def __init__(
        self, config: Optional[StackConfig] = None, mcp: Optional[FastMCP] = None
    ) -> None:
        """Initialize an empty MCP stack.

        Args:
            config: Optional stack-level configuration. If `None`, a default
                :class:`StackConfig` is created.
            mcp: Optional pre-initialized :class:`FastMCP` server.

        !!! tip "When to pass `mcp`?"
            Supply a custom `FastMCP` if you need non-default server behavior
            (e.g., custom name or host integration). Otherwise it's created
            lazily.
        """
        self.config = config or StackConfig()
        self.tools: list[BaseTool] = []
        self.mcp = mcp
        self._mcp_config_generators = ALL_MCP_CONFIG_GENERATORS
        self._built = False

    def with_config(self, config: StackConfig) -> "MCPStackCore":
        """Return a new stack using the provided configuration.

        This method **does not** mutate the current instance; it returns a clone
        with the same tools and MCP reference but a different `config`.

        Args:
            config: Configuration used for env/validation/paths.

        Returns:
            MCPStackCore: New stack instance with `config` applied.

        !!! tip "Apply early"
            If tools depend on env vars or paths, call this before adding them.
        """
        new = MCPStackCore(config=config, mcp=self.mcp)
        new.tools = self.tools[:]
        return new

    def with_tool(self, tool: BaseTool) -> "MCPStackCore":
        """Return a new stack with one additional tool.

        Tools are initialized and their actions registered **during**
        :meth:`build` in the order they were added.

        Args:
            tool: Tool instance to include.

        Returns:
            MCPStackCore: New stack instance including the tool.

        !!! note "Order matters"
            Many toolchains assume earlier tools register primitives consumed
            by later tools. Add in dependency order.
        """
        new = MCPStackCore(config=self.config, mcp=self.mcp)
        new.tools = [*self.tools, tool]
        return new

    def with_tools(self, tools: List[BaseTool]) -> "MCPStackCore":
        """Return a new stack with multiple tools appended.

        Args:
            tools: List of tool instances.

        Returns:
            MCPStackCore: New stack instance with the tools appended.
        """
        new = MCPStackCore(config=self.config, mcp=self.mcp)
        new.tools = self.tools + tools
        return new

    def with_preset(self, preset_name: str, **kwargs: Any) -> "MCPStackCore":
        """Extend the stack using a preset factory and return a new instance.

        A **preset** is a predefined pipeline configuration (tools + config)
        bundled for common use cases or reproducible experiments.

        Args:
            preset_name: Name of the preset in the preset registry.
            **kwargs: Extra parameters forwarded to the preset factory. If a
                `config` is provided here, it supersedes the current one for
                the merged stack.

        Returns:
            MCPStackCore: New stack instance with merged tools/config.

        Raises:
            MCPStackPresetError: If the preset name is unknown.

        !!! tip "Discover presets"
            Use the CLI: `mcpstack list-presets`.
        """
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
        **kwargs: Any,
    ) -> Union[dict, str]:
        """Validate, initialize, and register all tools; generate a config.

        The stack becomes **ready to run** after this call. The returned object
        is typically an MCP host configuration (format depends on `type`).

        Args:
            type: Key into the MCP config generator registry (e.g. `"fastmcp"`).
            command: Optional command for generator backends that spawn processes.
            args: Optional arg list for `command`.
            cwd: Working directory for process-based backends.
            module_name: Python module path for module-based backends.
            pipeline_config_path: Optional path to an existing pipeline config to
                incorporate/augment.
            save_path: Optional path where the generated config should be saved
                by the generator (if supported).

        Returns:
            dict | str: Generated configuration payload (type-specific).

        Raises:
            MCPStackValidationError: Invalid configuration or tool requirements.
            MCPStackInitializationError: A tool failed to initialize.

        !!! success "Idempotent"
            Safe to call multiple times; subsequent calls are no-ops if already
            built.

        !!! warning "Validation happens first"
            Environment and tool requirements are checked before any tool is
            initialized; failures raise before partial state is created.
        """
        self._validate()
        self._initialize_mcp()
        self._initialize_tools()
        self._register_actions()
        self._built = True
        return self._generate_config(
            type,
            command=command,
            args=args,
            cwd=cwd,
            module_name=module_name,
            pipeline_config_path=pipeline_config_path,
            save_path=save_path,
            **kwargs,
        )

    def run(self) -> None:
        """Start serving the `FastMCP` server (blocking in most hosts).

        Raises:
            MCPStackBuildError: If the stack hasn't been built yet.
            MCPStackInitializationError: If MCP failed to initialize.

        !!! warning "Blocking call"
            Some MCP hosts block the current thread until interrupted (e.g.,
            Ctrl/CMD+C). Teardown hooks will run on exit.

        !!! tip "Programmatic lifecycle"
            Wrap in `try/finally` or use external supervisors if you need
            robust restarts.
        """
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
        """Serialize the stack (config + tools) to a JSON file.

        Args:
            path: Filesystem path to write the JSON config.

        Raises:
            MCPStackBuildError: If called before :meth:`build`.

        !!! note "Security"
            Credentials are not written unless you explicitly put them in env
            vars. Nevertheless, audit your config for sensitive data before
            sharing. If fully-local usage, it could be "fine", yet do not share anything sensitive
            via PR or public-repo.

        !!! example "Output shape"
            ```json
            {
              "config": { ... },
              "tools": [
                {"type": "retriever", "params": { ... }},
                {"type": "writer", "params": { ... }}
              ]
            }
            ```
        """
        if not self._built:
            raise MCPStackBuildError("Call .build() before .save()")

        data = {
            "config": self.config.to_dict(),
            "tools": [
                {
                    "type": tool.__class__.__name__.lower(),
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
        """Load a stack configuration previously written by :meth:`save`.

        Args:
            path: Path to a JSON config file produced by :meth:`save`.

        Returns:
            MCPStackCore: A new stack instance reconstructed from the file.

        Raises:
            FileNotFoundError: If `path` doesn't exist.
            MCPStackValidationError: The file is malformed or references an
                unknown tool type.

        !!! tip "Post-load hooks"
            Each tool's `post_load()` is invoked to re-establish any backends
            or transient resources. Actions are re-registered with MCP.

        !!! warning "Version skew"
            If tool code changed since saving, ensure `from_dict` and
            `post_load` handle migration.
        """
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
        """Create the MCP server if not already provided.

        Side Effects:
            Sets `self.mcp` to a default :class:`FastMCP("mcpstack")` if `None`.
        """
        if not self.mcp:
            self.mcp = FastMCP("mcpstack")

    def _initialize_tools(self) -> None:
        """Call `initialize()` on each tool in insertion order.

        Raises:
            MCPStackInitializationError: Propagated if a tool's initialization
                intentionally raises; otherwise errors may bubble from tools.

        !!! tip "Keep init idempotent"
            Tool `initialize()` should be safe to call more than once.
        """
        for tool in self.tools:
            tool.initialize()

    def _register_actions(self) -> None:
        """Register all tool actions with the MCP server.

        Implementation detail:
            Flattens `tool.actions()` across all tools and registers each
            callable with `self.mcp.tool()` decorator.
        """
        actions = [action for tool in self.tools for action in tool.actions()]
        for action in actions:
            self.mcp.tool()(action)  # type: ignore

    def _generate_config(self, type: str, **kwargs) -> Union[dict, str]:
        """Generate an MCP host configuration via a registered generator.

        Args:
            type: Generator key (e.g., `"fastmcp"`).
            **kwargs: Forwarded to the generator's `generate(...)`.

        Returns:
            dict | str: Generator-specific configuration artifact.

        Raises:
            MCPStackValidationError: If `type` is unknown (with fuzzy suggestion).

        !!! example "Choosing a generator"
            ```python
            cfg = stack.build(type="fastmcp", save_path="mcp.json")
            ```
        """
        if type not in self._mcp_config_generators:
            available = list(self._mcp_config_generators.keys())
            best, score = process.extractOne(type, available) or (None, 0)
            suggestion = f" Did you mean '{best}'?" if score >= 80 else ""
            raise MCPStackValidationError(f"Unknown config type: {type}.{suggestion}")
        generator_class = self._mcp_config_generators[type]
        return generator_class.generate(self, **kwargs)  # type: ignore

    def _teardown_tools(self) -> None:
        """Best-effort teardown of tool backends after server shutdown.

        This traverses `tool.backends` (if present) and calls `backend.teardown()`
        when available, ignoring exceptions to guarantee best-effort cleanup.

        !!! note "Why ignore exceptions?"
            Teardown should not mask or replace the primary error context during
            shutdown; tools are responsible for robust cleanup.
        """
        for tool in self.tools:
            if hasattr(tool, "backends"):
                for backend in getattr(tool, "backends", {}).values():
                    try:
                        if hasattr(backend, "teardown"):
                            backend.teardown()
                    except Exception:
                        pass

    def _post_load(self) -> None:
        """Finalize a stack created by :meth:`load`.

        Calls `post_load()` on tools, re-registers actions (if MCP exists),
        and marks the stack as built.

        !!! success "Ready to run"
            After `_post_load`, you can call :meth:`run` without another
            :meth:`build`.
        """
        for tool in self.tools:
            tool.post_load()
        if self.mcp:
            self._register_actions()
        self._built = True
