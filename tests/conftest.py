"""
Pytest configuration and global fixtures.

This conftest.py prevents test pollution from the real .env file by patching
load_dotenv() before any test modules are imported.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure src/ is on sys.path for src-layout imports during testing
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


@pytest.fixture(scope="session", autouse=True)
def prevent_dotenv_loading():
    """
    Prevent load_dotenv() from loading the real .env file during tests.

    This fixture runs automatically for all tests and patches load_dotenv
    to be a no-op, ensuring test environment isolation.
    """
    with patch("dotenv.load_dotenv"):
        yield


@pytest.fixture
def clean_env():
    """
    Provide a clean environment for tests that need complete isolation.

    Usage:
        def test_something(clean_env):
            with clean_env({"VAR": "value"}):
                # Test with only specified env vars
    """
    def _clean_env(env_vars=None):
        if env_vars is None:
            env_vars = {}
        return patch.dict(os.environ, env_vars, clear=True)

    return _clean_env


@pytest.fixture
def mock_canary_env():
    """
    Provide standard mock Canary environment variables.

    This is a convenience fixture for tests that need typical Canary config.
    """
    return {
        "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
        "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
        "CANARY_API_TOKEN": "test-token-123",
        "CANARY_SESSION_TIMEOUT_MS": "120000",
        "CANARY_TIMEOUT": "30",
        "CANARY_POOL_SIZE": "10",
        "CANARY_RETRY_ATTEMPTS": "3",
        "LOG_LEVEL": "ERROR",  # Reduce log noise in tests
    }
