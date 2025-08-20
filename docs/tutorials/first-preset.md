# 🎛 Creating a Preset
# 🎛 Creating a Preset

Presets let you bundle tools together into a ready-made pipeline.

---

## 1. Why Presets?

- Reuse common stacks
- Share reproducible research pipelines
- Give users a one-liner to spin up a workflow

---

## 2. Define a Preset

```python
from MCPStack.core.preset.base import Preset
from MCPStack.stack import MCPStackCore
from MCPStack.tools.hello_world.hello_world import Hello_World

class HelloPreset(Preset):
    @classmethod
    def create(cls, config=None, **kwargs):
        stack = MCPStackCore(config=config)
        return stack.with_tool(Hello_World())
```

---

## 3. Use your preset

```python
from MCPStack.core.preset.registry import ALL_PRESETS

stack = ALL_PRESETS["hello"]().create()
stack.build(type="fastmcp")
stack.run()
```


!!! success "Tip"
    Presets are just factories — you can extend them with `.with_tool()`.
