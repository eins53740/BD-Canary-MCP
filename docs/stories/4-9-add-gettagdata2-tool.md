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

---

## Implementation Snapshot (2025-11-07)

- `src/canary_mcp/server.py` now exposes `get_tag_data2`, which mirrors the `read_timeseries` inputs but adds `aggregate_name`, `aggregate_interval`, and `max_size`. Responses include the same summary metadata plus the requested aggregate information so LLMs can describe results without re-querying.
- The HTTP helper (`src/canary_mcp/http_client.py`) registers `"get_tag_data2"` as a POST tool and the API reference documents when to choose it over `getTagData` (see `docs/API.md` comparison table).
- README highlights the tool in the capabilities list, and `.env.example` already carries the shared read configuration (no extra env vars required).
- Unit tests live in `tests/unit/test_get_tag_data2_tool.py`; they verify aggregate payload construction and the maxSize validation. Run with `python3 -m pytest tests/unit/test_get_tag_data2_tool.py -q -s`.
- Validation hint (`GET_TAG_DATA2_HINT`) guides LLMs to choose this tool for high-volume reads, and the default `max_size` stays at 1000 but can be overridden per call.
