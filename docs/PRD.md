# BD-hackaton-2025-10 Product Requirements Document (PRD)

**Author:** BD
**Date:** 2025-10-30
**Project Level:** 2
**Target Scale:** 5-15 stories across 1-2 epics

---

## Goals and Background Context

### Goals

1. **Enable LLM-Powered Operational Intelligence** - Provide seamless, standardized access to Canary Historian plant data through MCP protocol, allowing engineers and analysts to ask natural language questions and receive real-time insights
2. **Accelerate Data-Driven Decision Making** - Reduce time-to-insight from hours to minutes (95%+ time savings), enabling 3-5x increase in plant data analysis frequency
3. **Establish Universal Canary MCP Integration** - Create production-ready, reusable MCP server that works with any Canary deployment worldwide, supporting the 6-site rollout and future expansion

### Background Context

Industrial facilities implementing Canary Historian currently lack a standardized way to connect LLM-powered applications to operational data. Today, engineers and data analysts must manually export data from the Canary Views Web API and import it into LLM tools—a process that takes hours per analysis and is impractical for real-time operational intelligence.

With 6 Canary sites planned for deployment (1 POC complete, 5 upcoming), establishing a standardized MCP integration pattern now prevents technical debt multiplication and enables consistent LLM-powered insights across all facilities. This initiative aligns with the company's broader digital transformation and AI adoption strategy, positioning the organization to "catch the AI train" for long-term sustainability and competitiveness.

---

## Requirements

### Functional Requirements

**Phase 1: Setup & Deployment**

**FR012: Automated Deployment**
- System shall support Docker containerization with automated deployment scripts and configuration management for multi-site rollout

**FR008: Multi-Site Configuration**
- System shall support configuration for multiple Canary deployments via environment variables or config files, enabling universal deployment to any Canary Historian instance worldwide without code changes

**FR017: Configuration Validation**
- System shall provide configuration validation tool that verifies Canary connection, credentials, and deployment setup before accepting queries

**FR007: Canary API Authentication**
- System shall authenticate with Canary Views Web API using token-based authentication, managing session tokens with automatic refresh and secure credential handling (environment variables)

**Phase 2: Discovery & Exploration**

**FR001: MCP Protocol Implementation**
- System shall implement Model Context Protocol (MCP) standard, exposing tools that LLM clients can invoke via MCP-compatible interfaces (Claude Desktop, Continue, etc.)

**FR002: Namespace Discovery Tool**
- System shall provide `list_namespaces` MCP tool enabling top-level discovery of sites, assets, and namespaces available in Canary Historian

**FR003: Tag Search Tool**
- System shall provide `search_tags` MCP tool supporting tag search by name/regex with optional metadata filters (unit, type) to enable intelligent tag inference from natural language queries

**FR004: Tag Metadata Retrieval Tool**
- System shall provide `get_tag_metadata` MCP tool returning tag properties including units, data type, descriptions, min/max values, and sampling mode

**Phase 3: Data Access & Querying**

**FR014: Query Parsing and Validation**
- System shall parse natural language time expressions (e.g., "last week", "yesterday", "past 24 hours") and convert to absolute date/time ranges compatible with Canary API format

**FR005: Timeseries Data Access Tool**
- System shall provide `read_timeseries` MCP tool retrieving raw historical samples with paging support, quality flags, and configurable time windows

**FR015: Caching Layer**
- System shall implement caching layer for frequently accessed tag metadata and timeseries data to achieve <5 second median query response time and reduce Canary API load

**FR016: Connection Pooling**
- System shall maintain connection pool to Canary API with configurable pool size to optimize performance for concurrent requests

**FR020: Empty Result Handling**
- System shall distinguish between empty result sets (no data for time range), missing tags (tag not found), and errors, providing clear messaging for each scenario

**FR025: Data Quality Reporting**
- System shall surface data quality flags from Canary to users/LLMs, including warnings for incomplete data, sensor failures, or quality issues affecting query results

**Phase 4: Reliability & Operations**

**FR006: Server Health Check Tool**
- System shall provide `get_server_info` MCP tool returning Canary server health, version, time zones, and supported aggregation capabilities

**FR011: Health Check Endpoint**
- System shall expose HTTP health check endpoint for deployment validation and container orchestration monitoring

