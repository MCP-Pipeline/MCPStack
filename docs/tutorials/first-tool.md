# 🛠 Writing Your First Tool
# 🛠 Writing Your First Tool

This tutorial walks you through creating a custom MCP tool.

Template available at: [MCPStack-Tool-Builder](https://github.com/MCP-Pipeline/MCPStack-Tool-Builder)

---

## 1. Use the MCPStack Tool Builder

Instead of writing everything by hand, you can bootstrap a **tool skeleton**:

```bash
git clone https://github.com/MCP-Pipeline/MCPStack-Tool-Builder.git
cd MCPStack-Tool-Builder

uv sync  # or: pip install -e .[dev]
uv run mcpstack_tool.py init
```

Follow the interactive prompt to set:

- `tool_slug` (e.g. `weather`)
- `class_name` (e.g. `WeatherTool`)
- `env_prefix` (e.g. `WEATHER_`)

!!! tip
    Run `uv run mcpstack_tool.py --help` to see all available commands (`preview`, `apply`, `validate`, etc.).

---

## 2. Define your tool

Open `src/mcpstack_<your_tool_name>/tool.py` and add your actions:

```python
from MCPStack.core.tool.base import BaseTool

class WeatherTool(BaseTool):
    def actions(self):
        return [self.get_weather]

    def get_weather(self, city: str) -> str:
        return f"Weather for {city}: Sunny ☀️"
```

---

## 3. Add CLI support

In `cli.py` implement a Typer app for your tool’s configuration:

```python
import typer
from MCPStack.core.tool.base_cli import BaseToolCLI, ToolConfig

class WeatherCLI(BaseToolCLI):
    @classmethod
    def get_app(cls) -> typer.Typer:
        app = typer.Typer()

        @app.command()
        def status():
            print("Weather tool is configured.")

        return app

    @classmethod
    def configure(cls) -> ToolConfig:
        return {"env_vars": {}, "tool_params": {}}
```

---

## 4. Test your tool

Add it to a pipeline:

```python
from MCPStack.stack import MCPStackCore
from weather_tool.tool import WeatherTool

stack = MCPStackCore().with_tool(WeatherTool())
stack.build(type="fastmcp")
stack.run()
```

!!! success "Done!"
    You just wrote your first MCP tool with a CLI and action. Now stack it with other tools of interest!
