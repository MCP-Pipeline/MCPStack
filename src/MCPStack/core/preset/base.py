from abc import ABC, abstractmethod

from beartype import beartype

from MCPStack.core.config import StackConfig


@beartype
class Preset(ABC):
    """Abstract factory for creating pre-wired MCPStack pipelines.

    A **Preset** bundles a curated set of tools and configuration so users can
    spin up a working pipeline with **zero boilerplate**. Think of it as an
    opinionated recipe that returns a fully configured `MCPStackCore` you can
    `build()` and `run()` immediately.

    ### Example Preset: Clinical Research Stack

    This preset might combine:

    - **MIMIC-IV Tool** 🏥
      Conversational agent over the MIMIC-IV database. Lets the LLM query
      structured EHR data naturally (SQL hidden under the hood).

    - **Jupyter Notebook Tool** 📓
      Programmatic notebook creation and execution. Great for generating
      reproducible analyses or rich reports directly from pipeline outputs.

    - **Scikit-Longitudinal Tool** 📈
      Utilities for longitudinal EHR data classification. Provides ready-to-use
      classifiers and pipelines (e.g., Cox regression, survival models,
      patient-level trajectory classification).

    !!! tip "Why presets?"
        * Ship **opinionated tool bundles** (MIMIC-IV + Jupyter + SKLong).
        * Enable reproducible **clinical research workflows**.
        * Save time for non-technical users (clinicians, researchers).

    ### A quick sketch

    ```text
    +---------------------+      +---------------------+      +------------------------+
    |   MIMIC-IV Tool     | ---> |  Scikit-Longitudinal| ---> |   Jupyter Notebook     |
    | (EHR conversational)|      | (classification)    |      | (generate + run nb)    |
    +---------------------+      +---------------------+      +------------------------+
    ```

    Preset wires tools together, sets defaults (paths, API keys, DB creds),
    and returns an `MCPStackCore` ready to `.build()` and `.run()`.

    !!! note "Extensibility"
        Presets are **starting points**. Users can extend the returned stack with
        `.with_tool(...)` or override configs before building.
    """

    @classmethod
    @abstractmethod
    def create(cls, config: StackConfig | None = None, **kwargs: dict):
        """Return an MCPStackCore instance configured with tools/pipeline.

        Implementations should:
          1. Accept an optional :class:`StackConfig` (or create a default).
          2. Instantiate and compose the required tools **in dependency order**.
          3. Apply sensible defaults and merge any `**kwargs` into tool params.
          4. Return the configured (but **not yet built**) `MCPStackCore`.

        Args:
            config: Optional shared configuration (env/logging/paths). If `None`,
                implementations may construct a default `StackConfig`.
            **kwargs: Implementation-specific parameters (e.g., `mimic_db_url`,
                `notebook_dir`, `classifier_type`).

        Returns:
            MCPStackCore: A stack with tools added and ready for `build()`.

        !!! warning "Do not build here"
            `create(...)` must **not** call `.build()` or `.run()`. Leave that to
            the caller so they can modify or inspect the stack.
        """
