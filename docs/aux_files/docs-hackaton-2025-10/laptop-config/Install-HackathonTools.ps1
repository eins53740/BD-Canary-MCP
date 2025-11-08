<#
Secil Hackathon Setup - v6.1 (Final)
Installs Node.js, VS Code, Git and Claude CLI quickly and reliably.
Compatible with Intune (SYSTEM) and user execution contexts.
#>

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# --- Logging setup ---
$logDir = "C:\ProgramData\SecilHackathon"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }
$logFile = Join-Path $logDir "Install.log"
function Log($msg) {
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts][System] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

Log "=== Installation of Hackathon Tools (Node.js, VS Code, Git, Claude CLI) ==="

# 1. Ensure Administrator privileges
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Log "ERROR: This script must be executed as Administrator."
    exit 1
}

# 2. Allow script execution
try {
    Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope LocalMachine -Force
    Log "Execution policy set to Bypass."
} catch {
    Log "Warning: Could not change execution policy."
}

# 3. Install Chocolatey if missing
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Log "Installing Chocolatey..."
    Set-ExecutionPolicy Bypass -Scope Process -Force
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    Log "Chocolatey installed."
} else {
    Log "Chocolatey already installed."
}

# Refresh PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
             [System.Environment]::GetEnvironmentVariable("Path","User")

# 4. Install Node.js (LTS)
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Log "Installing Node.js (LTS)..."
    choco install nodejs-lts -y --no-progress
    Log "Node.js installed."
} else {
    Log ("Node.js already present: " + (node --version))
}

# 5. Install Visual Studio Code
if (-not (Get-Command code -ErrorAction SilentlyContinue)) {
    Log "Installing Visual Studio Code..."
    choco install vscode -y --no-progress
    Log "Visual Studio Code installed."
} else {
    Log "Visual Studio Code already present."
}

# 6. Install Git Bash (required for Claude CLI)
if (-not (Test-Path "C:\Program Files\Git\bin\bash.exe")) {
    Log "Installing Git Bash (required for Claude CLI)..."
    choco install git -y --no-progress
    Log "Git Bash installed."
} else {
    Log "Git Bash already present."
}

# 7. Set Claude CLI environment variables
Log "Setting Claude environment variables..."
[Environment]::SetEnvironmentVariable("CLAUDE_CODE_USE_BEDROCK", "1", "Machine")
[Environment]::SetEnvironmentVariable("DISABLE_PROMPT_CACHING", "1", "Machine")
[Environment]::SetEnvironmentVariable("AWS_REGION", "us-east-1", "Machine")
[Environment]::SetEnvironmentVariable("ANTHROPIC_MODEL", "us.anthropic.claude-sonnet-4-5-20250929-v1:0", "Machine")
[Environment]::SetEnvironmentVariable("CLAUDE_CODE_GIT_BASH_PATH", "C:\Program Files\Git\bin\bash.exe", "Machine")
Log "Environment variables configured."

# 8. Install Claude CLI (system-safe method)
$npmCmd = "C:\Program Files\nodejs\npm.cmd"
$claudeCmd = "C:\Program Files\nodejs\claude.cmd"

if (-not (Test-Path $claudeCmd)) {
    Log "Installing Claude CLI via npm.cmd (system-safe method)..."
    try {
        # Run npm.cmd explicitly inside cmd.exe (works in SYSTEM)
        Start-Process "cmd.exe" -ArgumentList "/c `"$npmCmd install -g @anthropic-ai/claude-code@latest --no-fund --no-audit --silent --loglevel=error`"" -Wait -NoNewWindow

        if (Test-Path $claudeCmd) {
            Log "Claude CLI installed successfully."
        } else {
            Log "WARNING: Claude CLI installation completed but claude.cmd not found. Retrying once..."
            Start-Process "cmd.exe" -ArgumentList "/c `"$npmCmd install -g @anthropic-ai/claude-code@latest --force --no-fund --no-audit`"" -Wait -NoNewWindow
        }
    } catch {
        Log "ERROR installing Claude CLI: $_"
    }
} else {
    Log "Claude CLI already present."
}

# 9. Post-install validation
try {
    $nodeV = node -v
    $codeV = code --version
    $claudeV = claude --version
    Log "Post-install check: Node $nodeV | VSCode $codeV | Claude $claudeV"
} catch {
    Log "Post-install validation warning: $_"
}

Log ""
Log "✅ Installation completed successfully. A reboot is recommended."
exit 0
