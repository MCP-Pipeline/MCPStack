# 🧪 Tutorial: MIMIC + Jupyter Pipeline
# 🧪 Tutorial: MIMIC + Jupyter Pipeline

This tutorial shows how to **stack two MCPs**:

- **MIMIC** (conversational AI on the MIMIC-IV clinical database)
- **Jupyter** (reproducible notebook analysis)

You’ll learn how to:

1. Build a pipeline with both tools
2. Ask natural language questions over MIMIC-IV
3. Export results into a Jupyter Notebook for reproducible Python analysis

---

## 🎥 Video Walkthrough

<iframe width="860" height="515" src="https://www.youtube.com/embed/uTjIbN0GSHU?si=4rwoYmX32y9Cs6vs" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

---

## 🔧 Step 1 — Build with Pipeline W/ MIMIC Default

MIMIC Default is basically using the default MIMIC-IV demo database.

```bash
uv run mcpstack pipeline mimic --new-pipeline my_pipeline.json
```

## 🔧 Step 2 — Create a Jupyter `ToolConfig`

Basically, Jupyter MCP works with some sort of connections between the LLM and the Jupyter instance. This is via a
URL and a TOKEN. Hence, the need for a `ToolConfig`.

```bash
uv run mcpstack tools jupyter configure \
    --token YOUR_JUPYTER_TOKEN

# This create a `jupyter_config.json` file
```

## 🔧 Step 3 — Add To The Tool To The Pipeline

```bash
uv run mcpstack pipeline mimic --to-pipeline my_pipeline.json --tool-config jupyter_config.json
```

## 🔧 Step 4 — Compose & Run the Pipeline On Claude Desktop

```bash
uv run mcpstack build --pipeline my_pipeline.json --config-type claude
```

Now you can ask the LLM to operate the MIMIC tool and export results into Jupyter.

## 📣 Prompt Used During The Demo Video

```text
Hey there! May you extract 50 patients from MIMIC-IV and do a quick reproducible analysis of the data with pandas
for me please?

If you need to add packages, `!uv add <package_name>`.
```

!!! tip
    Try chaining additional tools (e.g., scikit-longitudinal) to build research-ready clinical workflows.
