<#
Install-HackathonTools.ps1
Secil Hackathon Setup - Clean version (no special characters, fully Intune-safe)
#>

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Log($msg) { Write-Host $msg }

Log "=== Installation of Hackathon Tools (Node.js, VS Code, Claude CLI) ==="

# Check for admin rights
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Log "This script must be executed as Administrator."
    exit 1
}

# Install Chocolatey
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

# Install Node.js
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Log "Installing Node.js (LTS)..."
    choco install nodejs-lts -y --no-progress
    Start-Sleep -Seconds 10
    Log "Node.js installed."
} else {
    Log ("Node.js already present: " + (node --version))
}

# Install VS Code
if (-not (Get-Command code -ErrorAction SilentlyContinue)) {
    Log "Installing Visual Studio Code..."
    choco install vscode -y --no-progress
    Log "Visual Studio Code installed."
} else {
    Log "Visual Studio Code already present."
}

# Install Claude CLI globally
Log "Installing Claude Code CLI (global)..."
$npmPrefix = "C:\Program Files\nodejs"
try {
    npm config set prefix "$npmPrefix" --global | Out-Null
    npm install -g @anthropic-ai/claude-code --prefix "$npmPrefix" --no-audit --no-fund --silent | Out-Null
} catch {
    Log "First installation attempt failed. Trying again..."
    npm install -g @anthropic-ai/claude-code --prefix "$npmPrefix" --force --no-audit --no-fund | Out-Null
}

# Validate Claude CLI
$claudeCmd = Join-Path $npmPrefix "claude.cmd"
if (Test-Path $claudeCmd) {
    Log "Claude CLI installed at $npmPrefix"
} else {
    Log "Claude CLI not found after installation."
}

# Update PATH if necessary
$machinePath = [Environment]::GetEnvironmentVariable("Path","Machine")
if ($machinePath -notlike "*$npmPrefix*") {
    [Environment]::SetEnvironmentVariable("Path", "$machinePath;$npmPrefix", [EnvironmentVariableTarget]::Machine)
    Log "PATH updated with $npmPrefix"
} else {
    Log "PATH already contains $npmPrefix"
}

# Configure environment variables
Log "Setting environment variables..."
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

# Final verification
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
    Log "Warning: Could not verify all versions. Try reopening PowerShell."
}

Log ""
Log "Installation completed successfully."
Log "If this is your first time using Claude CLI, run 'claude setup' to configure your API key."
