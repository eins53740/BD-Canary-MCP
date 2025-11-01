# Test Canary API Endpoints
# This script tests various Canary API endpoint configurations to find the correct one

$server = "https://scunscanary.secil.pt"
$apiToken = "0120fd2e-e9c2-4c8d-8115-a6ceb41490ce"

$endpoints = @(
    # Read API v2 endpoints (most likely)
    @{
        url = "$server/api/v2/browseNodes"
        body = @{"apiToken" = $apiToken}
        name = "Read API v2 - /api/v2/browseNodes"
    },
    @{
        url = "$server/readapi/v2/browseNodes"
        body = @{"apiToken" = $apiToken}
        name = "Read API v2 - /readapi/v2/browseNodes"
    },

    # SAF API v1 endpoints (for session token)
    @{
        url = "$server/api/v1/getSessionToken"
        body = @{"userToken" = $apiToken}
        name = "SAF API v1 - /api/v1/getSessionToken"
    },
    @{
        url = "$server/readapi/v1/getSessionToken"
        body = @{"userToken" = $apiToken}
        name = "SAF API v1 - /readapi/v1/getSessionToken"
    },

    # Alternative paths
    @{
        url = "$server/v2/browseNodes"
        body = @{"apiToken" = $apiToken}
        name = "No prefix - /v2/browseNodes"
    },
    @{
        url = "$server/api/v1/browseNodes"
        body = @{"apiToken" = $apiToken}
        name = "Read API v1 - /api/v1/browseNodes"
    }
)

Write-Host "`n=== Testing Canary API Endpoints ===`n" -ForegroundColor Cyan

foreach ($endpoint in $endpoints) {
    Write-Host "Testing: $($endpoint.name)" -ForegroundColor Yellow
    Write-Host "  URL: $($endpoint.url)" -ForegroundColor Gray

    try {
        $headers = @{
            "Content-Type" = "application/json"
        }

        $jsonBody = $endpoint.body | ConvertTo-Json

        $response = Invoke-WebRequest `
            -Uri $endpoint.url `
            -Method POST `
            -Headers $headers `
            -Body $jsonBody `
            -TimeoutSec 10 `
            -ErrorAction Stop

        Write-Host "  Result: SUCCESS (HTTP $($response.StatusCode))" -ForegroundColor Green

        # Try to parse JSON response
        try {
            $jsonResponse = $response.Content | ConvertFrom-Json
            if ($jsonResponse.statusCode) {
                Write-Host "  Status: $($jsonResponse.statusCode)" -ForegroundColor Green
            }
            if ($jsonResponse.sessionToken) {
                Write-Host "  Session Token: $($jsonResponse.sessionToken.Substring(0, 20))..." -ForegroundColor Green
            }
        } catch {
            Write-Host "  Response: $($response.Content.Substring(0, [Math]::Min(100, $response.Content.Length)))..." -ForegroundColor Gray
        }

        Write-Host "`n  ✓ THIS ENDPOINT WORKS! Use this configuration:`n" -ForegroundColor Green -BackgroundColor Black

        # Extract base URL from working endpoint
        $baseUrl = $endpoint.url -replace '/[^/]+$', ''
        Write-Host "  CANARY_SAF_BASE_URL=$baseUrl" -ForegroundColor White -BackgroundColor DarkGreen
        Write-Host "  CANARY_VIEWS_BASE_URL=$server" -ForegroundColor White -BackgroundColor DarkGreen
        Write-Host "  CANARY_API_TOKEN=$apiToken`n" -ForegroundColor White -BackgroundColor DarkGreen

        break  # Stop testing once we find a working endpoint

    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode) {
            Write-Host "  Result: FAILED (HTTP $statusCode)" -ForegroundColor Red
        } else {
            Write-Host "  Result: FAILED ($($_.Exception.Message))" -ForegroundColor Red
        }
    }

    Write-Host ""
}

Write-Host "`n=== Testing Complete ===`n" -ForegroundColor Cyan
Write-Host "If you found a working endpoint above, update your .env file and" -ForegroundColor White
Write-Host "claude_desktop_config.json with the displayed configuration." -ForegroundColor White
Write-Host ""
