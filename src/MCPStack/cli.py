import importlib, inspect, json, logging, os, sys
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
from MCPStack.core.utils.logging import setup_logging
from MCPStack.core.tool.cli.base import BaseToolCLI
from MCPStack.core.utils.exceptions import MCPStackPresetError
from MCPStack.stack import MCPStackCore
from MCPStack.tools.registry import ALL_TOOLS
from MCPStack.core.preset.registry import ALL_PRESETS

logger = logging.getLogger(__name__)
console = Console()

@beartype
class StackCLI:
    def __init__(self) -> None:
        self._display_banner()
        self.app: typer.Typer = typer.Typer(
            help="MCPStack CLI", add_completion=False, pretty_exceptions_show_locals=False, rich_markup_mode="markdown",
        )
        self.app.callback()(self.main_callback)
        self.app.command(help="List available presets.")(self.list_presets)
        self.app.command(help="List available tools.")(self.list_tools)
        self.app.command(help="Run MCPStack: build + run MCP server.")(self.run)
        self.app.command(help="Build an MCP host configuration without running.")(self.build)
        self.app.command(help="Compose or extend a pipeline with a tool.")(self.pipeline)
        self.app.command(help="Search presets/tools.")(self.search)

        # Tool-specific subcommands (loaded if a tool provides a CLI module)
        self.tools_app: typer.Typer = typer.Typer(help="Tool-specific commands.")
        self.app.add_typer(self.tools_app, name="tools", help="Tool-specific subcommands.")
        self.tool_clis = self._load_tool_clis()

    def __call__(self) -> None:
        self.app()

    @staticmethod
    def version_callback(value: Optional[bool]) -> Optional[bool]:
        """Eager flag handler; returns value so Typer can continue parsing."""
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
        console.print("[bold green]💬 Available Presets[/bold green]")
        table = Table(title="")
        table.add_column("Preset", style="cyan")
        for preset in ALL_PRESETS.keys():
            table.add_row(preset)
        if not ALL_PRESETS:
            table.add_row("[dim]— none registered —[/dim]")
        console.print(table)

    def list_tools(self) -> None:
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
        pipeline: Annotated[Optional[str], typer.Option("--pipeline", help="Pipeline JSON path (!= Presets).")] = None,
        presets: Annotated[Optional[str], typer.Option("--presets", help="Comma-separated pipeline presets.")]="example_preset",
        config_type: Annotated[str, typer.Option("--config-type", help="MCP host configuration type.")] = "fastmcp",
        config_path: Annotated[Optional[str], typer.Option("--config-path","-c", help="Where to save pipeline JSON.")] = None,
        show_status: Annotated[bool, typer.Option("--show-status", help="Display tool status post-build.")] = True,
        command: Annotated[Optional[str], typer.Option("--command", help="Command for MCP host.")] = None,
        args: Annotated[Optional[str], typer.Option("--args", help="Comma-separated args for MCP host.")] = None,
        cwd: Annotated[Optional[str], typer.Option("--cwd", help="Working directory for MCP host.")] = None,
        module_name: Annotated[Optional[str], typer.Option("--module-name", help="Module name for default args.")] = None,
    ) -> None:
        console.print("[bold green]💬 Starting MCPStack run...[/bold green]")
        try:
            if pipeline and config_path:
                raise ValueError("Cannot specify both --pipeline and --config-path.")
            config = StackConfig(env_vars=os.environ.copy())
            _config_path = config_path or pipeline or "mcpstack_pipeline.json"
            _config_path = os.path.abspath(_config_path)
            if pipeline:
                console.print(f"[bold green]💬 Loaded pipeline: {pipeline}[/bold green]")
                stack = MCPStackCore.load(pipeline)
            else:
                stack = MCPStackCore(config=config)
                preset_list = [p.strip() for p in presets.split(",")] if presets else []
                for preset in preset_list:
                    if preset not in ALL_PRESETS:
                        available_presets = list(ALL_PRESETS.keys())
                        best_match, score = process.extractOne(preset, available_presets) or (None, 0)
                        suggestion_text = f" Did you mean '{best_match}'?" if score >= 80 else ""
                        raise MCPStackPresetError(f"Unknown preset: {preset}.{suggestion_text}")
                    console.print(f"[bold green]💬 Applying preset '{preset}'...[/bold green]")
                    stack = stack.with_preset(preset)
            console.print(f"[bold green]💬 Building with config type '{config_type}'...[/bold green]")
            args_list = args.split(",") if args else None
            stack.build(type=config_type, command=command, args=args_list, cwd=cwd, module_name=module_name, pipeline_config_path=_config_path, save_path=None)
            stack.save(_config_path)
            console.print(f"[bold green]💬 ✅ Saved pipeline config to {_config_path}.[/bold green]")
            console.print("[bold green]💬 Starting MCP server...[/bold green]")
            stack.run()
        except Exception as e:
            logger.error(f"Run failed: {e}", exc_info=True)
            console.print(f"[red]❌ Error: {e}[/red]")
            raise typer.Exit(code=1) from e

    def build(
        self,
        pipeline: Annotated[Optional[str], typer.Option("--pipeline", help="Pipeline JSON path (!= Presets).")] = None,
        presets: Annotated[Optional[str], typer.Option("--presets", help="Comma-separated pipeline presets.")]="example_preset",
        config_type: Annotated[str, typer.Option("--config-type", help="Configuration type for MCP host.")] = "fastmcp",
        config_path: Annotated[Optional[str], typer.Option("--config-path","-c", help="Where to save pipeline JSON.")] = None,
        output: Annotated[Optional[str], typer.Option("--output","-o", help="Output path for MCP host configuration.")] = None,
        show_status: Annotated[bool, typer.Option("--show-status", help="Display tool status post-build.")] = True,
        command: Annotated[Optional[str], typer.Option("--command", help="Command for MCP host.")] = None,
        args: Annotated[Optional[str], typer.Option("--args", help="Comma-separated args for MCP host.")] = None,
        cwd: Annotated[Optional[str], typer.Option("--cwd", help="Working directory for MCP host.")] = None,
        module_name: Annotated[Optional[str], typer.Option("--module-name", help="Module name for default args.")] = None,
    ) -> None:
        console.print("[bold green]💬 Starting MCPStack build...[/bold green]")
        try:
            if pipeline and config_path:
                raise ValueError("Cannot specify both --pipeline and --config-path.")
            config = StackConfig(env_vars=os.environ.copy())
            _config_path = config_path or pipeline or "mcpstack_pipeline.json"
            _config_path = os.path.abspath(_config_path)
            if pipeline:
                console.print(f"[bold green]💬 Loaded pipeline: {pipeline}[/bold green]")
                stack = MCPStackCore.load(pipeline)
            else:
                stack = MCPStackCore(config=config)
                preset_list = [p.strip() for p in presets.split(",")] if presets else []
                for preset in preset_list:
                    if preset not in ALL_PRESETS:
                        available_presets = list(ALL_PRESETS.keys())
                        best_match, score = process.extractOne(preset, available_presets) or (None, 0)
                        suggestion_text = f" Did you mean '{best_match}'?" if score >= 80 else ""
                        raise MCPStackPresetError(f"Unknown preset: {preset}.{suggestion_text}")
                    console.print(f"[bold green]💬 Applying preset '{preset}'...[/bold green]")
                    stack = stack.with_preset(preset)
            _save_path = os.path.abspath(output) if output else None
            console.print(f"[bold green]💬 Building with config type '{config_type}'...[/bold green]")
            args_list = args.split(",") if args else None
            stack.build(type=config_type, command=command, args=args_list, cwd=cwd, module_name=module_name, pipeline_config_path=_config_path, save_path=_save_path)
            stack.save(_config_path)
            console.print("[bold green]💬 ✅ Pipeline config saved.[/bold green]")
        except Exception as e:
            logger.error(f"Build failed: {e}", exc_info=True)
            console.print(f"[red]❌ Error: {e}[/red]")
            raise typer.Exit(code=1) from e

    def pipeline(
        self,
        tool_name: Annotated[str, typer.Argument(help="Tool to add (registered name).")],
        to_pipeline: Annotated[Optional[str], typer.Option("--to-pipeline", help="Append to existing pipeline JSON.")]=None,
        new_pipeline: Annotated[Optional[str], typer.Option("--new-pipeline", help="Create new pipeline JSON at path.")]="mcpstack_pipeline.json",
        tool_config: Annotated[Optional[str], typer.Option("--tool-config", help="Path to tool config JSON.")] = None,
    ) -> None:
        console.print(f"[bold green]💬 Adding tool '{tool_name}' to pipeline...[/bold green]")
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
                print(f"YOOOO?")
                console.print(f"[bold green]💬 Appending to {to_pipeline}[/bold green]")
            else:
                stack = MCPStackCore()
                console.print(f"[bold green]💬 Creating new pipeline at {pipeline_path}[/bold green]")
            stack.config.merge_env(tool_dict.get("env_vars", {}))
            tool_cls = ALL_TOOLS[tool_name]
            tool = tool_cls.from_dict(tool_dict.get("tool_params", {}))  # type: ignore
            print(f"TOOL: {tool}")
            stack = stack.with_tool(tool)
            print(f"sTack: {stack}")
            stack.build()
            stack.save(pipeline_path)
            console.print(f"[bold green]💬 ✅ Pipeline updated: {pipeline_path} (tools: {len(stack.tools)})[/bold green]")
        except Exception as e:
            logger.error(f"Failed to add {tool_name}: {e}", exc_info=True)
            console.print(f"[red]❌ Failed to add {tool_name}: {e}[/red]")
            raise typer.Exit(1) from e

    def search(self, query: str, type_: Annotated[str, typer.Option("--type", help="presets, tools, or both.")]="both", limit: int = 5) -> None:
        console.print(f"[bold green]💬 Searching for '{query}'...[/bold green]")
        if type_ not in ["presets", "tools", "both"]:
            console.print("[red]❌ Invalid type. Use `presets`, `tools`, or `both`.[/red]")
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
        tool_clis = {}
        for tool_name in ALL_TOOLS:
            if cli := self._load_tool_cli(tool_name):
                tool_clis[tool_name] = cli
                self.tools_app.add_typer(cli, name=tool_name, help=f"{tool_name} tool commands.")
        return tool_clis

    @staticmethod
    def _load_tool_cli(tool_name: str):
        try:
            module = importlib.import_module(f"MCPStack.tools.{tool_name}.cli")
            tool_cli_classes = [
                obj for _, obj in inspect.getmembers(module)
                if inspect.isclass(obj) and issubclass(obj, BaseToolCLI) and obj is not BaseToolCLI
            ]
            if not tool_cli_classes:
                return None
            app = tool_cli_classes[0].get_app()
            return app
        except ModuleNotFoundError:
            return None
        except Exception as e:
            logger.debug(f"Failed loading CLI for '{tool_name}': {e}")
            return None

    @staticmethod
    def _get_tool_cli_class(tool_name: str):
        module = importlib.import_module(f"MCPStack.tools.{tool_name}.cli")
        tool_cli_classes = [
            obj for _, obj in inspect.getmembers(module)
            if inspect.isclass(obj) and issubclass(obj, BaseToolCLI) and obj is not BaseToolCLI
        ]
        if not tool_cli_classes:
            raise RuntimeError(f"No CLI class found for '{tool_name}'.")
        return tool_cli_classes[0]

    def _status(self, tool: Optional[str] = None, verbose: bool = False) -> None:
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
        from MCPStack import __version__

        if any(arg in sys.argv for arg in ["--help", "-h"]):
            rich_fig = RichFiglet("MCPStack", font="ansi_shadow", colors=["#0ea5e9", "#0ea5e9", "#0ea5e9", "#FFFFFF", "#FFFFFF"], horizontal=True, remove_blank_lines=True,)
            entries = [("🏗️", " Project", "MCPStack — Modular MCP Pipelines"), ("🏎️", " Version", __version__)]
            max_label_len = max(cell_len(emoji + " " + key + ":") for emoji, key, value in entries)
            group_items = [Text(""), Text(""), rich_fig, Text(""), Text("Composable MCP pipelines."), Text("")]
            for i, (emoji, key, value) in enumerate(entries):
                label_plain = emoji + " " + key + ":"
                label_len = cell_len(label_plain)
                spaces = " " * (max_label_len - label_len + 2)
                line = f"[turquoise4]{label_plain}[/turquoise4]{spaces}{value}"
                group_items.append(Text.from_markup(line))
                if i == 0:
                    group_items.append(Text(""))
            group_items += [Text(""), Text("")]
            console.print(Panel(Group(*group_items), title="MCPStack CLI", width=80, title_align="left", expand=False, box=box.ROUNDED, padding=(1, 5)))

def main_cli() -> None:
    StackCLI()()
