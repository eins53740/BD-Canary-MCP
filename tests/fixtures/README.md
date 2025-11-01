# Test Fixtures Documentation

This directory contains reusable test data and mock responses for the Canary MCP Server test suite.

## Overview

Test fixtures enable offline development and testing without requiring a live Canary API connection. All fixtures are designed to match the Read API v2 response formats used by the implemented MCP tools.

## File Structure

```
tests/fixtures/
├── __init__.py                # Package initialization
├── test_data.py               # Sample data structures
├── mock_responses.py          # Mock HTTP responses
├── conftest_fixtures.py       # pytest fixtures
├── README.md                  # This file
└── test_mock_responses.py     # Validation tests (in tests/unit/)
```

## Available Fixtures

### Sample Data (`test_data.py`)

Raw data structures representing Canary historian data:

- **SAMPLE_NAMESPACES** - List of namespace paths (Maceira.Cement.Kiln6)
- **SAMPLE_TAGS** - List of tag dictionaries with metadata
- **SAMPLE_TAG_METADATA** - Dict of complete tag metadata by tag path
- **SAMPLE_TIMESERIES_DATA** - List of timeseries data points with quality flags
- **SAMPLE_SERVER_INFO** - Server capabilities information
- **SAMPLE_MCP_INFO** - MCP server configuration

### Mock Responses (`mock_responses.py`)

Pre-formatted API responses for all 5 MCP tools:

**Success Responses:**
- `MOCK_LIST_NAMESPACES_SUCCESS` - list_namespaces successful response
- `MOCK_SEARCH_TAGS_SUCCESS` - search_tags with results
- `MOCK_GET_TAG_METADATA_SUCCESS` - tag metadata response
- `MOCK_READ_TIMESERIES_SUCCESS` - timeseries data response
- `MOCK_GET_SERVER_INFO_SUCCESS` - server info response

**Empty/No Results:**
- `MOCK_SEARCH_TAGS_NO_RESULTS` - No tags found
- `MOCK_READ_TIMESERIES_EMPTY` - No data for time range

**Error Responses:**
- `MOCK_AUTH_ERROR` - Authentication failure
- `MOCK_API_ERROR_500` - Internal server error
- `MOCK_NETWORK_ERROR` - Connection timeout
- `MOCK_CONFIG_ERROR` - Missing configuration
- `MOCK_GET_TAG_METADATA_NOT_FOUND` - Tag not found
- `MOCK_READ_TIMESERIES_TAG_NOT_FOUND` - Tag not found
- `MOCK_MALFORMED_RESPONSE` - Invalid response format

**Alternative Formats:**
- `MOCK_GET_TIMEZONES_DICT` - Dict format (Read API v2 variation)
- `MOCK_GET_TIMEZONES_LIST` - List format (Read API v2 variation)
- `MOCK_GET_AGGREGATES_DICT` - Dict format
- `MOCK_GET_AGGREGATES_LIST` - List format

### pytest Fixtures (`conftest_fixtures.py`)

Reusable pytest fixtures for dependency injection:

**Mock Objects:**
- `mock_canary_auth_client` - Mock CanaryAuthClient
- `mock_http_client_success` - Mock httpx.AsyncClient with success responses

**Sample Data Fixtures:**
- `sample_namespaces` - Returns copy of SAMPLE_NAMESPACES
- `sample_tags` - Returns copy of SAMPLE_TAGS
- `sample_tag_metadata` - Returns copy of sample tag metadata
- `sample_timeseries_data` - Returns copy of SAMPLE_TIMESERIES_DATA
- `sample_server_info` - Returns copy of SAMPLE_SERVER_INFO
- `sample_mcp_info` - Returns copy of SAMPLE_MCP_INFO

**Mock HTTP Response Fixtures:**
- `mock_list_namespaces_response` - Mock response for list_namespaces
- `mock_search_tags_response` - Mock response for search_tags
- `mock_get_tag_metadata_response` - Mock response for get_tag_metadata
- `mock_read_timeseries_response` - Mock response for read_timeseries
- `mock_get_server_info_response` - Mock response for get_server_info
- `mock_get_timezones_dict_response` - Mock timezones in dict format
- `mock_get_timezones_list_response` - Mock timezones in list format
- `mock_get_aggregates_dict_response` - Mock aggregates in dict format
- `mock_get_aggregates_list_response` - Mock aggregates in list format

**Error Response Fixtures:**
- `mock_error_response_401` - 401 Unauthorized
- `mock_error_response_404` - 404 Not Found
- `mock_error_response_500` - 500 Internal Server Error

## Usage Examples

### Using Sample Data in Unit Tests

```python
from tests.fixtures.test_data import SAMPLE_NAMESPACES, SAMPLE_TAGS

def test_namespace_parsing():
    # Use sample data directly
    namespaces = SAMPLE_NAMESPACES
    assert len(namespaces) == 3
    assert "Maceira.Cement.Kiln6" in namespaces
```

### Using Mock Responses

```python
from tests.fixtures.mock_responses import MOCK_SEARCH_TAGS_SUCCESS

def test_tag_search_response_parsing():
    # Use pre-formatted mock response
    response = MOCK_SEARCH_TAGS_SUCCESS
    assert response["success"] is True
    assert len(response["tags"]) > 0
```

### Using pytest Fixtures in Tests

```python
import pytest

def test_with_sample_data(sample_tags):
    # sample_tags fixture provides a fresh copy
    assert len(sample_tags) > 0
    assert all("name" in tag for tag in sample_tags)
```

### Mocking API Calls in Integration Tests

