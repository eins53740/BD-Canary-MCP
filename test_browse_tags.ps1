$apiToken = "0120fd2e-e9c2-4c8d-8115-a6ceb41490ce"
$endpoint = "https://scunscanary.secil.pt:55236/api/v2/browseTags"

Write-Host ""
Write-Host "Testing browseTags with direct apiToken..." -ForegroundColor Cyan
Write-Host ""

try {
    $body = @{
        "apiToken" = $apiToken
        "path" = ""
        "deep" = $true
        "search" = ""
    } | ConvertTo-Json

    $response = Invoke-WebRequest -Uri $endpoint -Method POST -Body $body -ContentType "application/json" -TimeoutSec 10 -ErrorAction Stop

    Write-Host "SUCCESS! HTTP $($response.StatusCode)" -ForegroundColor Green

    $jsonResponse = $response.Content | ConvertFrom-Json

    if ($jsonResponse.statusCode) {
        Write-Host "Status: $($jsonResponse.statusCode)" -ForegroundColor Green
    }

    if ($jsonResponse.tags) {
        $tagCount = ($jsonResponse.tags | Measure-Object).Count
        Write-Host "Found $tagCount tags" -ForegroundColor Green

        if ($tagCount -gt 0) {
            Write-Host ""
            Write-Host "First few tags:" -ForegroundColor Yellow
            $jsonResponse.tags | Select-Object -First 5 | ForEach-Object {
                Write-Host "  - $($_.name)" -ForegroundColor White
            }
        }
    }

    Write-Host ""
    Write-Host "=== AUTHENTICATION METHOD CONFIRMED ===" -ForegroundColor Green -BackgroundColor Black
    Write-Host "Your Canary uses Read API v2 with direct apiToken" -ForegroundColor White
    Write-Host "No session token exchange needed!" -ForegroundColor White
    Write-Host ""

} catch {
    Write-Host "FAILED!" -ForegroundColor Red
    if ($_.Exception.Response) {
        $statusCode = [int]$_.Exception.Response.StatusCode
        Write-Host "HTTP Status: $statusCode" -ForegroundColor Red
    }
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
