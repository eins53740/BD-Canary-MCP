$server = "https://scunscanary.secil.pt"
$apiToken = "0120fd2e-e9c2-4c8d-8115-a6ceb41490ce"

Write-Host ""
Write-Host "=== Testing Canary API Endpoints ===" -ForegroundColor Cyan
Write-Host ""

$tests = @(
    @{ name = "Read API v2 - /api/v2"; url = "$server/api/v2/browseNodes"; token = "apiToken" },
    @{ name = "SAF API v1 - /api/v1"; url = "$server/api/v1/getSessionToken"; token = "userToken" },
    @{ name = "Read API v2 - /readapi/v2"; url = "$server/readapi/v2/browseNodes"; token = "apiToken" }
)

foreach ($test in $tests) {
    Write-Host "Testing: $($test.name)" -ForegroundColor Yellow
    Write-Host "  URL: $($test.url)" -ForegroundColor Gray

    try {
        $body = @{}
        $body[$test.token] = $apiToken
        $jsonBody = $body | ConvertTo-Json

        $response = Invoke-WebRequest -Uri $test.url -Method POST -Body $jsonBody -ContentType "application/json" -TimeoutSec 10 -ErrorAction Stop

        Write-Host "  SUCCESS (HTTP $($response.StatusCode))" -ForegroundColor Green
        $jsonResponse = $response.Content | ConvertFrom-Json

        if ($jsonResponse.statusCode) {
            Write-Host "  Status: $($jsonResponse.statusCode)" -ForegroundColor Green
        }
        if ($jsonResponse.sessionToken) {
            Write-Host "  Session Token received!" -ForegroundColor Green
        }

        Write-Host ""
        Write-Host "  WORKING ENDPOINT FOUND!" -ForegroundColor Green -BackgroundColor Black
        $baseUrl = $test.url -replace '/[^/]+$', ''
        Write-Host "  Base URL: $baseUrl" -ForegroundColor White
        Write-Host ""
        break

    } catch {
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode
            Write-Host "  FAILED (HTTP $statusCode)" -ForegroundColor Red
        } else {
            Write-Host "  FAILED: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    Write-Host ""
}

Write-Host "=== Testing Complete ===" -ForegroundColor Cyan
Write-Host ""
