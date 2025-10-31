"""Unit tests for custom exception hierarchy.

Tests exception structure, error message formatting, LLM-friendly messages,
and exception serialization for logging.
"""

import pytest

from canary_mcp.exceptions import (
    CanaryMCPError,
    CanaryAuthError,
    CanaryAPIError,
    ConfigurationError,
    TagNotFoundError,
)


class TestCanaryMCPErrorBase:
    """Test base exception class CanaryMCPError."""

    def test_base_exception_initialization(self):
        """Test that base exception can be initialized."""
        error = CanaryMCPError(
            message="Test error",
            what="Something went wrong",
            why="Because of a reason",
            how_to_fix="Do this to fix",
        )
        assert error.what == "Something went wrong"
        assert error.why == "Because of a reason"
        assert error.how_to_fix == "Do this to fix"

    def test_base_exception_defaults_what_to_message(self):
        """Test that 'what' defaults to message if not provided."""
        error = CanaryMCPError(message="Test error message")
        assert error.what == "Test error message"

    def test_base_exception_message_structure(self):
        """Test that exception message includes what/why/how_to_fix."""
        error = CanaryMCPError(
            message="Test error",
            what="Something failed",
            why="Invalid input",
            how_to_fix="Provide valid input",
        )
        error_msg = str(error)
        assert "Something failed" in error_msg
        assert "Cause: Invalid input" in error_msg
        assert "Solution: Provide valid input" in error_msg

    def test_base_exception_message_without_why(self):
        """Test exception message when 'why' is not provided."""
        error = CanaryMCPError(
            message="Test error",
            what="Something failed",
            how_to_fix="Do this",
        )
        error_msg = str(error)
        assert "Something failed" in error_msg
        assert "Cause:" not in error_msg
        assert "Solution: Do this" in error_msg

    def test_base_exception_message_without_how_to_fix(self):
        """Test exception message when 'how_to_fix' is not provided."""
        error = CanaryMCPError(
            message="Test error",
            what="Something failed",
            why="Bad input",
        )
        error_msg = str(error)
        assert "Something failed" in error_msg
        assert "Cause: Bad input" in error_msg
        assert "Solution:" not in error_msg

    def test_base_exception_to_dict(self):
        """Test exception serialization to dictionary."""
        error = CanaryMCPError(
            message="Test error",
            what="Something failed",
            why="Bad input",
            how_to_fix="Fix it",
        )
        error_dict = error.to_dict()

        assert error_dict["error_type"] == "CanaryMCPError"
        assert error_dict["what"] == "Something failed"
        assert error_dict["why"] == "Bad input"
        assert error_dict["how_to_fix"] == "Fix it"
        assert "message" in error_dict

    def test_base_exception_is_exception(self):
        """Test that CanaryMCPError inherits from Exception."""
        error = CanaryMCPError(message="Test")
        assert isinstance(error, Exception)


class TestCanaryAuthError:
    """Test CanaryAuthError exception."""

    def test_auth_error_initialization(self):
        """Test CanaryAuthError initialization."""
        error = CanaryAuthError(message="Auth failed")
        assert isinstance(error, CanaryMCPError)
        assert isinstance(error, CanaryAuthError)

    def test_auth_error_default_message(self):
        """Test CanaryAuthError default message."""
        error = CanaryAuthError()
        error_msg = str(error)
        assert "Authentication with Canary API failed" in error_msg

    def test_auth_error_default_why(self):
        """Test CanaryAuthError default 'why' explanation."""
        error = CanaryAuthError()
        assert "Invalid API token" in error.why or "connection issue" in error.why

    def test_auth_error_default_how_to_fix(self):
        """Test CanaryAuthError default remediation."""
        error = CanaryAuthError()
        assert "CANARY_API_TOKEN" in error.how_to_fix
        assert "environment variable" in error.how_to_fix

    def test_auth_error_custom_fields(self):
        """Test CanaryAuthError with custom what/why/how_to_fix."""
        error = CanaryAuthError(
            message="Custom auth error",
            what="Token expired",
            why="Session timeout",
            how_to_fix="Re-authenticate",
        )
        assert error.what == "Token expired"
        assert error.why == "Session timeout"
        assert error.how_to_fix == "Re-authenticate"

    def test_auth_error_to_dict(self):
        """Test CanaryAuthError serialization."""
        error = CanaryAuthError(message="Auth failed")
        error_dict = error.to_dict()
        assert error_dict["error_type"] == "CanaryAuthError"