```python
from unittest.mock import patch, AsyncMock
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_namespaces(mock_canary_auth_client, mock_list_namespaces_response):
    # Mock auth client
    with patch("canary_mcp.server.CanaryAuthClient", return_value=mock_canary_auth_client):
        # Mock HTTP client
        mock_http_client = AsyncMock()
        mock_http_client.post = AsyncMock(return_value=mock_list_namespaces_response)
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("canary_mcp.server.httpx.AsyncClient", return_value=mock_http_client):
            from canary_mcp.server import list_namespaces
            result = await list_namespaces.fn()

            assert result["success"] is True
            assert "namespaces" in result
```

### Testing Error Scenarios

```python
from tests.fixtures.mock_responses import MOCK_AUTH_ERROR
from canary_mcp.auth import CanaryAuthError

@pytest.mark.unit
@pytest.mark.asyncio
async def test_authentication_failure(mock_canary_auth_client):
    # Configure mock to raise auth error
    mock_canary_auth_client.get_valid_token = AsyncMock(
        side_effect=CanaryAuthError("Invalid API token")
    )

    # Test tool behavior with auth failure
    # ... test implementation
```

### Testing Multiple Response Formats

```python
def test_timezone_dict_format(mock_get_timezones_dict_response):
    # Test with dict format response
    data = mock_get_timezones_dict_response.json()
    assert "timeZones" in data
    timezones = data["timeZones"]
    assert isinstance(timezones, list)

def test_timezone_list_format(mock_get_timezones_list_response):
    # Test with list format response
    timezones = mock_get_timezones_list_response.json()
    assert isinstance(timezones, list)
    assert len(timezones) > 0
```

## Adding New Fixtures

### 1. Add Sample Data

Edit `test_data.py`:

```python
# Add new sample data structure
SAMPLE_NEW_DATA = {
    "field1": "value1",
    "field2": "value2",
}
```

### 2. Create Mock Response

Edit `mock_responses.py`:

```python
from tests.fixtures.test_data import SAMPLE_NEW_DATA

# Create mock response using sample data
MOCK_NEW_ENDPOINT_SUCCESS = {
    "success": True,
    "data": SAMPLE_NEW_DATA,
}
```

### 3. Add pytest Fixture

Edit `conftest_fixtures.py`:

```python
@pytest.fixture
def sample_new_data():
    """Sample new data for testing."""
    return SAMPLE_NEW_DATA.copy()

@pytest.fixture
def mock_new_endpoint_response():
    """Mock HTTP response for new endpoint."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_NEW_ENDPOINT_SUCCESS
    mock_response.raise_for_status = MagicMock()
    return mock_response
```

### 4. Add Validation Tests

Edit `test_mock_responses.py`:

```python
@pytest.mark.unit
def test_mock_new_endpoint_structure():
    """Test new endpoint mock response has expected structure."""
    assert MOCK_NEW_ENDPOINT_SUCCESS is not None
    assert "success" in MOCK_NEW_ENDPOINT_SUCCESS
    assert "data" in MOCK_NEW_ENDPOINT_SUCCESS
    assert MOCK_NEW_ENDPOINT_SUCCESS["success"] is True
```

## Offline Development Workflow

### 1. Write Tests Using Fixtures

Start by writing tests using mock data and responses:

```python
def test_new_feature(sample_tags, mock_search_tags_response):
    # Test implementation using fixtures
    pass
```

### 2. Implement Feature

Implement your feature to pass the tests:

```python
def new_feature(tags):
    # Feature implementation
    return processed_tags
```

### 3. Run Tests Offline

```bash
# Run all tests (no Canary API needed)
pytest tests/

# Run only unit tests
pytest tests/unit/ -m unit

# Run only integration tests (still mocked)
pytest tests/integration/ -m integration
```

### 4. Validate with Live API (Optional)

Once feature works with mocks, optionally test against live Canary API:

```bash
# Configure real Canary connection in .env
CANARY_VIEWS_BASE_URL=https://scunscanary.secil.pt:55236
CANARY_API_TOKEN=your-token-here

# Run live integration tests (requires network)
pytest tests/integration/ --live
```

## Best Practices

1. **Always use `.copy()` when returning mutable fixture data** to prevent test pollution
2. **Match Read API v2 response formats** exactly as they appear in real API calls
3. **Include both success and error scenarios** for comprehensive testing
4. **Use realistic Maceira plant data** for consistency with production
5. **Document any new fixtures** you add in this README
6. **Validate new fixtures** by adding tests in `test_mock_responses.py`
7. **Test both dict and list response formats** where API supports multiple formats

## Coverage Validation

To verify fixtures cover all MCP tools:

```bash
# Run fixture validation tests
pytest tests/unit/test_mock_responses.py -v

# Should see passing tests for:
# - All 5 MCP tools (list_namespaces, search_tags, get_tag_metadata, read_timeseries, get_server_info)
# - Success scenarios
# - Error scenarios
# - Empty/no results
# - Alternative response formats
```

## Troubleshooting

### Import Errors

If you get import errors:

```python
# Make sure PYTHONPATH includes project root
import sys
sys.path.insert(0, '/path/to/BD-hackaton-2025-10')

# Or run tests from project root
cd /path/to/BD-hackaton-2025-10
pytest tests/
```

### Fixture Not Found

If pytest can't find a fixture:

1. Check `conftest_fixtures.py` has the fixture defined with `@pytest.fixture` decorator
2. Ensure your test file imports fixtures or has conftest.py properly configured
3. Verify fixture name matches exactly (case-sensitive)

### Async Fixture Issues

For async tests:

```python
# Always use @pytest.mark.asyncio for async tests
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

## References

- [Story 1.8](../../docs/stories/1-8-test-data-fixtures-mock-responses.md) - Implementation story
- [Architecture](../../docs/architecture.md) - Project architecture
- [pytest Documentation](https://docs.pytest.org/) - pytest framework
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html) - Python mocking library
