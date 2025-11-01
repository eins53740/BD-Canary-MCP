$server = "https://scunscanary.secil.pt"
$apiToken = "0120fd2e-e9c2-4c8d-8115-a6ceb41490ce"

Write-Host ""
Write-Host "=== Testing All Canary Endpoint Variations ===" -ForegroundColor Cyan
Write-Host ""

$tests = @(
    # Standard Read API paths
    @{ url = "$server/api/v2/browseNodes"; token = "apiToken" },
    @{ url = "$server/api/v1/browseNodes"; token = "apiToken" },
    @{ url = "$server/readapi/v2/browseNodes"; token = "apiToken" },
    @{ url = "$server/readapi/v1/browseNodes"; token = "apiToken" },

    # Without prefix
    @{ url = "$server/v2/browseNodes"; token = "apiToken" },
    @{ url = "$server/v1/browseNodes"; token = "apiToken" },

    # Session token endpoints
    @{ url = "$server/api/v1/getSessionToken"; token = "userToken" },
    @{ url = "$server/readapi/v1/getSessionToken"; token = "userToken" },

    # Root level
    @{ url = "$server/browseNodes"; token = "apiToken" },
    @{ url = "$server/getSessionToken"; token = "userToken" }
)

$found = $false

foreach ($test in $tests) {
    $shortUrl = $test.url -replace "https://scunscanary.secil.pt", ""
    Write-Host "Testing: $shortUrl" -ForegroundColor Gray

    try {
        $body = @{}
        $body[$test.token] = $apiToken
        $jsonBody = $body | ConvertTo-Json

        $response = Invoke-WebRequest -Uri $test.url -Method POST -Body $jsonBody -ContentType "application/json" -TimeoutSec 10 -ErrorAction Stop

        Write-Host "  SUCCESS (HTTP $($response.StatusCode))" -ForegroundColor Green
        $found = $true

        $jsonResponse = $response.Content | ConvertFrom-Json
        if ($jsonResponse.statusCode) {
            Write-Host "  Status: $($jsonResponse.statusCode)" -ForegroundColor Green
        }

        Write-Host ""
        Write-Host "=== WORKING ENDPOINT ===" -ForegroundColor Green -BackgroundColor Black
        Write-Host "Full URL: $($test.url)" -ForegroundColor White
        $baseUrl = $test.url -replace '/[^/]+$', ''
        Write-Host "Base URL: $baseUrl" -ForegroundColor White
        Write-Host ""
        break

    } catch {
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode
            Write-Host "  Failed (HTTP $statusCode)" -ForegroundColor DarkGray
        }
    }
}

if (-not $found) {
    Write-Host ""
    Write-Host "=== NO WORKING ENDPOINT FOUND ===" -ForegroundColor Red
    Write-Host ""
    Write-Host "The server may require authentication headers or use a different path structure." -ForegroundColor Yellow
    Write-Host "Please check:" -ForegroundColor Yellow
    Write-Host "  1. Verify the server URL is correct: $server" -ForegroundColor White
    Write-Host "  2. Check if the API token has the correct permissions" -ForegroundColor White
    Write-Host "  3. Consult your Canary administrator for the correct API endpoint" -ForegroundColor White
}

Write-Host ""
