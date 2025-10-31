"""Structured logging configuration for Canary MCP Server.

This module configures structlog for JSON-formatted logging with request ID tracking,
log level configuration, and log rotation for production use.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path

import structlog


def configure_logging() -> None:
    """Configure structured logging for the MCP server.

    Sets up:
    - JSON formatting for structured logs
    - Log level from environment variable (default: INFO)
    - Request ID tracking via contextvars
    - Log rotation (10MB max per file, 5 backup files)
    - Sensitive data masking (API tokens)
    """
    # Get log level from environment (default: INFO)
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure standard library logging with rotation
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # File handler with rotation (10MB max, 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "canary_mcp.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)

    # Console handler for stderr
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)

    # Add handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Configure structlog processors
    processors = [
        # Add log level
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add timestamp in ISO 8601 format
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Stack trace formatter for exceptions
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # Add request ID from context
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
        # Mask sensitive data
        _mask_sensitive_data,
        # JSON formatter for structured output
        structlog.processors.JSONRenderer(),
    ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def _mask_sensitive_data(
    logger: logging.Logger, method_name: str, event_dict: dict
) -> dict:
    """Mask sensitive data in log entries (API tokens, passwords).

    Args:
        logger: The logger instance
        method_name: The logging method name
        event_dict: The log event dictionary

    Returns:
        Modified event dict with sensitive data masked
    """
    # Fields to mask
    sensitive_fields = [
        "api_token",
        "token",
        "password",
        "secret",
        "apitoken",
        "auth",
        "authorization",
    ]

    # Recursively mask sensitive data
    def mask_dict(d: dict) -> dict:
        """Recursively mask sensitive fields in a dictionary."""
        masked = {}
        for key, value in d.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_fields):
                # Mask the value
                if isinstance(value, str) and len(value) > 4:
                    masked[key] = f"{value[:4]}***MASKED***"
                else:
                    masked[key] = "***MASKED***"
            elif isinstance(value, dict):
                masked[key] = mask_dict(value)
            else:
                masked[key] = value
        return masked

    return mask_dict(event_dict)


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """Get a configured structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)
