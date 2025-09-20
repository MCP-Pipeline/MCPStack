# 🧪 Tutorial: Urban Mapper + AutoDDG + Jupyter Pipeline
# 🧪 Tutorial: Urban Mapper + AutoDDG +Jupyter Pipeline

This tutorial shows how to **stack three MCPs**:

- **Urban Mapper** (urban computing analysis utilising the Urban Mapper official library)
- **AutoDDG** (dataset description & context generation via Large Language Models)
- **Jupyter** (reproducible notebook analysis)

About Urban Mapper:

* Urban Mapper official repository: https://github.com/VIDA-NYU/UrbanMapper
* Urban Mapper documentation: https://urbanmapper.readthedocs.io/en/latest/
* Urban Mapper MCP: https://github.com/MCP-Pipeline/mcpstack-urbanmapper

About AutoDDG:

* AutoDDG official repository: https://github.com/VIDA-NYU/AutoDDG
* AutoDDG MCP: https://github.com/MCP-Pipeline/mcpstack-autoddg

You’ll learn how to:

1. Build a pipeline with the three tools
2. Ask in a natural language to build a reproducible urban analysis workflow utilising Urban Mapper, and let the LLM explore the dataset with AutoDDG to get context on it and better inform the analysis
3. Export code and results into a Jupyter Notebook for reproducible Python analysis

---

## 🎥 Video Walkthrough

<iframe width="860" height="515" src="https://www.youtube.com/embed/-kgIi7GzN6o?si=aWRBoNgeqIzJjew_" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

---

## Prerequisites

```bash
# If you prefer other Python package managers, feel free to adapt `pip install X`.

uv init --python 3.10
uv add mcpstack
uv add mcpstack-jupyter
uv add mcpstack-urbanmapper
uv add mcpstack-autoddg

# To see if the tools are all connected
uv run mcpstack list-tools
```

## 🔧 Step 1 — Build with Pipeline W/ Urban Mapper Default

Urban Mapper Default is basically using HuggingFace's datasets to load datasets for urban pipeline analysis.
You can control otherwise, but it would be preferable to start with the default.

```bash
uv run mcpstack pipeline urbanmapper --new-pipeline my_pipeline.json
```

## 🔧 Step 2 — Create a Jupyter `ToolConfig`

Basically, Jupyter MCP works with some sort of connections between the LLM and the Jupyter instance. This is via a
URL and a TOKEN. Hence, the need for a `ToolConfig`.

```bash
uv run mcpstack tools jupyter configure \
    --token YOUR_JUPYTER_TOKEN

# This create a `jupyter_config.json` file
# Ex of a token: 1117bf468693444a5608e882ab3b55d511f354a175a0df02
```

## 🔧 Step 3 — Add To The Tool To The Pipeline

```bash
uv run mcpstack pipeline jupyter --to-pipeline my_pipeline.json --tool-config jupyter_config.json
```

## 🔧 Step 4 — Add AutoDDG To The Pipeline

```bash
uv run mcpstack tools autoddg configure
```

This will prompt an interactive shell to set up at the very least one mandatory environment variable: `AUTO_DDG_OPENAI_API_KEY`.
This is required to let the LLM use OpenAI large language models. TO generate one key,
please refer to: https://platform.openai.com/account/api-keys.

## 🔧 Step 5 — Add To The Tool To The Pipeline

```bash
uv run mcpstack pipeline autoddg --to-pipeline my_pipeline.json --tool-config autoddg_config.json
```

## 🔧 Step 6 — Compose & Run the Pipeline On Claude Desktop

```bash
uv run mcpstack build --pipeline my_pipeline.json --config-type claude
```

Now you can ask the LLM to explore a dataset, operate a Urban Mapper's pipeline analysis and export results into Jupyter.

## 📣 Prompt Used During The Demo Video

### Initial Prompt
```text
Hi there! I am interested in a *per-street* `Urban Mapper (UM)` *pipeline* *analysis* in **Downtown Brooklyn, NYC, USA** using the `oscur/nyc_311` dataset showing broadly speaking complaints in the street of New York City. Such dataset can be obtained via via `UM` actions.

What I am genuinely interested into first is to explore the dataset's context & description, please, using `AutoDDG` actions. Do not add any manual analysis of the sort.

**Shall we? Additionally, do download the full **`oscur/nyc_311`** data, but stream/sample the dataset up to 30k rows maximum when using **`AutoDDG`** . **

Note, if you have to download any packages, do so via `!uv add <package_name>`
```

### Follow-up Prompt
````text
So prior even building a UM pipeline analysis with nyc_311, can you explore what is `UM`, examples about it, and then based on what you've seen from `UM` and what you have gathered from AutoDDG on the dataset, can you list out here not in the notebook, the various `enrichers` you believe would be interesting to extract out of the dataset to apply to the streets of Downtown brooklyn please? Be straighforward-thinking.

Attaching a bit more documentation about enrichers.
````

### Follow-up Prompt – Optional
````text
nunique is not available, and mean on categorical -based feature will most probably crash. 
You have to pass a custom lambda method function to deal with all that, very easy straightforward custom lambda functions.
````

### Follow-up Prompt
````text
Let's build the pipeline with the FULL data, all those very interesting stacked enrichers 
(
not need to create multiple time the pipeline, stack the enrichers, 
and then straight after building, .preview(.), .composed_transform(.) 
(by the way, no. need to grave the output of this function for the time being), 
and most importantly, follow by nothing else than of : .visualise([<with the name of all of our output column created>]
).

Shall we :) ?  Output everything in the jupyter notebook.

Recall for any packages needed `!uv add <package_name>`.
````

!!! tip
    Try chaining additional tools to build research-ready urban analysis (e.g. ML) workflows.
