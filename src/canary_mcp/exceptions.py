"""Custom exception hierarchy for Canary MCP Server.

This module defines a hierarchy of exceptions with LLM-friendly error messages
structured to explain what went wrong, why it happened, and how to fix it.
"""


class CanaryMCPError(Exception):
    """Base exception for all Canary MCP Server errors.

    All custom exceptions inherit from this base class, enabling
    consistent error handling and messaging patterns.
    """

    def __init__(
        self,
        message: str,
        what: str = "",
        why: str = "",
        how_to_fix: str = "",
    ):
        """Initialize the exception with structured error context.

        Args:
            message: Main error message
            what: What went wrong (brief description)
            why: Why it happened (root cause)
            how_to_fix: How to resolve the issue (remediation steps)
        """
        self.what = what or message
        self.why = why
        self.how_to_fix = how_to_fix

        # Build structured message
        parts = [self.what]
        if self.why:
            parts.append(f"Cause: {self.why}")
        if self.how_to_fix:
            parts.append(f"Solution: {self.how_to_fix}")

        full_message = ". ".join(parts)
        super().__init__(full_message)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for structured logging.

        Returns:
            Dictionary with error details
        """
        return {
            "error_type": self.__class__.__name__,
            "what": self.what,
            "why": self.why,
            "how_to_fix": self.how_to_fix,
            "message": str(self),
        }


class CanaryAuthError(CanaryMCPError):
    """Raised when Canary API authentication fails.

    This indicates invalid credentials, expired tokens, or connection issues
    with the Canary Views Web API authentication endpoint.
    """

    def __init__(
        self,
        message: str = "Authentication with Canary API failed",
        what: str = "",
        why: str = "",
        how_to_fix: str = "",
    ):
        """Initialize authentication error.

        Args:
            message: Main error message
            what: What went wrong
            why: Why authentication failed
            how_to_fix: How to resolve (check credentials, network, etc.)
        """
        if not what:
            what = message
        if not why:
            why = "Invalid API token or connection issue"
        if not how_to_fix:
            how_to_fix = (
                "Verify CANARY_API_TOKEN environment variable is set correctly "
                "and the Canary server is accessible"
            )

        super().__init__(message=message, what=what, why=why, how_to_fix=how_to_fix)


class CanaryAPIError(CanaryMCPError):
    """Raised when Canary API request fails.

    This indicates HTTP errors, network issues, or unexpected API responses
    from the Canary Views Web API.
    """

    def __init__(
        self,
        message: str = "Canary API request failed",
        status_code: int = None,
        what: str = "",
        why: str = "",
        how_to_fix: str = "",
    ):
        """Initialize API error.

        Args:
            message: Main error message
            status_code: HTTP status code if available
            what: What went wrong
            why: Why the request failed
            how_to_fix: How to resolve
        """
        self.status_code = status_code

        if not what:
            if status_code:
                what = f"API request failed with status {status_code}"
            else:
                what = message

        if not why:
            if status_code == 404:
                why = "Resource not found on Canary server"
            elif status_code == 500:
                why = "Canary server encountered an internal error"
            elif status_code:
                why = f"HTTP error {status_code}"
            else:
                why = "Network error or invalid response"

        if not how_to_fix:
            if status_code == 404:
                how_to_fix = "Verify the tag name, namespace, or resource path exists"
            elif status_code == 500:
                how_to_fix = "Check Canary server logs and contact administrator"
            else:
                how_to_fix = "Check network connectivity and Canary server status"

        super().__init__(message=message, what=what, why=why, how_to_fix=how_to_fix)

    def to_dict(self) -> dict:
        """Convert exception to dictionary including status code.

        Returns:
            Dictionary with error details including HTTP status
        """
        result = super().to_dict()
        result["status_code"] = self.status_code
        return result


class ConfigurationError(CanaryMCPError):
    """Raised when MCP server configuration is invalid or missing.

    This indicates missing environment variables, invalid config files,
    or incorrect server setup.
    """

    def __init__(
        self,
        message: str = "MCP server configuration error",
        what: str = "",
        why: str = "",
        how_to_fix: str = "",
    ):
        """Initialize configuration error.

        Args:
            message: Main error message
            what: What configuration is wrong
            why: Why it's invalid
            how_to_fix: How to fix the configuration
        """
        if not what:
            what = message
        if not why:
            why = "Required configuration is missing or invalid"
        if not how_to_fix:
            how_to_fix = (
                "Check environment variables (CANARY_API_URL, CANARY_API_TOKEN) "
                "and ensure they are set correctly"
            )

        super().__init__(message=message, what=what, why=why, how_to_fix=how_to_fix)


class TagNotFoundError(CanaryAPIError):
    """Raised when a requested tag is not found in Canary Historian.

    This is a specialized API error for missing tags, providing context
    about tag discovery and namespace exploration.
    """

    def __init__(
        self,
        tag_name: str,
        namespace: str = None,
        what: str = "",
        why: str = "",
        how_to_fix: str = "",
    ):
        """Initialize tag not found error.

        Args:
            tag_name: The tag that was not found
            namespace: Optional namespace that was searched
            what: What went wrong
            why: Why the tag wasn't found
            how_to_fix: How to find the correct tag
        """
        self.tag_name = tag_name
        self.namespace = namespace

        if not what:
            if namespace:
                what = f"Tag '{tag_name}' not found in namespace '{namespace}'"
            else:
                what = f"Tag '{tag_name}' not found in Canary Historian"

        if not why:
            why = "Tag name may be incorrect or tag does not exist"

        if not how_to_fix:
            how_to_fix = (
                "Use search_tags tool to find similar tags, "
                "or list_namespaces to explore available namespaces"
            )

        super().__init__(
            message=what,
            status_code=404,
            what=what,
            why=why,
            how_to_fix=how_to_fix,
        )

    def to_dict(self) -> dict:
        """Convert exception to dictionary including tag details.

        Returns:
            Dictionary with error details including tag name
        """
        result = super().to_dict()
        result["tag_name"] = self.tag_name
        result["namespace"] = self.namespace
        return result
