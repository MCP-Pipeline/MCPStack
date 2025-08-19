from MCPStack.core.config import StackConfig
from MCPStack.core.preset.base import Preset
from MCPStack.stack import MCPStackCore
from MCPStack.tools.hello_world import Hello_World


class ExamplePreset(Preset):
    """ExamplePreset class.

    Supporting Hello_World Tool.
    """

    @classmethod
    def create(
        cls, config: StackConfig | None = None, **kwargs: dict
    ) -> "MCPStack.stack.MCPStackCore":
        """ "create function."""
        stack = MCPStackCore(config=config or StackConfig())
        tool = Hello_World()
        return stack.with_tool(tool)
