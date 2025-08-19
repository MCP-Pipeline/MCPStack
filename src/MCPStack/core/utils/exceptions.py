from beartype import beartype


@beartype
class MCPStackError(Exception):
    """Base class for all MCPStack-related errors.

    Provides optional `details` to ease debugging.
    """

    ISSUE_REPORT_URL: str = "https://github.com/MCP-Pipeline/MCPStack/issues/"

    def __init__(self, message: str, details: str | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:
        base_msg = f"MCPStack Error: {self.message}"
        if self.details:
            base_msg += f"\nDetails: {self.details}"
        return base_msg


class MCPStackBuildError(MCPStackError):
    """Raised when pipeline build fails."""


class MCPStackConfigError(MCPStackError):
    """Raised for invalid or conflicting configuration."""


class MCPStackInitializationError(MCPStackError):
    """Raised when MCPStack fails to initialize."""


class MCPStackPresetError(MCPStackError):
    """Raised when a preset is missing or invalid."""


class MCPStackValidationError(MCPStackError):
    """Raised when validation of tools, env, or pipeline fails."""


class AuthenticationError(MCPStackError):
    """Raised when authentication with a service fails."""


class TokenValidationError(MCPStackError):
    """Raised when a token is missing, expired, or invalid."""
