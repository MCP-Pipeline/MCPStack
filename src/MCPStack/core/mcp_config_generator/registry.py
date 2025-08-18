from .mcp_config_generators.fast_mcp_config import FastMCPConfigGenerator
from .mcp_config_generators.claude_mcp_config import ClaudeConfigGenerator
from .mcp_config_generators.universal_mcp_config import UniversalConfigGenerator

ALL_MCP_CONFIG_GENERATORS = {
    "fastmcp": FastMCPConfigGenerator,
    "claude": ClaudeConfigGenerator,
    "universal": UniversalConfigGenerator,
}
