# Canary API Endpoint Diagnosis

## Problem Summary
The MCP server is failing to authenticate because we're trying to use the wrong API authentication method for your Canary server.

## Two Different Canary APIs

### 1. Canary Web **Read API** (v2)
- **Authentication**: Direct API token in every request (`apiToken`)
- **No session token exchange** - just use the API token directly
- **Endpoints**: `/api/v2/browseTags`, `/api/v2/getTagData`, etc.
- **Documented**: https://readapi.canarylabs.com/25.4/
- **Evidence**: Your Postman collection uses this method exclusively

### 2. Canary **SAF (Store and Forward) API** (v1)
- **Authentication**: Two-step session token exchange
  1. POST `/api/v1/getSessionToken` with `userToken`
  2. Get back `sessionToken`
  3. Use `sessionToken` in subsequent requests
- **Endpoints**: `/api/v1/storeData`, `/api/v1/getSessionToken`
- **Purpose**: Primarily for writing data to Canary

## Our Current Implementation
Our MCP server (auth.py) is implemented for **SAF API**, but your server likely uses the **Read API**.

## Diagnostic Tests

### Test 1: Check which API your server supports

Try these URLs in your browser or Postman:

#### Option A: Read API v2 (most likely)
```
POST https://scunscanary.secil.pt/api/v2/browseNodes
Body: {"apiToken": "your-api-token-here"}
```

#### Option B: SAF API v1 (what we're currently trying)
```
POST https://scunscanary.secil.pt/api/v1/getSessionToken
Body: {"userToken": "your-api-token-here"}
```

### Test 2: Try different base paths

Your server might use a different path structure. Test these:

1. `https://scunscanary.secil.pt/api/v2/browseNodes`
2. `https://scunscanary.secil.pt/readapi/v2/browseNodes`
3. `https://scunscanary.secil.pt/api/v1/browseNodes`
4. `https://scunscanary.secil.pt/v2/browseNodes` (no /api prefix)

## How to Test

### Using PowerShell:
```powershell
# Test Read API v2
$headers = @{"Content-Type" = "application/json"}
$body = @{"apiToken" = "your-api-token-here"} | ConvertTo-Json
Invoke-WebRequest -Uri "https://scunscanary.secil.pt/api/v2/browseNodes" `
    -Method POST `
    -Headers $headers `
    -Body $body
```

### Using curl (if installed):
```bash
curl -X POST "https://scunscanary.secil.pt/api/v2/browseNodes" \
  -H "Content-Type: application/json" \
  -d '{"apiToken": "your-api-token-here"}'
```

## Expected Results

### Success (200 OK):
You'll see JSON response with `"statusCode": "Good"` and data about nodes/tags.
**This tells us the correct endpoint!**

### 404 Not Found:
The endpoint path is wrong. Try the other options above.

### 401 Unauthorized:
The API token is invalid or the authentication method is wrong.

## Next Steps

### If Read API v2 works:
We need to modify auth.py to support direct API token authentication instead of session token exchange. This is a straightforward change.

### If SAF API v1 works:
We just need to update the `CANARY_SAF_BASE_URL` in your .env file to the correct path.

### If neither works:
Check with your Canary administrator to confirm:
- Which API version is deployed
- What the base URL should be
- Whether the API token has the correct permissions

## Quick Reference

Your current configuration:
- Server: `https://scunscanary.secil.pt`
- API Token: `<your-token-here>`
- Current base URL: `https://scunscanary.secil.pt/readapi/v1` (returns 404)

Most likely correct configurations:
1. **Read API v2**: `https://scunscanary.secil.pt/api/v2`
2. **SAF API v1**: `https://scunscanary.secil.pt/api/v1`
