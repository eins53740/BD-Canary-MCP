$server = "https://scunscanary.secil.pt"

Write-Host ""
Write-Host "Testing Canary server connection..." -ForegroundColor Cyan
Write-Host "Server: $server" -ForegroundColor White
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri $server -Method GET -TimeoutSec 10 -ErrorAction Stop
    Write-Host "SUCCESS! Server is reachable" -ForegroundColor Green
    Write-Host "HTTP Status: $($response.StatusCode)" -ForegroundColor White
    Write-Host "Content Length: $($response.Content.Length) bytes" -ForegroundColor White

    # Check if it's a web interface
    if ($response.Content -like "*<html*" -or $response.Content -like "*<HTML*") {
        Write-Host "Response type: HTML web interface detected" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "This looks like a web interface. The API might be at a different path." -ForegroundColor Yellow
    }

} catch {
    Write-Host "FAILED to connect to server" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possible issues:" -ForegroundColor Yellow
    Write-Host "  - Server is not accessible from your network" -ForegroundColor White
    Write-Host "  - Firewall blocking the connection" -ForegroundColor White
    Write-Host "  - Server URL is incorrect" -ForegroundColor White
    Write-Host "  - SSL/TLS certificate issue" -ForegroundColor White
}

Write-Host ""
