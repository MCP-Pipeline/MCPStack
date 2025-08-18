from beartype import beartype

@beartype
class MCPStackError(Exception):
    ISSUE_REPORT_URL: str = "https://github.com/your-org/mcpstack/issues/new"

    def __init__(self, message: str, details: str | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:
        base_msg = f"MCPStack Error: {self.message}"
        if self.details:
            base_msg += f"\nDetails: {self.details}"
        return base_msg

class MCPStackBuildError(MCPStackError): ...
class MCPStackConfigError(MCPStackError): ...
class MCPStackInitializationError(MCPStackError): ...
class MCPStackPresetError(MCPStackError): ...
class MCPStackValidationError(MCPStackError): ...
class AuthenticationError(MCPStackError): ...
class TokenValidationError(MCPStackError): ...
