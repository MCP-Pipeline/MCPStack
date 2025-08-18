from abc import ABC, abstractmethod
from beartype import beartype
from MCPStack.core.config import StackConfig

@beartype
class Preset(ABC):
    @classmethod
    @abstractmethod
    def create(cls, config: StackConfig | None = None, **kwargs: dict):
        """Return an MCPStackCore instance configured with tools/pipeline."""
