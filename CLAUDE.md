# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Core Development
- **Install dependencies**: `uv sync` (or `pip install -e .`)
- **Run tests**: `pytest` or `uv run pytest`
- **Run tests with coverage**: `pytest --cov=src/MCPStack --cov-report=html`
- **Lint code**: `ruff check` (or `uv run ruff check`)
- **Format code**: `ruff format` (or `uv run ruff format`)
- **Pre-commit hooks**: `uv run pre-commit install` then `uv run pre-commit run --all-files`

### CLI Usage
- **MCPStack CLI**: `uv run mcpstack --help` (main CLI interface)
- **List available tools**: `uv run mcpstack list-tools`
- **List presets**: `uv run mcpstack list-presets`
- **Build pipeline**: `uv run mcpstack build --pipeline <path> --config-type <type>`
- **Tool configuration**: `uv run mcpstack tools <tool_name> configure`

### Documentation
- **Build docs**: `./build_docs.sh`
- **Serve docs locally**: `mkdocs serve` (after installing dev dependencies)

## Architecture Overview

MCPStack is a scikit-learn-inspired pipeline orchestrator for Model Context Protocol (MCP) tools that enables stacking and composing MCP tools into pipelines for LLM environments.

### Core Components

#### 1. MCPStackCore (`src/MCPStack/stack.py`)
The main orchestrator class that provides a fluent API for building pipelines:
- **Chaining methods**: `with_tool()`, `with_tools()`, `with_preset()`, `with_config()`
- **Pipeline lifecycle**: `build()` → `run()` → `save()`/`load()`
- **Immutable design**: All `with_*` methods return new instances
- **Validation**: Tools and environment variables validated before initialization

#### 2. Configuration System (`src/MCPStack/core/config.py`)
- **StackConfig**: Central configuration container for logging, env vars, and paths
- **Environment management**: Merges and validates env vars across tools
- **Path resolution**: Auto-detects project root and data directories
- **Tool validation**: Ensures required env vars are present before tool initialization

#### 3. Tool System (`src/MCPStack/core/tool/`)
- **BaseTool**: Abstract base class for all MCP tools with lifecycle methods
- **Registry**: Auto-discovery via `[project.entry-points."mcpstack.tools"]`
- **CLI Integration**: BaseToolCLI for tool-specific command interfaces
- **Lifecycle**: `initialize()` → `actions()` → `post_load()` → `teardown()`

#### 4. Preset System (`src/MCPStack/core/preset/`)
- **Base preset class**: Pre-configured tool combinations for common use cases
- **Registry**: Auto-discovery via entry points
- **Factory pattern**: Create method returns configured MCPStackCore instances

#### 5. MCP Config Generators (`src/MCPStack/core/mcp_config_generator/`)
- **Multiple backends**: FastMCP, Claude Desktop, Universal
- **Host integration**: Generate appropriate configs for different MCP hosts
- **Pluggable**: Registry-based system for adding new config generators

### Key Design Patterns

#### Pipeline Composition
```python
stack = (
    MCPStackCore(StackConfig())
    .with_tool(ToolA())
    .with_tool(ToolB())
    .build(type="fastmcp")
)
```

#### Tool Registration
Tools auto-register via pyproject.toml entry points:
```toml
[project.entry-points."mcpstack.tools"]
hello_world = "MCPStack.tools.hello_world:HelloWorldTool"
```

#### Validation First
- Environment variables validated before any tool initialization
- Tools validated against StackConfig requirements
- Fail-fast approach prevents partial initialization

### Development Guidelines

#### Adding New Tools
1. Inherit from `BaseTool` in `src/MCPStack/core/tool/base.py`
2. Implement required methods: `initialize()`, `actions()`
3. Add entry point in pyproject.toml
4. Follow lifecycle: validate → initialize → register → teardown

#### Tool CLI Integration
1. Inherit from `BaseToolCLI` in `src/MCPStack/core/tool/cli/base.py`
2. Register CLI app with tool registry
3. Use `@click.command()` decorators for subcommands

#### Testing
- Test files mirror src structure: `tests/core/`, `tests/tools/`
- Use pytest with async support enabled
- Mock external dependencies and MCP server interactions
- Test both success and error paths

### File Structure Context
- `src/MCPStack/`: Main package with core orchestration
- `src/MCPStack/core/`: Core abstractions (tools, presets, config)
- `src/MCPStack/tools/`: Built-in tool implementations
- `tests/`: Test suite mirroring source structure
- `docs/`: MkDocs documentation source

### Important Notes
- Uses `beartype` for runtime type checking throughout
- Async support via pytest-asyncio for MCP operations
- Rich CLI with typer for enhanced user experience
- FastMCP integration for actual MCP server functionality
- UV preferred for dependency management, but pip also supported