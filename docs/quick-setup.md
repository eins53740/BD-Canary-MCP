# Canary MCP - UNS-OT Preview

Audience: IT developers on Windows evaluating the first release of this MCP server for local (stdio) use.

Project: `Canary-MCP-Server`

Goal: Get up and running quickly in Claude Desktop (local MCP over stdio) and VS Code on Windows, with Python deps managed via `uv`.

Repository (Enterprise GitHub): https://secil.ghe.com/secil-uns-ot/CanaryMCP
Alternative: https://github.com/eins53740/BD-Canary-MCP

Repo Guide: https://deepwiki.com/eins53740/BD-Canary-MCP

---

## 1. Prerequisites

- OS: Windows 10/11
- Tools:
  - Python 3.11+ (recommended 3.12)
  - Git
  - VS Code (latest)
  - Claude Desktop (latest)
  - Node.js LTS (optional; not required for MCP usage)


## 2. Install Python tooling with uv (Windows)

`uv` is a fast Python package and environment manager.

1) Install uv (PowerShell):

```powershell
iwr https://astral.sh/uv/install.ps1 -UseBasicParsing | iex
$env:Path += ";$env:USERPROFILE\.local\bin"
uv --version
```

2) Ensure Python 3.11+ available

```powershell
uv python install 3.12
uv python list
```

3) Create and activate a project environment

Use this path as your local clone root: `C:\Users\<username>\Documents\GitHub\CanaryMCP`

Create a venv and verify Python:

```powershell
cd C:\Users\<username>\Documents\GitHub\CanaryMCP
uv venv --python 3.12
uv run python -V
```

4) Install dependencies

If the project provides `pyproject.toml`/`requirements.txt`, run:

```powershell
uv pip install -e .
# or
uv pip install -r requirements.txt
```

If none exist yet, install runtime deps your MCP server needs, for example:

```powershell
uv pip install mcp python-dotenv pydantic loguru
```

Note: Replace with the exact packages defined by this project when available.


### One-shot setup script (PowerShell)

Save as `scripts/setup.ps1`, then right-click → Run with PowerShell (or execute from a PowerShell terminal). Adjust `<username>` if needed.

```powershell
param(
  [string]$RepoDir = "C:\Users\<username>\Documents\GitHub\CanaryMCP"
)

Write-Host "Installing uv..."
iwr https://astral.sh/uv/install.ps1 -UseBasicParsing | iex
$env:Path += ";$env:USERPROFILE\.local\bin"
uv --version

Write-Host "Ensuring Python 3.12 with uv..."
uv python install 3.12

Write-Host "Creating venv in $RepoDir ..."
if (!(Test-Path $RepoDir)) { New-Item -ItemType Directory -Force -Path $RepoDir | Out-Null }
Set-Location $RepoDir
uv venv --python 3.12

Write-Host "Installing project dependencies..."
if (Test-Path "$RepoDir\pyproject.toml") {
  uv pip install -e .
} elseif (Test-Path "$RepoDir\requirements.txt") {
  uv pip install -r requirements.txt
} else {
  uv pip install mcp python-dotenv pydantic loguru
}

Write-Host "Verifying interpreter..."
uv run python -V

Write-Host "Done. You can now run: uv run python -m canary_mcp.server"
```


## 3. Verify the MCP server entry point (Windows)

Identify the server’s executable entry (stdio mode). Common patterns:

- A console script (installed via `pip`) such as `canary-mcp-server`
- A Python module you run with `uv run -m package.module`
- A script file such as `uv run python -m src.server` or `uv run python scripts/server.py`

For this project, a typical local run might look like:

```powershell
uv run python -m canary_mcp.server
```

Adjust the command to match your actual entry point. You should be able to run it without errors; it will wait for stdio connections once launched by a client.


## 4. Claude Desktop MCP configuration (Windows, local stdio)

Claude Desktop discovers MCP servers via a JSON manifest. Create the config file and point it to this project’s stdio command.

1) Find Claude Desktop’s MCP config directory (Windows): `%APPDATA%\Claude\mcp`

2) Create or edit `config.json` in that directory and use this content:

```json
{
  "mcpServers": {
    "canary-uv": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\<username>\\Documents\\GitHub\\CanaryMCP",
        "run",
        "python",
        "-m",
        "canary_mcp.server"
      ],
      "env": {
        "CANARY_SAF_BASE_URL": "https://scunscanary.secil.pt:55236/api/v2",
        "CANARY_VIEWS_BASE_URL": "https://scunscanary.secil.pt:55236",
        "CANARY_API_TOKEN": "0120fd2e-e9c2-4c8d-8115-a6ceb41490ce"
      }
    }
  }
}
```

Notes:
- Set `workingDirectory` to the absolute path of your `Canary-MCP-Server` repo (e.g., `C:\Users\you\code\Canary-MCP-Server` or `/Users/you/code/Canary-MCP-Server`).
- If your server installs a console script `canary-mcp-server`, you can simplify to:
  ```json
  {
    "canary-mcp": {
      "command": "canary-mcp-server",
      "args": ["--stdio"],
      "env": { "PYTHONUNBUFFERED": "1" }
    }
  }
  ```

3) Restart Claude Desktop.

4) Open a new chat and enable the `canary-uv` tool when prompted. If not prompted, open Settings → Developer → MCP Servers to confirm it’s recognized.


## 5. VS Code setup (Windows)

1) Install Python extension (Microsoft) and recommended linters/formatters:
   - Ruff, Black

2) Open the repository folder in VS Code and select the `uv` virtualenv interpreter:
   - Command Palette → “Python: Select Interpreter” → your `.venv` created by `uv venv`.

3) Optional: Add workspace settings `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": ".venv\\Scripts\\python.exe",
  "python.testing.pytestEnabled": true,
  "python.formatting.provider": "black",
  "ruff.enable": true
}
```


## 6. Running and testing locally

- Dry run the server (from repo root):
  ```powershell
  uv run python -m canary_mcp.server
  ```
  Expect it to wait for a client connection from Claude via stdio when launched by Claude.

- If you have unit tests:
  ```bash
  uv run pytest -q
  ```

- Linting:
  ```powershell
  ruff check .
  ```


## 7. Troubleshooting

- Claude doesn’t list the server:
  - Recheck `servers.json` path, command, and `workingDirectory`.
  - Ensure the entry point runs manually with `uv run ...`.
  - Restart Claude Desktop after edits.

- Import/module errors:
  - Verify you installed deps in the active `uv` env.
  - Confirm the module name in `-m canary_mcp_server` matches your package.

- Windows path issues:
  - Use escaped backslashes in JSON or forward slashes.
  - Ensure `.venv\Scripts` is used by VS Code.


## 8. Example .env (optional)

Create `.env` in the repo root if the server reads config from environment. Example:

```
LOG_LEVEL=INFO
CANARY_ENDPOINT=https://scunscanary.secil.pt:55236
API_KEY=changeme
```

Never commit real secrets.


## 9. Next steps

- Share the `servers.json` snippet with teammates to standardize setup.
- Add tests and linters to CI (Ruff, Black, Pytest) for consistency.
- Document server capabilities and MCP tool definitions in `README.md`.
