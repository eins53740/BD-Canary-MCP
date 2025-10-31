@echo off
REM Test Canary API Endpoints - Batch wrapper for PowerShell script

echo.
echo ========================================
echo Canary API Endpoint Tester
echo ========================================
echo.
echo This will test various endpoint configurations to find the correct one.
echo.
pause

powershell.exe -ExecutionPolicy Bypass -File "%~dp0test_canary_endpoints.ps1"

echo.
echo.
echo Testing complete! Press any key to close...
pause >nul
