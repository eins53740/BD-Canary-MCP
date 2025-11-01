# Canary MCP Server Deployment Script
# Automated installation for Windows workstations
# Version: 1.0
# Date: 2025-11-01

<#
.SYNOPSIS
    Automated deployment script for Canary MCP Server

.DESCRIPTION
    This script automates the installation of the Canary MCP Server for Claude Desktop.
    It handles prerequisite checks, installation, configuration, and validation.

.PARAMETER InstallPath
    Installation directory (default: %USERPROFILE%\Documents\Canary-MCP)

.PARAMETER CanarySafUrl
    Canary SAF API base URL

.PARAMETER CanaryViewsUrl
    Canary Views base URL

.PARAMETER ApiToken
    Canary API token for authentication

.PARAMETER SkipValidation
    Skip post-installation validation tests

.EXAMPLE
    .\deploy_canary_mcp.ps1 -CanarySafUrl "https://scunscanary.secil.pt/api/v1" -CanaryViewsUrl "https://scunscanary.secil.pt" -ApiToken "your-token-here"

.NOTES
    Requires: Windows 10/11, PowerShell 5.1+
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$InstallPath = "$env:USERPROFILE\Documents\Canary-MCP",

    [Parameter(Mandatory=$false)]
    [string]$CanarySafUrl = "",

    [Parameter(Mandatory=$false)]
    [string]$CanaryViewsUrl = "",

    [Parameter(Mandatory=$false)]
    [string]$ApiToken = "",

    [Parameter(Mandatory=$false)]
    [switch]$SkipValidation = $false
)

# =============================================================================
# CONFIGURATION
# =============================================================================

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$RepoUrl = "https://github.com/your-org/BD-hackaton-2025-10.git"
$PythonMinVersion = [version]"3.11.0"
$RequiredDiskSpaceMB = 500

# Colors for output
$ColorSuccess = "Green"
$ColorWarning = "Yellow"
$ColorError = "Red"
$ColorInfo = "Cyan"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

function Write-Step {
    param([string]$Message)
    Write-Host "`n[$([DateTime]::Now.ToString('HH:mm:ss'))] " -NoNewline -ForegroundColor Gray
    Write-Host $Message -ForegroundColor $ColorInfo
}

function Write-Success {
    param([string]$Message)
    Write-Host "  [✓] " -NoNewline -ForegroundColor $ColorSuccess
    Write-Host $Message -ForegroundColor $ColorSuccess
}

function Write-Warning {
    param([string]$Message)
    Write-Host "  [!] " -NoNewline -ForegroundColor $ColorWarning
    Write-Host $Message -ForegroundColor $ColorWarning
}

function Write-Error {
    param([string]$Message)
    Write-Host "  [✗] " -NoNewline -ForegroundColor $ColorError
    Write-Host $Message -ForegroundColor $ColorError
}

