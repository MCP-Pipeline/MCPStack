import importlib
import inspect
import logging
import os
from importlib.metadata import entry_points
from pathlib import Path

from beartype import beartype

from MCPStack.core.tool.base import BaseTool

logger = logging.getLogger(__name__)

TOOLS_DIR = Path(__file__).parent
ALL_TOOLS: dict[str, type[BaseTool]] = {}


@beartype
def _discover_tools() -> None:
    """Discover and register tools from subpackages or single-file modules."""
    for entry in os.scandir(TOOLS_DIR):
        if entry.name.startswith("_"):
            continue
        if entry.is_file() and entry.name in {"__init__.py", "registry.py"}:
            continue

        tool_name = entry.name.rsplit(".", 1)[0].lower()
        mod_path = None

        try:
            if entry.is_dir():
                candidate_file = TOOLS_DIR / tool_name / f"{tool_name}.py"
                if not candidate_file.exists():
                    continue
                importlib.import_module(f"MCPStack.tools.{tool_name}")
                mod_path = f"MCPStack.tools.{tool_name}.{tool_name}"
            elif entry.is_file() and entry.name.endswith(".py"):
                mod_path = f"MCPStack.tools.{tool_name}"
            else:
                continue

            module = importlib.import_module(mod_path)
            tool_classes = [
                obj
                for _, obj in inspect.getmembers(module, inspect.isclass)
                if issubclass(obj, BaseTool) and obj is not BaseTool
            ]

            if len(tool_classes) != 1:
                logger.warning(
                    f"Tool '{tool_name}' must declare exactly one BaseTool subclass in {mod_path}.py (found {len(tool_classes)}). Skipping."
                )
                continue

            ALL_TOOLS[tool_name] = tool_classes[0]

        except ModuleNotFoundError as e:
            logger.warning(f"Skipping '{tool_name}': {e}")
        except Exception as e:
            logger.error(f"Error loading tool '{tool_name}': {e}", exc_info=True)


def _discover_entrypoint_tools() -> None:
    """_discover_entrypoint_tools function."""
    try:
        eps = entry_points().select(group="mcpstack.tools")
    except Exception:
        return
    for ep in eps:
        try:
            cls = ep.load()
            if isinstance(cls, type) and issubclass(cls, BaseTool):
                ALL_TOOLS[ep.name.lower()] = cls
        except Exception:
            logger.debug("Failed loading entry point %s", ep.name, exc_info=True)


_discover_tools()
_discover_entrypoint_tools()
