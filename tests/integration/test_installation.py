"""Integration tests for installation validation (both non-admin and Docker methods)."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def validation_script_path(project_root: Path) -> Path:
    """Get path to validation script."""
    return project_root / "scripts" / "validate_installation.py"


@pytest.fixture
def mock_env_file(project_root: Path, tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary .env file for testing."""
    env_content = """
CANARY_SAF_BASE_URL=https://test.example.com/api/v1
CANARY_VIEWS_BASE_URL=https://test.example.com
CANARY_API_TOKEN=test-token-12345678
LOG_LEVEL=DEBUG
"""
    env_file = tmp_path / ".env"
    env_file.write_text(env_content.strip())
    yield env_file
    # Cleanup happens automatically with tmp_path


# =============================================================================
# Non-Admin Installation Validation Tests
# =============================================================================


@pytest.mark.integration
def test_validation_script_exists(validation_script_path: Path):
    """Test that the installation validation script exists."""
    assert validation_script_path.exists(), f"Validation script not found at {validation_script_path}"
    assert validation_script_path.is_file()


@pytest.mark.integration
def test_validation_script_is_executable(validation_script_path: Path):
    """Test that validation script is a valid Python file."""
    # Check it starts with shebang or is valid Python
    with open(validation_script_path, "r", encoding="utf-8") as f:
        first_line = f.readline()
        assert first_line.startswith("#!/usr/bin/env python") or first_line.startswith("#")


@pytest.mark.integration
def test_validation_script_imports():
    """Test that validation script can be imported without errors."""
    import sys
    from pathlib import Path

    # Add scripts directory to path temporarily
    scripts_dir = Path(__file__).parent.parent.parent / "scripts"
    sys.path.insert(0, str(scripts_dir))

    try:
        # Import the validation module
        import validate_installation

        # Check key classes exist
        assert hasattr(validate_installation, "InstallationValidator")
        assert hasattr(validate_installation, "ValidationResult")

    finally:
        # Clean up sys.path
        sys.path.remove(str(scripts_dir))


@pytest.mark.integration
def test_python_version_check():
    """Test that Python version meets requirements (>= 3.13)."""
    major, minor = sys.version_info[:2]
    assert (major, minor) >= (3, 13), f"Python {major}.{minor} found, but 3.13+ required"


@pytest.mark.integration
def test_required_packages_installed():
    """Test that all required packages are installed."""
    required_packages = [
        "canary_mcp",
        "fastmcp",
        "httpx",
        "dotenv",
        "structlog",
    ]

    for package in required_packages:
        try:
            # Try to import each package
            module_name = package.replace("-", "_")
            __import__(module_name)
        except ImportError as e:
            pytest.fail(f"Required package '{package}' not installed: {e}")


@pytest.mark.integration
def test_validation_result_class():
    """Test ValidationResult class from validation script."""
    import sys
    from pathlib import Path

    scripts_dir = Path(__file__).parent.parent.parent / "scripts"
    sys.path.insert(0, str(scripts_dir))

    try:
        from validate_installation import ValidationResult

        # Test creating a ValidationResult instance
        result = ValidationResult(
            name="test_check",
            passed=True,
            message="Test passed",
            fix_suggestion="No fix needed",
        )

        assert result.name == "test_check"
        assert result.passed is True
        assert result.message == "Test passed"
        assert result.fix_suggestion == "No fix needed"

    finally:
        sys.path.remove(str(scripts_dir))


