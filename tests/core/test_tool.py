import pytest

from MCPStack.core.tool.base import BaseTool
from MCPStack.core.tool.cli.base import BaseToolCLI


class TestBaseTool:
    """Tests for BaseTool."""

    def test_abstract_methods(self):
        """Test BaseTool abstract methods."""
        with pytest.raises(TypeError):
            BaseTool()


class TestBaseToolCLI:
    """Tests for BaseToolCLI."""

    def test_abstract_methods(self):
        """Test BaseToolCLI abstract methods."""
        with pytest.raises(TypeError):
            BaseToolCLI()
