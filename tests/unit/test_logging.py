"""Unit tests for logging infrastructure and configuration.

Tests structured logging setup, JSON formatting, request ID tracking,
log level configuration, and sensitive data masking.
"""

import json
import logging
import os
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
import structlog

from canary_mcp.logging_setup import (
    configure_logging,
    get_logger,
    _mask_sensitive_data,
)
from canary_mcp.request_context import (
    set_request_id,
    get_request_id,
    clear_request_context,
)


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test."""
    # Clear all handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Clear request context
    clear_request_context()

    yield

    # Cleanup after test
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    clear_request_context()


@pytest.fixture
def temp_log_dir(tmp_path):
    """Create a temporary log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


class TestLoggingConfiguration:
    """Test logging configuration and setup."""

    def test_configure_logging_creates_log_directory(self, tmp_path):
        """Test that configure_logging creates logs directory."""
        with patch("canary_mcp.logging_setup.Path") as mock_path:
            mock_path.return_value = tmp_path / "logs"
            configure_logging()
            mock_path.return_value.mkdir.assert_called_once()

    def test_configure_logging_sets_log_level_from_env(self):
        """Test that log level is read from LOG_LEVEL environment variable."""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            configure_logging()
            root_logger = logging.getLogger()
            assert root_logger.level == logging.DEBUG

    def test_configure_logging_defaults_to_info(self):
        """Test that log level defaults to INFO if not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove LOG_LEVEL if it exists
            os.environ.pop("LOG_LEVEL", None)
            configure_logging()
            root_logger = logging.getLogger()
            assert root_logger.level == logging.INFO

    def test_configure_logging_creates_file_handler(self, tmp_path):
        """Test that file handler is created with rotation."""
        with patch("canary_mcp.logging_setup.Path") as mock_path:
            mock_path.return_value = tmp_path / "logs"
            configure_logging()

            root_logger = logging.getLogger()
            # Check that at least one RotatingFileHandler exists
            file_handlers = [
                h for h in root_logger.handlers
                if isinstance(h, logging.handlers.RotatingFileHandler)
            ]
            assert len(file_handlers) > 0

    def test_configure_logging_creates_console_handler(self):
        """Test that console handler (stderr) is created."""
        configure_logging()

        root_logger = logging.getLogger()
        # Check that at least one StreamHandler exists
        stream_handlers = [
            h for h in root_logger.handlers
            if isinstance(h, logging.StreamHandler)
            and not isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(stream_handlers) > 0

    def test_get_logger_returns_structlog_logger(self):
        """Test that get_logger returns a structlog BoundLogger."""
        configure_logging()
        logger = get_logger("test_module")
        assert isinstance(logger, structlog.stdlib.BoundLogger)


class TestStructuredLogOutput:
    """Test structured log output format."""

    def test_log_output_is_json_formatted(self):
        """Test that log output is in JSON format."""
        configure_logging()

        # Capture log output
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        root_logger = logging.getLogger()
        root_logger.handlers = [handler]

        logger = get_logger("test")
        logger.info("test_message", test_field="test_value")

        log_output = log_stream.getvalue().strip()
        # Should be valid JSON
        try:
            log_data = json.loads(log_output)
            assert "event" in log_data or "message" in log_data
        except json.JSONDecodeError:
            pytest.fail("Log output is not valid JSON")

    def test_log_contains_required_fields(self):
        """Test that logs contain required fields: timestamp, level, message."""
        configure_logging()

        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        root_logger = logging.getLogger()
        root_logger.handlers = [handler]

        logger = get_logger("test")
        logger.info("test_event", key="value")

        log_output = log_stream.getvalue().strip()
        log_data = json.loads(log_output)

        # Check required fields
        assert "timestamp" in log_data
        assert "level" in log_data
        assert log_data["level"] == "info"
        assert "event" in log_data
        assert log_data["event"] == "test_event"

    def test_log_includes_custom_fields(self):
        """Test that custom fields are included in log output."""
        configure_logging()

        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        root_logger = logging.getLogger()
        root_logger.handlers = [handler]

        logger = get_logger("test")
        logger.info("test_event", custom_field="custom_value", another_field=123)

        log_output = log_stream.getvalue().strip()
        log_data = json.loads(log_output)

        assert log_data["custom_field"] == "custom_value"
        assert log_data["another_field"] == 123

    def test_log_includes_logger_name(self):
        """Test that logger name is included in log output."""
        configure_logging()

        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        root_logger = logging.getLogger()
        root_logger.handlers = [handler]

        logger = get_logger("test_module_name")
        logger.info("test_event")

        log_output = log_stream.getvalue().strip()
        log_data = json.loads(log_output)

        assert "logger" in log_data
        assert "test_module_name" in log_data["logger"]


class TestRequestIdTracking:
    """Test request ID generation and propagation."""

    def test_request_id_is_generated(self):
        """Test that request ID is generated when set."""
        request_id = set_request_id()
        assert request_id is not None
        assert len(request_id) > 0

    def test_request_id_is_retrievable(self):
        """Test that request ID can be retrieved."""
        request_id = set_request_id()
        retrieved_id = get_request_id()
        assert request_id == retrieved_id

    def test_request_id_can_be_set_explicitly(self):
        """Test that request ID can be set to a specific value."""
        custom_id = "test-request-id-12345"
        set_request_id(custom_id)
        retrieved_id = get_request_id()
        assert retrieved_id == custom_id

    def test_request_id_defaults_to_unknown(self):
        """Test that request ID defaults to 'unknown' if not set."""
        clear_request_context()
        request_id = get_request_id()
        assert request_id == "unknown"

    def test_request_id_persists_across_calls(self):
        """Test that request ID persists across multiple get calls."""
        request_id = set_request_id()
        retrieved_id_1 = get_request_id()
        retrieved_id_2 = get_request_id()
        assert retrieved_id_1 == retrieved_id_2 == request_id


class TestSensitiveDataMasking:
    """Test sensitive data masking in logs."""

    def test_mask_api_token_field(self):
        """Test that api_token field is masked."""
        logger = logging.getLogger("test")
        event_dict = {
            "event": "test",
            "api_token": "secret_token_12345",
        }
        masked = _mask_sensitive_data(logger, "info", event_dict)
        assert "***MASKED***" in masked["api_token"]
        assert "secret_token_12345" not in str(masked["api_token"])

    def test_mask_token_field(self):
        """Test that token field is masked."""
        logger = logging.getLogger("test")
        event_dict = {
            "event": "test",
            "token": "my_secret_token",
        }
        masked = _mask_sensitive_data(logger, "info", event_dict)
        assert "***MASKED***" in masked["token"]

    def test_mask_password_field(self):
        """Test that password field is masked."""
        logger = logging.getLogger("test")
        event_dict = {
            "event": "test",
            "password": "my_password_123",
        }
        masked = _mask_sensitive_data(logger, "info", event_dict)
        assert "***MASKED***" in masked["password"]

    def test_mask_preserves_prefix(self):
        """Test that masking preserves first 4 characters for strings > 4 chars."""
        logger = logging.getLogger("test")
        event_dict = {
            "event": "test",
            "api_token": "abcd_secret_token",
        }
        masked = _mask_sensitive_data(logger, "info", event_dict)
        assert masked["api_token"].startswith("abcd")
        assert "***MASKED***" in masked["api_token"]

    def test_mask_short_values_completely(self):
        """Test that short values (<=4 chars) are completely masked."""
        logger = logging.getLogger("test")
        event_dict = {
            "event": "test",
            "token": "abc",
        }
        masked = _mask_sensitive_data(logger, "info", event_dict)
        assert masked["token"] == "***MASKED***"

    def test_mask_nested_sensitive_fields(self):
        """Test that sensitive fields in nested dicts are masked."""
        logger = logging.getLogger("test")
        event_dict = {
            "event": "test",
            "config": {
                "api_token": "nested_secret_token",
                "other_field": "not_secret",
            },
        }
        masked = _mask_sensitive_data(logger, "info", event_dict)
        assert "***MASKED***" in masked["config"]["api_token"]
        assert masked["config"]["other_field"] == "not_secret"

    def test_mask_case_insensitive(self):
        """Test that masking is case-insensitive."""
        logger = logging.getLogger("test")
        event_dict = {
            "event": "test",
            "API_TOKEN": "secret_token_12345",
            "ApiToken": "another_secret",
        }
        masked = _mask_sensitive_data(logger, "info", event_dict)
        assert "***MASKED***" in masked["API_TOKEN"]
        assert "***MASKED***" in masked["ApiToken"]

    def test_mask_authorization_field(self):
        """Test that authorization field is masked."""
        logger = logging.getLogger("test")
        event_dict = {
            "event": "test",
            "authorization": "Bearer secret_token",
        }
        masked = _mask_sensitive_data(logger, "info", event_dict)
        assert "***MASKED***" in masked["authorization"]

    def test_non_sensitive_fields_not_masked(self):
        """Test that non-sensitive fields are not masked."""
        logger = logging.getLogger("test")
        event_dict = {
            "event": "test",
            "user_name": "john_doe",
            "tag_name": "temperature",
            "count": 123,
        }
        masked = _mask_sensitive_data(logger, "info", event_dict)
        assert masked["user_name"] == "john_doe"
        assert masked["tag_name"] == "temperature"
        assert masked["count"] == 123


class TestLogRotation:
    """Test log rotation configuration."""

    def test_file_handler_has_rotation_config(self):
        """Test that file handler has rotation configuration."""
        configure_logging()

        root_logger = logging.getLogger()
        file_handlers = [
            h for h in root_logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]

        assert len(file_handlers) > 0
        handler = file_handlers[0]

        # Check rotation parameters
        assert handler.maxBytes == 10 * 1024 * 1024  # 10MB
        assert handler.backupCount == 5

    def test_log_file_location(self):
        """Test that log file is created in logs directory."""
        configure_logging()

        root_logger = logging.getLogger()
        file_handlers = [
            h for h in root_logger.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]

        assert len(file_handlers) > 0
        handler = file_handlers[0]

        # Check that baseFilename contains 'logs' and 'canary_mcp.log'
        assert "logs" in handler.baseFilename
        assert "canary_mcp.log" in handler.baseFilename
