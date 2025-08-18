import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from beartype import beartype
from beartype.typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

@beartype
class BaseTool(ABC):
    def __init__(self) -> None:
        self.required_env_vars: Dict[str, Optional[str]] = {}
        self.backends: Dict[str, Any] = {}

    @abstractmethod
    def actions(self) -> list[Callable]:
        ...

    def initialize(self) -> None:
        for backend in self.backends.values():
            if hasattr(backend, "initialize"):
                backend.initialize()
        self._initialize()

    def teardown(self) -> None:
        self._teardown()
        for backend in self.backends.values():
            try:
                if hasattr(backend, "teardown"):
                    backend.teardown()
            except Exception:
                logger.debug("Backend teardown error", exc_info=True)

    def post_load(self) -> None:
        self._post_load()
        self.initialize()

    def _initialize(self) -> None: ...
    def _teardown(self) -> None: ...
    def _post_load(self) -> None: ...

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]: ...
    @classmethod
    @abstractmethod
    def from_dict(cls, params: Dict[str, Any]): ...
