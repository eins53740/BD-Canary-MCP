<#
Install-HackathonTools.ps1
Secil Hackathon Setup - Clean ASCII version (v5, stable)
#>

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Log($msg) { Write-Host $msg }

Log "=== Installation of Hackathon Tools (Node.js, VS Code, Claude CLI) ==="

# 1. Ensure Administrator privileges
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Log "This script must be executed as Administrator."
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
    Start-Sleep -Seconds 10
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

# Set global variable for Claude Bash path
if (Test-Path "C:\Program Files\Git\bin\bash.exe") {
    [Environment]::SetEnvironmentVariable("CLAUDE_CODE_GIT_BASH_PATH", "C:\Program Files\Git\bin\bash.exe", [EnvironmentVariableTarget]::Machine)
    Log "CLAUDE_CODE_GIT_BASH_PATH set globally."
}

# 7. Validate Node/npm availability
Log "Checking Node.js and npm availability..."
Start-Sleep -Seconds 10
$nodeOk = (Get-Command node -ErrorAction SilentlyContinue)
$npmOk  = (Get-Command npm -ErrorAction SilentlyContinue)

if (-not $npmOk) {
    Log "npm not detected yet, refreshing PATH..."
    $nodeDir = "C:\Program Files\nodejs"
    if (Test-Path $nodeDir) {
        $env:Path += ";$nodeDir"
    }
    Start-Sleep -Seconds 5
}

try {
    $nodeVersion = node -v
    $npmVersion = npm -v
    Log "Node.js version: $nodeVersion | npm version: $npmVersion"
} catch {
    Log "Warning: Could not retrieve Node/npm versions yet."
    Start-Sleep -Seconds 10
}

# 8. Install Claude CLI globally (stable version)
$npmPrefix = "C:\Program Files\nodejs"
Log "Preparing folders for Claude CLI..."

# Ensure npm global folder exists and is writable
if (-not (Test-Path "$npmPrefix\node_modules")) {
    New-Item -ItemType Directory -Force -Path "$npmPrefix\node_modules" | Out-Null
}
if (-not (Test-Path "$npmPrefix\bin")) {
    New-Item -ItemType Directory -Force -Path "$npmPrefix\bin" | Out-Null
}

Start-Sleep -Seconds 15
Log "Installing Claude Code CLI (global)..."

try {
    Start-Process "npm" -ArgumentList "install -g @anthropic-ai/claude-code --prefix `"$npmPrefix`" --no-audit --no-fund --silent" -Wait -NoNewWindow
} catch {
    Log "First installation attempt failed, retrying..."
    Start-Process "npm" -ArgumentList "install -g @anthropic-ai/claude-code --prefix `"$npmPrefix`" --force --no-audit --no-fund" -Wait -NoNewWindow
}

# Validate Claude CLI installation
$claudeCmd = Join-Path $npmPrefix "claude.cmd"
if (Test-Path $claudeCmd) {
    Log "Claude CLI installed successfully at $npmPrefix"
} else {
    Log "Claude CLI not found after installation, retrying..."
    Start-Process "npm" -ArgumentList "install -g @anthropic-ai/claude-code --prefix `"$npmPrefix`" --force --no-audit --no-fund" -Wait -NoNewWindow
    if (-not (Test-Path $claudeCmd)) {
        Log "Final retry failed. Intune will reattempt installation."
        exit 1
    }
}

# 9. Update PATH globally
$machinePath = [Environment]::GetEnvironmentVariable("Path","Machine")
if ($machinePath -notlike "*$npmPrefix*") {
    [Environment]::SetEnvironmentVariable("Path", "$machinePath;$npmPrefix", [EnvironmentVariableTarget]::Machine)
    Log "PATH updated with $npmPrefix"
} else {
    Log "PATH already includes $npmPrefix"
}

# 10. Set environment variables (Machine scope)
Log "Setting global environment variables..."
$envVars = @{
    "CLAUDE_CODE_USE_BEDROCK" = "1"
    "DISABLE_PROMPT_CACHING"  = "1"
    "AWS_REGION"              = "us-east-1"
    "ANTHROPIC_MODEL"         = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
}

foreach ($key in $envVars.Keys) {
    [Environment]::SetEnvironmentVariable($key, $envVars[$key], [EnvironmentVariableTarget]::Machine)
    Log "$key = $($envVars[$key])"
}

# 11. Post-installation check
Log ""
Log "=== Post-installation check ==="
try {
    $nodeV = node -v
    $codeV = code --version
    $claudeV = claude --version
    Log "Node.js version: $nodeV"
    Log "VS Code version: $codeV"
    Log "Claude CLI version: $claudeV"
} catch {
    Log "Warning: Could not verify all versions (may require new PowerShell session)."
}

Log ""
Log "Installation completed successfully."
Log "If this is your first time using Claude CLI, run 'claude setup' to configure your API key."
