# 🛠 Tools & Actions
# 🛠 Tools & Actions

Tools are the **building blocks** of MCPStack pipelines. Each tool:

* Encapsulates logic (e.g. querying MIMIC-IV, running Jupyter, calling scikit-longitudinal classifiers)  
* Exposes **actions** — Python callables that the MCP host can invoke

---

## What is an Action?

An **action** is a function exposed to the LLM/host.  
For example, in the `HelloWorld` tool:

```python
from MCPStack.core.tool.base import BaseTool

class HelloWorld(BaseTool):
    def actions(self):
        return [self.say_hello]

    def say_hello(self, name: str = "world") -> str:
        return f"Hello, {name}!"
```

MCPStack registers these actions so they can be called through the MCP server.

---

### Lifecycle hooks

Tools can also manage backends (like databases or API clients):

* `initialize()` → open connections or caches
* `teardown()` → clean up
* `post_load()` → called after deserialization

This ensures consistent behavior whether you load tools from JSON or build them in Python.

---

### Example: Jupyter Tool

A Jupyter tool may expose actions like:

* `create_notebook()`
* `run_notebook(path)`
* `list_kernels()`

Each is just a Python function returning JSON-serializable output.
