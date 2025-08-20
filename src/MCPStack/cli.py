import importlib
import inspect
import json
import logging
import os
import sys
from pathlib import Path

import rich.box as box
import typer
from beartype import beartype
from beartype.typing import Annotated, Dict, Optional
from rich.cells import cell_len
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich_pyfiglet import RichFiglet
from thefuzz import process

from MCPStack.core.config import StackConfig
from MCPStack.core.preset.registry import ALL_PRESETS
from MCPStack.core.tool.cli.base import BaseToolCLI
from MCPStack.core.utils.exceptions import MCPStackPresetError
from MCPStack.core.utils.logging import setup_logging
from MCPStack.stack import MCPStackCore
from MCPStack.tools.registry import ALL_TOOLS

logger = logging.getLogger(__name__)
console = Console()


@beartype
class StackCLI:
    """Rich TUI CLI for composing, building, and running MCPStack pipelines.

    The CLI wraps :class:`MCPStackCore` for quick, scriptable workflows:
    listing presets/tools, composing pipelines, building configs, and running
    the MCP server.

    !!! tip "Completion & help"
        Use `--help` on the root and each subcommand for detailed usage and
        options. Flags shown in help mirror the method parameters below.

    Attributes:
        app (typer.Typer): Root Typer application.
        tools_app (typer.Typer): Sub-application mounted under `tools` for
            tool-specific subcommands, if provided by a tool.
        tool_clis (dict[str, typer.Typer]): Loaded tool CLI apps by tool name.

    Examples:
        ```bash
        mcpstack --help
        mcpstack list-presets
        mcpstack build --presets example_preset --config-type fastmcp
        mcpstack run --presets example_preset
        mcpstack tools my_tool --help
        mcpstack pipeline my_tool --new-pipeline my_pipeline.json
        mcpstack pipeline my_tool_2 --to-pipeline my_pipeline.json
        mcpstack search one_tool_named_hello_world --type tools
        mcpstack search example --type presets
        ```
    """

    def __init__(self) -> None:
        self._display_banner()
        self.app: typer.Typer = typer.Typer(
            help="MCPStack CLI",
            add_completion=False,
            pretty_exceptions_show_locals=False,
            rich_markup_mode="markdown",
        )
        self.app.callback()(self.main_callback)
        self.app.command(help="List available presets.")(self.list_presets)
        self.app.command(help="List available tools.")(self.list_tools)
        self.app.command(help="Run MCPStack: build + run MCP server.")(self.run)
        self.app.command(help="Build an MCP host configuration without running.")(
            self.build
        )
        self.app.command(help="Compose or extend a pipeline with a tool.")(
            self.pipeline
        )
        self.app.command(help="Search presets/tools.")(self.search)

        # Tool-specific subcommands (loaded if a tool provides a CLI module)
        self.tools_app: typer.Typer = typer.Typer(help="Tool-specific commands.")
        self.app.add_typer(
            self.tools_app, name="tools", help="Tool-specific subcommands."
        )
        self.tool_clis = self._load_tool_clis()

    def __call__(self) -> None:
        self.app()

    @staticmethod
    def version_callback(value: Optional[bool]) -> Optional[bool]:
        """Handle `--version` eagerly and exit if provided.

        Args:
            value: Flag value parsed by Typer.

        Returns:
            Optional[bool]: `value` so Typer can continue parsing when False.

        Behavior:
            When `True`, prints the MCPStack CLI version and exits the process.
        """
        if value:
            from MCPStack import __version__

            console.print(
                f"[bold green]💬 MCPStack CLI Version: {__version__}[/bold green]"
            )
            raise typer.Exit()
        return value

    def main_callback(
        self,
        version: Annotated[
            Optional[bool],
            typer.Option(
                "--version",
                "-v",
                # is_flag=True,  # make it a flag
                is_eager=True,  # run early
                callback=version_callback.__func__,  # staticmethod
                help="Show CLI version and exit.",
            ),
        ] = False,
        verbose: Annotated[
            bool, typer.Option("--verbose", "-V", help="Enable DEBUG level logging.")
        ] = False,
    ) -> None:
        level = "DEBUG" if verbose else "INFO"
        setup_logging(level=level)
        if verbose:
            logger.debug("Verbose mode enabled.")

    def list_presets(self) -> None:
        """List available presets from the registry.

        Output:
            Prints a Rich table of preset names, or a placeholder if none.

        !!! tip "Where do presets come from?"
            Presets are discovered from :mod:`MCPStack.core.preset.registry`.
        """
        console.print("[bold green]💬 Available Presets[/bold green]")
        table = Table(title="")
        table.add_column("Preset", style="cyan")
        for preset in ALL_PRESETS.keys():
            table.add_row(preset)
        if not ALL_PRESETS:
            table.add_row("[dim]— none registered —[/dim]")
        console.print(table)

    def list_tools(self) -> None:
        """List discovered tools (built-in and entry-point based).

        Output:
            Prints a Rich table of tool names, or a placeholder if none.

        !!! note "Discovery"
            Tools are sourced from :mod:`MCPStack.tools.registry`.
        """
        console.print("[bold green]💬 Available Tools[/bold green]")
        table = Table(title="")
        table.add_column("Tool", style="cyan")
        for tool in ALL_TOOLS.keys():
            table.add_row(tool)
        if not ALL_TOOLS:
            table.add_row("[dim]— none registered —[/dim]")
        console.print(table)

    def run(
        self,
        pipeline: Annotated[
            Optional[str],
            typer.Option("--pipeline", help="Pipeline JSON path (!= Presets)."),
        ] = None,
        presets: Annotated[
            Optional[str],
            typer.Option("--presets", help="Comma-separated pipeline presets."),
        ] = "example_preset",
        config_type: Annotated[
            str, typer.Option("--config-type", help="MCP host configuration type.")
        ] = "fastmcp",
        config_path: Annotated[
            Optional[str],
            typer.Option("--config-path", "-c", help="Where to save pipeline JSON."),
        ] = None,
        show_status: Annotated[
            bool, typer.Option("--show-status", help="Display tool status post-build.")
        ] = True,
        command: Annotated[
            Optional[str], typer.Option("--command", help="Command for MCP host.")
        ] = None,
        args: Annotated[
            Optional[str],
            typer.Option("--args", help="Comma-separated args for MCP host."),
        ] = None,
        cwd: Annotated[
            Optional[str], typer.Option("--cwd", help="Working directory for MCP host.")
        ] = None,
        module_name: Annotated[
            Optional[str],
            typer.Option("--module-name", help="Module name for default args."),
        ] = None,
    ) -> None:
        """Build the (possibly preset-based) pipeline and run the MCP server.

        Args:
            pipeline: Path to an existing pipeline JSON to load and run.
            presets: Comma-separated list of preset names to compose (ignored
                if `pipeline` is provided).
            config_type: Config generator key (e.g. `"fastmcp"`).
            config_path: Target path to write the pipeline JSON (default:
                `mcpstack_pipeline.json`), ignored when `pipeline` points to an
                existing file.
            show_status: Whether to display tool statuses after build.
            command: Optional command used by certain config generators.
            args: Optional comma-separated args to pass with `command`.
            cwd: Working directory used by some host backends.
            module_name: Module path used by module-based hosts.

        Behavior:
            * Loads a pipeline from `--pipeline` **or** composes from `--presets`.
            * Builds the stack, saves the pipeline JSON, and starts the MCP server.
            * Displays errors via Rich and exits non-zero on failure.

        !!! warning "Mutually exclusive"
            `--pipeline` and `--config-path` cannot be used together.
        """
        console.print("[bold green]💬 Starting MCPStack run...[/bold green]")
        try:
            if pipeline and config_path:
                raise ValueError("Cannot specify both --pipeline and --config-path.")
            config = StackConfig(env_vars=os.environ.copy())
            _config_path = config_path or pipeline or "mcpstack_pipeline.json"
            _config_path = os.path.abspath(_config_path)
            if pipeline:
                console.print(
                    f"[bold green]💬 Loaded pipeline: {pipeline}[/bold green]"
                )
                stack = MCPStackCore.load(pipeline)
            else:
                stack = MCPStackCore(config=config)
                preset_list = [p.strip() for p in presets.split(",")] if presets else []
                for preset in preset_list:
                    if preset not in ALL_PRESETS:
                        available_presets = list(ALL_PRESETS.keys())
                        best_match, score = process.extractOne(
                            preset, available_presets
                        ) or (None, 0)
                        suggestion_text = (
                            f" Did you mean '{best_match}'?" if score >= 80 else ""
                        )
                        raise MCPStackPresetError(
                            f"Unknown preset: {preset}.{suggestion_text}"
                        )
                    console.print(
                        f"[bold green]💬 Applying preset '{preset}'...[/bold green]"
                    )
                    stack = stack.with_preset(preset)
            console.print(
                f"[bold green]💬 Building with config type '{config_type}'...[/bold green]"
            )
            args_list = args.split(",") if args else None
            stack.build(
                type=config_type,
                command=command,
                args=args_list,
                cwd=cwd,
                module_name=module_name,
                pipeline_config_path=_config_path,
                save_path=None,
            )
            stack.save(_config_path)
            console.print(
                f"[bold green]💬 ✅ Saved pipeline config to {_config_path}.[/bold green]"
            )
            console.print("[bold green]💬 Starting MCP server...[/bold green]")
            stack.run()
        except Exception as e:
            logger.error(f"Run failed: {e}", exc_info=True)
            console.print(f"[red]❌ Error: {e}[/red]")
            raise typer.Exit(code=1) from e

    def build(
        self,
        pipeline: Annotated[
            Optional[str],
            typer.Option("--pipeline", help="Pipeline JSON path (!= Presets)."),
        ] = None,
        presets: Annotated[
            Optional[str],
            typer.Option("--presets", help="Comma-separated pipeline presets."),
        ] = "example_preset",
        config_type: Annotated[
            str, typer.Option("--config-type", help="Configuration type for MCP host.")
        ] = "fastmcp",
        config_path: Annotated[
            Optional[str],
            typer.Option("--config-path", "-c", help="Where to save pipeline JSON."),
        ] = None,
        output: Annotated[
            Optional[str],
            typer.Option(
                "--output", "-o", help="Output path for MCP host configuration."
            ),
        ] = None,
        show_status: Annotated[
            bool, typer.Option("--show-status", help="Display tool status post-build.")
        ] = True,
        command: Annotated[
            Optional[str], typer.Option("--command", help="Command for MCP host.")
        ] = None,
        args: Annotated[
            Optional[str],
            typer.Option("--args", help="Comma-separated args for MCP host."),
        ] = None,
        cwd: Annotated[
            Optional[str], typer.Option("--cwd", help="Working directory for MCP host.")
        ] = None,
        module_name: Annotated[
            Optional[str],
            typer.Option("--module-name", help="Module name for default args."),
        ] = None,
    ) -> None:
        """Generate an MCP host configuration file without running.

        Args:
            pipeline: Path to an existing pipeline JSON to load and build from.
            presets: Comma-separated list of preset names to compose (ignored
                if `pipeline` is provided).
            config_type: Config generator key.
            config_path: Path to save the composed pipeline JSON.
            output: Optional path where the generated host config should be
                written by the generator (if supported).
            show_status: Whether to display tool statuses after build.
            command: Optional command for process-based generators.
            args: Optional comma-separated args for `command`.
            cwd: Working directory for the host/generator.
            module_name: Module path for module-based generators.

        Behavior:
            * Composes a pipeline (or loads one), builds it, saves the pipeline
              JSON, and optionally writes a host config to `--output`.

        !!! warning "Mutually exclusive"
            `--pipeline` and `--config-path` cannot be used together.
        """
        console.print("[bold green]💬 Starting MCPStack build...[/bold green]")
        try:
            if pipeline and config_path:
                raise ValueError("Cannot specify both --pipeline and --config-path.")
            config = StackConfig(env_vars=os.environ.copy())
            _config_path = config_path or pipeline or "mcpstack_pipeline.json"
            _config_path = os.path.abspath(_config_path)
            if pipeline:
                console.print(
                    f"[bold green]💬 Loaded pipeline: {pipeline}[/bold green]"
                )
                stack = MCPStackCore.load(pipeline)
            else:
                stack = MCPStackCore(config=config)
                preset_list = [p.strip() for p in presets.split(",")] if presets else []
                for preset in preset_list:
                    if preset not in ALL_PRESETS:
                        available_presets = list(ALL_PRESETS.keys())
                        best_match, score = process.extractOne(
                            preset, available_presets
                        ) or (None, 0)
                        suggestion_text = (
                            f" Did you mean '{best_match}'?" if score >= 80 else ""
                        )
                        raise MCPStackPresetError(
                            f"Unknown preset: {preset}.{suggestion_text}"
                        )
                    console.print(
                        f"[bold green]💬 Applying preset '{preset}'...[/bold green]"
                    )
                    stack = stack.with_preset(preset)
            _save_path = os.path.abspath(output) if output else None
            console.print(
                f"[bold green]💬 Building with config type '{config_type}'...[/bold green]"
            )
            args_list = args.split(",") if args else None
            stack.build(
                type=config_type,
                command=command,
                args=args_list,
                cwd=cwd,
                module_name=module_name,
                pipeline_config_path=_config_path,
                save_path=_save_path,
            )
            stack.save(_config_path)
            console.print("[bold green]💬 ✅ Pipeline config saved.[/bold green]")
        except Exception as e:
            logger.error(f"Build failed: {e}", exc_info=True)
            console.print(f"[red]❌ Error: {e}[/red]")
            raise typer.Exit(code=1) from e

    def pipeline(
        self,
        tool_name: Annotated[
            str, typer.Argument(help="Tool to add (registered name).")
        ],
        to_pipeline: Annotated[
            Optional[str],
            typer.Option("--to-pipeline", help="Append to existing pipeline JSON."),
        ] = None,
        new_pipeline: Annotated[
            Optional[str],
            typer.Option("--new-pipeline", help="Create new pipeline JSON at path."),
        ] = "mcpstack_pipeline.json",
        tool_config: Annotated[
            Optional[str],
            typer.Option("--tool-config", help="Path to tool config JSON."),
        ] = None,
    ) -> None:
        """Append a tool to a pipeline (existing or new) and save it.

        Args:
            tool_name: Registered tool name (see `list-tools`).
            to_pipeline: Path to an existing pipeline JSON to append to.
            new_pipeline: Path to create if `to_pipeline` is not supplied.
            tool_config: Path to a JSON file with `env_vars` and `tool_params`
                for the tool being added.

        Behavior:
            * Loads or creates a pipeline, merges env vars, constructs the tool
              from params, builds and saves the updated pipeline.

        !!! failure "Unknown tool?"
            If `tool_name` is not in the registry, the command suggests the
            closest match and exits with an error.
        """
        console.print(
            f"[bold green]💬 Adding tool '{tool_name}' to pipeline...[/bold green]"
        )
        if tool_name not in ALL_TOOLS:
            available = list(ALL_TOOLS.keys())
            best_match, score = process.extractOne(tool_name, available) or (None, 0)
            suggestion_text = f" Did you mean '{best_match}'?" if score >= 80 else ""
            console.print(f"[red]❌ Unknown tool: {tool_name}.{suggestion_text}[/red]")
            raise typer.Exit(code=1)
        try:
            if tool_config:
                with open(tool_config) as f:
                    tool_dict = json.load(f)
            else:
                tool_dict = {"env_vars": {}, "tool_params": {}}
            pipeline_path = to_pipeline or new_pipeline
            if to_pipeline and Path(to_pipeline).exists():
                stack: MCPStackCore = MCPStackCore.load(to_pipeline)
                console.print(f"[bold green]💬 Appending to {to_pipeline}[/bold green]")
            else:
                stack = MCPStackCore()
                console.print(
                    f"[bold green]💬 Creating new pipeline at {pipeline_path}[/bold green]"
                )
            stack.config.merge_env(tool_dict.get("env_vars", {}))
            tool_cls = ALL_TOOLS[tool_name]
            tool = tool_cls.from_dict(tool_dict.get("tool_params", {}))  # type: ignore
            stack = stack.with_tool(tool)
            stack.build()
            stack.save(pipeline_path)
            console.print(
                f"[bold green]💬 ✅ Pipeline updated: {pipeline_path} (tools: {len(stack.tools)})[/bold green]"
            )
        except Exception as e:
            logger.error(f"Failed to add {tool_name}: {e}", exc_info=True)
            console.print(f"[red]❌ Failed to add {tool_name}: {e}[/red]")
            raise typer.Exit(1) from e

    def search(
        self,
        query: str,
        type_: Annotated[
            str, typer.Option("--type", help="presets, tools, or both.")
        ] = "both",
        limit: int = 5,
    ) -> None:
        """Fuzzy-search across preset and tool names.

        Args:
            query: Search string.
            type_: Domain to search: `"presets"`, `"tools"`, or `"both"`.
            limit: Maximum number of matches to show for each domain.

        Output:
            Prints category tables with matches and scores.

        !!! tip "Partial names welcome"
            Short fragments are fine; results are ranked by fuzzy score.
        """
        console.print(f"[bold green]💬 Searching for '{query}'...[/bold green]")
        if type_ not in ["presets", "tools", "both"]:
            console.print(
                "[red]❌ Invalid type. Use `presets`, `tools`, or `both`.[/red]"
            )
            raise typer.Exit(code=1)
        results = []
        if type_ in ["presets", "both"]:
            presets = list(ALL_PRESETS.keys())
            from thefuzz import process as _p

            preset_matches = _p.extract(query, presets, limit=limit)
            results.append(("Presets", preset_matches))
        if type_ in ["tools", "both"]:
            tools = list(ALL_TOOLS.keys())
            from thefuzz import process as _p

            tool_matches = _p.extract(query, tools, limit=limit)
            results.append(("Tools", tool_matches))
        for category, matches in results:
            table = Table(title=f"[bold green]💬 {category} matches[/bold green]")
            table.add_column("Match", style="cyan")
            table.add_column("Score", style="magenta")
            for match, score in matches:
                table.add_row(str(match), str(score))
            console.print(table)

    def _load_tool_clis(self) -> Dict[str, typer.Typer]:
        """Discover and mount tool CLIs under `mcpstack tools`."""
        tool_clis: Dict[str, typer.Typer] = {}

        for tool_name in ALL_TOOLS:
            if app := self._load_tool_cli(tool_name):
                tool_clis[tool_name] = app
                self.tools_app.add_typer(
                    app, name=tool_name, help=f"{tool_name} tool commands."
                )
            else:
                logger.debug("No CLI found for tool '%s'", tool_name)

        return tool_clis

    @staticmethod
    def _load_tool_cli(tool_name: str):
        """Return a Typer app for a tool CLI, either internal or external"""
        try:
            from importlib.metadata import entry_points

            eps = entry_points().select(group="mcpstack.tool_clis")
            for ep in eps:
                if ep.name.lower() != tool_name.lower():
                    continue
                obj = ep.load()
                app = _materialize_cli_app(obj)
                if app:
                    return app
        except Exception as e:
            logger.debug(
                "Entry point CLI load failed for '%s': %s", tool_name, e, exc_info=True
            )

        try:
            module = importlib.import_module(f"MCPStack.tools.{tool_name}.cli")
            # Prefer a BaseToolCLI subclass, else a top-level get_app(), else a Typer app
            for _, cls in inspect.getmembers(module, inspect.isclass):
                if issubclass(cls, BaseToolCLI) and cls is not BaseToolCLI:
                    app = cls.get_app()
                    if app:
                        return app
            get_app = getattr(module, "get_app", None)
            if callable(get_app):
                return get_app()
        except ModuleNotFoundError:
            return None
        except Exception as e:
            logger.debug(
                "Built-in CLI load failed for '%s': %s", tool_name, e, exc_info=True
            )

        return None

    @staticmethod
    def _get_tool_cli_class(tool_name: str):
        """Return the BaseToolCLI subclass for a tool (if provided as a class).

        Supports:
          * Entry point 'mcpstack.tool_clis' (object must be a BaseToolCLI subclass)
          * MCPStack.tools.<tool_name>.cli (first-party fallback)

        If the CLI is exposed only as a callable / app, this accessor will not apply.
        """
        try:
            from importlib.metadata import entry_points

            eps = entry_points().select(group="mcpstack.tool_clis")
            for ep in eps:
                if ep.name.lower() != tool_name.lower():
                    continue
                obj = ep.load()
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, BaseToolCLI)
                    and obj is not BaseToolCLI
                ):
                    return obj
        except Exception:
            pass

        module = importlib.import_module(f"MCPStack.tools.{tool_name}.cli")
        tool_cli_classes = [
            obj
            for _, obj in inspect.getmembers(module)
            if inspect.isclass(obj)
            and issubclass(obj, BaseToolCLI)
            and obj is not BaseToolCLI
        ]
        if not tool_cli_classes:
            raise RuntimeError(f"No CLI class found for '{tool_name}'.")
        return tool_cli_classes[0]

    def _status(self, tool: Optional[str] = None, verbose: bool = False) -> None:
        """Render a status panel for a tool, showing env and configuration.

        Args:
            tool: Specific tool to inspect. If omitted, attempts all tools that
                expose a CLI.
            verbose: Whether to print extended diagnostics (tool-dependent).

        Output:
            Relies on each tool CLI's `status()` implementation to render.
        """
        console.print("[bold green]💬 Checking status...[/bold green]")
        tools_to_check = [tool] if tool else list(self._load_tool_clis().keys())
        for _tool in tools_to_check:
            try:
                tool_cli_class = self._get_tool_cli_class(_tool)
                tool_cli_class.status(verbose=verbose)
            except Exception as e:
                logger.debug(f"Status not available for '{_tool}': {e}")

    @staticmethod
    def _display_banner() -> None:
        """Render the banner header for the CLI when `--help` is detected.

        Behavior:
            Prints a stylized Rich panel with project name and version, using a
            multi-color figlet header when help is requested.

        !!! tip "Quiet mode"
            The banner is only displayed on help screens to avoid noisy output
            during normal command execution.
        """
        from MCPStack import __version__

        if any(arg in sys.argv for arg in ["--help", "-h"]):
            rich_fig = RichFiglet(
                "MCPStack",
                font="ansi_shadow",
                colors=["#0ea5e9", "#0ea5e9", "#0ea5e9", "#FFFFFF", "#FFFFFF"],
                horizontal=True,
                remove_blank_lines=True,
            )
            entries = [
                ("🏗️", " Project", "MCPStack — Modular MCP Pipelines"),
                ("🏎️", " Version", __version__),
            ]
            max_label_len = max(
                cell_len(emoji + " " + key + ":") for emoji, key, value in entries
            )
            group_items = [
                Text(""),
                Text(""),
                rich_fig,
                Text(""),
                Text("Composable MCP pipelines."),
                Text(""),
            ]
            for i, (emoji, key, value) in enumerate(entries):
                label_plain = emoji + " " + key + ":"
                label_len = cell_len(label_plain)
                spaces = " " * (max_label_len - label_len + 2)
                line = f"[turquoise4]{label_plain}[/turquoise4]{spaces}{value}"
                group_items.append(Text.from_markup(line))
                if i == 0:
                    group_items.append(Text(""))
            group_items += [Text(""), Text("")]
            console.print(
                Panel(
                    Group(*group_items),
                    title="MCPStack CLI",
                    width=80,
                    title_align="left",
                    expand=False,
                    box=box.ROUNDED,
                    padding=(1, 5),
                )
            )


def _materialize_cli_app(obj):
    """Return a Typer app from an entry-point object.

    Accepts:
      - BaseToolCLI subclass (calls get_app())
      - Callable returning a Typer app
      - A Typer app instance directly
    """
    try:
        if (
            inspect.isclass(obj)
            and issubclass(obj, BaseToolCLI)
            and obj is not BaseToolCLI
        ):
            return obj.get_app()
        if callable(obj):
            return obj()
        if hasattr(obj, "registered_groups") or obj.__class__.__name__ == "Typer":
            return obj
    except Exception as e:
        logger.debug("Failed materializing Typer app: %s", e, exc_info=True)
    return None


def main_cli() -> None:
    StackCLI()()
