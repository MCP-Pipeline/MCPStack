# 🚀 Getting Started
# 🚀 Getting Started

This quickstart walks you through:

1. Installing **MCPStack**  
2. Building a pipeline with the `hello_world` tool — both **via CLI** and **programmatically**  
3. Running it with an MCP host configuration (`fastmcp` or **Claude Desktop**)

---

## 1. Installation

We recommend installing via [**uv**](https://github.com/astral-sh/uv), which provides fast, isolated environments.  
If you prefer `pip`, it works the same.

=== "uv"
    ```bash
    uv add mcpstack
    ```

=== "pip"
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install mcpstack
    ```

---

## 2. Creating a pipeline with Hello_World

The `hello_world` tool is bundled with MCPStack. It exposes a single action (`say_hello`) to demonstrate the tool interface.

=== "CLI"
    ```bash
    mcpstack pipeline hello_world --new-pipeline my_pipeline.json
    ```
    This command creates a new pipeline JSON with the hello_world tool inside.
    To inspect your pipeline:
    ```bash
    cat my_pipeline.json
    ```

=== "Programmatically"
    You can also build pipelines directly in Python:
    ```python
    from MCPStack.stack import MCPStackCore
    from MCPStack.tools.hello_world.hello_world import Hello_World

    stack = MCPStackCore()
    stack = stack.with_tool(Hello_World())
    stack.save("my_pipeline.json")
    ```

---

## 3. Running the pipeline with a host

MCPStack can generate and run host configurations.

=== "FastMCP"
    ```bash
    mcpstack run --pipeline my_pipeline.json --config-type fastmcp
    ```

	MCPStack will:

	1. Load your pipeline
	2. Generate a fastmcp configuration
	3. Start the MCP server

=== "Claude Desktop"
    ```bash
    mcpstack build --pipeline my_pipeline.json --config-type claude
    ```

	Claude supports local MCP servers. You can export the config and point Claude to it.
	Then open Claude Desktop and enjoy your pipeline being called by the LLM.

!!! tip
	You can always combine multiple tools into the same pipeline — e.g. `mimic`, `jupyter`, `scikit-longitudinal`, and more!