class TestCanaryAPIError:
    """Test CanaryAPIError exception."""

    def test_api_error_initialization(self):
        """Test CanaryAPIError initialization."""
        error = CanaryAPIError(message="API request failed")
        assert isinstance(error, CanaryMCPError)
        assert isinstance(error, CanaryAPIError)

    def test_api_error_with_status_code(self):
        """Test CanaryAPIError with HTTP status code."""
        error = CanaryAPIError(message="Request failed", status_code=404)
        assert error.status_code == 404

    def test_api_error_status_404_defaults(self):
        """Test CanaryAPIError defaults for 404 status."""
        error = CanaryAPIError(status_code=404)
        assert "404" in error.what
        assert "not found" in error.why.lower()
        assert "tag name" in error.how_to_fix.lower() or "namespace" in error.how_to_fix.lower()

    def test_api_error_status_500_defaults(self):
        """Test CanaryAPIError defaults for 500 status."""
        error = CanaryAPIError(status_code=500)
        assert "500" in error.what
        assert "internal error" in error.why.lower()
        assert "server logs" in error.how_to_fix.lower() or "administrator" in error.how_to_fix.lower()

    def test_api_error_default_why(self):
        """Test CanaryAPIError default 'why' without status code."""
        error = CanaryAPIError()
        assert "Network error" in error.why or "invalid response" in error.why

    def test_api_error_to_dict_includes_status_code(self):
        """Test CanaryAPIError serialization includes status_code."""
        error = CanaryAPIError(message="Request failed", status_code=403)
        error_dict = error.to_dict()
        assert error_dict["error_type"] == "CanaryAPIError"
        assert error_dict["status_code"] == 403

    def test_api_error_custom_fields(self):
        """Test CanaryAPIError with custom what/why/how_to_fix."""
        error = CanaryAPIError(
            message="Custom API error",
            status_code=429,
            what="Rate limited",
            why="Too many requests",
            how_to_fix="Wait and retry",
        )
        assert error.what == "Rate limited"
        assert error.why == "Too many requests"
        assert error.how_to_fix == "Wait and retry"
        assert error.status_code == 429


class TestConfigurationError:
    """Test ConfigurationError exception."""

    def test_configuration_error_initialization(self):
        """Test ConfigurationError initialization."""
        error = ConfigurationError(message="Config invalid")
        assert isinstance(error, CanaryMCPError)
        assert isinstance(error, ConfigurationError)

    def test_configuration_error_default_message(self):
        """Test ConfigurationError default message."""
        error = ConfigurationError()
        error_msg = str(error)
        assert "configuration error" in error_msg.lower()

    def test_configuration_error_default_why(self):
        """Test ConfigurationError default 'why' explanation."""
        error = ConfigurationError()
        assert "configuration" in error.why.lower()
        assert "missing" in error.why.lower() or "invalid" in error.why.lower()

    def test_configuration_error_default_how_to_fix(self):
        """Test ConfigurationError default remediation."""
        error = ConfigurationError()
        assert "environment variables" in error.how_to_fix.lower()
        assert "CANARY" in error.how_to_fix

    def test_configuration_error_custom_fields(self):
        """Test ConfigurationError with custom what/why/how_to_fix."""
        error = ConfigurationError(
            message="Missing API URL",
            what="CANARY_API_URL not set",
            why="Environment variable missing",
            how_to_fix="Set CANARY_API_URL in .env file",
        )
        assert error.what == "CANARY_API_URL not set"
        assert error.why == "Environment variable missing"
        assert error.how_to_fix == "Set CANARY_API_URL in .env file"

    def test_configuration_error_to_dict(self):
        """Test ConfigurationError serialization."""
        error = ConfigurationError(message="Config error")
        error_dict = error.to_dict()
        assert error_dict["error_type"] == "ConfigurationError"


