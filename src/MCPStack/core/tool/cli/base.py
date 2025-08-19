from abc import ABC, abstractmethod

import typer
from beartype import beartype
from beartype.typing import Any, Dict, TypedDict


class ToolConfig(TypedDict):
    """Shape of a tool's configuration.

    Contains both environment variables to export and tool parameters used to
    construct the tool instance via `from_dict(...)`.

    Keys:
        env_vars (dict[str, str]): Environment variables required/optional for
            the tool to run (e.g., API keys, paths).
        tool_params (dict[str, Any]): Constructor parameters for the tool.

    """

    env_vars: Dict[str, str]
    tool_params: Dict[str, Any]


@beartype
class BaseToolCLI(ABC):
    """Base class for tool CLIs.

    Provides a standard interface so every MCPStack tool can ship a consistent,
    discoverable CLI that plugs into the global `mcpstack tools <name> ...`
    namespace.

    !!! note "Why a CLI?"
        MCPStack tools are both **programmable** and **operable via CLI**.
        The CLI is great for quick inspection, local setup, status checks,
        and generating config that can later be loaded programmatically.

    Required responsibilities:
      * expose a Typer app via :meth:`get_app`
      * implement first-time setup :meth:`init`
      * provide configuration via :meth:`configure`
      * display human-readable status via :meth:`status`

    !!! tip "Keep it non-interactive by default"
        Prefer flags/options over interactive prompts so the CLI is easy to
        automate in CI scripts.
    """

    @classmethod
    @abstractmethod
    def get_app(cls) -> typer.Typer:
        """Return the `typer.Typer` app that defines the tool subcommands.

        The returned app will be mounted under `mcpstack tools <tool-name>`.
        Define commands like `init`, `configure`, `status`, or any
        tool-specific operations.

        Returns:
            typer.Typer: A fully configured Typer application.

        !!! example "Minimal Typer app"
            ```python
            import typer

            @classmethod
            def get_app(cls) -> typer.Typer:
                app = typer.Typer(help="MyTool CLI")

                @app.command()
                def ping():
                    '''Quick health check.'''
                    typer.echo("pong")

                return app
            ```
        """
        ...

    @classmethod
    @abstractmethod
    def init(cls, *args: Any, **kwargs: Any) -> None:
        """Perform first-time setup for the tool.

        Use this to create local directories (if needed), warm caches, or write template
        config files. This method should be **idempotent**.

        Args:
            *args: Implementation-defined positional arguments.
            **kwargs: Implementation-defined keyword arguments.
        """
        ...

    @classmethod
    @abstractmethod
    def configure(cls) -> ToolConfig:
        """Return a `ToolConfig` payload with env vars and tool params.

        This is typically used by the top-level CLI to merge environment
        variables and pass parameters into the tool is `from_dict(...)`.

        Returns:
            ToolConfig: A mapping with `env_vars` and `tool_params`.

        !!! warning "Do not include secrets you cannot verify"
            Only include env vars the user opted into or that you can read from
            the current process environment.
        """
        ...

    @classmethod
    @abstractmethod
    def status(cls, *args: Any, **kwargs: Any) -> None:
        """Print human-readable status for diagnostics.

        Show effective env values (mask secrets), key configuration, and any
        external service connectivity checks. Output should be concise and
        suitable for terminals.

        Args:
            *args: Implementation-defined positional arguments.
            **kwargs: Implementation-defined keyword arguments.

        !!! note "Be careful with secrets"
            Mask tokens and passwords by default (e.g., show last 4 chars).
        """
        ...
