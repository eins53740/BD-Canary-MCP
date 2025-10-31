# Story 1.4: Search Tags Tool & Validation

Status: done

## Change Log

- **2025-10-31** - Story implemented and marked ready for review - All 4 tasks complete, 66 tests passing, 86% coverage

## Story

As a **UNS Developer**,
I want an MCP tool to search for tags in Canary by name pattern,
so that I can discover available process variables and their hierarchical paths.

## Acceptance Criteria

1. MCP tool `search_tags` implemented using FastMCP decorator pattern
2. Tool accepts search pattern parameter (tag name or partial match)
3. Tool uses authenticated CanaryAuthClient from Story 1.2
4. Tool queries Canary Views API to search for tags matching pattern
5. Tool returns list of matching tags with their paths and metadata
6. Error handling for API failures with clear error messages
7. Integration test validates tool returns expected search results
8. Unit tests verify search logic and error handling paths

## Tasks / Subtasks

- [x] Task 1: Implement search_tags MCP tool (AC: #1, #2, #3, #4)
  - [x] Create tool function with @mcp.tool() decorator in server.py
  - [x] Add search_pattern parameter to tool function
  - [x] Integrate CanaryAuthClient to get valid session token
  - [x] Implement API call to Canary Views tag search endpoint
  - [x] Parse and format tag search response data
  - [x] Return structured JSON response with tag list

- [x] Task 2: Implement error handling (AC: #6)
  - [x] Handle authentication failures gracefully
  - [x] Handle API connection errors
  - [x] Handle empty search results
  - [x] Handle malformed response data
  - [x] Return clear error messages to tool caller
  - [x] Log errors for debugging

- [x] Task 3: Create integration tests (AC: #7)
  - [x] Create tests/integration/test_search_tags.py
  - [x] Mock Canary API responses for tag search data
  - [x] Test successful tag search with results
  - [x] Test search with no matches (empty results)
  - [x] Test authentication failure handling
  - [x] Test API error handling
  - [x] Verify response format matches expected structure

- [x] Task 4: Create unit tests (AC: #8)
  - [x] Create tests/unit/test_search_tags_tool.py
  - [x] Test tool registration with FastMCP
  - [x] Test search pattern parameter handling
  - [x] Test data parsing logic
  - [x] Test error message formatting
  - [x] Verify test coverage meets 75% target

## Dev Notes

### Technical Context

**Epic Context:**
Fourth story in Epic 1: Core MCP Server & Data Access. Builds on namespace browsing (Story 1.3) to implement tag search capability, enabling discovery of specific process variables by name pattern.

**Requirements Mapping:**
- Case Objective: Retrieve metadata about tags and their properties
- Canary Views Web API endpoint: /api/v1/browseTags or similar search endpoint
- Story 1.2 Dependency: Uses CanaryAuthClient for authenticated API access
- Story 1.3 Dependency: Similar pattern to list_namespaces tool

**Key Technical Constraints:**
- Use authenticated session tokens from CanaryAuthClient
- Follow FastMCP decorator pattern established in Story 1.1
- Handle async API calls properly
- Support wildcard/pattern matching in tag names
- Return structured data format for MCP protocol
- Maintain 75%+ test coverage target

### Project Structure Notes

**Files to Create:**
- tests/integration/test_search_tags.py - Integration tests
- tests/unit/test_search_tags_tool.py - Unit tests

**Files to Extend:**
- `src/canary_mcp/server.py` - Add search_tags tool function

**Configuration Available:**
From Story 1.2:
- CANARY_SAF_BASE_URL - Base URL for Canary API
- CANARY_VIEWS_BASE_URL - Views API base URL
- Authentication via CanaryAuthClient

### Learnings from Story 1.3

**From Story 1-3-list-namespaces-tool-validation (Status: review)**

- **Tool Implementation Pattern**: FastMCP @mcp.tool() decorator
  ```python
  @mcp.tool()
  async def tool_name() -> dict[str, Any]:
      # Implementation
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

- **Response Format**: Consistent structure across tools
  ```python
  {
      "success": bool,
      "data_key": [...],  # Varies by tool
      "count": int,
      "error": str  # Optional, only on failure
  }
  ```

- **Error Handling**: Comprehensive exception catching
  - CanaryAuthError → Authentication failed
  - HTTPStatusError → API request failed with status code
  - RequestError → Network error
  - Generic Exception → Unexpected error

- **Testing Pattern**: FastMCP FunctionTool wrapper
  - Import tool: `from canary_mcp.server import tool_name`
  - Access function: `tool_name.fn()` for actual function
  - Test structure: 7 integration + 8 unit tests pattern works well

- **Files to Reuse**:
  - `src/canary_mcp/auth.py` - CanaryAuthClient already set up
  - `src/canary_mcp/server.py` - Add new tool alongside list_namespaces
  - Test infrastructure patterns from test_list_namespaces.py

[Source: stories/1-3-list-namespaces-tool-validation.md#Dev-Agent-Record]

### Testing Standards

**Integration Test Requirements:**
- Create `tests/integration/test_search_tags.py`
- Mock Canary API responses using httpx mocking pattern from Story 1.3
- Test successful tag search with multiple results
- Test search with no matches (empty array)
- Test error scenarios (auth failure, API error, malformed response)
- Verify response format includes tag details (path, name, metadata)

**Unit Test Requirements:**
- Create `tests/unit/test_search_tags_tool.py`
- Test tool function logic independently
- Test search pattern parameter validation
- Mock CanaryAuthClient interactions
- Test data transformation and formatting
- Test error handling paths

**Testing Strategy:**
- Follow pytest patterns from Stories 1.1, 1.2, and 1.3
- Use @pytest.mark.integration and @pytest.mark.unit markers
- Target 75%+ coverage
- Use pytest-asyncio for async test functions

### Canary API Reference

**Tag Search Endpoint (assumed based on typical historian APIs):**
- POST `/api/v1/browseTags` or GET `/api/v1/searchTags`
- Requires sessionToken from authentication
- Parameters:
  - searchPattern or tagFilter: string pattern to match
  - May support wildcards (* or %)
- Returns list of tags with metadata
- Response format: JSON with tags array containing {tagName, path, dataType, etc}

Note: Exact endpoint may need discovery during implementation. Refer to Canary Views Web API documentation at https://readapi.canarylabs.com/25.4/

### References

- [Source: docs/MCP Canary - Process Historical Data.md] - Case objective and API reference
- [Source: stories/1-3-list-namespaces-tool-validation.md] - Tool implementation patterns and testing strategy
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
- Added search_tags tool to server.py using @mcp.tool() decorator
- Used CanaryAuthClient.get_valid_token() for authenticated API access
- Implemented browseTags API endpoint call with search pattern and includeProperties flag
- Added input validation for empty/whitespace search patterns
- Comprehensive error handling for all failure scenarios
- Created 10 integration tests + 10 unit tests = 20 new tests for this story

**Technical Decisions:**
- Used /api/v1/browseTags endpoint for tag search
- Added search_pattern parameter validation before API call
- Async/await pattern with httpx.AsyncClient for API calls
- Error responses include success=False flag for graceful handling
- Tag response format: {success: bool, tags: list, count: int, pattern: str, error: str?}
- Tag metadata includes: name, path, dataType, description

**Test Strategy:**
- Integration tests mock httpx.AsyncClient.post responses
- Unit tests validate data parsing logic and response formats
- All edge cases covered: empty pattern, no results, malformed data, missing config, network errors, auth failures

### Completion Notes List

✅ **Story 1.4 Complete - Tag Search Tool Implemented**

**Key Accomplishments:**
- ✅ search_tags MCP tool implemented with FastMCP decorator pattern
- ✅ Accepts search_pattern parameter for tag name matching
- ✅ Integrated CanaryAuthClient for authenticated API access
- ✅ Querying Canary Views API /api/v1/browseTags endpoint
- ✅ Structured JSON response format with tag list and metadata
- ✅ Input validation for empty/whitespace patterns
- ✅ Comprehensive error handling (auth, API, network, config errors)
- ✅ 20 new tests (10 integration + 10 unit) - all passing (66/66 total)
- ✅ 86% test coverage (exceeds 75% target)
- ✅ Type-safe code (mypy --strict passes)
- ✅ Linter clean (ruff passes)

**Technical Implementation:**
1. **search_tags(search_pattern: str) async function** - MCP tool for tag search
   - Validates search_pattern is not empty or whitespace
   - Validates CANARY_VIEWS_BASE_URL configuration
   - Uses CanaryAuthClient async context manager for authentication
   - Posts to /api/v1/browseTags with sessionToken, searchPattern, includeProperties=True
   - Parses tags array and extracts name, path, dataType, description fields
   - Returns {success, tags, count, pattern, error?} format

2. **Error Handling** - Graceful failure for all scenarios
   - CanaryAuthError → Authentication failed message
   - HTTPStatusError → API request failed with status code
   - RequestError → Network error accessing API
   - Generic Exception → Unexpected error message
   - Empty pattern → Validation error with clear message

3. **Testing Coverage** - Comprehensive test suite
   - Integration: Success with results, no results, empty pattern, whitespace pattern, auth failure, API error, network error, missing config, malformed response, wildcard pattern
   - Unit: Tool registration, documentation, empty/whitespace validation, data parsing (valid/missing fields/empty tags), response formats, error message formatting

**Architecture Patterns:**
- Async context manager for CanaryAuthClient (reused from Story 1.2)
- FastMCP @mcp.tool() decorator pattern (established in Story 1.1)
- Consistent error response format across all tools (from Story 1.3)
- Proper async/await patterns with httpx
- Input parameter validation before API calls

**Next Story Prerequisites:**
- Story 1.5 will add get_tag_metadata tool using similar authenticated API patterns
- Tag search foundation ready for detailed tag metadata retrieval

### File List

**NEW:**
- tests/integration/test_search_tags.py (298 lines) - Integration tests for search_tags tool
- tests/unit/test_search_tags_tool.py (190 lines) - Unit tests for tool logic

**MODIFIED:**
- src/canary_mcp/server.py - Added search_tags tool function (120 lines added)

### Completion Notes

**Completed:** 2025-10-31
**Definition of Done:** All acceptance criteria met, code reviewed, tests passing
