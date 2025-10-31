@echo off
REM Install Canary MCP Server Configuration for Claude Desktop

echo ========================================
echo Canary MCP Server - Claude Desktop Setup
echo ========================================
echo.

set SOURCE=C:\Github\BD\BD-hackaton-2025-10\claude_desktop_config.json
set DEST=%APPDATA%\Claude\claude_desktop_config.json

echo Source: %SOURCE%
echo Destination: %DEST%
echo.

REM Create Claude directory if it doesn't exist
if not exist "%APPDATA%\Claude" (
    echo Creating Claude config directory...
    mkdir "%APPDATA%\Claude"
    echo Done!
)

REM Backup existing config if it exists
if exist "%DEST%" (
    echo Backing up existing config...
    copy "%DEST%" "%DEST%.backup"
    echo Done!
)

REM Copy the config file
echo Copying configuration file...
copy /Y "%SOURCE%" "%DEST%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Installation Complete!
    echo ========================================
    echo.
    echo Next steps:
    echo 1. Close Claude Desktop completely (if running^)
    echo 2. Restart Claude Desktop
    echo 3. Look for the 'canary-historian' MCP server
    echo 4. Test with: "Can you ping the Canary MCP server?"
    echo.
    echo Config file installed at:
    echo %DEST%
    echo.
) else (
    echo.
    echo ERROR: Failed to copy config file!
    echo.
)

pause
