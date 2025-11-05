# Canary Historian MCP Server

A Model Context Protocol (MCP) server that connects to Canary Historian, enabling AI assistants to query and analyze industrial time-series data through natural language.

## Features

- **Natural Language Time Queries**: Use expressions like "last week", "yesterday", "now-30d"
- **Tag Discovery**: Browse and search through tag hierarchies
- **Historical Data Access**: Query raw and aggregated time-series data
- **Asset-Based Queries**: Navigate equipment hierarchies using virtual views
- **Statistical Aggregations**: Support for TimeAverage2, Maximum2, Minimum2, and more
- **Intelligent Caching**: Optimized performance with in-memory caching
- **AI-Friendly Formatting**: Data responses optimized for AI analysis

## Available Tools

The server provides 2 essential MCP tools optimized for AI interaction:

1. **browse_tags** - Search and discover tags with filtering (find available sensors and data points)
2. **get_tag_data** - Query historical time-series data (get actual sensor readings with natural language time expressions)

**Note:** Additional tools (browse_nodes, get_aggregates, get_tag_context, virtual views, asset tools) are available in the codebase but currently disabled for optimal AI performance. They can be re-enabled in `src/tools/index.ts` if needed.

## Installation

1. **Install dependencies**:
   ```bash
   cd canary-mcp-server
   npm install
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

3. **Edit .env with your Canary server details**:
   ```env
   CANARY_BASE_URL=https://your-server:55235/api/v2
   CANARY_API_TOKEN=your-api-token-here
   CANARY_TIMEZONE=Europe/Lisbon
   ```

4. **Build the project**:
   ```bash
   npm run build
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CANARY_BASE_URL` | Canary server API base URL | Required |
| `CANARY_API_TOKEN` | API token for authentication | Required |
| `CANARY_TIMEZONE` | IANA timezone for timestamps | Europe/Lisbon |
| `CANARY_CACHE_TTL` | Cache TTL in seconds | 300 |
| `CANARY_MAX_SIZE` | Max data points per request | 10000 |
| `CANARY_REQUEST_TIMEOUT` | Request timeout in ms | 30000 |
| `DEBUG` | Enable debug logging | false |

### MCP Configuration

The server is already configured in `.mcp.json`. Update the environment variables there with your actual Canary server details:

```json
{
  "mcpServers": {
    "canary": {
      "command": "node",
      "args": ["dist/index.js"],
      "cwd": "path/to/canary-mcp-server",
      "env": {
        "CANARY_BASE_URL": "https://your-server:port/api/v2",
        "CANARY_API_TOKEN": "your-token",
        "CANARY_TIMEZONE": "Europe/Lisbon"
      }
    }
  }
}
```

## Example Natural Language Queries

Once connected, you can use natural language to query your industrial data:

### Basic Data Queries

```
"Show me temperature data for tag 'Kiln.Kiln3.Temperature' from yesterday"
```

```
"Get the last week of pressure readings for 'Plant.Reactor1.Pressure'"
```

```
"What were the values for 'Motor.Speed' between now-24h and now?"
```

### Aggregated Queries

```
"Give me hourly averages for 'Kiln.Temperature' over the last 7 days"
```

```
"Show me the maximum values per day for 'Pump.Pressure' this month"
```

```
"Get 30-minute average temperature readings for the last 48 hours"
```

### Tag Discovery

```
"Find all tags under the 'Kiln' node"
```

```
"Search for tags containing 'temperature' in their name"
```

```
"List all available sensors in the cement plant"
```

### Asset-Based Queries

```
"What virtual views are available?"
```

```
"Show me all asset types in the 'Production' view"
```

```
"Find all instances of 'Kiln' assets"
```

```
"Get all tags associated with 'Motor' asset types"
```

## Time Expression Reference

The server supports natural language time expressions:

| Expression | Meaning |
|-----------|---------|
| `now` | Current timestamp |
| `yesterday` | Previous day at midnight |
| `last week` | 7 days ago |
| `last month` | 30 days ago |
| `now-30d` | 30 days ago from now |
| `now-7d` | 7 days ago from now |
| `now-24h` | 24 hours ago from now |
| `now-30m` | 30 minutes ago from now |

### Interval Expressions

For aggregation intervals:

| Expression | Meaning |
|-----------|---------|
| `1h` | 1 hour |
| `30m` | 30 minutes |
| `1d` | 1 day |
| `15s` | 15 seconds |

## API Reference

### browse_nodes

Navigate the tag hierarchy one level at a time.

**Parameters:**
- `path` (optional): Path to browse (default: root)

**Example:**
```json
{
  "path": "Plant.Kiln"
}
```

### browse_tags

Search and discover tags with optional filtering.

**Parameters:**
- `path` (optional): Starting path
- `deep` (optional): Search all child nodes
- `search` (optional): Filter tags by name pattern
- `maxSize` (optional): Max number of results

**Example:**
```json
{
  "path": "Plant",
  "deep": true,
  "search": "temperature"
}
```

### get_tag_data

Query historical time-series data for tags.

**Parameters:**
- `tags`: Array of tag names
- `startTime` (optional): Start time expression
- `endTime` (optional): End time expression
- `aggregateName` (optional): Aggregate function name
- `aggregateInterval` (optional): Interval for aggregation
- `includeQuality` (optional): Include quality codes
- `maxSize` (optional): Max data points per tag

**Example:**
```json
{
  "tags": ["Kiln.Temperature", "Kiln.Pressure"],
  "startTime": "now-7d",
  "endTime": "now",
  "aggregateName": "TimeAverage2",
  "aggregateInterval": "1h"
}
```

### get_tag_context

Get data availability information for tags.

**Parameters:**
- `tags`: Array of tag names

**Example:**
```json
{
  "tags": ["Motor.Speed", "Motor.Current"]
}
```

### get_virtual_views

List all available virtual views (no parameters required).

### get_asset_types

Get asset types defined in a virtual view.

**Parameters:**
- `view`: Virtual view name
- `parentType` (optional): Filter by parent type

**Example:**
```json
{
  "view": "Production",
  "parentType": "Equipment"
}
```

### get_asset_type_tags

Get tags associated with an asset type.

**Parameters:**
- `view`: Virtual view name
- `assetType`: Asset type name
- `deep` (optional): Include child nodes

**Example:**
```json
{
  "view": "Production",
  "assetType": "Kiln",
  "deep": true
}
```

### get_asset_instances

Find asset instances of a specific type.

**Parameters:**
- `view`: Virtual view name
- `assetType`: Asset type name
- `path` (optional): Path to search within
- `filterExpression` (optional): Filter expression

**Example:**
```json
{
  "view": "Production",
  "assetType": "Motor",
  "filterExpression": "[Speed] > 1000"
}
```

## Development

### Run in development mode:
```bash
npm run dev
```

### Build for production:
```bash
npm run build
```

### Run tests:
```bash
npm test
```

### Type checking:
```bash
npm run typecheck
```

## Troubleshooting

### Connection Issues

1. **Verify Canary server URL**: Ensure the URL includes `/api/v2`
2. **Check API token**: Confirm the token is valid and has necessary permissions
3. **Network connectivity**: Ensure the server is accessible from your network
4. **SSL certificates**: For HTTPS, ensure certificates are valid

### Performance Optimization

1. **Reduce maxSize**: Limit data points returned per request
2. **Use aggregations**: Request aggregated data instead of raw values
3. **Enable caching**: Cache TTL is set to 5 minutes by default
4. **Narrow time ranges**: Query smaller time windows for faster responses

### Debug Mode

Enable debug logging:
```env
DEBUG=true
```

This will output detailed logs to stderr.

## Architecture

```
canary-mcp-server/
├── src/
│   ├── canary/          # Canary API client and types
│   ├── tools/           # MCP tool implementations
│   ├── utils/           # Utilities (cache, time parsing, formatting)
│   ├── config.ts        # Configuration management
│   ├── server.ts        # MCP server setup
│   └── index.ts         # Entry point
└── dist/                # Compiled JavaScript
```

## Success Criteria

✅ MCP server successfully connects to Canary Historian API
✅ Users can browse and discover available tags/sensors
✅ Historical data queries return results with correct timestamps
✅ Support for basic aggregations (average, min, max over time periods)
✅ Query response time under 10 seconds for typical requests
✅ Data format is compatible with AI analysis and visualization
✅ Documentation includes examples of natural language queries

## License

MIT

## Support

For issues and questions, please refer to the Canary Historian API documentation at `Documents/canary_api_specs.html`.
