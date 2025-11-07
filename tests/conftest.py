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


def pytest_configure(config):
    """Register custom markers used across the suite."""
    config.addinivalue_line("markers", "e2e: end-to-end workflow tests exercising prompts")








