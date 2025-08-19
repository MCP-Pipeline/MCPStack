# ⚙️ Configuration & Environment Variables
# ⚙️ Configuration & Environment Variables

MCPStack uses a central `StackConfig` object to manage configuration.

---

## Environment Variables

Tools may require environment variables (API keys, paths, etc).  
MCPStack validates and merges these via `StackConfig`.

```python
config = StackConfig(env_vars={"MIMIC_DB_PATH": "/data/mimic"})
stack = MCPStackCore(config=config)
```

---

### Conflict detection

If two tools define the same env var with different values, MCPStack raises a `MCPStackConfigError`.

---

### Data & project paths

StackConfig also infers paths:

* `project_root` → repository or home
* `data_dir` → default data storage
* `databases_dir`, raw_files_dir → structured subpaths

These are set automatically, but can be overridden with `MCPSTACK_DATA_DIR`.
