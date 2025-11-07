# Story 4.9 — Add getTagData2 Tool

**User Story:** As a developer, I want to use the `getTagData2` API endpoint to retrieve historical data from Canary Historian, so that I can leverage its improved performance and simplified pagination.

**Context & Constraints:**

*   The `getTagData2` endpoint is a newer, more efficient alternative to `getTagData`.
*   The primary advantage of `getTagData2` is its ability to handle a larger `maxSize`, reducing the need for continuation tokens and simplifying data retrieval.
*   To avoid breaking existing tools and workflows, a new tool (`get_tag_data2`) will be created instead of modifying the existing `get_tag_data` tool.
*   The new tool must be thoroughly documented, including its parameters, usage, and the benefits it provides over `getTagData`.

**Acceptance Criteria (Checklist):**

*   A new tool, `get_tag_data2`, is created to interact with the `getTagData2` API endpoint.
*   The tool supports all relevant parameters, including `tags`, `startTime`, `endTime`, `aggregateName`, `aggregateInterval`, and `maxSize`.
*   The tool is documented in the project's tool manifest and has clear usage instructions for LLMs.
*   Unit tests are created for the new tool, covering both raw and aggregated data retrieval.
*   A comparison of `getTagData` and `getTagData2` is added to the API documentation (`docs/API.md`).

**Validation:**

*   Run unit tests for the `get_tag_data2` tool to ensure it functions correctly.
*   Manually test the tool with a large `maxSize` to verify that it returns a large dataset without requiring pagination.
*   Review the updated API documentation to ensure it clearly explains the differences between `getTagData` and `getTagData2`.

**Deliverables:**

*   New tool: `get_tag_data2`
*   Updated documentation: `docs/API.md` and tool manifest.
*   Unit tests for the new tool.
