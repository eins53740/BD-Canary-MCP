**Story: Enhance MCP Tooling and Deployment for Production Readiness**

**As a developer/operator,**
**I want to ensure all MCP tools are thoroughly tested, new essential tools are implemented, and the deployment process is robust,**
**So that the MCP server is production-ready, reliable, and fully functional for LLM agents and users.**

---

**Acceptance Criteria:**

**1. Comprehensive Tool Test Scripts:**
*   **Given** the existing `test_mcp_tools.py` script,
*   **When** new manual test scripts are created for `get_metrics`, `get_cache_stats`, `cleanup_expired_cache`, and `get_health`,
*   **Then** all core MCP tools will have dedicated, executable test scripts in the `scripts` directory, demonstrating their functionality.

**2. Implementation of Essential New Tools:**
*   **Given** the identified need for additional Canary API functionalities,
*   **When** new tools are implemented for:
    *   `getAggregates` (to retrieve supported aggregation functions),
    *   `getEvents_Limit 10` (to handle event data),
    *   `getAssetTypes` (to retrieve available asset types),
    *   `getAssetInstances` (to retrieve instances of asset types),
*   **Then** these new tools will be integrated into the MCP server, exposed to LLM agents, and documented in `MCP_API_semantics_tags.md` (or a similar tool documentation).

**3. Full Verification of Deployment Script:**
*   **Given** the `Install-Canary-MCP.cmd` wrapper and the `deploy_canary_mcp.ps1` PowerShell script,
*   **When** `deploy_canary_mcp.ps1` is thoroughly reviewed and tested for:
    *   Handling of local stdio MCP server configurations. (Verified: The script correctly sets up the local environment for Claude Desktop to interact with the MCP server via stdio.)
    *   Handling of http remotely available MCP server configurations. (Not Met: The script does not contain logic to configure or deploy the MCP server as an HTTP service. It only supports local execution for Claude Desktop.)
    *   Robustness for non-admin users. (Mostly Met: The script avoids global system changes and uses user-specific paths. The PowerShell execution policy handling is managed by the `Install-Canary-MCP.cmd` wrapper.)
    *   Clear configuration options and error handling. (Verified: The script provides good configuration options and robust error handling with `try-catch` blocks, prerequisite checks, and informative messages.)
*   **Then** the deployment process will reliably set up the MCP server in various required configurations.

**4. CI/CD Verification of Code Coverage Policy:**
*   **Given** the project's goal of 75% minimum test coverage and the policy to warn (not fail) on lower coverage,
*   **When** the CI/CD pipeline is configured to:
    *   Run coverage reports using `uv run pytest --cov=canary_mcp --cov-report=html`.
    *   Check if coverage is below 75%.
    *   Provide a clear warning in the build output if coverage is below 75% without blocking the PR.
*   **Then** the code quality gate will be automated and transparent, ensuring adherence to coverage standards while allowing flexibility.

---

**Verification of Additional Information:**

Here's a verification of whether the provided additional information is included in this story document:

**1. MCP server resources contains this file: "\docs\aux_files\Canary Resources\Canary_Path_description_maceira.json"**
*   **Status:** Not explicitly mentioned in this document.

**2. Write API contracts information are in "docs\aux_files\Canary API"**
*   **Status:** Not present in this document. This document focuses on MCP tooling and deployment, not detailed API contracts.

**2.1 Write API Authentication:**
*   **Status:** Not present in this document.

**2.2. Canary READ API info are in: "docs\aux_files\Canary API"**
*   **Status:** Not present in this document.

**3. Definition of Done & Acceptance tests (detailed criteria)**
*   **Status:** The document has an "Acceptance Criteria" section, but the specific detailed criteria provided (e.g., "For each major section add a DoD and 2–4 acceptance tests (measurable)", "Security review passed", "Performance: 95th percentile latency < X ms", and the detailed `tag_lookup_workflow` acceptance test example) are not present here. The existing criteria are specific to the tasks of this story.

**4. Example: Concrete tag_lookup_workflow (practical pseudocode)**
*   **Status:** Not present in this document. The document mentions `tag_lookup_workflow` in the context of new tool implementation and documentation in `MCP_API_semantics_tags.md`, but does not contain the detailed pseudocode.

**5. Testing & CI (detailed aspects)**
*   **Status:** The document includes a section on "CI/CD Verification of Code Coverage Policy" with some details about running coverage reports and a 75% warning. However, other detailed aspects provided (e.g., "Local test scripts: ... add a simple harness tests/e2e/test_tag_lookup.py", "Pre-commit: black + isort + flake8 + mypy", "CI: one job for unit tests; one for integration tests... Fail CI if new code coverage decreases by >5% and warn if repo coverage <75%", "Performance tests: use locust or k6", and specific CI commands for `uv run pytest` and `python scripts/run_integration_tests.py`) are not fully present in this document.

**6. Documentation & handover**
*   **Status:** Not present in this document.

**Conclusion:**

The provided additional information is not present in this specific story document (`4-11-enhance-mcp-tooling.md`). This document is focused on the specific tasks and acceptance criteria related to enhancing MCP tooling and deployment. The additional information seems to belong to a broader epic, a project-level README, or a dedicated design/architecture document.
