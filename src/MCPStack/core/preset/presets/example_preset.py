from MCPStack.core.preset.base import Preset
from MCPStack.core.config import StackConfig
from MCPStack.tools.hello_world import HelloWorld
from MCPStack.stack import MCPStackCore

class ExamplePreset(Preset):
    @classmethod
    def create(cls, config: StackConfig | None = None, **kwargs: dict) -> "MCPStack.stack.MCPStackCore":
        stack = MCPStackCore(config=config or StackConfig())
        tool = HelloWorld()
        return stack.with_tool(tool)
