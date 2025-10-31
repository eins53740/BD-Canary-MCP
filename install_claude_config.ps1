# Install Canary MCP Server Configuration for Claude Desktop
# Run this script to automatically copy the MCP config to Claude Desktop

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Canary MCP Server - Claude Desktop Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Define paths
$sourceConfig = "C:\Github\BD\BD-hackaton-2025-10\claude_desktop_config.json"
$claudeConfigDir = "$env:APPDATA\Claude"
$destConfig = "$claudeConfigDir\claude_desktop_config.json"

Write-Host "Source config: $sourceConfig" -ForegroundColor Yellow
Write-Host "Destination:   $destConfig" -ForegroundColor Yellow
Write-Host ""

# Check if source file exists
if (-not (Test-Path $sourceConfig)) {
    Write-Host "ERROR: Source config file not found!" -ForegroundColor Red
    Write-Host "Expected at: $sourceConfig" -ForegroundColor Red
    exit 1
}

# Create Claude directory if it doesn't exist
if (-not (Test-Path $claudeConfigDir)) {
    Write-Host "Creating Claude config directory..." -ForegroundColor Yellow
    New-Item -Path $claudeConfigDir -ItemType Directory -Force | Out-Null
    Write-Host "✓ Directory created" -ForegroundColor Green
}

# Backup existing config if it exists
if (Test-Path $destConfig) {
    $backupPath = "$destConfig.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Write-Host "Backing up existing config to: $backupPath" -ForegroundColor Yellow
    Copy-Item $destConfig $backupPath
    Write-Host "✓ Backup created" -ForegroundColor Green
}

# Copy the config file
try {
    Copy-Item $sourceConfig $destConfig -Force
    Write-Host "✓ Configuration file copied successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Installation Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Close Claude Desktop completely (if running)" -ForegroundColor White
    Write-Host "2. Restart Claude Desktop" -ForegroundColor White
    Write-Host "3. Look for the 'canary-historian' MCP server indicator" -ForegroundColor White
    Write-Host "4. Test with: 'Can you ping the Canary MCP server?'" -ForegroundColor White
    Write-Host ""
    Write-Host "Configuration file location:" -ForegroundColor Yellow
    Write-Host $destConfig -ForegroundColor White
    Write-Host ""
}
catch {
    Write-Host "ERROR: Failed to copy config file" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
