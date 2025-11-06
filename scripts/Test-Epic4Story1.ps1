param(
    [string]$RepositoryRoot = (Resolve-Path "$PSScriptRoot\..")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location $RepositoryRoot

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python3 -ErrorAction SilentlyContinue
}

if (-not $python) {
    Write-Error "Python executable not found. Install Python 3.11+ and ensure it is on PATH."
    exit 1
}

$testFilter = 'test_http_method_enforcement or test_response_size_guard'

Write-Host "Running unit guardrail checks with $($python.Path)..."
& $python.Path -m pytest -m unit -k $testFilter -q -s
