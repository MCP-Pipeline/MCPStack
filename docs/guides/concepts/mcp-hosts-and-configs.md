# 🖥 MCP Hosts & Config Generators
# 🖥 MCP Hosts & Config Generators

MCPStack can target different **MCP hosts** by generating configuration files.

---

## Supported hosts

- **FastMCP** — lightweight reference host (for testing/debugging)
- **Claude Desktop** — Anthropic’s local integration
- **Universal** — a generic config emitter

---

## Let's explore how to generate configurations for these hosts

=== "From CLI"
    ```bash
    # Run with fastmcp
    mcpstack run --pipeline my_pipeline.json --config-type fastmcp

    # Export for Claude
    mcpstack build --pipeline my_pipeline.json --config-type claude
    ```

=== "Programmatic usage"
    ```python
    stack.build(
        type="fastmcp",
        command=None,
        args=None,
        cwd=None,
        module_name=None,
        pipeline_config_path="my_pipeline.json",
        save_path="fastmcp_config.json",
    )
    ```
