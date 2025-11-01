# Story 1.3: List Namespaces Tool & Validation

Status: done

## Change Log

- **2025-10-31** - Story implemented and marked ready for review - All 4 tasks complete, 46 tests passing, 85% coverage

## Story

As a **UNS Developer**,
I want an MCP tool to list available Canary namespaces,
so that I can browse the hierarchical organization of industrial process tags.

## Acceptance Criteria

1. MCP tool `list_namespaces` implemented using FastMCP decorator pattern
2. Tool uses authenticated CanaryAuthClient from Story 1.2
3. Tool queries Canary Views API to retrieve namespace list
4. Tool returns hierarchical namespace structure in JSON format
5. Error handling for API failures with clear error messages
6. Integration test validates tool returns expected namespace structure
7. Unit tests verify tool logic and error handling paths

## Tasks / Subtasks

- [x] Task 1: Implement list_namespaces MCP tool (AC: #1, #2, #3)
  - [x] Create tool function with @mcp.tool() decorator in server.py
  - [x] Integrate CanaryAuthClient to get valid session token
  - [x] Implement API call to Canary Views namespace endpoint
  - [x] Parse and format namespace response data
  - [x] Return structured JSON response

- [x] Task 2: Implement error handling (AC: #5)
  - [x] Handle authentication failures gracefully
  - [x] Handle API connection errors
  - [x] Handle malformed response data
  - [x] Return clear error messages to tool caller
  - [x] Log errors for debugging

- [x] Task 3: Create integration tests (AC: #6)
  - [x] Create tests/integration/test_list_namespaces.py
  - [x] Mock Canary API responses for namespace data
  - [x] Test successful namespace retrieval
  - [x] Test authentication failure handling
  - [x] Test API error handling
  - [x] Verify response format matches expected structure

- [x] Task 4: Create unit tests (AC: #7)
  - [x] Create tests/unit/test_list_namespaces_tool.py
  - [x] Test tool registration with FastMCP
  - [x] Test data parsing logic
  - [x] Test error message formatting
  - [x] Verify test coverage meets 75% target

## Dev Notes

### Technical Context

**Epic Context:**
Third story in Epic 1: Core MCP Server & Data Access. Builds on authentication foundation (Story 1.2) to implement the first data access tool, enabling namespace browsing for Canary industrial process tags.

**Requirements Mapping:**
- Case Objective: Retrieve metadata about tags and their properties
- Canary Views Web API endpoint: /views or /api/v1/browseNodes
- Story 1.2 Dependency: Uses CanaryAuthClient for authenticated API access

**Key Technical Constraints:**
- Use authenticated session tokens from CanaryAuthClient
- Follow FastMCP decorator pattern established in Story 1.1
- Handle async API calls properly
- Return structured data format for MCP protocol
- Maintain 75%+ test coverage target

### Project Structure Notes

**Files to Create:**
- tests/integration/test_list_namespaces.py - Integration tests
- tests/unit/test_list_namespaces_tool.py - Unit tests

**Files to Extend:**
- `src/canary_mcp/server.py` - Add list_namespaces tool function

**Configuration Available:**
From Story 1.2:
- CANARY_SAF_BASE_URL - Base URL for Canary API
- CANARY_VIEWS_BASE_URL - Views API base URL
- Authentication via CanaryAuthClient

### Learnings from Story 1.2

**From Story 1-2-canary-api-authentication-session-management (Status: done)**

- **New Service Created**: `CanaryAuthClient` class available at `src/canary_mcp/auth.py`
  - Use `CanaryAuthClient.get_valid_token()` method for authenticated requests
  - Handles automatic token refresh (when <30s remaining)
  - Returns valid session token for API calls

- **Authentication Pattern**: Async context manager for HTTP client lifecycle
  ```python
  async with CanaryAuthClient() as client:
      token = await client.get_valid_token()
      # Use token in API requests
  ```

- **Error Handling**: Use `CanaryAuthError` exception for auth failures
  - Custom retry decorator `@retry_with_backoff` available for connection errors
  - Exponential backoff with configurable attempts (CANARY_RETRY_ATTEMPTS env var)

- **HTTP Client**: httpx.AsyncClient already in dependencies
  - Async/await patterns throughout
  - Proper context manager cleanup

- **Testing Setup**:
  - pytest with markers (@pytest.mark.unit, @pytest.mark.integration)
  - pytest-asyncio for async test functions
  - Mock httpx responses for integration tests
  - 85% coverage achieved in Story 1.2

- **Configuration**: python-dotenv for environment variable loading
  - validate_config() function integrated into server startup
  - Server validates Canary connection before starting

- **Files to Reuse**:
  - `src/canary_mcp/auth.py` - CanaryAuthClient, CanaryAuthError, validate_config
  - `src/canary_mcp/server.py` - FastMCP server instance with decorator pattern
  - Test infrastructure in tests/integration and tests/unit

[Source: stories/1-2-canary-api-authentication-session-management.md#Dev-Agent-Record]

### Testing Standards

**Integration Test Requirements:**
- Create `tests/integration/test_list_namespaces.py`
- Mock Canary API responses using httpx mocking pattern from Story 1.2
- Test successful namespace retrieval with authenticated client
- Test error scenarios (auth failure, API error, malformed response)
- Verify response format matches MCP tool output expectations

**Unit Test Requirements:**
- Create `tests/unit/test_list_namespaces_tool.py`
- Test tool function logic independently
- Mock CanaryAuthClient interactions
- Test data transformation and formatting
- Test error handling paths

**Testing Strategy:**
- Follow pytest patterns from Stories 1.1 and 1.2
- Use @pytest.mark.integration and @pytest.mark.unit markers
- Target 75%+ coverage
- Use pytest-asyncio for async test functions

### Canary API Reference

**Namespace Endpoint (assumed based on typical historian APIs):**
- GET `/api/v1/browseNodes` or similar
- Requires sessionToken from authentication
- Returns hierarchical namespace structure
- Response format: JSON with namespace hierarchy

Note: Exact endpoint may need discovery during implementation. Refer to Canary Views Web API documentation at https://readapi.canarylabs.com/25.4/

### References

- [Source: docs/MCP Canary - Process Historical Data.md] - Case objective and API reference
- [Source: stories/1-2-canary-api-authentication-session-management.md] - Authentication patterns and CanaryAuthClient usage
- [Source: stories/1-1-mcp-server-foundation-protocol-implementation.md] - FastMCP decorator pattern and server setup
- [Source: https://readapi.canarylabs.com/25.4/] - Canary Views Web API documentation

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Sonnet 4.5 (us.anthropic.claude-sonnet-4-5-20250929-v1:0)

### Debug Log References

**Implementation Plan:**
- Added list_namespaces tool to server.py using @mcp.tool() decorator
- Used CanaryAuthClient.get_valid_token() for authenticated API access
- Implemented browseNodes API endpoint call with recursive flag
- Comprehensive error handling for all failure scenarios
- Created 7 integration tests + 8 unit tests = 15 new tests for this story

**Technical Decisions:**
- Used /api/v1/browseNodes endpoint for namespace hierarchy
- Async/await pattern with httpx.AsyncClient for API calls
- Error responses include success=False flag for graceful handling
- Namespace response format: {success: bool, namespaces: list, count: int, error: str?}

**Test Strategy:**
- Integration tests mock httpx.AsyncClient.post responses
- Unit tests validate data parsing logic and response formats
- All edge cases covered: empty response, malformed data, missing config, network errors

### Completion Notes

**Completed:** 2025-10-31
**Definition of Done:** All acceptance criteria met, code reviewed, tests passing

### Completion Notes List

✅ **Story 1.3 Complete - Namespace Browsing Tool Implemented**

**Key Accomplishments:**
- ✅ list_namespaces MCP tool implemented with FastMCP decorator pattern
- ✅ Integrated CanaryAuthClient for authenticated API access
- ✅ Querying Canary Views API /api/v1/browseNodes endpoint
- ✅ Structured JSON response format with namespace paths
- ✅ Comprehensive error handling (auth, API, network, config errors)
- ✅ 15 new tests (7 integration + 8 unit) - all passing (46/46 total)
- ✅ 85% test coverage (exceeds 75% target)
- ✅ Type-safe code (mypy --strict passes)
- ✅ Linter clean (ruff passes)

**Technical Implementation:**
1. **list_namespaces() async function** - MCP tool for namespace browsing
   - Validates CANARY_VIEWS_BASE_URL configuration
   - Uses CanaryAuthClient async context manager for authentication
   - Posts to /api/v1/browseNodes with sessionToken, nodeId="", recursive=True
   - Parses nodes array and extracts path fields
   - Returns {success, namespaces, count, error?} format

2. **Error Handling** - Graceful failure for all scenarios
   - CanaryAuthError → Authentication failed message
   - HTTPStatusError → API request failed with status code
   - RequestError → Network error accessing API
   - Generic Exception → Unexpected error message

3. **Testing Coverage** - Comprehensive test suite
   - Integration: Success, empty response, auth failure, API error, network error, missing config, malformed response
   - Unit: Tool registration, documentation, data parsing (valid/missing/empty nodes), response formats

**Architecture Patterns:**
- Async context manager for CanaryAuthClient (reused from Story 1.2)
- FastMCP @mcp.tool() decorator pattern (established in Story 1.1)
- Consistent error response format across all tools
- Proper async/await patterns with httpx

**Next Story Prerequisites:**
- Story 1.4 will add search_tags tool using similar authenticated API patterns
- Namespace browsing foundation ready for tag discovery tools

### File List

**NEW:**
- tests/integration/test_list_namespaces.py (221 lines) - Integration tests for namespace tool
- tests/unit/test_list_namespaces_tool.py (133 lines) - Unit tests for tool logic

**MODIFIED:**
- src/canary_mcp/server.py - Added list_namespaces tool function (78 lines added)
