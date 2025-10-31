$apiToken = "0120fd2e-e9c2-4c8d-8115-a6ceb41490ce"
$endpoint = "https://scunscanary.secil.pt:55236/api/v2/getTimeZones"

Write-Host ""
Write-Host "Testing correct Canary endpoint..." -ForegroundColor Cyan
Write-Host "Endpoint: $endpoint" -ForegroundColor White
Write-Host ""

try {
    $body = @{"apiToken" = $apiToken} | ConvertTo-Json

    $response = Invoke-WebRequest -Uri $endpoint -Method POST -Body $body -ContentType "application/json" -TimeoutSec 10 -ErrorAction Stop

    Write-Host "SUCCESS! HTTP $($response.StatusCode)" -ForegroundColor Green
    Write-Host ""

    $jsonResponse = $response.Content | ConvertFrom-Json

    if ($jsonResponse.statusCode) {
        Write-Host "Status Code: $($jsonResponse.statusCode)" -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "=== ENDPOINT CONFIRMED WORKING ===" -ForegroundColor Green -BackgroundColor Black
    Write-Host ""
    Write-Host "Use this configuration:" -ForegroundColor White
    Write-Host "  CANARY_SAF_BASE_URL=https://scunscanary.secil.pt:55236/api/v2" -ForegroundColor Yellow
    Write-Host "  CANARY_VIEWS_BASE_URL=https://scunscanary.secil.pt:55236" -ForegroundColor Yellow
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
