# 🏗️ Build Your First Pipeline
# 🏗️ Build Your First Pipeline

In this tutorial, you’ll learn how to build your first MCPStack pipeline step by step.

---

## 1. Create a simple pipeline with `HelloWorld`

MCPStack ships with a demo tool called `HelloWorld`. Let’s use it.

=== "CLI"

    ```bash
    mcpstack pipeline hello_world --new-pipeline hello_pipeline.json
    ```

=== "Python"

    ```python
    from MCPStack.stack import MCPStackCore
    from MCPStack.tools.hello_world.hello_world import HelloWorld

    stack = MCPStackCore()
    stack = stack.with_tool(HelloWorld())
    stack.save("hello_pipeline.json")
    ```

---

## 2. Build and run with FastMCP

```bash
mcpstack run --pipeline hello_pipeline.json --config-type fastmcp
```

You now have a live MCP server exposing your `say_hello` action.

---

## 3. Test in Claude Desktop

Export a Claude config:

```bash
mcpstack build --pipeline hello_pipeline.json --config-type claude
```

Then Open Claude Desktop, and tada!

!!! success "Congrats"
    You’ve just created and launched your **first MCPStack pipeline**! The idea now is to explore the marketplace and find other tools to stack-up with!