function Test-Command {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

function Test-DiskSpace {
    param([string]$Path, [int]$RequiredMB)

    $drive = Split-Path -Qualifier $Path
    if (-not $drive) {
        $drive = $env:SystemDrive
    }

    $disk = Get-PSDrive $drive.TrimEnd(':')
    $freeSpaceGB = [math]::Round($disk.Free / 1GB, 2)
    $requiredGB = [math]::Round($RequiredMB / 1024, 2)

    return $disk.Free -gt ($RequiredMB * 1MB)
}

function Get-PythonVersion {
    try {
        $version = python --version 2>&1
        if ($version -match "Python (\d+\.\d+\.\d+)") {
            return [version]$matches[1]
        }
    } catch {
        return $null
    }
    return $null
}

# =============================================================================
# PREREQUISITE CHECKS
# =============================================================================

function Test-Prerequisites {
    Write-Step "Checking prerequisites..."

    $allPassed = $true

    # Check PowerShell version
    if ($PSVersionTable.PSVersion.Major -lt 5) {
        Write-Error "PowerShell 5.1 or higher required. Current version: $($PSVersionTable.PSVersion)"
        $allPassed = $false
    } else {
        Write-Success "PowerShell version: $($PSVersionTable.PSVersion)"
    }

    # Check disk space
    if (Test-DiskSpace -Path $InstallPath -RequiredMB $RequiredDiskSpaceMB) {
        Write-Success "Sufficient disk space available"
    } else {
        Write-Error "Insufficient disk space. Required: ${RequiredDiskSpaceMB}MB"
        $allPassed = $false
    }

    # Check Python
    $pythonVersion = Get-PythonVersion
    if ($pythonVersion -and $pythonVersion -ge $PythonMinVersion) {
        Write-Success "Python version: $pythonVersion"
    } else {
        Write-Warning "Python 3.11+ not found. Will attempt to install."
        $script:needsPython = $true
    }

    # Check Git
    if (Test-Command "git") {
        Write-Success "Git is installed"
    } else {
        Write-Error "Git is not installed. Please install Git first."
        $allPassed = $false
    }

    # Check Claude Desktop
    $claudeConfigPath = "$env:APPDATA\Claude\claude_desktop_config.json"
    if (Test-Path "$env:LOCALAPPDATA\AnthropicClaude") {
        Write-Success "Claude Desktop is installed"
    } else {
        Write-Warning "Claude Desktop not detected. Install from https://claude.ai/download"
    }

    # Check internet connectivity
    try {
        $null = Invoke-WebRequest -Uri "https://www.google.com" -UseBasicParsing -TimeoutSec 5
        Write-Success "Internet connection verified"
    } catch {
        Write-Error "No internet connection detected"
        $allPassed = $false
    }

    return $allPassed
}

# =============================================================================
# PYTHON INSTALLATION
# =============================================================================

function Install-Python {
    Write-Step "Installing Python 3.13..."

    $pythonInstaller = "$env:TEMP\python-3.13-installer.exe"
    $pythonUrl = "https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe"

    try {
        Write-Host "  Downloading Python installer..."
        Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller -UseBasicParsing

        Write-Host "  Installing Python (this may take a few minutes)..."
        Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1" -Wait

        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","User") + ";" + [System.Environment]::GetEnvironmentVariable("Path","Machine")

        # Verify installation
        $pythonVersion = Get-PythonVersion
        if ($pythonVersion) {
            Write-Success "Python $pythonVersion installed successfully"
        } else {
            throw "Python installation verification failed"
        }

        # Cleanup
        Remove-Item $pythonInstaller -Force -ErrorAction SilentlyContinue

    } catch {
        Write-Error "Failed to install Python: $_"
        throw
    }
}

# =============================================================================
# UV PACKAGE MANAGER INSTALLATION
# =============================================================================

function Install-UV {
    Write-Step "Installing uv package manager..."

    try {
        if (Test-Command "uv") {
            Write-Success "uv is already installed"
            return
        }

        # Install uv using PowerShell script
        Write-Host "  Downloading and installing uv..."
        Invoke-Expression "& { $(Invoke-WebRequest -Uri 'https://astral.sh/uv/install.ps1' -UseBasicParsing).Content }"

        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","User") + ";" + [System.Environment]::GetEnvironmentVariable("Path","Machine")

        if (Test-Command "uv") {
            Write-Success "uv installed successfully"
        } else {
            throw "uv installation verification failed"
        }

    } catch {
        Write-Error "Failed to install uv: $_"
        throw
    }
}

# =============================================================================
# REPOSITORY SETUP
# =============================================================================

function Install-Repository {
    Write-Step "Setting up Canary MCP Server repository..."

    try {
        # Check if installation directory exists
        if (Test-Path $InstallPath) {
            Write-Warning "Installation directory already exists: $InstallPath"
            $response = Read-Host "Do you want to remove it and reinstall? (y/N)"
            if ($response -eq 'y') {
                Remove-Item $InstallPath -Recurse -Force
                Write-Success "Removed existing installation"
            } else {
                Write-Host "  Using existing installation"
                return
            }
        }

        # Create parent directory if needed
        $parentPath = Split-Path $InstallPath -Parent
        if (-not (Test-Path $parentPath)) {
            New-Item -ItemType Directory -Path $parentPath -Force | Out-Null
        }

        # Clone repository
        Write-Host "  Cloning repository from $RepoUrl..."
        git clone $RepoUrl $InstallPath 2>&1 | Out-Null

        if (Test-Path "$InstallPath\src\canary_mcp\server.py") {
            Write-Success "Repository cloned successfully"
        } else {
            throw "Repository structure validation failed"
        }

        # Install dependencies
        Write-Host "  Installing Python dependencies..."
        Push-Location $InstallPath
        uv sync 2>&1 | Out-Null
        Pop-Location

        Write-Success "Dependencies installed successfully"

    } catch {
        Write-Error "Failed to setup repository: $_"
        throw
    }
}

# =============================================================================
# CONFIGURATION
# =============================================================================

function New-EnvironmentFile {
    Write-Step "Creating environment configuration..."

    $envFile = "$InstallPath\.env"

    try {
        # Prompt for credentials if not provided
        if (-not $CanarySafUrl) {
            $CanarySafUrl = Read-Host "Enter Canary SAF Base URL (e.g., https://scunscanary.secil.pt/api/v1)"
        }

        if (-not $CanaryViewsUrl) {
            $CanaryViewsUrl = Read-Host "Enter Canary Views Base URL (e.g., https://scunscanary.secil.pt)"
        }

        if (-not $ApiToken) {
            $ApiToken = Read-Host "Enter Canary API Token" -AsSecureString
            $ApiToken = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($ApiToken))
        }

        # Create .env file
        $envContent = @"
# Canary API Configuration (REQUIRED)
CANARY_SAF_BASE_URL=$CanarySafUrl
CANARY_VIEWS_BASE_URL=$CanaryViewsUrl
CANARY_API_TOKEN=$ApiToken

# Session Configuration
CANARY_SESSION_TIMEOUT_MS=120000

# Performance Settings
CANARY_POOL_SIZE=10
CANARY_TIMEOUT=30
CANARY_RETRY_ATTEMPTS=6

# Cache Configuration
CANARY_CACHE_DIR=.cache
CANARY_CACHE_METADATA_TTL=3600
CANARY_CACHE_TIMESERIES_TTL=300
CANARY_CACHE_MAX_SIZE_MB=100

# Circuit Breaker
CANARY_CIRCUIT_CONSECUTIVE_FAILURES=5
CANARY_CIRCUIT_RESET_SECONDS=60

# Logging
LOG_LEVEL=INFO
"@

        $envContent | Out-File -FilePath $envFile -Encoding UTF8 -Force
        Write-Success "Environment file created: $envFile"

    } catch {
        Write-Error "Failed to create environment file: $_"
        throw
    }
}

