# Story 3.1: `get_tag_path` Tool Foundation

As a **Plant Engineer**,
I want a new MCP tool called `get_tag_path` that accepts a natural language description,
So that I can start the process of finding a tag without knowing any part of its path.

**Acceptance Criteria:**
1. New `get_tag_path` MCP tool is created in `server.py`.
2. Tool accepts a single string argument `description`.
3. The tool performs an initial search using the existing `search_tags` logic.
4. The tool extracts and cleans keywords from the input description (e.g., removes stop words).
5. A basic list of candidate tags is returned if any are found.
6. Validation test: `test_get_tag_path_foundation.py` confirms the tool can be called and returns initial candidates.

**Prerequisites:** Epic 1 complete.
