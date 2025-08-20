# 🎛 Presets
# 🎛 Presets

Presets are **pre-wired pipelines**. Instead of manually composing tools, you can ship a ready-to-run stack.

## Why Presets?

!!! tip

    * Reduce boilerplate — zero-config pipelines for common use cases
    * Enable reproducibility (research / clinical workflows)
    * Provide a smooth on-ramp for end users

---

## Example: Hello_World preset

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

### Visualizing a preset pipeline

Here’s how a preset with MIMIC-IV, Jupyter, and scikit-longitudinal might look:

```text
+------------------------+    +---------------+    +----------------------------+
| MIMIC-IV Tool         | -->| Jupyter Tool  | -->| Scikit-Longitudinal Tool   |
+------------------------+    +---------------+    +----------------------------+
```

* The MIMIC-IV tool retrieves patient data
* Jupyter allows creating and running notebooks
* Scikit-longitudinal provides classification pipelines