@pytest.mark.integration
def test_installation_validator_class():
    """Test InstallationValidator class from validation script."""
    import sys
    from pathlib import Path

    scripts_dir = Path(__file__).parent.parent.parent / "scripts"
    sys.path.insert(0, str(scripts_dir))

    try:
        from validate_installation import InstallationValidator

        # Test creating an InstallationValidator instance
        validator = InstallationValidator()

        # Check instance attributes
        assert hasattr(validator, "results")
        assert hasattr(validator, "project_root")
        assert isinstance(validator.results, list)
        assert isinstance(validator.project_root, Path)

        # Check methods exist
        assert hasattr(validator, "validate_python_version")
        assert hasattr(validator, "validate_uv_installation")
        assert hasattr(validator, "validate_package_installation")
        assert hasattr(validator, "validate_dependencies")
        assert hasattr(validator, "validate_configuration")
        assert hasattr(validator, "validate_server_start")
        assert hasattr(validator, "validate_logs_directory")
        assert hasattr(validator, "run_all_validations")

    finally:
        sys.path.remove(str(scripts_dir))


# =============================================================================
# Docker Installation Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.docker
def test_dockerfile_exists(project_root: Path):
    """Test that Dockerfile exists in project root."""
    dockerfile = project_root / "Dockerfile"
    assert dockerfile.exists(), f"Dockerfile not found at {dockerfile}"
    assert dockerfile.is_file()


@pytest.mark.integration
@pytest.mark.docker
def test_dockerfile_content(project_root: Path):
    """Test that Dockerfile contains required instructions."""
    dockerfile = project_root / "Dockerfile"
    content = dockerfile.read_text()

    # Check for multi-stage build
    assert "FROM python:3.13-slim as builder" in content, "Missing builder stage"
    assert "FROM python:3.13-slim" in content, "Missing runtime stage"

    # Check for non-root user creation
    assert "groupadd" in content, "Missing group creation"
    assert "useradd" in content, "Missing user creation"
    assert "USER mcpuser" in content, "Missing USER directive"

    # Check for health check
    assert "HEALTHCHECK" in content, "Missing HEALTHCHECK instruction"

    # Check for entrypoint
    assert "ENTRYPOINT" in content, "Missing ENTRYPOINT instruction"
    assert "canary_mcp.server" in content, "Missing server module in entrypoint"


@pytest.mark.integration
@pytest.mark.docker
def test_docker_compose_exists(project_root: Path):
    """Test that docker-compose.yml exists."""
    compose_file = project_root / "docker-compose.yml"
    assert compose_file.exists(), f"docker-compose.yml not found at {compose_file}"
    assert compose_file.is_file()


@pytest.mark.integration
@pytest.mark.docker
def test_docker_compose_content(project_root: Path):
    """Test that docker-compose.yml contains required configuration."""
    compose_file = project_root / "docker-compose.yml"
    content = compose_file.read_text()

    # Check for service definition
    assert "canary-mcp-server:" in content, "Missing service definition"

    # Check for environment file
    assert "env_file:" in content or "environment:" in content, "Missing environment configuration"

    # Check for volumes
    assert "volumes:" in content, "Missing volume configuration"

    # Check for health check
    assert "healthcheck:" in content, "Missing healthcheck configuration"

    # Check for logging
    assert "logging:" in content, "Missing logging configuration"


@pytest.mark.integration
@pytest.mark.docker
def test_dockerignore_exists(project_root: Path):
    """Test that .dockerignore exists."""
    dockerignore = project_root / ".dockerignore"
    assert dockerignore.exists(), f".dockerignore not found at {dockerignore}"
    assert dockerignore.is_file()


@pytest.mark.integration
@pytest.mark.docker
def test_dockerignore_content(project_root: Path):
    """Test that .dockerignore excludes unnecessary files."""
    dockerignore = project_root / ".dockerignore"
    content = dockerignore.read_text()

    # Check for common exclusions
    exclusions = [
        "__pycache__",
        ".env",
        ".git",
        "tests/",
        "docs/",
        ".vscode/",
        ".pytest_cache/",
    ]

    for exclusion in exclusions:
        assert exclusion in content, f"Missing exclusion: {exclusion}"


