# Developer Quick Start Guide

Get the Canary MCP Server development environment running in under 5 minutes.

## Prerequisites

- **Python 3.13+** - [Download from python.org](https://www.python.org/downloads/)
- **Git** - [Download from git-scm.com](https://git-scm.com/)
- **uv** - Fast Python package manager

## Quick Setup (< 5 minutes)

### 1. Install uv (30 seconds)

```powershell
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and Setup (2 minutes)

```bash
# Clone repository
git clone <repository-url>
cd BD-hackaton-2025-10

# Install dependencies (creates .venv automatically)
uv sync --all-extras

# Create environment file
copy .env.example .env
# Edit .env with your Canary API credentials
```

### 3. Install Pre-commit Hooks (1 minute)

```bash
# Install pre-commit hooks
uv run pre-commit install

# Test hooks (optional)
uv run pre-commit run --all-files
```

### 4. Validate Setup (30 seconds)

```bash
# Run validation script
uv run python scripts/validate_dev_setup.py

# Run tests to verify
uv run pytest tests/ -v
```

### 5. Start Developing! (30 seconds)

```bash
# Run server in development mode
uv run python -m canary_mcp.server

# Run tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/unit/test_auth.py -v

# Check code quality
uv run ruff check .
uv run ruff format .
```

## IDE Setup

### VS Code (Recommended)

1. Open folder in VS Code
2. Install recommended extensions (popup will appear)
3. Select Python interpreter: `.venv/Scripts/python.exe`
4. Done! Settings are pre-configured

### PyCharm

1. Open project in PyCharm
2. Configure Python interpreter: Settings → Project → Python Interpreter → Add → Existing Environment → Select `.venv/Scripts/python.exe`
3. Enable pytest: Settings → Tools → Python Integrated Tools → Testing → pytest
4. Install Ruff plugin: Settings → Plugins → Search "Ruff" → Install

## Common Development Workflows

### Running the Server

```bash
# Standard mode
uv run python -m canary_mcp.server

# Debug mode (if implemented)
uv run python -m canary_mcp.server --debug
```

### Running Tests

```bash
# All tests
uv run pytest

# Unit tests only
uv run pytest tests/unit -v

# Integration tests only
uv run pytest tests/integration -v

# Specific test file
uv run pytest tests/unit/test_auth.py -v

# With coverage
uv run pytest --cov=src --cov-report=html
```

### Code Quality

```bash
# Check linting
uv run ruff check .

# Auto-fix linting issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Run all pre-commit hooks manually
uv run pre-commit run --all-files
```

### Debugging

**VS Code:**
1. Open Debug panel (Ctrl+Shift+D)
2. Select "Python: MCP Server" configuration
3. Press F5 to start debugging

**PyCharm:**
1. Right-click on `src/canary_mcp/server.py`
2. Select "Debug 'server'"

## Troubleshooting

### Issue: `uv: command not found`

**Solution:**
```bash
# Restart terminal after installing uv
# Or add to PATH manually:
# Windows: %USERPROFILE%\.cargo\bin
# Linux/macOS: ~/.cargo/bin
```

### Issue: `ModuleNotFoundError: No module named 'canary_mcp'`

**Solution:**
```bash
# Reinstall in editable mode
uv sync --all-extras

# Or explicitly:
uv pip install -e .
```

### Issue: Tests fail with import errors

**Solution:**
```bash
# Ensure PYTHONPATH includes src/
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"  # Linux/macOS
$env:PYTHONPATH="$(pwd)\src"  # Windows PowerShell
```

### Issue: Pre-commit hooks too slow

**Solution:**
```bash
# Skip hooks for urgent commits
git commit --no-verify -m "message"

# Or disable pytest hook (see .pre-commit-config.yaml)
```

### Issue: `.env` file missing

**Solution:**
```bash
# Copy from example
copy .env.example .env

# Add your Canary API credentials
# CANARY_SAF_BASE_URL=https://your-server.com/api/v1
# CANARY_VIEWS_BASE_URL=https://your-server.com
# CANARY_API_TOKEN=your-token-here
```

## Next Steps

- Review [Development Environment Guide](dev-environment.md) for detailed information
- Check [Architecture Documentation](../architecture.md)
- See [Testing Strategy](../testing-strategy.md)
- Read [Contributing Guidelines](../../CONTRIBUTING.md) (if available)

## Need Help?

- Check `docs/` for comprehensive documentation
- Review test files for usage examples
- See [Troubleshooting Guide](../installation/troubleshooting.md)

---

**Time to first commit:** < 5 minutes ✅
