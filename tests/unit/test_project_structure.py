"""Unit tests for project structure and configuration."""

import os
import pytest
from pathlib import Path


@pytest.mark.unit
def test_project_directories_exist():
    """Test that required project directories exist."""
    project_root = Path(__file__).parent.parent.parent

    required_dirs = [
        project_root / "src",
        project_root / "src" / "canary_mcp",
        project_root / "tests",
        project_root / "tests" / "unit",
        project_root / "tests" / "integration",
        project_root / "docs",
        project_root / "config",
    ]

    for directory in required_dirs:
        assert directory.exists(), f"Required directory not found: {directory}"
        assert directory.is_dir(), f"Path is not a directory: {directory}"


@pytest.mark.unit
def test_pyproject_toml_exists():
    """Test that pyproject.toml exists and is valid."""
    project_root = Path(__file__).parent.parent.parent
    pyproject_path = project_root / "pyproject.toml"

    assert pyproject_path.exists(), "pyproject.toml not found"
    assert pyproject_path.is_file(), "pyproject.toml is not a file"

    # Read and verify basic content
    content = pyproject_path.read_text()
    assert "[project]" in content
    assert "canary-mcp" in content
    assert "fastmcp" in content


@pytest.mark.unit
def test_env_example_exists():
    """Test that .env.example template exists."""
    project_root = Path(__file__).parent.parent.parent
    env_example = project_root / ".env.example"

    assert env_example.exists(), ".env.example not found"
    assert env_example.is_file(), ".env.example is not a file"

    # Verify it contains expected configuration keys
    content = env_example.read_text()
    assert "CANARY_SAF_BASE_URL" in content or "CANARY_VIEWS_BASE_URL" in content
    assert "CANARY_API_TOKEN" in content
    assert "MCP_SERVER_HOST" in content


@pytest.mark.unit
def test_package_imports():
    """Test that main package can be imported."""
    try:
        import canary_mcp
        from canary_mcp import main
        from canary_mcp.server import mcp, ping

        assert canary_mcp is not None
        assert main is not None
        assert mcp is not None
        assert ping is not None
    except ImportError as e:
        pytest.fail(f"Failed to import package: {e}")
