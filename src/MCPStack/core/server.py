import logging, os
from beartype import beartype
from MCPStack.core.utils.logging import setup_logging
from MCPStack.stack import MCPStackCore
from MCPStack.core.utils.exceptions import MCPStackValidationError

logger = logging.getLogger(__name__)

@beartype
def main() -> None:
    setup_logging(level=os.getenv("MCPSTACK_LOG_LEVEL", "INFO"))
    logger.info("Starting MCPStack MCP server...")
    config_path = os.getenv("MCPSTACK_CONFIG_PATH")
    if not config_path:
        raise MCPStackValidationError("MCPSTACK_CONFIG_PATH env var not set. Build a pipeline and set it.")
    stack = MCPStackCore.load(config_path)
    logger.info(f"Loaded pipeline from config: {config_path}")
    stack.build()
    stack.run()

if __name__ == "__main__":
    main()
