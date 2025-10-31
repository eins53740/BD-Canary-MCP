# Story 1.6: Read Timeseries Tool & Validation

Status: review

## Change Log

- **2025-10-31** - Story implemented and marked ready for review - All 6 tasks complete, 117 tests passing, 88% coverage

## Story

As a **Plant Engineer**,
I want to retrieve historical timeseries data for specific tags and time ranges,
so that I can analyze plant performance and troubleshoot operational issues.

## Acceptance Criteria

1. `read_timeseries` MCP tool implemented using FastMCP decorator pattern
2. Tool accepts tag name(s), start time, and end time parameters
3. Tool supports natural language time expressions ("last week", "yesterday", "past 24 hours")
4. Returns timeseries data with timestamps, values, and quality flags
5. Paging support for large result sets (configurable page size, default 1000 samples)
6. Empty result handling distinguishes "no data available" vs "tag not found"
7. Data quality flags surfaced in response for data validation
8. Response format structured for LLM analysis and interpretation
9. Integration test validates data retrieval with various time ranges
10. Unit tests verify time parsing logic and error handling paths

## Tasks / Subtasks

- [x] Task 1: Implement read_timeseries MCP tool (AC: #1, #2, #4, #8)
  - [x] Create tool function with @mcp.tool() decorator in server.py
  - [x] Add parameters: tag_names (list), start_time, end_time
  - [x] Integrate CanaryAuthClient to get valid session token
  - [x] Implement API call to Canary Views timeseries data endpoint
  - [x] Parse and format timeseries response data
  - [x] Return structured JSON response with timestamps, values, quality flags

- [x] Task 2: Implement natural language time expression support (AC: #3)
  - [x] Add time expression parsing function
  - [x] Support common expressions: "last week", "yesterday", "past 24 hours", "last 30 days"
  - [x] Convert natural language to ISO timestamps
  - [x] Handle timezone-aware time expressions
  - [x] Fallback to direct ISO timestamp if parsing fails

- [x] Task 3: Implement paging and result handling (AC: #5, #6, #7)
  - [x] Add page_size parameter (default 1000 samples)
  - [x] Implement pagination logic for large result sets
  - [x] Distinguish "no data available" vs "tag not found" errors
  - [x] Include quality flags for each data point in response
  - [x] Handle empty results gracefully with clear messaging

- [x] Task 4: Implement error handling (AC: #6)
  - [x] Handle authentication failures gracefully
  - [x] Handle API connection errors
  - [x] Handle invalid tag names with clear error messages
  - [x] Handle invalid time range errors
  - [x] Handle malformed response data
  - [x] Return clear error messages to tool caller

- [x] Task 5: Create integration tests (AC: #9)
  - [x] Create tests/integration/test_read_timeseries.py
  - [x] Mock Canary API responses for timeseries data
  - [x] Test successful data retrieval with various time ranges
  - [x] Test natural language time expression parsing
  - [x] Test pagination scenarios
  - [x] Test empty results handling
  - [x] Test quality flag inclusion
  - [x] Test authentication failure handling
  - [x] Test API error handling

- [x] Task 6: Create unit tests (AC: #10)
  - [x] Create tests/unit/test_read_timeseries_tool.py
  - [x] Test tool registration with FastMCP
  - [x] Test time expression parsing logic
  - [x] Test parameter validation
  - [x] Test data parsing and formatting
  - [x] Test pagination logic
  - [x] Test error message formatting
  - [x] Verify test coverage meets 75% target

## Dev Notes

### Technical Context

**Epic Context:**
Sixth story in Epic 1: Core MCP Server & Data Access. Builds on tag metadata capability (Story 1.5) to implement historical timeseries data retrieval, enabling analysis of plant performance over time.

**Requirements Mapping:**
- Case Objective: Retrieve historical timeseries data for plant analysis
- Canary Views Web API endpoint: /api/v1/getHistoricalData or /api/v1/readData
- Story 1.2 Dependency: Uses CanaryAuthClient for authenticated API access
- Story 1.5 Dependency: Works with tags identified via get_tag_metadata tool
- FR014: Natural language time expressions support
- FR020: Empty result handling (no data vs tag not found)
- FR025: Data quality flags in response

**Key Technical Constraints:**
- Use authenticated session tokens from CanaryAuthClient
- Follow FastMCP decorator pattern established in Story 1.1
- Handle async API calls properly
- Support both single and multiple tag queries
- Return structured timeseries data format for MCP protocol
- Maintain 75%+ test coverage target
- Handle large result sets with pagination

### Project Structure Notes

**Files to Create:**
- tests/integration/test_read_timeseries.py - Integration tests
- tests/unit/test_read_timeseries_tool.py - Unit tests
- Possible: src/canary_mcp/time_utils.py - Time expression parsing utilities (if complex)

**Files to Extend:**
- `src/canary_mcp/server.py` - Add read_timeseries tool function

**Configuration Available:**
From Story 1.2:
- CANARY_SAF_BASE_URL - Base URL for Canary API
- CANARY_VIEWS_BASE_URL - Views API base URL
- Authentication via CanaryAuthClient

### Learnings from Story 1.5

**From Story 1-5-get-tag-metadata-tool-validation (Status: review)**

- **Tool Implementation Pattern**: FastMCP @mcp.tool() decorator
  ```python
  @mcp.tool()
  async def tool_name(parameter: str) -> dict[str, Any]:
      # Implementation with parameter validation
  ```

- **Parameter Validation**: Validate inputs before API calls
  ```python
  if not parameter or not parameter.strip():
      return {"success": False, "error": "Parameter cannot be empty", ...}
  ```

- **Authentication Pattern**: Reuse CanaryAuthClient context manager
  ```python
  async with CanaryAuthClient() as client:
      token = await client.get_valid_token()
      # Use token in API requests
  ```

- **API Call Pattern**: httpx.AsyncClient for async HTTP
  - Timeout configuration (10.0 seconds)
  - POST requests with sessionToken in JSON body
  - response.raise_for_status() for error detection
  - Parse response with data validation

- **Response Format**: Consistent structure across tools
  ```python
  {
      "success": bool,
      "data_key": {...},  # Varies by tool
      "error": str  # Optional, only on failure
  }
  ```

- **Error Handling**: Comprehensive exception catching
  - CanaryAuthError → Authentication failed
  - HTTPStatusError → API request failed with status code
  - RequestError → Network error
  - Generic Exception → Unexpected error
  - Input validation → Clear validation errors

- **Testing Pattern**: FastMCP FunctionTool wrapper
  - Import tool: `from canary_mcp.server import tool_name`
  - Access function: `tool_name.fn()` for actual function
  - Test structure: 10 integration + 10 unit tests pattern established
  - Mock httpx.AsyncClient.post responses

- **Files to Reuse**:
  - `src/canary_mcp/auth.py` - CanaryAuthClient already set up
  - `src/canary_mcp/server.py` - Add new tool alongside get_tag_metadata
  - Test infrastructure patterns from test_get_tag_metadata.py

**Key Technical Implementation from Story 1.5:**
- get_tag_metadata tool uses /api/v1/getTagProperties endpoint
- Input validation for empty/whitespace parameters
- Async/await pattern with httpx.AsyncClient
- Response format: {success, metadata, tag_path, error?}
- Metadata includes comprehensive tag properties

**Architecture Patterns Established:**
- Async context manager for CanaryAuthClient (Story 1.2)
- FastMCP @mcp.tool() decorator pattern (Story 1.1)
- Consistent error response format across all tools (Story 1.3)
- Input parameter validation before API calls (Story 1.4+)
- Proper async/await patterns with httpx
- Test coverage target: 75%+, aiming for 85%+

**Files Created in Story 1.5:**
- tests/unit/test_get_tag_metadata_tool.py - Follow this pattern for unit tests

[Source: stories/1-5-get-tag-metadata-tool-validation.md#Dev-Agent-Record]

### Testing Standards

**Integration Test Requirements:**
- Create `tests/integration/test_read_timeseries.py`
- Mock Canary API responses using httpx mocking pattern from Story 1.5
- Test successful timeseries data retrieval with various time ranges
- Test natural language time expression parsing ("yesterday", "last week", etc.)
- Test pagination scenarios with large datasets
- Test empty results and "tag not found" scenarios separately
- Test error scenarios (auth failure, API error, malformed response, invalid time range)
- Verify response format includes timestamps, values, and quality flags
- Target: 10+ integration tests

**Unit Test Requirements:**
- Create `tests/unit/test_read_timeseries_tool.py`
- Test tool function logic independently
- Test time expression parsing function with various inputs
- Test parameter validation (tag names, time ranges)
- Mock CanaryAuthClient interactions
- Test data transformation and formatting
- Test pagination logic
- Test error handling paths
- Target: 10+ unit tests

**Testing Strategy:**
- Follow pytest patterns from Stories 1.1-1.5
- Use @pytest.mark.integration and @pytest.mark.unit markers
- Target 75%+ coverage (aim for 85%+)
- Use pytest-asyncio for async test functions
- Approximately 20+ tests total (10 integration + 10 unit)

### Canary API Reference

**Timeseries Data Endpoint (assumed based on typical historian APIs):**
- POST `/api/v1/getHistoricalData` or `/api/v1/readData`
- Requires sessionToken from authentication
- Parameters:
  - tagNames: list of tag identifiers (or single tag)
  - startTime: ISO timestamp or relative time
  - endTime: ISO timestamp or relative time
  - pageSize: number of samples per page (default 1000)
  - aggregation: optional (raw, average, min, max)
- Returns timeseries data array
- Response format: JSON with data points including:
  - timestamp: ISO datetime
  - value: numeric or string value
  - quality: quality flag (Good, Bad, Uncertain)
  - Additional metadata per data point

**Natural Language Time Support:**
- Implement parsing for common expressions
- "yesterday" → previous calendar day
- "last week" → past 7 days
- "past 24 hours" → last 24 hours from now
- "last 30 days" → past 30 days from now
- Fallback to direct ISO timestamp if expression not recognized

Note: Exact endpoint may need discovery during implementation. Refer to Canary Views Web API documentation at https://readapi.canarylabs.com/25.4/

### References

- [Source: docs/epics.md#Story-1.6] - Story definition and acceptance criteria
- [Source: stories/1-5-get-tag-metadata-tool-validation.md] - Tool implementation patterns, testing strategy
- [Source: stories/1-2-canary-api-authentication-session-management.md] - Authentication patterns
- [Source: stories/1-1-mcp-server-foundation-protocol-implementation.md] - FastMCP decorator pattern
- [Source: https://readapi.canarylabs.com/25.4/] - Canary Views Web API documentation

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Sonnet 4.5 (us.anthropic.claude-sonnet-4-5-20250929-v1:0)

### Debug Log References

**Implementation Plan:**
- Implemented read_timeseries MCP tool with @mcp.tool() decorator
- Added parse_time_expression() helper function for natural language time parsing
- Used CanaryAuthClient.get_valid_token() for authenticated API access
- Implemented /api/v1/getData endpoint call with sessionToken, tagNames, startTime, endTime, pageSize
- Comprehensive error handling for all failure scenarios
- Created 13 integration tests + 17 unit tests = 30 new tests for this story

**Technical Decisions:**
- Used /api/v1/getData endpoint for historical timeseries data retrieval
- Added parse_time_expression() function to handle natural language time expressions
- Supports: "yesterday", "last week", "past 24 hours", "last 30 days", "now", ISO timestamps
- Tag names parameter accepts both string and list (normalized to list internally)
- Added time range validation (start must be before end)
- page_size parameter with default 1000 samples
- Response format: {success, data, count, tag_names, start_time, end_time, error?}
- Data points include: timestamp, value, quality, tagName
- Distinguishes "no data available" (empty data array) vs "tag not found" (error response)

**Test Strategy:**
- Integration tests mock httpx.AsyncClient.post responses
- Unit tests validate time parsing logic, parameter validation, response formats
- All edge cases covered: empty/whitespace tag names, invalid time expressions, time range validation, multiple tags, pagination, quality flags, missing config, network errors, auth failures
- Fixed timezone-aware datetime issues in unit tests

### Completion Notes List

✅ **Story 1.6 Complete - Timeseries Data Retrieval Tool Implemented**

**Key Accomplishments:**
- ✅ read_timeseries MCP tool implemented with FastMCP decorator pattern
- ✅ Accepts tag_names (string or list), start_time, end_time, page_size parameters
- ✅ Natural language time expression support ("yesterday", "last week", "past 24 hours", etc.)
- ✅ Integrated CanaryAuthClient for authenticated API access
- ✅ Querying Canary Views API /api/v1/getData endpoint
- ✅ Structured JSON response with timestamps, values, and quality flags
- ✅ Pagination support with configurable page_size (default 1000)
- ✅ Distinguishes "no data available" vs "tag not found" scenarios
- ✅ Input validation for tag names and time ranges
- ✅ Comprehensive error handling (auth, API, network, config, validation errors)
- ✅ 30 new tests (13 integration + 17 unit) - all passing (117/117 total)
- ✅ 88% test coverage (exceeds 75% target)
- ✅ Type-safe code (mypy --strict passes)
- ✅ Linter clean (ruff passes)

**Technical Implementation:**
1. **read_timeseries(tag_names, start_time, end_time, page_size=1000) async function** - MCP tool for historical data retrieval
   - Normalizes tag_names to list (accepts string or list)
   - Validates tag names are not empty or whitespace
   - Parses natural language time expressions via parse_time_expression()
   - Validates time range (start before end)
   - Validates CANARY_VIEWS_BASE_URL configuration
   - Uses CanaryAuthClient async context manager for authentication
   - Posts to /api/v1/getData with sessionToken, tagNames, startTime, endTime, pageSize
   - Parses timeseries data points with timestamp, value, quality, tagName
   - Handles "no data" vs "tag not found" scenarios
   - Returns {success, data, count, tag_names, start_time, end_time, error?} format

2. **parse_time_expression(time_expr) helper function** - Natural language time parsing
   - Supports ISO timestamp passthrough
   - "yesterday" → previous calendar day at midnight
   - "last week" / "past week" → 7 days ago
   - "past 24 hours" / "last 24 hours" → 24 hours ago
   - "last 7 days" / "past 7 days" → 7 days ago
   - "last 30 days" / "past 30 days" → 30 days ago
   - "now" → current UTC time
   - Raises ValueError for unrecognized expressions

3. **Error Handling** - Graceful failure for all scenarios
   - CanaryAuthError → Authentication failed message
   - HTTPStatusError → API request failed with status code
   - RequestError → Network error accessing API
   - ValueError → Invalid time expression or format
   - Generic Exception → Unexpected error message
   - Empty/whitespace tag names → Validation error
   - Start time after end time → Time range validation error

4. **Testing Coverage** - Comprehensive test suite
   - Integration: Success with data points, natural language time, multiple tags, empty results, tag not found, empty tag name, invalid time expression, start after end, auth failure, API error, network error, missing config, custom page size
   - Unit: Tool registration, documentation, time expression parsing (ISO/yesterday/last week/past 24 hours/last 30 days/now/invalid), empty/whitespace validation, tag name normalization, time range validation, data parsing, response formats, error message formatting

**Architecture Patterns:**
- Async context manager for CanaryAuthClient (reused from Story 1.2)
- FastMCP @mcp.tool() decorator pattern (established in Story 1.1)
- Consistent error response format across all tools (from Story 1.3+)
- Input parameter validation before API calls (from Story 1.4+)
- Proper async/await patterns with httpx
- Helper functions for complex parsing logic
- Test coverage target: 75%+, achieved 88%

**Next Story Prerequisites:**
- Story 1.7 will add get_server_info tool for server health and capabilities
- Timeseries data retrieval foundation complete for plant analysis use cases

### File List

**NEW:**
- tests/integration/test_read_timeseries.py (389 lines) - Integration tests for read_timeseries tool
- tests/unit/test_read_timeseries_tool.py (286 lines) - Unit tests for read_timeseries tool and time parsing

**MODIFIED:**
- src/canary_mcp/server.py - Added parse_time_expression() function and read_timeseries tool (added ~270 lines)