# =============================================================================
# CLAUDE DESKTOP CONFIGURATION
# =============================================================================

function Update-ClaudeDesktopConfig {
    Write-Step "Configuring Claude Desktop..."

    $claudeConfigDir = "$env:APPDATA\Claude"
    $claudeConfigFile = "$claudeConfigDir\claude_desktop_config.json"

    try {
        # Create Claude config directory if it doesn't exist
        if (-not (Test-Path $claudeConfigDir)) {
            New-Item -ItemType Directory -Path $claudeConfigDir -Force | Out-Null
        }

        # Load existing config or create new
        if (Test-Path $claudeConfigFile) {
            $config = Get-Content $claudeConfigFile -Raw | ConvertFrom-Json
        } else {
            $config = @{
                mcpServers = @{}
            }
        }

        # Add Canary MCP Server configuration
        $installPathEscaped = $InstallPath -replace '\\', '\\'
        $srcPathEscaped = "$InstallPath\src" -replace '\\', '\\'

        $config.mcpServers.'canary-mcp-server' = @{
            command = "uv"
            args = @(
                "--directory",
                $InstallPath,
                "run",
                "python",
                "-m",
                "canary_mcp.server"
            )
            env = @{
                PYTHONPATH = "$InstallPath\src"
            }
        }

        # Save configuration
        $config | ConvertTo-Json -Depth 10 | Out-File -FilePath $claudeConfigFile -Encoding UTF8 -Force

        Write-Success "Claude Desktop configured successfully"
        Write-Host "  Configuration file: $claudeConfigFile" -ForegroundColor Gray

    } catch {
        Write-Error "Failed to configure Claude Desktop: $_"
        throw
    }
}

