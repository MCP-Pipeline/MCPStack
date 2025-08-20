import json
from typing import Annotated

import typer
from beartype import beartype
from rich.console import Console
from rich.panel import Panel

from MCPStack.core.tool.cli.base import BaseToolCLI, ToolConfig

console = Console()


@beartype
class Hello_WorldCLI(BaseToolCLI):
    """Hello_WorldCLI class."""

    @classmethod
    def get_app(cls) -> typer.Typer:
        """get_app function."""
        app = typer.Typer(
            help="hello_world tool commands.",
            add_completion=False,
            pretty_exceptions_show_locals=False,
            rich_markup_mode="markdown",
        )
        app.command(help="Quick init (sets a default prefix).")(cls.init)
        app.command(help="Configure hello_world (env + params).")(cls.configure)
        app.command(help="Show current hello_world status.")(cls.status)
        return app

    @classmethod
    def init(
        cls,
        prefix: Annotated[
            str | None,
            typer.Option("--prefix", "-p", help="Greeting prefix emoji/text."),
        ] = "👋",
    ) -> None:
        """init function."""
        console.print(f"[green]✅ Set default prefix to '{prefix}'[/green]")
        console.print("Export and run with:")
        console.print(f"\n    export MCP_HELLO_PREFIX='{prefix}'\n")

    @classmethod
    def configure(
        cls,
        prefix: Annotated[
            str | None,
            typer.Option("--prefix", "-p", help="Greeting prefix emoji/text."),
        ] = None,
        languages: Annotated[
            str | None,
            typer.Option(
                "--languages", "-l", help="Comma list: french,italian,german,chinese"
            ),
        ] = None,
        output: Annotated[
            str | None,
            typer.Option("--output", "-o", help="Where to save config JSON."),
        ] = None,
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Print config.")
        ] = False,
    ) -> ToolConfig:
        """configure function."""
        env_vars = {}
        tool_params = {}
        if prefix is None:
            prefix = typer.prompt("Prefix (emoji/text)", default="")
        env_vars["MCP_HELLO_PREFIX"] = prefix
        if languages:
            lang_list = [s.strip().lower() for s in languages.split(",") if s.strip()]
        else:
            lang_list = []
        if lang_list:
            tool_params["allowed_languages"] = lang_list
        cfg: ToolConfig = {"env_vars": env_vars, "tool_params": tool_params}
        path = output or "hello_world_config.json"
        with open(path, "w") as f:
            json.dump(cfg, f, indent=2)
        console.print(f"[green]✅ Saved hello_world config to {path}[/green]")
        if verbose:
            console.print(
                Panel.fit(
                    json.dumps(cfg, indent=2),
                    title="[bold green]Configuration[/bold green]",
                )
            )
        return cfg

    @classmethod
    def status(cls, verbose: bool = False) -> None:
        """status function."""
        import os

        prefix = os.getenv("MCP_HELLO_PREFIX", "")
        msg = f"Prefix: '{prefix or '[none]'}'"
        console.print(
            Panel.fit(msg, title="[bold green]hello_world status[/bold green]")
        )
