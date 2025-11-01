@echo off
REM Canary MCP Server - Simple Installer Wrapper
REM Version: 1.0
REM This batch file makes it easy for users to run the PowerShell deployment script

setlocal enabledelayedexpansion

REM =============================================================================
REM CONFIGURATION
REM =============================================================================

set SCRIPT_NAME=deploy_canary_mcp.ps1
set SCRIPT_DIR=%~dp0
set LOG_FILE=%TEMP%\canary-mcp-install.log

REM =============================================================================
REM BANNER
REM =============================================================================

cls
echo.
echo ========================================================
echo.
echo    Canary MCP Server - Automated Installer
echo.
echo    This will install the Canary MCP Server
echo    on your computer and configure Claude Desktop
echo.
echo ========================================================
echo.

REM =============================================================================
REM CHECK PREREQUISITES
REM =============================================================================

echo [1/5] Checking prerequisites...

REM Check Windows version
for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
if "%version%" == "10.0" (
    echo   [OK] Windows 10/11 detected
) else (
    echo   [ERROR] Windows 10/11 required
    pause
    exit /b 1
)

REM Check if PowerShell is available
powershell -Command "exit 0" >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] PowerShell not found
    echo   Please ensure PowerShell is installed
    pause
    exit /b 1
)
echo   [OK] PowerShell available

REM Check if script exists
if not exist "%SCRIPT_DIR%%SCRIPT_NAME%" (
    echo   [ERROR] Deployment script not found
    echo   Expected: %SCRIPT_DIR%%SCRIPT_NAME%
    pause
    exit /b 1
)
echo   [OK] Deployment script found

echo.

REM =============================================================================
REM GATHER CREDENTIALS
REM =============================================================================

echo [2/5] Gathering configuration...
echo.

REM Ask for credentials
set /p CANARY_SAF_URL="Enter Canary SAF URL [https://scunscanary.secil.pt/api/v1]: "
if "%CANARY_SAF_URL%"=="" set CANARY_SAF_URL=https://scunscanary.secil.pt/api/v1

set /p CANARY_VIEWS_URL="Enter Canary Views URL [https://scunscanary.secil.pt]: "
if "%CANARY_VIEWS_URL%"=="" set CANARY_VIEWS_URL=https://scunscanary.secil.pt

echo.
echo [!] API Token will be requested by the PowerShell script
echo     (Input will be hidden for security)
echo.

REM =============================================================================
REM CONFIRM INSTALLATION
REM =============================================================================

echo [3/5] Ready to install...
echo.
echo Configuration:
echo   - SAF URL: %CANARY_SAF_URL%
echo   - Views URL: %CANARY_VIEWS_URL%
echo   - Install Location: %USERPROFILE%\Documents\Canary-MCP
echo.

choice /C YN /M "Proceed with installation"
if errorlevel 2 (
    echo.
    echo Installation cancelled by user
    pause
    exit /b 0
)

REM =============================================================================
REM RUN POWERSHELL SCRIPT
REM =============================================================================

echo.
echo [4/5] Running installation script...
echo.
echo This may take 10-15 minutes. Please wait...
echo.

REM Check execution policy
powershell -Command "Get-ExecutionPolicy" | findstr /i "Restricted" >nul
if not errorlevel 1 (
    echo [!] PowerShell execution policy is Restricted
    echo [!] Attempting to run with bypass policy...
    echo.

    REM Run with bypass
    powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%%SCRIPT_NAME%" -CanarySafUrl "%CANARY_SAF_URL%" -CanaryViewsUrl "%CANARY_VIEWS_URL%" 2>&1 | tee "%LOG_FILE%"
    set INSTALL_EXIT=%ERRORLEVEL%
) else (
    REM Run normally
    powershell -File "%SCRIPT_DIR%%SCRIPT_NAME%" -CanarySafUrl "%CANARY_SAF_URL%" -CanaryViewsUrl "%CANARY_VIEWS_URL%" 2>&1 | tee "%LOG_FILE%"
    set INSTALL_EXIT=%ERRORLEVEL%
)

echo.

REM =============================================================================
REM CHECK RESULT
REM =============================================================================

if %INSTALL_EXIT% == 0 (
    echo [5/5] Installation completed successfully!
    echo.
    echo ========================================================
    echo    Installation Complete - Next Steps
    echo ========================================================
    echo.
    echo 1. RESTART CLAUDE DESKTOP
    echo    - Close Claude Desktop completely
    echo    - Reopen it from Start Menu
    echo.
    echo 2. VERIFY CONNECTION
    echo    - Look for "MCP Servers: 1 Connected"
    echo    - Try: "What MCP tools are available?"
    echo.
    echo 3. FIRST QUERY
    echo    - Try: "Ping the Canary server"
    echo.
    echo 4. DOCUMENTATION
    echo    - Location: %USERPROFILE%\Documents\Canary-MCP\docs\
    echo    - Examples: USER_ONBOARDING_GUIDE.md
    echo.
    echo ========================================================
    echo.
    echo Press any key to open documentation folder...
    pause >nul
    explorer "%USERPROFILE%\Documents\Canary-MCP\docs"
) else (
    echo [5/5] Installation failed!
    echo.
    echo ========================================================
    echo    Installation Failed
    echo ========================================================
    echo.
    echo The installation encountered an error.
    echo.
    echo Log file: %LOG_FILE%
    echo.
    echo Common issues:
    echo   - Network connection required
    echo   - Antivirus may block downloads
    echo   - Insufficient disk space
    echo.
    echo For help:
    echo   1. Check the log file above
    echo   2. Contact IT helpdesk
    echo   3. See troubleshooting guide
    echo.
    echo ========================================================
    echo.
    pause
)

endlocal
exit /b %INSTALL_EXIT%
