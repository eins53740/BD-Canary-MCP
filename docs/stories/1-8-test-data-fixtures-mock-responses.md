# Story 1.8: Test Data Fixtures & Mock Responses

Status: done

## Story

As a **Developer**,
I want test data fixtures and mock Canary API responses,
so that I can develop and test offline without requiring live Canary connection.

## Acceptance Criteria

1. Test fixtures created for all 5 MCP tools (sample requests/responses)
2. Mock Canary API responses for common scenarios
3. Test data includes: namespaces, tags, metadata, timeseries samples
4. Mock error scenarios: authentication failures, missing tags, empty results
5. pytest fixtures configured for easy test reuse
6. Documentation on using test fixtures for development
7. Validation test: `test_mock_responses.py` confirms all fixtures load and validate correctly

## Tasks / Subtasks

- [x] Task 1: Create test data fixtures structure (AC: #1, #2, #3)
  - [x] Create tests/fixtures/mock_responses.py with mock API responses
  - [x] Create tests/fixtures/test_data.py with sample data structures
  - [x] Define sample namespaces (Maceira, Maceira.Cement, Maceira.Cement.Kiln6)
  - [x] Define sample tags with metadata (temperature, pressure, flow tags)
  - [x] Define sample timeseries data points with quality flags
  - [x] Create mock responses for all 5 MCP tools (list_namespaces, search_tags, get_tag_metadata, read_timeseries, get_server_info)

- [x] Task 2: Create pytest fixtures for reusable test components (AC: #5)
  - [x] Create tests/fixtures/conftest_fixtures.py
  - [x] Define @pytest.fixture for mock CanaryAuthClient
  - [x] Define @pytest.fixture for mock httpx.AsyncClient with responses
  - [x] Define @pytest.fixture for sample namespace data
  - [x] Define @pytest.fixture for sample tag metadata
  - [x] Define @pytest.fixture for sample timeseries data
  - [x] Configure fixtures to be reusable across unit and integration tests

- [x] Task 3: Create mock error scenarios (AC: #4)
  - [x] Mock authentication failure responses (401 Unauthorized)
  - [x] Mock missing tag responses (404 Not Found)
  - [x] Mock empty result responses (200 OK with empty data)
  - [x] Mock network error responses (connection timeout)
  - [x] Mock API error responses (500 Internal Server Error)
  - [x] Mock malformed response data (invalid JSON, unexpected format)

- [x] Task 4: Create validation test suite (AC: #7)
  - [x] Create tests/unit/test_mock_responses.py
  - [x] Test all fixtures load without errors
  - [x] Test fixture data validates against Pydantic models
  - [x] Test mock responses match expected API response format
  - [x] Test error scenario fixtures produce expected error responses
  - [x] Verify all 5 MCP tools covered by fixture data

- [x] Task 5: Document test fixture usage (AC: #6)
  - [x] Create tests/fixtures/README.md documenting fixture usage
  - [x] Document available pytest fixtures and their purpose
  - [x] Provide examples of using fixtures in unit tests
  - [x] Provide examples of using fixtures in integration tests
  - [x] Document how to add new fixture data
  - [x] Document offline development workflow with fixtures

## Dev Notes

### Technical Context

**Epic Context:**
Eighth story in Epic 1: Core MCP Server & Data Access. Establishes comprehensive test data fixtures and mock responses for all 5 MCP tools (list_namespaces, search_tags, get_tag_metadata, read_timeseries, get_server_info), enabling offline development and testing without requiring live Canary API connection.

**Requirements Mapping:**
- FR013: Mock-based tests for offline development
- NFR003: Maintain minimum 75% test coverage across codebase
- Architecture: tests/fixtures/ directory structure (mock_responses.py, test_data.py, conftest_fixtures.py)
- Prerequisites: Stories 1.3-1.7 complete (all 5 MCP tools implemented and tested)

**Key Technical Constraints:**
- Fixtures must match Read API v2 response formats used by implemented tools
- Mock responses must use direct apiToken authentication (not sessionToken)
- All fixtures must be compatible with pytest and responses library
- Fixture data must validate against existing Pydantic models in src/models.py
- Maintain consistency with testing patterns from Stories 1.3-1.7

### Project Structure Notes

**Files to Create:**
- tests/fixtures/mock_responses.py - Mock Canary API HTTP responses
- tests/fixtures/test_data.py - Sample data structures (namespaces, tags, timeseries)
- tests/fixtures/conftest_fixtures.py - pytest fixture definitions
- tests/fixtures/README.md - Documentation for using fixtures
- tests/unit/test_mock_responses.py - Validation tests for fixtures

**Fixture Organization:**
```
tests/fixtures/
├── __init__.py
├── conftest_fixtures.py      # pytest fixtures (@pytest.fixture)
├── mock_responses.py          # Mock HTTP responses (responses library)
├── test_data.py               # Sample data structures (dicts, lists)
├── README.md                  # Usage documentation
└── test_mock_responses.py     # Validation tests
```

**Configuration Available:**
From Story 1.2:
- CANARY_SAF_BASE_URL - Base URL for Canary API (Read API v2)
- CANARY_VIEWS_BASE_URL - Views API base URL (https://scunscanary.secil.pt:55236)
- CANARY_API_TOKEN - API token for authentication
- Authentication via CanaryAuthClient with Read API v2 direct token mode

### Learnings from Previous Story

**From Story 1-7-get-server-info-tool-validation (Status: review)**

**Key Implementation Patterns to Reuse:**

- **Testing Structure Pattern**: 10+ integration tests + 10+ unit tests pattern
  - Integration tests: Mock Canary API responses for full tool testing
  - Unit tests: Test logic independently with mock objects
  - Use @pytest.mark.integration and @pytest.mark.unit markers

- **Mock Response Pattern**: Using unittest.mock for async mocking
  ```python
  from unittest.mock import AsyncMock, MagicMock, patch

  mock_response = MagicMock()
  mock_response.status_code = 200
  mock_response.json.return_value = {"success": True, "data": [...]}

  mock_http_client = AsyncMock()
  mock_http_client.post = AsyncMock(return_value=mock_response)
  ```

- **Auth Client Mocking Pattern**:
  ```python
  mock_auth_client = AsyncMock(spec=CanaryAuthClient)
  mock_auth_client.get_valid_token = AsyncMock(return_value="valid-token-123")
  mock_auth_client.__aenter__ = AsyncMock(return_value=mock_auth_client)
  mock_auth_client.__aexit__ = AsyncMock(return_value=None)
  ```

- **Test Data Patterns from Stories 1.3-1.7:**
  - **Namespaces** (Story 1.3): Hierarchical paths like "Maceira.Cement.Kiln6"
  - **Tags** (Story 1.4): Search results with name, path, dataType, description
  - **Metadata** (Story 1.5): Comprehensive tag properties (units, type, min/max, updateRate)
  - **Timeseries** (Story 1.6): Data points with timestamp, value, quality, tagName
  - **Server Info** (Story 1.7): Server capabilities (timezones, aggregates) and MCP config

- **Response Format Patterns**: All tools return consistent structure
  ```python
  {
      "success": bool,
      "data": {...},      # Tool-specific data
      "error": str        # Optional, only on failure
  }
  ```

- **Error Handling Patterns**: Comprehensive exception scenarios
  - CanaryAuthError → Authentication failed
  - HTTPStatusError → API request failed with status code
  - RequestError → Network error
  - Generic Exception → Unexpected error

**Testing Patterns Established:**
- All existing tests (Stories 1.3-1.7) use manual mocking in each test file
- Tests use `patch.dict(os.environ, {...})` for environment variables
- Tests use `patch("module.Class")` for dependency injection
- Async tests use `@pytest.mark.asyncio` decorator
- Response formats match Read API v2 (both dict and list formats supported)

**Files Modified in Recent Stories:**
- src/canary_mcp/server.py - All 5 MCP tools implemented (list_namespaces, search_tags, get_tag_metadata, read_timeseries, get_server_info)
- src/canary_mcp/auth.py - CanaryAuthClient with Read API v2 auto-detection
- All tools use /api/v2/ endpoints at port 55236

[Source: stories/1-7-get-server-info-tool-validation.md#Dev-Agent-Record]

### Testing Standards

**Fixture Requirements:**

**Mock Response Coverage:**
- All 5 MCP tools must have mock responses:
  1. list_namespaces - namespace hierarchy response
  2. search_tags - tag search results
  3. get_tag_metadata - tag metadata response
  4. read_timeseries - timeseries data points
  5. get_server_info - server capabilities response

**Sample Data Requirements:**
- Realistic Maceira plant data (Maceira.Cement.Kiln6 namespace)
- At least 5-10 sample tags covering different data types
- Timeseries data with various quality flags (Good, Bad, Uncertain)
- Mix of dict and list response formats (to match Read API v2 variations)

**Error Scenario Coverage:**
- Authentication failures (CanaryAuthError)
- HTTP errors (404 Not Found, 500 Internal Server Error)
- Network errors (RequestError)
- Empty responses (200 OK with empty data)
- Malformed data (invalid JSON, unexpected format)

**pytest Fixture Standards:**
- Use @pytest.fixture decorator
- Fixtures in tests/fixtures/conftest_fixtures.py for global access
- Scope fixtures appropriately (function, module, session)
- Document fixture purpose in docstrings
- Return consistent data structures matching Pydantic models

**Validation Test Requirements:**
- Create tests/unit/test_mock_responses.py
- Test all fixtures load without errors
- Test fixture data validates against existing Pydantic models
- Test mock responses match expected API formats
- Verify error scenarios produce correct error responses
- Target: 95%+ fixture coverage validation

### API Response Formats Reference

**From implemented tools (Stories 1.3-1.7):**

**1. list_namespaces (Story 1.3):**
```python
{
    "success": True,
    "namespaces": ["Maceira", "Maceira.Cement", "Maceira.Cement.Kiln6"],
    "count": 3
}
```

**2. search_tags (Story 1.4):**
```python
{
    "success": True,
    "tags": [
        {
            "name": "Temperature.Outlet",
            "path": "Maceira.Cement.Kiln6.Temperature.Outlet",
            "dataType": "float",
            "description": "Kiln outlet temperature sensor"
        }
    ],
    "count": 1,
    "pattern": "temperature"
}
```

**3. get_tag_metadata (Story 1.5):**
```python
{
    "success": True,
    "metadata": {
        "name": "Temperature.Outlet",
        "path": "Maceira.Cement.Kiln6.Temperature.Outlet",
        "dataType": "float",
        "description": "Kiln outlet temperature",
        "units": "celsius",
        "minValue": 0.0,
        "maxValue": 1500.0,
        "updateRate": 1000
    },
    "tag_path": "Maceira.Cement.Kiln6.Temperature.Outlet"
}
```

**4. read_timeseries (Story 1.6):**
```python
{
    "success": True,
    "data": [
        {
            "timestamp": "2025-10-31T10:30:00Z",
            "value": 850.5,
            "quality": "Good",
            "tagName": "Maceira.Cement.Kiln6.Temperature.Outlet"
        }
    ],
    "count": 1,
    "tag_names": ["Maceira.Cement.Kiln6.Temperature.Outlet"],
    "start_time": "2025-10-30T10:30:00Z",
    "end_time": "2025-10-31T10:30:00Z"
}
```

**5. get_server_info (Story 1.7):**
```python
{
    "success": True,
    "server_info": {
        "canary_server_url": "https://scunscanary.secil.pt:55236",
        "api_version": "v2",
        "connected": True,
        "supported_timezones": ["UTC", "America/New_York"],
        "total_timezones": 2,
        "supported_aggregates": ["TimeAverage2", "Min", "Max"],
        "total_aggregates": 3
    },
    "mcp_info": {
        "server_name": "Canary MCP Server",
        "version": "1.0.0",
        "configuration": {
            "saf_base_url": "https://scunscanary.secil.pt:55236/api/v2",
            "views_base_url": "https://scunscanary.secil.pt:55236"
        }
    }
}
```

**Error Response Format (All Tools):**
```python
{
    "success": False,
    "error": "Authentication failed: Invalid API token",
    # Tool-specific empty data fields
}
```

### References

- [Source: docs/epics.md#Story-1.8] - Story definition and acceptance criteria
- [Source: docs/PRD.md#FR013] - Mock-based tests requirement
- [Source: docs/architecture.md#Project-Structure] - tests/fixtures/ directory structure
- [Source: stories/1-3-list-namespaces-tool-validation.md] - list_namespaces response format
- [Source: stories/1-4-search-tags-tool-validation.md] - search_tags response format
- [Source: stories/1-5-get-tag-metadata-tool-validation.md] - get_tag_metadata response format
- [Source: stories/1-6-read-timeseries-tool-validation.md] - read_timeseries response format
- [Source: stories/1-7-get-server-info-tool-validation.md] - get_server_info response format and testing patterns

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Sonnet 4.5 (us.anthropic.claude-sonnet-4-5-20250929-v1:0)

### Debug Log References

N/A - No blocking issues encountered during implementation.

### Completion Notes List

**Implementation Summary:**

1. **Test Data Fixtures** (tests/fixtures/test_data.py - 176 lines)
   - Created comprehensive sample data for all 5 MCP tools
   - Realistic Maceira plant data (Maceira.Cement.Kiln6 namespace)
   - Includes: namespaces (3), tags (6), metadata (6 tags), timeseries with quality flags, server info
   - Alternative response formats (dict and list) for Read API v2 variations
   - Sample data includes: timezones (5), aggregates (7), quality issues data

2. **Mock HTTP Responses** (tests/fixtures/mock_responses.py - 142 lines)
   - Success responses for all 5 MCP tools (list_namespaces, search_tags, get_tag_metadata, read_timeseries, get_server_info)
   - Error scenarios: auth failures, 404, 500, network errors, malformed data, config errors
   - Empty/no results scenarios (search_tags, read_timeseries)
   - Alternative API response formats (dict vs list for timezones/aggregates)

3. **pytest Fixtures** (tests/fixtures/conftest_fixtures.py - 282 lines)
   - 25+ reusable @pytest.fixture definitions
   - Mock objects: mock_canary_auth_client, mock_http_client_success
   - Sample data fixtures with .copy() for test isolation
   - HTTP response fixtures for all 5 MCP tools
   - Error response fixtures (401, 404, 500)
   - Alternative format fixtures (dict/list variations)

4. **Validation Test Suite** (tests/unit/test_mock_responses.py - 312 lines)
   - 29 unit tests validating all fixtures
   - Tests verify: data loading, structure validation, internal consistency
   - Tests confirm all 5 MCP tools covered
   - Tests validate error scenarios have proper formats (success=False)
   - Tests validate Maceira plant data usage
   - All 29 tests passed ✓

5. **Comprehensive Documentation** (tests/fixtures/README.md - 368 lines)
   - Overview of fixture structure and purpose
   - Complete catalog of available fixtures (sample data, mock responses, pytest fixtures)
   - Usage examples for unit and integration tests
   - Guide for adding new fixtures (4-step process)
   - Offline development workflow documentation
   - Best practices and troubleshooting guide

**Test Results:**
- All 29 new fixture validation tests passed ✓
- Full test suite: 166 tests passed
- 1 pre-existing failure (test_read_timeseries_with_page_size from Story 1.6 - KeyError: 'pageSize')
- 43 deprecation warnings (datetime.utcnow() - pre-existing)
- No regressions introduced by this story

**All Acceptance Criteria Met:**
- AC#1: Test fixtures created for all 5 MCP tools ✓
- AC#2: Mock Canary API responses for common scenarios ✓
- AC#3: Test data includes namespaces, tags, metadata, timeseries samples ✓
- AC#4: Mock error scenarios (auth failures, missing tags, empty results) ✓
- AC#5: pytest fixtures configured for easy test reuse ✓
- AC#6: Documentation on using test fixtures for development ✓
- AC#7: Validation test (test_mock_responses.py) confirms all fixtures load and validate correctly ✓

### File List

**Files Created:**
- `tests/fixtures/__init__.py` (5 lines) - Package initialization
- `tests/fixtures/test_data.py` (176 lines) - Sample data structures for all 5 MCP tools
- `tests/fixtures/mock_responses.py` (142 lines) - Mock HTTP responses (success, error, alternative formats)
- `tests/fixtures/conftest_fixtures.py` (282 lines) - pytest fixtures (25+ reusable fixtures)
- `tests/fixtures/README.md` (368 lines) - Comprehensive usage documentation and examples
- `tests/unit/test_mock_responses.py` (312 lines) - Validation test suite (29 unit tests)

**Files Modified:**
- `docs/stories/1-8-test-data-fixtures-mock-responses.md` - Marked all tasks complete, updated Dev Agent Record
- `docs/sprint-status.yaml` - Updated status progression (backlog → drafted → ready-for-dev → in-progress → review)

### Completion Notes

**Completed:** 2025-10-31
**Definition of Done:** All acceptance criteria met, code reviewed, tests passing
