# Quick Setup Guide

## Step 1: Configure Your Canary Server Connection

Edit the `.mcp.json` file in the root directory and update the Canary server configuration:

```json
"canary": {
  "env": {
    "CANARY_BASE_URL": "https://YOUR-SERVER:PORT/api/v2",
    "CANARY_API_TOKEN": "YOUR-API-TOKEN",
    "CANARY_TIMEZONE": "Europe/Lisbon"
  }
}
```

Replace:
- `YOUR-SERVER:PORT` with your actual Canary server address (e.g., `canary.secil.com:55235`)
- `YOUR-API-TOKEN` with your Canary API token
- Adjust timezone if needed

## Step 2: Test the Connection

The MCP server is already built and ready to use. To test it, restart your Claude Code application and the Canary MCP server will be available.

## Step 3: Try Example Queries

Once connected, try these example queries:

```
"List all virtual views available in Canary"
```

```
"Show me all tags under the root path"
```

```
"Get temperature data for tag 'Plant.Kiln.Temperature' from yesterday"
```

```
"Show me all available aggregation functions"
```

## Troubleshooting

If you encounter connection issues:

1. Verify the Canary server URL is accessible
2. Check that the API token is valid
3. Ensure the server uses HTTPS (or configure for HTTP)
4. Check firewall settings if applicable

## Development

To rebuild after making changes:

```bash
cd canary-mcp-server
npm run build
```

To run in development mode with auto-reload:

```bash
npm run dev
```

For more details, see `README.md`.
