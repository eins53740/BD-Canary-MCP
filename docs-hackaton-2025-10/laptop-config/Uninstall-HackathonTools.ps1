<#
Secil Hackathon Tools - Uninstaller v5.1 (Final)
Removes Node.js, VS Code, Git, Claude CLI, and environment variables.
Compatible with Intune or manual execution.
#>

$ErrorActionPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Log($msg) { Write-Host $msg }

Log "=== Starting Hackathon Tools Uninstallation ==="

# 1. Ensure Administrator privileges
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Log "ERROR: This script must be executed as Administrator."
    exit 1
}

# 2. Define paths and logs
$logDir = "C:\ProgramData\SecilHackathon"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }
$logFile = Join-Path $logDir "Uninstall.log"

function WriteLog($msg) {
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Add-Content -Path $logFile -Value "[$ts] $msg"
    Write-Host $msg
}

WriteLog "Uninstall process started."

# 3. Uninstall Claude CLI
WriteLog "Checking for Claude CLI..."
$claudeCmd = "C:\Program Files\nodejs\claude.cmd"
if (Test-Path $claudeCmd) {
    WriteLog "Removing Claude CLI..."
    try {
        Start-Process "npm" -ArgumentList "uninstall -g @anthropic-ai/claude-code --force --no-audit --silent" -Wait -NoNewWindow
        Remove-Item $claudeCmd -Force -ErrorAction SilentlyContinue
        Remove-Item "C:\Program Files\nodejs\claude.ps1" -Force -ErrorAction SilentlyContinue
        WriteLog "Claude CLI removed."
    } catch {
        WriteLog "WARNING: Error while removing Claude CLI: $_"
    }
} else {
    WriteLog "Claude CLI not found."
}

# 4. Uninstall Node.js (if installed via Chocolatey)
if (Get-Command node -ErrorAction SilentlyContinue) {
    WriteLog "Uninstalling Node.js..."
    choco uninstall nodejs-lts -y --no-progress
    WriteLog "Node.js removed."
} else {
    WriteLog "Node.js not found."
}

# 5. Uninstall Visual Studio Code
if (Get-Command code -ErrorAction SilentlyContinue) {
    WriteLog "Uninstalling Visual Studio Code..."
    choco uninstall vscode -y --no-progress
    WriteLog "Visual Studio Code removed."
} else {
    WriteLog "Visual Studio Code not found."
}

# 6. Uninstall Git
if (Test-Path "C:\Program Files\Git\bin\bash.exe") {
    WriteLog "Uninstalling Git..."
    choco uninstall git -y --no-progress
    WriteLog "Git removed."
} else {
    WriteLog "Git not found."
}

# 7. Remove environment variables
WriteLog "Removing global environment variables..."
$envVars = @(
    "CLAUDE_CODE_USE_BEDROCK",
    "DISABLE_PROMPT_CACHING",
    "AWS_REGION",
    "ANTHROPIC_MODEL",
    "CLAUDE_CODE_GIT_BASH_PATH"
)

foreach ($v in $envVars) {
    try {
        [Environment]::SetEnvironmentVariable($v, $null, [EnvironmentVariableTarget]::Machine)
        WriteLog "Removed variable $v"
    } catch {
        WriteLog "WARNING: Failed to remove variable $v"
    }
}

# 8. Clean old logs and folders
WriteLog "Cleaning old installation files..."
$oldFiles = @("$logDir\Install.log", "$logDir\npm_install.log")
foreach ($f in $oldFiles) {
    if (Test-Path $f) {
        Remove-Item $f -Force -ErrorAction SilentlyContinue
        WriteLog "Deleted $f"
    }
}

# 9. Optional cleanup of residual folders
$pathsToClean = @(
    "C:\ProgramData\SecilHackathon",
    "C:\Program Files\nodejs\node_modules\@anthropic-ai"
)
foreach ($path in $pathsToClean) {
    if (Test-Path $path) {
        try {
            Remove-Item -Recurse -Force -Path $path -ErrorAction SilentlyContinue
            WriteLog "Cleaned $path"
        } catch {
            WriteLog "WARNING: Could not remove $path"
        }
    }
}

# 10. Summary
WriteLog "✅ Uninstallation completed successfully."
WriteLog "A system reboot is recommended to finalize environment cleanup."

exit 0