**FR009: Error Handling and Resilience**
- System shall implement retry logic with exponential backoff (3-5 retries), circuit breaker pattern for cascading failure protection, and graceful degradation with meaningful error messages to LLM clients

**FR010: Request Logging and Metrics**
- System shall log all requests/responses for debugging and collect metrics including query latency, success/failure rates, Canary API response times, and cache hit/miss rates

**FR021: Query Transparency**
- System shall log and optionally return to user which specific tags were queried, enabling users to verify LLM tag inference accuracy

**Phase 5: Quality & User Support**

**FR013: Comprehensive Testing**
- System shall include unit tests (95%+ coverage), integration tests with Canary API (contract tests), and mock-based tests for offline development

**FR018: API Documentation**
- System shall auto-generate API documentation for all MCP tools including parameter specifications, return types, and usage examples

**FR019: Example Query Library**
- System shall include comprehensive example query library demonstrating common use cases (temperature trends, cross-tag comparisons, anomaly detection patterns) for Phase 2 user self-service

### Non-Functional Requirements

**NFR001: Performance**
- System shall achieve <5 second median query response time for typical timeseries data queries
- System shall support 25 concurrent users without performance degradation
- System shall maintain 95th percentile query response time <10 seconds

**NFR002: Reliability & Availability**
- System shall target 99.5% uptime for MCP server availability
- System shall implement automatic recovery from transient Canary API failures
- System shall provide graceful degradation when Canary API is unavailable (cached data, clear error messages)

**NFR003: Quality Assurance**
- System shall maintain minimum 75% test coverage across codebase
- System shall achieve 85%+ unit test pass rate
- System shall include integration tests validated against live Canary API

---

## User Journeys

### Journey 1: UNS Developer Validates Plant Data During Site Rollout

**Persona:** Carlos, UNS OT Developer validating Canary deployment at new cement plant site

**Goal:** Verify that Canary Historian is correctly capturing and storing plant data from kiln operations

**Scenario:** Carlos has just completed Canary Historian setup at the Maceira plant and needs to validate data availability before handing off to operations team.

**Steps:**

1. **Setup & Configuration**
   - Carlos deploys the Universal Canary MCP server via Docker on his laptop
   - Configures environment variables: Canary API URL, authentication token, historian name
   - Runs configuration validation tool - receives confirmation: "✓ Connected to Canary API - 3 namespaces found"

2. **Discover Data Structure**
   - Carlos opens Claude Desktop (connected to MCP server)
   - Asks: "What namespaces are available in this Canary instance?"
   - MCP server returns: `Maceira`, `Maceira.Cement`, `Maceira.Cement.Kiln6`
   - Carlos confirms UNS namespace structure matches design

3. **Validate Tag Discovery**
   - Carlos asks: "Show me all temperature tags for Kiln 6"
   - MCP server searches tags with filter: `namespace=Maceira.Cement.Kiln6`, `type=temperature`
   - Returns: 8 temperature tags (inlet, outlet, zone1-6)
   - Carlos verifies expected sensors are present

4. **Query Historical Data**
   - Carlos asks: "Show me Kiln 6 outlet temperature for the past 24 hours"
   - MCP server parses "past 24 hours", queries correct tag: `Maceira.Cement.Kiln6.Temperature.Outlet`
   - Returns timeseries data: 1,440 samples (1-minute intervals), quality flags all "Good"
   - Claude analyzes data: "Temperature ranged 850-920°C with normal variance"

5. **Validate Data Quality**
   - Carlos notices data quality flags in results
   - Asks: "Were there any data quality issues in the past week?"
   - MCP server reports: "3 tags had brief sensor failures on 2025-10-28, totaling 15 minutes downtime"
   - Carlos documents finding for operations team awareness

6. **Success Confirmation**
   - Carlos verifies: ✓ Namespace structure correct, ✓ All expected tags present, ✓ Data collecting continuously, ✓ Quality monitoring active
   - Updates deployment checklist: "Maceira site validation complete - ready for Phase 2 users"
   - Shares example queries with plant engineers for their upcoming onboarding

**Outcome:** Carlos completes site validation in 30 minutes instead of 4+ hours of manual API testing. Confident to proceed with remaining 5 site deployments using same pattern.

---

## UX Design Principles

### Core UX Principles

**1. Invisible Infrastructure**
- MCP server operates transparently - users interact through familiar LLM interfaces (Claude, ChatGPT)
- Success = users forget they're using an MCP server and focus on asking plant data questions

