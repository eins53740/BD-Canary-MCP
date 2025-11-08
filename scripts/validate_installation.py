#!/usr/bin/env python
"""Installation validation script for Canary MCP Server.

This script validates that the Canary MCP Server is correctly installed
and configured for non-admin users on Windows. It checks all prerequisites
and provides actionable error messages for any issues found.

Usage:
    python scripts/validate_installation.py

Exit codes:
    0 - All validations passed
    1 - One or more validations failed
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List

# ANSI color codes for terminal output
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


class InstallationValidator:
    """Validates Canary MCP Server installation."""

    def __init__(self):
        self.results: List[ValidationResult] = []
        self.project_root = Path(__file__).parent.parent

    def print_header(self):
        """Print validation header."""
        print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
        print(f"{BOLD}{BLUE}Canary MCP Server - Installation Validation{RESET}")
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
        self.print_section("Checking Python Installation")

        try:
            result = subprocess.run(
                ["python", "--version"],
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
                    "Install Python 3.13 from https://www.python.org/downloads/",
                )
                return False

        except FileNotFoundError:
            self.check_failed(
                "python_version",
                "Python not found in PATH",
                "Add Python to your PATH or install from https://www.python.org/downloads/",
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
        """Check if uv package manager is installed and accessible."""
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
                'Install uv: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"',
            )
            return False
        except Exception as e:
            self.check_failed(
                "uv_installation",
                f"Error checking uv: {e}",
                "Verify uv is installed and in PATH",
            )
            return False

    def validate_package_installation(self) -> bool:
        """Check if canary-mcp-server package is installed."""
        self.print_section("Checking Package Installation")

        try:
            # Try importing the main module
            import canary_mcp

            package_path = Path(canary_mcp.__file__).parent
            self.check_passed(
                "package_installation",
                f"canary-mcp package found at: {package_path}",
            )
            return True

        except ImportError:
            self.check_failed(
                "package_installation",
                "canary-mcp package not installed",
                "Install package: uv pip install -e .",
            )
            return False
        except Exception as e:
            self.check_failed(
                "package_installation",
                f"Error checking package: {e}",
                "Reinstall package: uv pip install -e .",
            )
            return False

    def validate_dependencies(self) -> bool:
        """Check if required dependencies are installed."""
        self.print_section("Checking Dependencies")

        required_packages = {
            "fastmcp": "FastMCP framework",
            "httpx": "HTTP client library",
            "python-dotenv": "Environment variable loader",
            "structlog": "Structured logging",
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
                    f"Install: uv pip install {package}",
                )
                all_installed = False

        return all_installed

    def validate_configuration(self) -> bool:
        """Check if configuration file exists and is valid."""
        self.print_section("Checking Configuration")

        # Check for .env file in project root
        env_file = self.project_root / ".env"
        env_example = self.project_root / ".env.example"

        if not env_file.exists():
            if env_example.exists():
                self.check_failed(
                    "config_file",
                    ".env file not found (but .env.example exists)",
                    f"Copy .env.example to .env and configure: copy {env_example} {env_file}",
                )
            else:
                self.check_failed(
                    "config_file",
                    ".env file not found",
                    "Create .env file in project root with Canary API credentials",
                )
            return False

        self.check_passed(
            "config_file",
            f".env file found at: {env_file}",
        )

        # Validate required environment variables
        from dotenv import load_dotenv

        load_dotenv(env_file)

        required_vars = [
            "CANARY_SAF_BASE_URL",
            "CANARY_VIEWS_BASE_URL",
            "CANARY_API_TOKEN",
        ]

        all_present = True
        for var in required_vars:
            value = os.getenv(var)
            if value:
                # Mask token for security
                if "TOKEN" in var:
                    masked_value = (
                        f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"
                    )
                    self.check_passed(
                        f"config_{var}",
                        f"{var} is set (value: {masked_value})",
                    )
                else:
                    self.check_passed(
                        f"config_{var}",
                        f"{var} is set (value: {value})",
                    )
            else:
                self.check_failed(
                    f"config_{var}",
                    f"{var} is not set",
                    f"Add {var} to .env file",
                )
                all_present = False

        return all_present

    def validate_server_start(self) -> bool:
        """Check if server can start without admin privileges."""
        self.print_section("Checking Server Startup")

        try:
            # Try to import the server module (doesn't actually start it)
            from canary_mcp import server

            self.check_passed(
                "server_import",
                "Server module can be imported successfully",
            )

            # Check if main entry point exists
            if hasattr(server, "main"):
                self.check_passed(
                    "server_entrypoint",
                    "Server entry point (main function) exists",
                )
            else:
                self.check_failed(
                    "server_entrypoint",
                    "Server entry point (main function) not found",
                    "Verify server.py has a main() function",
                )
                return False

            return True

        except ImportError as e:
            self.check_failed(
                "server_import",
                f"Cannot import server module: {e}",
                "Verify package is installed correctly: uv pip install -e .",
            )
            return False
        except Exception as e:
            self.check_failed(
                "server_import",
                f"Error checking server: {e}",
                "Verify package installation is complete",
            )
            return False

    def validate_logs_directory(self) -> bool:
        """Check if logs directory can be created (no admin needed)."""
        self.print_section("Checking Logs Directory")

        logs_dir = self.project_root / "logs"

        try:
            # Create logs directory if it doesn't exist
            logs_dir.mkdir(exist_ok=True)

            # Try to create a test file to verify write permissions
            test_file = logs_dir / ".validation_test"
            test_file.write_text("test")
            test_file.unlink()  # Clean up

            self.check_passed(
                "logs_directory",
                f"Logs directory accessible and writable: {logs_dir}",
            )
            return True

        except PermissionError:
            self.check_failed(
                "logs_directory",
                f"Cannot write to logs directory: {logs_dir}",
                "Check directory permissions or choose a different location",
            )
            return False
        except Exception as e:
            self.check_failed(
                "logs_directory",
                f"Error with logs directory: {e}",
                "Verify directory can be created in project root",
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
            print(f"{GREEN}{BOLD}✓ All validations passed!{RESET}")
            print(
                f"{GREEN}Your Canary MCP Server installation is ready to use.{RESET}\n"
            )
            print("To start the server, run:")
            print(f"  {BLUE}python -m canary_mcp.server{RESET}\n")
            return True
        else:
            print(f"{RED}{BOLD}✗ Some validations failed.{RESET}")
            print(
                f"{RED}Please fix the issues listed above before running the server.{RESET}\n"
            )
            print("For detailed troubleshooting, see:")
            print(f"  {BLUE}docs/installation/troubleshooting.md{RESET}\n")
            return False

    def run_all_validations(self) -> bool:
        """Run all validation checks."""
        self.print_header()

        # Run all checks
        self.validate_python_version()
        self.validate_uv_installation()
        self.validate_package_installation()
        self.validate_dependencies()
        self.validate_configuration()
        self.validate_server_start()
        self.validate_logs_directory()

        # Print summary
        return self.print_summary()


def main():
    """Main entry point for validation script."""
    validator = InstallationValidator()

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
