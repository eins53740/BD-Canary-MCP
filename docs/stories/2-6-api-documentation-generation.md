# Story 2.6: API Documentation Generation

As a **Phase 2 User (Plant Engineer)**,
I want comprehensive API documentation for all MCP tools,
So that I can understand available tools and how to use them without developer assistance.

**Acceptance Criteria:**
1. API documentation auto-generated from MCP tool definitions
2. Documentation includes: tool name, description, parameters, return types, examples
3. Documentation format: Markdown for human reading, JSON schema for tooling
4. Each tool documented with: purpose, use cases, parameter details, response format
5. Error codes and troubleshooting guide included
6. Documentation published to docs/ folder and README
7. Examples show real Canary queries for common use cases
8. Documentation versioned with MCP server releases
9. Validation test: `test_documentation.py` confirms docs generated and complete

**Prerequisites:** Story 2.5 (multi-site configuration)