**2. Clear Feedback & Transparency**
- Error messages optimized for both LLMs (machine-readable) and humans (plain language with remediation steps)
- Query transparency: Users can see which tags were queried and why (FR021)
- Data quality warnings surfaced prominently when present

**3. Configuration Simplicity**
- Zero-configuration defaults for common scenarios
- Environment variable-based setup (no complex config files for basic use)
- Validation tools provide immediate feedback on setup correctness
- Non-admin users can deploy and run MCP server without elevated privileges

**4. Progressive Disclosure**
- Basic queries work out-of-the-box (simple tag + time range)
- Advanced features discoverable through documentation and examples
- Power users can access lower-level controls when needed

---

## User Interface Design Goals

### Primary Interface: Natural Language via LLM

**Platform:** Command-line LLM clients (Claude Desktop, Continue, ChatGPT with MCP support)

**Interaction Model:**
- Users ask questions in natural language about plant data
- MCP server provides tools to LLM for data retrieval
- LLM interprets results and presents insights conversationally

**Key Design Constraints:**
- No graphical UI in MVP (Phase 1)
- All interaction through text-based LLM chat
- Documentation and examples serve as "UI" for learning system capabilities

### Secondary Interfaces

**Configuration & Setup:**
- Docker command-line deployment (no admin/root privileges required)
- User-space installation - runs under non-admin user accounts
- Environment variables or simple YAML config file
- Validation script with terminal output (success/error indicators)

**Monitoring & Diagnostics:**
- Health check HTTP endpoint (JSON response)
- Log file output (structured JSON logs for parsing)
- Metrics endpoint (Prometheus format for visualization tools)

---

## Epic List

### Epic 1: Core MCP Server & Data Access
**Estimated Stories:** 9-11 stories

**Goal:** Establish production-ready MCP server with 5 core tools (list_namespaces, search_tags, get_tag_metadata, read_timeseries, get_server_info) enabling basic plant data queries through LLM interfaces, with validation test scripts for each capability.

**Epic Completion Criteria:** User can run validation test suite that demonstrates all 5 MCP tools working against live Canary API with successful happy path results.

**Key Deliverables:**
- MCP server with 5 core tools operational
- Canary API authentication and session management
- User-runnable validation test scripts for each tool (happy path)
- Test data fixtures for offline development
- Basic error handling and logging
- Docker deployment package
- Local development environment setup

---

### Epic 2: Production Hardening & User Enablement
**Estimated Stories:** 6-8 stories

**Goal:** Add production-grade reliability, performance optimization (caching, connection pooling), comprehensive documentation, and deployment automation with performance validation to support 6-site rollout.

**Epic Completion Criteria:** User can run performance validation script that confirms <5s median query response time and error handling with retry logic demonstrates resilience.

**Key Deliverables:**
- Performance optimization (caching layer, connection pooling)
- Advanced error handling and resilience (retry logic, circuit breaker)
- Performance validation test suite with baseline benchmarking
- Multi-site configuration management
- Comprehensive documentation and example query library
- Configuration validation tools
- Deployment guide for site rollout

---

### Epic 3: Semantic Tag Search
**Estimated Stories:** 5 stories

**Goal:** Introduce a new "get_tag_path" MCP tool that uses natural language processing to find the most likely tag path from a user's descriptive query, making the server more intuitive and user-friendly.

**Epic Completion Criteria:** A user can provide a natural language query like "average temperature for the kiln shell in section 15" to the `get_tag_path` tool and receive the correct, full tag path as a result.

**Key Deliverables:**
- `get_tag_path` MCP tool with semantic search capabilities
- Tag ranking and scoring algorithm
- Integration with `getTagProperties` for more accurate results
- Caching strategy for the new tool
- Comprehensive testing and validation

**Deferred to Post-MVP (Phase 1.5):**
- Error injection testing framework (manual error testing in MVP)
- Automated multi-site deployment validation scripts (manual validation for sites 2-6)
- Comprehensive deployment runbook with troubleshooting (basic guide in MVP, expanded based on lessons learned)

---

**Total Estimated Stories:** 15-19 stories across 2 epics

**MVP Validation Approach:** Core functionality validated with automated tests; advanced validation scenarios (error injection, multi-site automation) validated manually during initial rollout, then automated based on real-world learnings.

