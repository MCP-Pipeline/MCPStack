from abc import ABC, abstractmethod

import typer
from beartype import beartype
from beartype.typing import Any, Dict, TypedDict

class ToolConfig(TypedDict):
    env_vars: Dict[str, str]
    tool_params: Dict[str, Any]

@beartype
class BaseToolCLI(ABC):
    """Base class for tool CLIs."""

    @classmethod
    @abstractmethod
    def get_app(cls) -> typer.Typer: ...

    @classmethod
    @abstractmethod
    def init(cls, *args: Any, **kwargs: Any) -> None: ...

    @classmethod
    @abstractmethod
    def configure(cls) -> ToolConfig: ...

    @classmethod
    @abstractmethod
    def status(cls, *args: Any, **kwargs: Any) -> None: ...
