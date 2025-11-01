#!/usr/bin/env python
"""Development environment validation script for Canary MCP Server.

This script validates that the development environment is correctly set up
with all required tools, dependencies, and configurations.

Usage:
    python scripts/validate_dev_setup.py

Exit codes:
    0 - All validations passed
    1 - One or more validations failed
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


class ValidationResult:
    """Represents the result of a single validation check."""

    def __init__(self, name: str, passed: bool, message: str, fix_suggestion: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.fix_suggestion = fix_suggestion


class DevEnvironmentValidator:
    """Validates development environment setup."""

    def __init__(self):
        self.results: List[ValidationResult] = []
        self.project_root = Path(__file__).parent.parent

    def print_header(self):
        """Print validation header."""
        print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
        print(f"{BOLD}{BLUE}Canary MCP Server - Development Environment Validation{RESET}")
        print(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")

    def print_section(self, title: str):
        """Print section header."""
        print(f"\n{BOLD}{YELLOW}>>> {title}{RESET}")

    def check_passed(self, name: str, message: str):
        """Record a passed check."""
        result = ValidationResult(name, True, message)
        self.results.append(result)
        print(f"  {GREEN}✓{RESET} {message}")

    def check_failed(self, name: str, message: str, fix_suggestion: str = ""):
        """Record a failed check."""
        result = ValidationResult(name, False, message, fix_suggestion)
        self.results.append(result)
        print(f"  {RED}✗{RESET} {message}")
        if fix_suggestion:
            print(f"    {YELLOW}Fix:{RESET} {fix_suggestion}")

    def validate_python_version(self) -> bool:
        """Check if Python version is 3.13 or higher."""
        self.print_section("Checking Python Version")

        try:
            result = subprocess.run(
                [sys.executable, "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            version_str = result.stdout.strip()
            version_parts = version_str.split()[1].split(".")
            major = int(version_parts[0])
            minor = int(version_parts[1])

            if (major, minor) >= (3, 13):
                self.check_passed(
                    "python_version",
                    f"Python version: {version_str}",
                )
                return True
            else:
                self.check_failed(
                    "python_version",
                    f"Python {version_str} found, but 3.13+ required",
                    "Install Python 3.13+ from https://www.python.org/downloads/",
                )
                return False

        except Exception as e:
            self.check_failed(
                "python_version",
                f"Error checking Python version: {e}",
                "Verify Python is installed correctly",
            )
            return False

    def validate_uv_installation(self) -> bool:
        """Check if uv package manager is installed."""
        self.print_section("Checking uv Package Manager")

        try:
            result = subprocess.run(
                ["uv", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            version_str = result.stdout.strip()
            self.check_passed(
                "uv_installation",
                f"uv version: {version_str}",
            )
            return True

        except FileNotFoundError:
            self.check_failed(
                "uv_installation",
                "uv not found in PATH",
                "Install uv: powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"",
            )
            return False
        except Exception as e:
            self.check_failed(
                "uv_installation",
                f"Error checking uv: {e}",
                "Verify uv is installed and in PATH",
            )
            return False

    def validate_venv_exists(self) -> bool:
        """Check if virtual environment exists."""
        self.print_section("Checking Virtual Environment")

        venv_path = self.project_root / ".venv"

        if venv_path.exists() and venv_path.is_dir():
            self.check_passed(
                "venv_exists",
                f"Virtual environment found at: {venv_path}",
            )
            return True
        else:
            self.check_failed(
                "venv_exists",
                "Virtual environment not found",
                "Run: uv sync --all-extras",
            )
            return False

    def validate_dependencies(self) -> bool:
        """Check if all required dependencies are installed."""
        self.print_section("Checking Dependencies")

        required_packages = {
            "fastmcp": "FastMCP framework",
            "httpx": "HTTP client library",
            "python-dotenv": "Environment variable loader",
            "structlog": "Structured logging",
            "pytest": "Testing framework",
        }

        all_installed = True

        for package, description in required_packages.items():
            try:
                __import__(package.replace("-", "_"))
                self.check_passed(
                    f"dependency_{package}",
                    f"{description} ({package})",
                )
            except ImportError:
                self.check_failed(
                    f"dependency_{package}",
                    f"Missing: {description} ({package})",
                    f"Install: uv sync --all-extras",
                )
                all_installed = False

        return all_installed

    def validate_pre_commit_hooks(self) -> bool:
        """Check if pre-commit hooks are installed."""
        self.print_section("Checking Pre-commit Hooks")

        # Check if .pre-commit-config.yaml exists
        config_file = self.project_root / ".pre-commit-config.yaml"
        if not config_file.exists():
            self.check_failed(
                "precommit_config",
                ".pre-commit-config.yaml not found",
                "Pre-commit configuration missing",
            )
            return False

        self.check_passed(
            "precommit_config",
            f"Pre-commit config found: {config_file}",
        )

        # Check if pre-commit is installed
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pre_commit", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            version_str = result.stdout.strip()
            self.check_passed(
                "precommit_installed",
                f"Pre-commit installed: {version_str}",
            )

            # Check if hooks are installed in .git
            git_hooks = self.project_root / ".git" / "hooks" / "pre-commit"
            if git_hooks.exists():
                self.check_passed(
                    "precommit_hooks",
                    "Pre-commit hooks installed in .git/hooks",
                )
                return True
            else:
                self.check_failed(
                    "precommit_hooks",
                    "Pre-commit hooks not installed",
                    "Run: uv run pre-commit install",
                )
                return False

        except FileNotFoundError:
            self.check_failed(
                "precommit_installed",
                "Pre-commit not installed",
                "Install: uv sync --all-extras",
            )
            return False
        except Exception as e:
            self.check_failed(
                "precommit_installed",
                f"Error checking pre-commit: {e}",
                "Verify pre-commit is installed",
            )
            return False

    def validate_ide_configuration(self) -> bool:
        """Check if IDE configuration files exist."""
        self.print_section("Checking IDE Configuration")

        vscode_dir = self.project_root / ".vscode"
        vscode_files = {
            "settings.json": "VS Code settings",
            "extensions.json": "Recommended extensions",
            "launch.json": "Debug configurations",
        }

        all_present = True
        for filename, description in vscode_files.items():
            filepath = vscode_dir / filename
            if filepath.exists():
                self.check_passed(
                    f"vscode_{filename}",
                    f"{description}: {filepath}",
                )
            else:
                self.check_failed(
                    f"vscode_{filename}",
                    f"{description} not found",
                    "IDE configuration may be incomplete",
                )
                all_present = False

        return all_present

    def validate_env_file(self) -> bool:
        """Check if .env file exists."""
        self.print_section("Checking Environment Configuration")

        env_file = self.project_root / ".env"
        env_example = self.project_root / ".env.example"

        if not env_file.exists():
            if env_example.exists():
                self.check_failed(
                    "env_file",
                    ".env file not found (but .env.example exists)",
                    f"Copy .env.example to .env and configure: copy {env_example} {env_file}",
                )
            else:
                self.check_failed(
                    "env_file",
                    ".env file not found",
                    "Create .env file with Canary API credentials",
                )
            return False

        self.check_passed(
            "env_file",
            f".env file found at: {env_file}",
        )
        return True

    def validate_tests_pass(self) -> bool:
        """Check if tests pass."""
        self.print_section("Running Tests")

        try:
            # Run a quick test to verify setup
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=line"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                # Extract test count from output
                output_lines = result.stdout.strip().split("\n")
                last_line = output_lines[-1] if output_lines else ""
                self.check_passed(
                    "tests_pass",
                    f"Tests passed: {last_line}",
                )
                return True
            else:
                self.check_failed(
                    "tests_pass",
                    "Some tests failed",
                    "Fix failing tests before continuing development",
                )
                return False

        except subprocess.TimeoutExpired:
            self.check_failed(
                "tests_pass",
                "Tests timed out (>60s)",
                "Check for hanging tests or slow operations",
            )
            return False
        except Exception as e:
            self.check_failed(
                "tests_pass",
                f"Error running tests: {e}",
                "Verify pytest is installed: uv sync --all-extras",
            )
            return False

    def print_summary(self):
        """Print validation summary."""
        print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
        print(f"{BOLD}{BLUE}Validation Summary{RESET}")
        print(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")

        passed_count = sum(1 for r in self.results if r.passed)
        failed_count = sum(1 for r in self.results if not r.passed)
        total_count = len(self.results)

        print(f"Total checks: {total_count}")
        print(f"{GREEN}Passed: {passed_count}{RESET}")
        print(f"{RED}Failed: {failed_count}{RESET}\n")

        if failed_count == 0:
            print(f"{GREEN}{BOLD}✓ Development environment is ready!{RESET}")
            print(f"{GREEN}You can start developing and testing.{RESET}\n")
            print(f"Quick start:")
            print(f"  {BLUE}uv run python -m canary_mcp.server{RESET}  # Run server")
            print(f"  {BLUE}uv run pytest tests/ -v{RESET}            # Run tests")
            print(f"  {BLUE}uv run ruff check .{RESET}                # Check code quality\n")
            return True
        else:
            print(f"{RED}{BOLD}✗ Some validations failed.{RESET}")
            print(f"{RED}Please fix the issues listed above.{RESET}\n")
            print(f"For help, see:")
            print(f"  {BLUE}docs/development/quick-start.md{RESET}\n")
            return False

    def run_all_validations(self) -> bool:
        """Run all validation checks."""
        self.print_header()

        # Run all checks
        self.validate_python_version()
        self.validate_uv_installation()
        self.validate_venv_exists()
        self.validate_dependencies()
        self.validate_pre_commit_hooks()
        self.validate_ide_configuration()
        self.validate_env_file()
        self.validate_tests_pass()

        # Print summary
        return self.print_summary()


def main():
    """Main entry point for validation script."""
    validator = DevEnvironmentValidator()

    try:
        all_passed = validator.run_all_validations()
        sys.exit(0 if all_passed else 1)

    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Validation interrupted by user.{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Unexpected error during validation: {e}{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
