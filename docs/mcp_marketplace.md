# 🛍️ MCPs Marketplace
# 🛍️ MCPs Marketplace

Welcome to the **MCPStack MCPs Marketplace** — the central hub where we list all supported MCPStack MCP tools, built by us and by the community. Each tile below represents a tool: what it does, and a link to its repository.

Whether you’re a researcher, clinician, or developer, the Marketplace helps you quickly discover, install, and stack tools into powerful pipelines.

## 🚀 How to Use an MCP Tool

All MCPStack-compatible tools must register themselves via an **entry point** in their `pyproject.toml`.  
This makes tools **auto-discoverable** once you `uv add` (or `pip install`) their repository.

```toml
[project.entry-points."mcpstack.tools"]
your_tool_name = "mcpstack_your_tool_name.tool:YourTool"
```

* ✅ Once installed, `MCPStack` will detect the tool automatically.
* ❌ If detection fails, please open an issue @ [MCPStack/Issues](https://github.com/MCP-Pipeline/MCPStack).

<br />

# 📦 Stop Waffling & Show Me The Available Tools


<input id="marketplace-filter-input"
       placeholder="Type to filter tools (e.g., 'hello', 'mimic', etc.)" />

<div class="grid cards" markdown>

-   :material-hand-wave:{ .lg .middle } __Hello World__
    {: data-marketplace-card data-filter="hello world demo example greeting minimal"}

    ---

    A minimal MCP tool showcasing the basic structure and functionality of an MCPStack tool.

    [:octicons-arrow-right-24: ~~View Repository~~](#)

-   :material-table:{ .lg .middle } __MIMIC__
    {: data-marketplace-card data-filter="MIMIC-IV Conversational AI Healthcare Database"}

    ---

    MCPStack MIMIC is a MCP tool that allows to communicate with the MIMIC-IV clinical database.


    [:octicons-arrow-right-24: View Repository](https://github.com/MCP-Pipeline/mcpstack-mimic)

</div>

!!! tip
    This page will expand as more tools are contributed by the community. If you’ve built a tool, submit a PR to be featured here!