### Epic 4: MCP Server Enhancements & Prompt/Resource Optimization
**Estimated Stories:** 8 stories

**Goal:** Strengthen brownfield readiness by tightening HTTP method usage, formalizing LLM prompt workflows, enforcing response-size limits, improving tool coverage, and documenting RAG feasibility — without disrupting existing Canary deployments.

**Epic Completion Criteria:**
- All MCP tools follow REST semantics (GET for idempotent lookups, POST for complex/multi-parameter requests) and enforce ≤1MB response payloads per invocation.
- Prompt workflows (`tag_lookup_workflow`, `timeseries_query_workflow`) documented with inputs/outputs and clarifying-question steps; reproducible from examples.
- CLI validation script exercises core and new tools end-to-end.
- Write operations are restricted to approved test datasets only (e.g., `Test/Maceira`, `Test/Outao`).
- RAG feasibility documented using existing on-disk resources; no new infra required.

**Key Deliverables:**
- Method-usage matrix for all tools and error-handling patterns
- Size-limit guardrails across tools (≤1MB per LLM request)
- Updated prompt workflow docs and examples
- New/expanded tools (e.g., `getTagProperties`, `getAggregates` basics) with usage guidance
- Telemetry write tool gated to test datasets
- RAG feasibility note and resource index

> **Note:** Detailed epic breakdown with full story specifications is available in [epics.md](./epics.md)

---

## Out of Scope

### Deferred MCP Tools (Phase 2)
- **aggregate_timeseries** - Server-side aggregation and rollups (avg, min, max, percentiles, time-weighted averages)
- **interpolate_timeseries** - Data alignment and interpolation for correlation analysis
- **export_timeseries** - Structured export to CSV/Parquet formats

**Rationale:** LLMs can perform basic aggregation on retrieved data for MVP. Server-side aggregation adds complexity without blocking core validation use cases.

### Advanced Features (Future Phases)
- **Real-time streaming subscriptions** - Long-lived connections for continuous data monitoring
- **Multi-tenant support** - User-level permissions and role-based access control
- **Advanced caching strategies** - Intelligent cache warming, predictive pre-fetching
- **Cross-site data federation** - Unified queries aggregating data across all 6 sites simultaneously
- **Machine learning-based tag recommendation** - AI-powered tag discovery from natural language
- **GraphQL API alternative** - Alternative query interface beyond MCP protocol
- **Web UI dashboard** - Graphical interface for non-LLM users

### Security Features (Deferred to Phase 2)
- **Data encryption at rest** - Encrypted cache storage
- **Advanced certificate management** - Custom CA certificates, mutual TLS
- **Enterprise SSO integration** - Active Directory, LDAP, SAML authentication
- **Audit logging for compliance** - Detailed access logs for regulatory requirements

### Integration Capabilities (Not in Current Scope)
- **Other historian platforms** - OSIsoft PI, InfluxDB, Grafana integrations (focus remains exclusively on Canary)
- **UNS/MQTT direct integration** - Direct Sparkplug B or MQTT broker connectivity (Canary API is the sole data source)
- **ERP/MES system integration** - SAP, manufacturing execution systems
- **External alerting systems** - PagerDuty, email notifications, SMS alerts

### Operational Features (Post-MVP)
- **Cloud-hosted centralized deployment** - Phase 1 uses local deployment only
- **Advanced monitoring dashboards** - Grafana, Prometheus integration (basic metrics endpoint provided)
- **Automated scaling and load balancing** - Kubernetes orchestration
- **Backup and disaster recovery** - Automated backup procedures
- **A/B testing framework** - Query optimization experiments

### Documentation and Training (Minimal in MVP)
- **Video tutorials and training materials** - Text documentation only in MVP
- **Interactive onboarding wizard** - Users follow written setup guide
- **Community forum or support portal** - Direct user support only during validation phase

### Clear Boundaries
**This project is NOT:**
- A replacement for existing Canary Views interface (complementary tool)
- A data historian itself (relies entirely on Canary Historian)
- A general-purpose industrial data platform (Canary-specific only)
- An autonomous AI agent system (requires human-in-the-loop via LLM chat)

**Scope Creep Prevention:** Any feature requests during implementation must be evaluated against 3-month timeline and MVP success criteria. New capabilities should be captured for Phase 1.5 or Phase 2 planning.
