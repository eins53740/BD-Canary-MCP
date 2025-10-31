# Story 1.5: Get Tag Metadata Tool & Validation

Status: drafted

## Story

As a **UNS Developer**,
I want an MCP tool to retrieve detailed metadata for specific tags,
so that I can understand tag properties, data types, and configuration before querying historical data.

## Acceptance Criteria

1. MCP tool `get_tag_metadata` implemented using FastMCP decorator pattern
2. Tool accepts tag path/name parameter to identify specific tag
3. Tool uses authenticated CanaryAuthClient from Story 1.2
4. Tool queries Canary Views API to retrieve detailed tag metadata
5. Tool returns comprehensive metadata including properties, data type, units, description
6. Error handling for API failures and invalid tag paths with clear error messages
7. Integration test validates tool returns expected metadata structure
8. Unit tests verify metadata parsing logic and error handling paths

## Tasks / Subtasks

- [ ] Task 1: Implement get_tag_metadata MCP tool (AC: #1, #2, #3, #4)
  - [ ] Create tool function with @mcp.tool() decorator in server.py
  - [ ] Add tag_path parameter to tool function
  - [ ] Integrate CanaryAuthClient to get valid session token
  - [ ] Implement API call to Canary Views tag metadata endpoint
  - [ ] Parse and format metadata response data
  - [ ] Return structured JSON response with metadata details

- [ ] Task 2: Implement error handling (AC: #6)
  - [ ] Handle authentication failures gracefully
  - [ ] Handle API connection errors
  - [ ] Handle invalid/non-existent tag paths
  - [ ] Handle malformed response data
  - [ ] Return clear error messages to tool caller
  - [ ] Log errors for debugging

- [ ] Task 3: Create integration tests (AC: #7)
  - [ ] Create tests/integration/test_get_tag_metadata.py
  - [ ] Mock Canary API responses for tag metadata
  - [ ] Test successful metadata retrieval with complete properties
  - [ ] Test invalid tag path handling
  - [ ] Test authentication failure handling
  - [ ] Test API error handling
  - [ ] Verify response format matches expected structure

- [ ] Task 4: Create unit tests (AC: #8)
  - [ ] Create tests/unit/test_get_tag_metadata_tool.py
  - [ ] Test tool registration with FastMCP
  - [ ] Test tag_path parameter handling
  - [ ] Test metadata parsing logic
  - [ ] Test error message formatting
  - [ ] Verify test coverage meets 75% target

## Dev Notes

### Technical Context

**Epic Context:**
Fifth story in Epic 1: Core MCP Server & Data Access. Builds on tag search capability (Story 1.4) to implement detailed metadata retrieval, enabling understanding of tag properties before querying historical data.

**Requirements Mapping:**
- Case Objective: Retrieve metadata about tags and their properties
- Canary Views Web API endpoint: /api/v1/getTagProperties or /api/v1/metadata
- Story 1.2 Dependency: Uses CanaryAuthClient for authenticated API access
- Story 1.4 Dependency: Works with tags discovered via search_tags tool

**Key Technical Constraints:**
- Use authenticated session tokens from CanaryAuthClient
- Follow FastMCP decorator pattern established in Story 1.1
- Handle async API calls properly
- Return comprehensive tag metadata (dataType, units, description, properties)
- Return structured data format for MCP protocol
- Maintain 75%+ test coverage target

### Project Structure Notes

**Files to Create:**
- tests/integration/test_get_tag_metadata.py - Integration tests
- tests/unit/test_get_tag_metadata_tool.py - Unit tests

**Files to Extend:**
- `src/canary_mcp/server.py` - Add get_tag_metadata tool function

**Configuration Available:**
From Story 1.2:
- CANARY_SAF_BASE_URL - Base URL for Canary API
- CANARY_VIEWS_BASE_URL - Views API base URL
- Authentication via CanaryAuthClient

### Learnings from Story 1.4

**From Story 1-4-search-tags-tool-validation (Status: review)**

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
  - `src/canary_mcp/server.py` - Add new tool alongside search_tags
  - Test infrastructure patterns from test_search_tags.py

**Key Technical Implementation:**
- search_tags tool uses /api/v1/browseTags endpoint
- Input validation for empty/whitespace parameters
- Async/await pattern with httpx.AsyncClient
- Response format: {success, tags, count, pattern, error?}
- Tag data includes: name, path, dataType, description

**Architecture Patterns:**
- Async context manager for CanaryAuthClient (Story 1.2)
- FastMCP @mcp.tool() decorator pattern (Story 1.1)
- Consistent error response format across all tools (Story 1.3)
- Input parameter validation before API calls (Story 1.4)
- Proper async/await patterns with httpx

[Source: stories/1-4-search-tags-tool-validation.md#Dev-Agent-Record]

### Testing Standards

**Integration Test Requirements:**
- Create `tests/integration/test_get_tag_metadata.py`
- Mock Canary API responses using httpx mocking pattern from Story 1.4
- Test successful metadata retrieval with complete properties
- Test invalid/non-existent tag path scenarios
- Test error scenarios (auth failure, API error, malformed response)
- Verify response format includes comprehensive metadata details

**Unit Test Requirements:**
- Create `tests/unit/test_get_tag_metadata_tool.py`
- Test tool function logic independently
- Test tag_path parameter validation
- Mock CanaryAuthClient interactions
- Test metadata transformation and formatting
- Test error handling paths

**Testing Strategy:**
- Follow pytest patterns from Stories 1.1-1.4
- Use @pytest.mark.integration and @pytest.mark.unit markers
- Target 75%+ coverage
- Use pytest-asyncio for async test functions
- 10 integration + 10 unit tests pattern (from Story 1.4)

### Canary API Reference

**Tag Metadata Endpoint (assumed based on typical historian APIs):**
- POST `/api/v1/getTagProperties` or `/api/v1/metadata`
- Requires sessionToken from authentication
- Parameters:
  - tagPath or tagName: specific tag identifier
  - May support path-based addressing
- Returns detailed tag metadata
- Response format: JSON with properties including:
  - name, path, dataType, units, description
  - min/max values, engineering units
  - update rate, quality flags
  - Additional properties specific to tag type

Note: Exact endpoint may need discovery during implementation. Refer to Canary Views Web API documentation at https://readapi.canarylabs.com/25.4/

### References

- [Source: docs/MCP Canary - Process Historical Data.md] - Case objective: "Retrieve metadata about tags and their properties"
- [Source: stories/1-4-search-tags-tool-validation.md] - Tool implementation patterns, testing strategy, and parameter validation
- [Source: stories/1-2-canary-api-authentication-session-management.md] - Authentication patterns
- [Source: stories/1-1-mcp-server-foundation-protocol-implementation.md] - FastMCP decorator pattern
- [Source: https://readapi.canarylabs.com/25.4/] - Canary Views Web API documentation

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Claude Sonnet 4.5 (us.anthropic.claude-sonnet-4-5-20250929-v1:0)

### Debug Log References

### Completion Notes List

### File List
