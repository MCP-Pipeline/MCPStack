import logging
from abc import ABC, abstractmethod
from collections.abc import Callable

from beartype import beartype
from beartype.typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@beartype
class BaseTool(ABC):
    """Abstract base for MCPStack tools with lifecycle hooks and backends.

    `BaseTool` defines the minimal contract every MCP tool must implement so it
    can be composed into a pipeline and exposed to an MCP host.

    Core responsibilities:
      * Declare **actions** (callables) that the MCP server will expose.
      * Manage **lifecycle** (`initialize` / `teardown` / `post_load`) and any
        underlying **backends** (clients, connections, caches).
      * Provide **(de-)serialization** via `to_dict` / `from_dict`.

    !!! tip "What is an *action*?"
        An **action** is a Python callable (function or bound method) that the
        MCP server exposes to the LLM or client. MCPStack registers your
        actions by calling :meth:`actions`, then internally doing
        `self.mcp.tool()(action)` for each callable.

        *Keep signatures simple and data JSON-serializable.*

    !!! example "Minimal custom tool"
        ```python
        from MCPStack.core.tool.base import BaseTool

        class HelloTool(BaseTool):
            def __init__(self, greeting: str = "Hello"):
                super().__init__()
                self.greeting = greeting
                self.required_env_vars = {"HELLO_API_KEY": None}  # required

            def actions(self) -> list[callable]:
                # Expose the bound method below as an MCP action
                return [self.say_hello]

            def _initialize(self) -> None:
                # Create clients, read env, warm caches, etc.
                self.api_key = self.required_env_vars.get("HELLO_API_KEY")

            def _teardown(self) -> None:
                # Close clients if needed
                pass

            def _post_load(self) -> None:
                # Reconnect handles after deserialization
                pass

            def say_hello(self, name: str) -> dict:
                '''Return a greeting payload.'''
                return {"message": f"{self.greeting}, {name}!"}

            def to_dict(self) -> dict:
                return {"greeting": self.greeting}

            @classmethod
            def from_dict(cls, params: dict) -> "HelloTool":
                return cls(**params)
        ```

    Attributes:
        required_env_vars (dict[str, Optional[str]]): Names and defaults for
            env vars the tool needs. A value of `None` marks a **required**
            variable; non-`None` acts as a default.
        backends (dict[str, Any]): Optional backing resources (e.g., DB
            clients). If a backend object implements `initialize()` and/or
            `teardown()`, they will be called automatically.

    !!! note "Backends"
        A tool can expose multiple backends; each may have `initialize()` /
        `teardown()`. Keep them **idempotent** — lifecycle hooks may run more
        than once across builds or reloads.

    !!! warning "Serialization boundary"
        Only **configuration/state** should be persisted via `to_dict`. Do not
        serialize live handles (DB connections, HTTP clients). Recreate those
        in `_initialize` or `_post_load`.
    """

    def __init__(self) -> None:
        self.required_env_vars: Dict[str, Optional[str]] = {}
        self.backends: Dict[str, Any] = {}

    @abstractmethod
    def actions(self) -> list[Callable]:
        """Return the list of callables to be registered as MCP actions.

        MCPStack will iterate this list and register each callable with the MCP
        server. Each callable becomes invokable by the client/LLM.

        !!! tip "Designing an action"
            - Keep parameters and return values **JSON-serializable**.
            - Prefer **explicit, typed** parameters; avoid `*args/**kwargs`.
            - Validate inputs early; raise a descriptive `MCPStackError` on
              misuse.
            - Return **small payloads** or **stream** large data via backends,
              depending on your host capabilities.

        !!! example "Typical return"
            ```python
            def get_schema(self, table: str) -> dict:
                return {"table": table, "columns": [...], "primary_key": "id"}
            ```

        Returns:
            list[Callable]: The MCP-exposed actions in this tool.
        """
        ...

    def initialize(self) -> None:
        """Initialize all backends, then call the tool's `_initialize()` hook.

        Lifecycle entry point invoked by MCPStack during :meth:`build` or
        :meth:`post_load`.

        Steps:
          1. For each backend in :attr:`backends`, call `backend.initialize()`
             if present.
          2. Invoke :meth:`_initialize` for tool-specific setup.

        !!! success "Idempotent by design"
            Your initialization should be safe to call multiple times. Guard
            with flags if needed (e.g., `if self._ready: return`).
        """
        for backend in self.backends.values():
            if hasattr(backend, "initialize"):
                backend.initialize()
        self._initialize()

    def teardown(self) -> None:
        """Run the tool's `_teardown()` then attempt to teardown each backend.

        Called by MCPStack on server shutdown so tools can release resources.

        Steps:
          1. Invoke :meth:`_teardown` for tool-specific cleanup.
          2. For each backend in :attr:`backends`, call `backend.teardown()` if
             present. Errors are logged at DEBUG and **suppressed**.

        !!! warning "Be robust"
            Teardown should never raise fatally — leave the system in a
            consistent state even if some backends fail to close cleanly.
        """
        self._teardown()
        for backend in self.backends.values():
            try:
                if hasattr(backend, "teardown"):
                    backend.teardown()
            except Exception:
                logger.debug("Backend teardown error", exc_info=True)

    def post_load(self) -> None:
        """Hook called after deserialization; re-initializes the tool.

        Invoked by MCPStack after :meth:`from_dict` when a pipeline is loaded
        from disk. Use this to re-bind handles that cannot be serialized.

        Order:
          1. :meth:`_post_load`
          2. :meth:`initialize`

        !!! tip "What belongs here?"
            - Re-construct in-memory caches.
            - Recreate clients/sessions that depend on current process env.
        """
        self._post_load()
        self.initialize()

    def _initialize(self) -> None:
        """Optional hook for subclasses to implement `initialize` logic.

        Implement tool-specific setup here (e.g., reading env vars, creating
        clients, warming caches).

        !!! example
            ```python
            def _initialize(self) -> None:
                self.api_key = os.getenv("MY_API_KEY")
                self.client = Client(self.api_key)
            ```
        """
        ...

    def _teardown(self) -> None:
        """Optional hook for subclasses to implement `teardown` logic.

        Implement tool-specific cleanup here (close cursors, flush buffers,
        persist metrics, etc.).
        """
        ...

    def _post_load(self) -> None:
        """Optional hook for subclasses to implement `post_load` logic.

        Called immediately after deserialization but before :meth:`initialize`.
        Use this to restore transient state that isn't persisted by `to_dict`.
        """
        ...

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize this tool's configuration to a JSON-serializable mapping.

        Only include **configuration** — not live connections. The output of
        this method must be consumable by :meth:`from_dict`.

        Returns:
            Dict[str, Any]: Tool parameters and metadata.

        !!! example
            ```python
            def to_dict(self) -> dict:
                return {"endpoint": self.endpoint, "timeout": self.timeout}
            ```
        """
        ...

    @classmethod
    @abstractmethod
    def from_dict(cls, params: Dict[str, Any]):
        """Create a tool instance from a serialized mapping.

        This is the inverse of :meth:`to_dict`. Construct the tool using the
        provided parameters but **do not** create live connections here — do
        that in `_initialize` or `_post_load`.

        Args:
            params: Mapping produced by `to_dict()`.

        Returns:
            BaseTool: A configured tool instance.

        !!! example
            ```python
            @classmethod
            def from_dict(cls, params: dict) -> "MyTool":
                return cls(**params)
            ```
        """
        ...