class TestTagNotFoundError:
    """Test TagNotFoundError exception."""

    def test_tag_not_found_error_initialization(self):
        """Test TagNotFoundError initialization."""
        error = TagNotFoundError(tag_name="Temperature.PV")
        assert isinstance(error, CanaryAPIError)
        assert isinstance(error, TagNotFoundError)

    def test_tag_not_found_error_with_tag_name(self):
        """Test TagNotFoundError includes tag name in message."""
        error = TagNotFoundError(tag_name="Temperature.PV")
        assert error.tag_name == "Temperature.PV"
        assert "Temperature.PV" in error.what

    def test_tag_not_found_error_with_namespace(self):
        """Test TagNotFoundError includes namespace in message."""
        error = TagNotFoundError(
            tag_name="Temperature.PV",
            namespace="Plant1.Area2",
        )
        assert error.tag_name == "Temperature.PV"
        assert error.namespace == "Plant1.Area2"
        assert "Temperature.PV" in error.what
        assert "Plant1.Area2" in error.what

    def test_tag_not_found_error_status_code_is_404(self):
        """Test TagNotFoundError has 404 status code."""
        error = TagNotFoundError(tag_name="Temperature.PV")
        assert error.status_code == 404

    def test_tag_not_found_error_default_why(self):
        """Test TagNotFoundError default 'why' explanation."""
        error = TagNotFoundError(tag_name="Temperature.PV")
        assert "incorrect" in error.why.lower() or "does not exist" in error.why.lower()

    def test_tag_not_found_error_default_how_to_fix(self):
        """Test TagNotFoundError default remediation."""
        error = TagNotFoundError(tag_name="Temperature.PV")
        assert "search_tags" in error.how_to_fix or "list_namespaces" in error.how_to_fix

    def test_tag_not_found_error_to_dict_includes_tag_details(self):
        """Test TagNotFoundError serialization includes tag details."""
        error = TagNotFoundError(
            tag_name="Temperature.PV",
            namespace="Plant1",
        )
        error_dict = error.to_dict()
        assert error_dict["error_type"] == "TagNotFoundError"
        assert error_dict["tag_name"] == "Temperature.PV"
        assert error_dict["namespace"] == "Plant1"
        assert error_dict["status_code"] == 404

    def test_tag_not_found_error_custom_fields(self):
        """Test TagNotFoundError with custom what/why/how_to_fix."""
        error = TagNotFoundError(
            tag_name="Pressure.PV",
            what="Custom what message",
            why="Custom why message",
            how_to_fix="Custom how to fix",
        )
        assert error.what == "Custom what message"
        assert error.why == "Custom why message"
        assert error.how_to_fix == "Custom how to fix"


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""

    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from CanaryMCPError."""
        assert issubclass(CanaryAuthError, CanaryMCPError)
        assert issubclass(CanaryAPIError, CanaryMCPError)
        assert issubclass(ConfigurationError, CanaryMCPError)
        assert issubclass(TagNotFoundError, CanaryMCPError)

    def test_tag_not_found_inherits_from_api_error(self):
        """Test that TagNotFoundError inherits from CanaryAPIError."""
        assert issubclass(TagNotFoundError, CanaryAPIError)

    def test_exception_can_be_caught_by_base(self):
        """Test that specific exceptions can be caught by base class."""
        try:
            raise CanaryAuthError("Auth failed")
        except CanaryMCPError as e:
            assert isinstance(e, CanaryAuthError)

    def test_tag_not_found_can_be_caught_by_api_error(self):
        """Test that TagNotFoundError can be caught by CanaryAPIError."""
        try:
            raise TagNotFoundError(tag_name="Test")
        except CanaryAPIError as e:
            assert isinstance(e, TagNotFoundError)


class TestLLMFriendlyErrorMessages:
    """Test that error messages are LLM-friendly and informative."""

    def test_error_message_has_clear_structure(self):
        """Test that error messages follow what/why/how structure."""
        error = CanaryAuthError(
            what="Authentication failed",
            why="Invalid API token",
            how_to_fix="Check CANARY_API_TOKEN",
        )
        error_msg = str(error)

        # Should have clear sections
        parts = error_msg.split(". ")
        assert len(parts) >= 2  # At least what and one other section

    def test_error_message_is_readable(self):
        """Test that error messages are human/LLM readable."""
        error = ConfigurationError(
            what="Missing required credentials: CANARY_API_TOKEN",
            why="Required environment variables are not set",
            how_to_fix="Set these environment variables in your .env file",
        )
        error_msg = str(error)

        # Should not be just stack traces or codes
        assert len(error_msg) > 20
        assert "Missing required credentials" in error_msg
        assert not error_msg.startswith("Traceback")

    def test_error_provides_actionable_guidance(self):
        """Test that error messages provide actionable guidance."""
        error = TagNotFoundError(
            tag_name="Temperature.PV",
            namespace="Plant1",
        )
        error_msg = str(error)

        # Should mention tools or actions the LLM can take
        assert "search_tags" in error_msg or "list_namespaces" in error_msg

    def test_error_explains_root_cause(self):
        """Test that error messages explain root cause."""
        error = CanaryAPIError(
            status_code=500,
            what="API request failed",
            why="Canary server encountered an internal error",
            how_to_fix="Check server logs",
        )

        # 'why' should explain the cause
        assert len(error.why) > 10
        assert "internal error" in error.why.lower()

    def test_error_to_dict_suitable_for_logging(self):
        """Test that error.to_dict() is suitable for structured logging."""
        error = CanaryAuthError(
            what="Auth failed",
            why="Invalid token",
            how_to_fix="Check credentials",
        )
        error_dict = error.to_dict()

        # Should have all required fields for logging
        assert "error_type" in error_dict
        assert "what" in error_dict
        assert "why" in error_dict
        assert "how_to_fix" in error_dict
        assert "message" in error_dict

        # Should be JSON-serializable
        import json
        try:
            json.dumps(error_dict)
        except (TypeError, ValueError):
            pytest.fail("error.to_dict() is not JSON-serializable")


class TestExceptionRaising:
    """Test that exceptions can be raised and caught properly."""

    def test_can_raise_and_catch_auth_error(self):
        """Test raising and catching CanaryAuthError."""
        with pytest.raises(CanaryAuthError) as exc_info:
            raise CanaryAuthError("Auth failed")
        assert "Auth failed" in str(exc_info.value)

    def test_can_raise_and_catch_api_error(self):
        """Test raising and catching CanaryAPIError."""
        with pytest.raises(CanaryAPIError) as exc_info:
            raise CanaryAPIError("API error", status_code=500)
        assert exc_info.value.status_code == 500

    def test_can_raise_and_catch_config_error(self):
        """Test raising and catching ConfigurationError."""
        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError("Config invalid")
        assert "Config invalid" in str(exc_info.value)

    def test_can_raise_and_catch_tag_not_found_error(self):
        """Test raising and catching TagNotFoundError."""
        with pytest.raises(TagNotFoundError) as exc_info:
            raise TagNotFoundError(tag_name="Test.Tag")
        assert "Test.Tag" in str(exc_info.value)