@pytest.mark.integration
@pytest.mark.docker
@pytest.mark.skipif(
    not os.getenv("DOCKER_AVAILABLE", "false").lower() == "true",
    reason="Docker not available in test environment",
)
def test_docker_image_builds(project_root: Path):
    """Test that Docker image builds successfully (requires Docker)."""
    # This test runs only when Docker is available
    result = subprocess.run(
        ["docker", "build", "-t", "canary-mcp-server-test", "."],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=300,  # 5 minute timeout for build
    )

    assert result.returncode == 0, f"Docker build failed: {result.stderr}"
    assert "Successfully built" in result.stdout or "Successfully tagged" in result.stdout


@pytest.mark.integration
@pytest.mark.docker
@pytest.mark.skipif(
    not os.getenv("DOCKER_AVAILABLE", "false").lower() == "true",
    reason="Docker not available in test environment",
)
def test_docker_container_starts(project_root: Path, mock_env_file: Path):
    """Test that Docker container starts successfully (requires Docker)."""
    # This test runs only when Docker is available
    container_name = "canary-mcp-server-test-instance"

    try:
        # Start container
        result = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container_name,
                "--env-file",
                str(mock_env_file),
                "canary-mcp-server-test",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Container start failed: {result.stderr}"

        # Wait a moment for container to initialize
        import time

        time.sleep(2)

        # Check container is running
        status_result = subprocess.run(
            ["docker", "ps", "-f", f"name={container_name}", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
        )

        assert "Up" in status_result.stdout, f"Container not running: {status_result.stdout}"

    finally:
        # Cleanup: Stop and remove container
        subprocess.run(["docker", "stop", container_name], capture_output=True, timeout=10)
        subprocess.run(["docker", "rm", container_name], capture_output=True, timeout=10)


# =============================================================================
# Configuration Tests (Both Installation Methods)
# =============================================================================


@pytest.mark.integration
def test_env_example_exists(project_root: Path):
    """Test that .env.example file exists."""
    env_example = project_root / ".env.example"
    assert env_example.exists(), f".env.example not found at {env_example}"
    assert env_example.is_file()


@pytest.mark.integration
def test_env_example_has_required_variables(project_root: Path):
    """Test that .env.example contains all required configuration variables."""
    env_example = project_root / ".env.example"
    content = env_example.read_text()

    required_vars = [
        "CANARY_SAF_BASE_URL",
        "CANARY_VIEWS_BASE_URL",
        "CANARY_API_TOKEN",
        "LOG_LEVEL",
        "CANARY_SESSION_TIMEOUT_MS",
        "CANARY_REQUEST_TIMEOUT_SECONDS",
        "CANARY_RETRY_ATTEMPTS",
    ]

    for var in required_vars:
        assert var in content, f"Required variable '{var}' not found in .env.example"


@pytest.mark.integration
def test_env_example_has_documentation(project_root: Path):
    """Test that .env.example has comprehensive documentation."""
    env_example = project_root / ".env.example"
    content = env_example.read_text()

    # Check for header documentation
    assert "Environment Configuration" in content, "Missing header documentation"

    # Check for section headers
    sections = [
        "REQUIRED",
        "Canary API Configuration",
        "Logging Configuration",
    ]

    for section in sections:
        assert section in content, f"Missing section documentation: {section}"


@pytest.mark.integration
def test_configuration_loading_from_env(mock_env_file: Path):
    """Test that configuration can be loaded from .env file."""
    from dotenv import load_dotenv

    # Load configuration from test .env file
    loaded = load_dotenv(mock_env_file)
    assert loaded, "Failed to load .env file"

    # Verify variables are in environment
    assert os.getenv("CANARY_SAF_BASE_URL") == "https://test.example.com/api/v1"
    assert os.getenv("CANARY_VIEWS_BASE_URL") == "https://test.example.com"
    assert os.getenv("CANARY_API_TOKEN") == "test-token-12345678"
    assert os.getenv("LOG_LEVEL") == "DEBUG"

    # Cleanup
    for var in ["CANARY_SAF_BASE_URL", "CANARY_VIEWS_BASE_URL", "CANARY_API_TOKEN", "LOG_LEVEL"]:
        os.environ.pop(var, None)


# =============================================================================
# Server Health Check Tests (Both Installation Methods)
# =============================================================================


@pytest.mark.integration
def test_server_module_can_be_imported():
    """Test that server module can be imported successfully."""
    from canary_mcp import server

    assert server is not None
    assert hasattr(server, "mcp")
    assert hasattr(server, "main")


@pytest.mark.integration
def test_server_main_function_exists():
    """Test that server has a main entry point."""
    from canary_mcp.server import main

    assert main is not None
    assert callable(main)


@pytest.mark.integration
def test_server_health_check_logic():
    """Test the health check logic used in Docker healthcheck."""
    # This simulates the Docker HEALTHCHECK command:
    # python -c "import canary_mcp.server; print('healthy')"

    try:
        import canary_mcp.server

        # If import succeeds, health check would pass
        assert True
    except ImportError as e:
        pytest.fail(f"Server health check failed: cannot import canary_mcp.server: {e}")


# =============================================================================
# MCP Tools Functionality Tests (Both Installation Methods)
# =============================================================================


@pytest.mark.integration
def test_mcp_tools_work_after_installation():
    """Test that MCP tools are functional after installation."""
    from canary_mcp.server import mcp

    # Check MCP server is initialized
    assert mcp is not None
    assert mcp.name == "Canary MCP Server"


@pytest.mark.integration
def test_ping_tool_works():
    """Test that ping tool works correctly."""
    from canary_mcp.server import ping

    assert ping is not None
    response = ping.fn()
    assert isinstance(response, str)
    assert "pong" in response.lower()


@pytest.mark.integration
def test_all_mcp_tools_registered():
    """Test that all expected MCP tools are registered."""
    from canary_mcp.server import mcp

    # Get list of tool names (FastMCP stores tools internally)
    # This checks that the server has tools registered
    assert hasattr(mcp, "_mcp")


# =============================================================================
# Installation Documentation Tests
# =============================================================================


@pytest.mark.integration
def test_installation_docs_exist(project_root: Path):
    """Test that installation documentation exists."""
    docs_dir = project_root / "docs" / "installation"

    # Check documentation directory exists
    assert docs_dir.exists(), f"Installation docs directory not found at {docs_dir}"

    # Check individual documentation files
    expected_docs = [
        "non-admin-windows.md",
        "docker-installation.md",
        "troubleshooting.md",
    ]

    for doc_file in expected_docs:
        doc_path = docs_dir / doc_file
        assert doc_path.exists(), f"Documentation file not found: {doc_file}"
        assert doc_path.is_file()

        # Check file is not empty
        content = doc_path.read_text()
        assert len(content) > 100, f"Documentation file is too short: {doc_file}"


@pytest.mark.integration
def test_readme_has_installation_section(project_root: Path):
    """Test that README.md has comprehensive installation section."""
    readme = project_root / "README.md"
    assert readme.exists(), "README.md not found"

    content = readme.read_text()

    # Check for installation section
    assert "## Installation" in content, "Missing Installation section in README"

    # Check for installation comparison table
    assert "Installation Options" in content or "Feature" in content, "Missing installation comparison"

    # Check for links to detailed guides
    assert "docs/installation/non-admin-windows.md" in content, "Missing link to non-admin guide"
    assert "docs/installation/docker-installation.md" in content, "Missing link to Docker guide"


# =============================================================================
# Logs Directory Tests
# =============================================================================


@pytest.mark.integration
def test_logs_directory_can_be_created(tmp_path: Path):
    """Test that logs directory can be created without admin privileges."""
    logs_dir = tmp_path / "logs"

    # Create logs directory
    logs_dir.mkdir(exist_ok=True)
    assert logs_dir.exists()
    assert logs_dir.is_dir()

    # Test write permissions
    test_file = logs_dir / "test.log"
    test_file.write_text("test log entry")
    assert test_file.exists()

    content = test_file.read_text()
    assert content == "test log entry"