# =============================================================================
# VALIDATION
# =============================================================================

function Test-Installation {
    Write-Step "Validating installation..."

    try {
        Push-Location $InstallPath

        # Run validation script
        Write-Host "  Running validation tests..."
        $validationOutput = uv run python scripts/validate_installation.py 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Success "All validation tests passed"
        } else {
            Write-Warning "Some validation tests failed:"
            Write-Host $validationOutput -ForegroundColor Yellow
        }

        Pop-Location

    } catch {
        Write-Warning "Validation tests encountered an error: $_"
    }
}

# =============================================================================
# MAIN INSTALLATION FLOW
# =============================================================================

function Start-Installation {
    Write-Host "`n" -NoNewline
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor $ColorInfo
    Write-Host "║                                                            ║" -ForegroundColor $ColorInfo
    Write-Host "║         Canary MCP Server Deployment Script v1.0           ║" -ForegroundColor $ColorInfo
    Write-Host "║                                                            ║" -ForegroundColor $ColorInfo
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor $ColorInfo
    Write-Host ""

    try {
        # Phase 1: Prerequisites
        if (-not (Test-Prerequisites)) {
            throw "Prerequisites check failed. Please resolve issues and try again."
        }

        # Phase 2: Install Python if needed
        if ($script:needsPython) {
            Install-Python
        }

        # Phase 3: Install uv
        Install-UV

        # Phase 4: Clone repository and install
        Install-Repository

        # Phase 5: Configure environment
        New-EnvironmentFile

        # Phase 6: Configure Claude Desktop
        Update-ClaudeDesktopConfig

        # Phase 7: Validate installation
        if (-not $SkipValidation) {
            Test-Installation
        }

        # Success message
        Write-Host "`n" -NoNewline
        Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor $ColorSuccess
        Write-Host "║                                                            ║" -ForegroundColor $ColorSuccess
        Write-Host "║              Installation Completed Successfully!          ║" -ForegroundColor $ColorSuccess
        Write-Host "║                                                            ║" -ForegroundColor $ColorSuccess
        Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor $ColorSuccess
        Write-Host ""

        Write-Host "Next Steps:" -ForegroundColor $ColorInfo
        Write-Host "  1. Restart Claude Desktop" -ForegroundColor White
        Write-Host "  2. Look for 'Connected' status in Claude Desktop" -ForegroundColor White
        Write-Host "  3. Try: 'What MCP tools are available?'" -ForegroundColor White
        Write-Host ""
        Write-Host "Installation Path: $InstallPath" -ForegroundColor Gray
        Write-Host "Documentation: $InstallPath\docs\" -ForegroundColor Gray
        Write-Host "Examples: $InstallPath\docs\examples.md" -ForegroundColor Gray
        Write-Host ""

    } catch {
        Write-Host "`n" -NoNewline
        Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor $ColorError
        Write-Host "║                                                            ║" -ForegroundColor $ColorError
        Write-Host "║                  Installation Failed!                      ║" -ForegroundColor $ColorError
        Write-Host "║                                                            ║" -ForegroundColor $ColorError
        Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor $ColorError
        Write-Host ""
        Write-Host "Error: $_" -ForegroundColor $ColorError
        Write-Host ""
        Write-Host "Please check the error message above and try again." -ForegroundColor Yellow
        Write-Host "For support, see: $InstallPath\DEPLOYMENT_CHECKLIST.md" -ForegroundColor Gray
        Write-Host ""
        exit 1
    }
}

# =============================================================================
# ENTRY POINT
# =============================================================================

Start-Installation
