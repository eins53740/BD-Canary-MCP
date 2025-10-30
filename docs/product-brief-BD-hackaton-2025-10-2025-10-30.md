# Product Brief: BD-hackaton-2025-10

**Date:** 2025-10-30
**Author:** BD
**Status:** Draft for PM Review

---

## Executive Summary

**The Universal Canary MCP Server** enables LLM-powered operational intelligence for industrial facilities by providing seamless access to Canary Historian plant data through the Model Context Protocol. This production-ready MCP server wraps the Canary Views Web API into standardized tools, allowing engineers and analysts to ask natural language questions and receive real-time insights in seconds instead of hours.

**The Problem:** Industrial facilities deploying Canary Historian lack a standardized way to connect LLM applications to operational data. Today's manual export/import workflows take hours per analysis and are impractical for real-time decision-making. With 6 Canary sites planned for deployment, the lack of a standardized integration pattern creates unsustainable maintenance burden and blocks the company's AI adoption initiative.

**The Solution:** The first purpose-built MCP server for Canary Historian, designed as a universal solution for any Canary deployment worldwide. Five core MCP tools (namespace discovery, tag search, metadata retrieval, timeseries data access, server health) enable intelligent tag inference from natural language queries, delivering structured plant data to LLMs for analysis and correlation.

**Target Users:** Phase 1 focuses on UNS OT developers validating the 6-site Canary rollout. Phase 2 expands to dozens of plant engineers, data analysts, and operational staff across all sites. The universal design enables global adoption by any organization using Canary Historian across manufacturing, utilities, food processing, and heavy industry.

**Business Impact:** Reduces time-to-insight from hours to minutes (95%+ time savings), enables 3-5x increase in plant data analysis frequency, and contributes to measurable EBITDA improvements through data-driven operational optimizations. Positions company as industrial AI thought leader while future-proofing operations by "catching the AI train" for long-term sustainability and competitiveness.

---

## Problem Statement

**Current State:**

Industrial facilities implementing Canary Historian lack a standardized way to connect LLM-powered applications to their operational data. Today, engineers and data analysts must manually export data from the Canary Views Web API and import it into LLM tools - a process that takes hours per analysis and is impractical for real-time or daily operational intelligence.

**Quantifiable Pain Points:**

- **Integration overhead:** Each LLM use case requires custom API integration work (hours of development per use case)
- **Manual workflow bottleneck:** Export/import cycles prevent real-time analysis and block time-sensitive operational questions
- **Scaling challenge:** With 6 Canary sites planned for deployment (1 POC complete, 5 upcoming), the lack of a standardized integration approach will create unsustainable maintenance burden
- **API friction:** Canary Views Web API has documentation gaps and potentially non-standard REST patterns, increasing integration complexity

**Business Impact:**

Without a standardized MCP server, operational teams cannot efficiently ask critical questions like:
- "Show me temperature trends for Maceira plant - Kiln 6 last week"
- "Compare production efficiency across all sites"
- "Our kiln 5 had a bad month with 10% lower production - tell me why"
- "Alert me to anomalies in real-time"

**Why Now:**

The 6-site Canary rollout is underway, and establishing a standardized MCP integration pattern now - during the POC phase - prevents technical debt multiplication and enables consistent LLM-powered operational intelligence across all facilities.

---

## Proposed Solution

**Core Approach:**

A production-ready MCP server that wraps the Canary Views Web API into standardized MCP tools, enabling LLMs to query industrial plant data as easily as they query any other tool. This is the first purpose-built MCP server for Canary Historian, filling a critical gap in the industrial AI ecosystem.

**How It Works:**

Plant engineers and data analysts connect their LLM interface (Claude, ChatGPT, or other MCP-compatible tools) to the Canary MCP server. They can then ask complex operational questions in natural language, and the MCP server provides a comprehensive set of tools:

**Discovery & Metadata Tools:**
- `list_namespaces` - Top-level discovery of sites/assets/namespaces; lets clients browse what data exists
- `search_tags` - Find tags quickly by name/regex and optional metadata filters (unit, type)
- `get_tag_metadata` - Fetch properties like units, data type, descriptions, min/max, sampling mode per tag

**Data Access Tools:**
- `read_timeseries` - Retrieve raw historical samples (with paging and quality flags) over a time window
- `aggregate_timeseries` - Server-side rollups/resampling (avg, min, max, count, pXX, TWAvg) on intervals
- `interpolate_timeseries` - Return values aligned to provided timestamps (linear/step) for joins/plots

**Utility Tools:**
- `get_server_info` - Health/capabilities: server version, time zones, supported aggregates/features
- `export_timeseries` - Convenience export of queried data to CSV/Parquet with a download handle

The MCP server handles authentication, data extraction, format conversion, and structured delivery to the LLM for analysis.

**Key Differentiators:**

- **First-of-its-kind:** The first useful, production-ready MCP server specifically designed for Canary Historian access
- **Seamless LLM integration:** Eliminates manual export/import workflows - LLMs access plant data as naturally as they access web search or code execution tools
- **Complex query support:** Enables sophisticated analysis beyond simple data retrieval - correlations, anomaly detection, cross-site comparisons, root cause analysis
- **Standardized pattern:** Leverages proven MCP protocol patterns, reducing custom integration work to zero for end users

**Success Factors:**

- **MCP protocol maturity:** Building on established Model Context Protocol standards with proven implementations across other domains
- **Proven architecture patterns:** Following patterns from successful MCP servers in other industries
- **API validation approach:** Proactively validates Canary API robustness and documentation quality, identifying and working around any non-standard REST patterns

**User Experience Vision:**

An engineer opens Claude and asks: *"Our kiln 5 had a bad month with 10% lower production - tell me why."*

The MCP server:
1. Authenticates seamlessly with Canary
2. Retrieves relevant historical data (temperatures, pressures, production rates) using `search_tags`, `get_tag_metadata`, and `read_timeseries` tools
3. Delivers structured data to the LLM
4. LLM correlates patterns, identifies anomalies, and provides actionable insights

The engineer gets a comprehensive analysis in seconds - no exports, no manual data wrangling, no custom code.

---

## Target Users

### Primary User Segment (Phase 1: Implementation & Validation)

**UNS OT Developers**

**Profile:**
- Operational Technology developers implementing Canary Historian within Unified Namespace (UNS) architecture
- Technical experts responsible for validating historian setup and data flows across 6 sites
- Currently working on POC at one site, preparing for 5 additional site rollouts

**Current Workflow:**
- Manual API testing and data validation
- Custom scripts to verify Canary data integrity and UNS integration
- Direct Canary Views API calls for troubleshooting

**Specific Pain Points:**
- Need rapid validation that historian is capturing correct data from industrial equipment
- Must verify UNS architecture correctly maps plant tags to Canary namespace structure
- Time-consuming manual testing of data queries across multiple tags and time ranges
- Difficulty spotting data quality issues or missing tags without comprehensive tooling

**Goals:**
- Validate Canary historian implementation is correct and complete
- Test data availability, quality, and consistency across namespaces
- Identify configuration gaps or data flow issues early
- Build confidence in the platform before handing off to operational users
- Establish patterns for remaining 5 site deployments

### Primary User Segment (Phase 2: Production Operations)

**Plant Engineers & Process Engineers**

**Profile:**
- On-site engineers managing day-to-day plant operations at cement/industrial facilities
- Responsible for troubleshooting production issues, optimizing processes, ensuring quality output
- Limited time for data analysis - need fast answers to operational questions

**Current Workflow:**
- Request data exports from IT or data team (hours of delay)
- Review static dashboards that may not answer specific questions
- Manual investigation of production issues using limited historical context

**Specific Pain Points:**
- Cannot get timely answers to urgent operational questions ("Why did kiln 5 underperform?")
- Data access requires IT intermediaries or manual export workflows
- Lack of historical context when troubleshooting real-time issues
- Cannot easily correlate multiple variables across equipment

**Goals:**
- Rapid troubleshooting of production anomalies and equipment issues
- Understand root causes of efficiency drops or quality problems
- Make data-driven decisions about process adjustments
- Identify optimization opportunities across kilns/equipment

**Data Analysts**

**Profile:**
- Analysts supporting multiple plant sites with performance reporting and trend analysis
- Build regular reports on production efficiency, quality metrics, equipment performance
- More technical than plant engineers but not developers

**Current Workflow:**
- Manual data exports from Canary to Excel/BI tools
- Custom queries for each analysis request
- Time-consuming data preparation before analysis can begin

**Specific Pain Points:**
- Hours spent on data extraction and preparation vs. actual analysis
- Cannot perform real-time or near-real-time analysis
- Difficult to perform cross-site comparisons without extensive manual work
- Ad-hoc requests from management require significant manual effort

**Goals:**
- Streamline data access for regular reporting
- Enable ad-hoc analysis without manual data wrangling
- Perform cross-site performance comparisons efficiently
- Deliver faster insights to management and plant teams

### Secondary User Segment

**Plant Managers & Company Employees**

**Profile:**
- Management reviewing operational KPIs and making strategic decisions
- Broader employee base with occasional need for plant data insights
- Less technical, consume insights rather than perform deep analysis

**Usage:**
- Ask high-level questions about plant performance
- Review summaries and insights generated by primary users
- Occasional exploration of specific metrics or trends

**Value:**
- Democratized access to plant data through natural language queries
- No technical barriers to getting operational insights
- Self-service answers without depending on analysts or engineers

---

## Goals and Success Metrics

### Business Objectives

**Phase 1: Implementation & Validation (0-3 months)**
- **Historian validation:** Successfully query real-time and historical plant data from Canary via MCP server with 99%+ reliability
- **POC completion:** Complete validation at initial site, demonstrating all 8 MCP tools functioning correctly
- **Multi-site rollout:** Deploy MCP server to remaining 5 sites within 3 months of POC completion
- **API assessment:** Document Canary API quality, gaps, and any workarounds needed for production use

**Phase 2: Operational Excellence (3-12 months)**
- **User adoption:** Achieve 30-50 active users (plant engineers, data analysts) across 6 sites within 6 months
- **Analysis velocity:** Increase frequency of plant data analysis by 3-5x through reduced friction
- **Operational efficiency:** Reduce time-to-insight from hours to minutes, enabling more proactive decision-making
- **Business impact:** Contribute to measurable EBITDA improvement through data-driven operational optimizations (equipment efficiency gains, quality improvements, reduced downtime)

**Technical Objectives**
- **Production readiness:** Deliver production-grade MCP server with comprehensive error handling, retry logic, rate limiting
- **Performance:** Sub-5 second response time for typical queries (median), handle concurrent multi-user access
- **Reliability:** 99.5% uptime for MCP server availability
- **Scalability:** Support 6-site deployment with centralized or distributed architecture as needed

### User Success Metrics

**Adoption Metrics:**
- Active weekly users: 30-50 users within 6 months post-deployment
- Query volume: 100+ successful MCP queries per day across all sites
- User retention: 80%+ of users continue using MCP server month-over-month

**Efficiency Metrics:**
- **Time savings per analysis:** Reduce from 2-4 hours (manual export/import) to <5 minutes (LLM query)
- **Report generation speed:** Save 3-5 hours per report for data analysts
- **Ad-hoc query capability:** Enable plant engineers to answer urgent operational questions in real-time vs. waiting hours/days
- **IT request reduction:** Decrease manual data export requests to IT by 70%+

**Quality & Satisfaction Metrics:**
- Query success rate: 95%+ of MCP queries return valid, usable data
- User satisfaction: 4+ out of 5 rating for ease of use and data access speed
- LLM answer accuracy: Users find LLM insights actionable and accurate 80%+ of the time
- Repeat usage: Users return to MCP-powered queries as primary method for plant data access

### Key Performance Indicators (KPIs)

**Top 5 KPIs to Track:**

1. **Active Users per Week** - Number of unique users making MCP queries (target: 30-50 across 6 sites)

2. **Time-to-Insight** - Median time from question asked to actionable answer received (target: <5 minutes vs. current hours)

3. **Query Success Rate** - Percentage of MCP queries that successfully return data (target: 95%+)

4. **Analysis Frequency** - Number of plant data analyses conducted per week (target: 3-5x increase)

5. **EBITDA Impact** - Measured operational improvements attributable to data-driven insights (tracked via specific efficiency gains, quality improvements, downtime reduction)

**Secondary KPIs:**
- Sites deployed: 6 of 6 (completion metric)
- MCP server uptime: 99.5%+
- IT data request volume: 70% reduction
- User satisfaction score: 4+/5

---

## Strategic Alignment and Financial Impact

### Financial Impact

**Investment Profile:**
- Development effort: Part of existing digital transformation budget
- Timeline: 3-month MVP development aligned with 6-site Canary rollout
- Incremental cost: Minimal - leverages existing UNS team and infrastructure

**Operational Cost Savings:**
- **Time savings:** 2-4 hours per analysis reduced to <5 minutes = 95%+ time reduction
- **Report efficiency:** 3-5 hours saved per report for data analysts
- **IT request reduction:** 70% reduction in manual data export requests, freeing IT resources
- **Multi-site leverage:** Cost avoidance across 6 sites by standardizing data access (vs. 6 custom integrations)

**EBITDA Impact Drivers:**
- **Plant optimization:** Data-driven decisions enable faster identification of efficiency opportunities (equipment optimization, quality improvements, energy reduction)
- **Reduced downtime:** Faster root cause analysis of production issues minimizes production losses
- **Cross-site learning:** Easy comparison across 6 sites enables best practice identification and replication
- **Proactive vs. reactive:** Real-time LLM-powered analysis enables predictive maintenance and proactive interventions

**Return on Investment:**
- Low development cost (existing team, open-source foundation)
- High leverage (6 sites × dozens of users × daily usage)
- Multiplier effect: More analysis → Better insights → Continuous improvement culture

### Company Objectives Alignment

**Digital Transformation Initiative (60+ people, Year 3):**
- ✅ **Core pillar:** MCP server exemplifies AI-first approach to operational data access
- ✅ **Scalable pattern:** Establishes reusable pattern for AI integration across other systems beyond Canary
- ✅ **Team capability building:** UNS developers gain hands-on experience with MCP protocol and industrial AI tooling

**AI Adoption & Massification:**
- ✅ **Democratization:** Enables company-wide AI access to plant data (not just data scientists)
- ✅ **Friction removal:** Eliminates technical barriers that currently limit AI adoption
- ✅ **Usage acceleration:** Natural language interface drives organic adoption across engineering teams
- ✅ **Measurement:** Clear KPIs (active users, query volume) demonstrate AI adoption progress

**Operational Excellence:**
- ✅ **Data-driven culture:** Makes plant data accessible for daily decision-making
- ✅ **Continuous improvement:** Enables rapid hypothesis testing and optimization experiments
- ✅ **Cross-functional insights:** Breaks down data silos between sites and departments

### Strategic Initiatives

**Industry Leadership & Future-Proofing:**
- **First-mover advantage:** First universal Canary MCP server positions company as industrial AI thought leader
- **Sustainability through innovation:** "Catching the AI train" ensures long-term competitiveness in increasingly AI-driven industrial sector
- **Ecosystem contribution:** Open, universal architecture enables community adoption and establishes company as contributor to industrial AI standards
- **Talent attraction:** Cutting-edge AI tooling attracts and retains top engineering and data science talent

**Risk Mitigation:**
- **Avoiding obsolescence:** Proactive AI adoption prevents future vulnerability as competitors adopt AI-driven operations
- **Platform independence:** MCP protocol reduces vendor lock-in, future-proofs against technology shifts
- **Knowledge preservation:** Structured data access enables institutional knowledge capture and AI-augmented decision support

**Opportunity Cost of NOT Building:**
- **6-site inefficiency:** Manual workflows replicated across all sites, compounding operational friction
- **Suboptimal operations:** Plants operate with limited historical context and slow analysis cycles
- **Competitive disadvantage:** Competitors who adopt industrial AI faster gain operational efficiency edge
- **Digital transformation stall:** Without practical AI tools, transformation initiative loses momentum and credibility
- **Brain drain:** Best engineers and analysts frustrated by manual processes seek opportunities at AI-forward companies

**Strategic Value Beyond Internal Use:**
- **Open source positioning:** Releasing as universal Canary MCP server builds industry goodwill
- **Partnership opportunities:** Positions company for collaboration with Canary Labs and other industrial software vendors
- **Conference presence:** Provides compelling case study for industrial AI conferences and publications
- **Customer/supplier confidence:** Demonstrates operational excellence and innovation to stakeholders

---

## MVP Scope

### Core Features (Must Have)

**Critical Design Principle:**

⚠️ **Universal Canary MCP Server** - This MCP server must be designed as a universal, reusable solution for ANY Canary Historian deployment worldwide, not just our specific POC. While it will be validated within our 6-site rollout, the architecture, configuration, and tooling must support any Canary user globally without custom modifications.

**Design Implications:**
- Zero hardcoded site-specific logic (all configuration-driven)
- Generic tag discovery and namespace browsing (works with any Canary data structure)
- Configurable connection parameters (base URLs, authentication, historians)
- Standard MCP protocol implementation (no proprietary extensions)
- Documentation and examples applicable to any industrial scenario
- Open architecture enabling community adoption and contribution

**Essential MCP Tools (5 of 8):**

1. **`list_namespaces`** - CRITICAL: Browse available sites/assets/namespaces to understand data structure
2. **`search_tags`** - CRITICAL: Find relevant tags based on user query (inference capability)
3. **`get_tag_metadata`** - CRITICAL: Understand tag properties to ensure correct data retrieval
4. **`read_timeseries`** - CRITICAL: Retrieve actual historical/real-time data
5. **`get_server_info`** - Essential for validation: Verify Canary connection, capabilities, health

**Rationale:** These 5 tools enable the core workflow - *"Infer what tags the user needs → Retrieve data from correct dataset → Deliver to LLM"*

**Authentication & Session Management:**
- Canary API token-based authentication
- Session token management with automatic refresh
- Secure credential handling (environment variables, not hardcoded)

**Production-Grade Error Handling:**
- Comprehensive error handling with meaningful messages to LLM
- Retry logic with exponential backoff for transient failures
- Circuit breaker to protect Canary API from cascading failures
- Graceful degradation when Canary API is unavailable

**Monitoring & Observability:**
- Request/response logging for debugging
- Success/failure metrics tracking
- Performance metrics (query latency, API response times)
- Health check endpoint for deployment validation

**Deployment Process:**
- Automated deployment scripts for 6-site rollout
- Configuration management for multi-site setup
- Environment-specific configs (dev, staging, production)
- Docker containerization for consistent deployment

**Testing Coverage:**
- Unit tests for all MCP tools (95%+ coverage)
- Integration tests with Canary API (contract tests)
- Mock/fixture-based tests for offline development
- Test data validation for UNS developers

**Documentation:**
- Setup guide for UNS developers
- MCP tool usage examples
- Troubleshooting guide for common issues
- API validation findings and workarounds

### Out of Scope for MVP

**Deferred MCP Tools (Phase 2):**
- `aggregate_timeseries` - Server-side aggregation (LLM can aggregate post-retrieval for MVP)
- `interpolate_timeseries` - Advanced alignment feature (not needed for initial validation)
- `export_timeseries` - Convenience export (users can work with raw data initially)

**Advanced Features (Future):**
- Advanced caching layer for frequently accessed data
- Multi-tenant support with user-level permissions
- Advanced rate limiting with per-user quotas
- Real-time streaming data subscriptions (long-lived connections)
- Custom aggregation functions beyond Canary API defaults
- Data quality scoring and anomaly flagging
- Cross-site data federation queries
- GraphQL API alternative to MCP tools
- Web UI for non-LLM access

**Nice-to-Haves (Post-Launch):**
- Advanced performance optimization (query planning, batch optimization)
- Comprehensive audit logging for compliance
- Advanced monitoring dashboards (Grafana, Prometheus integration)
- A/B testing framework for query optimization
- Machine learning-based tag recommendation

### MVP Success Criteria

**Primary Acceptance Criteria:**

✅ **Core Functionality:** Ask for a tag value(s) within a date and time interval and retrieve it successfully
   - User/LLM specifies: tag name(s), start date/time, end date/time
   - MCP server infers correct Canary tags from user query
   - Retrieves data from correct dataset/namespace
   - Returns structured timeseries data to LLM
   - Handles multiple tags in single query

**Testing Requirements:**
- ✅ All tests passed (unit, integration, contract)
- ✅ Test coverage: 75% minimum across codebase
- ✅ Unit tests: 85% pass rate minimum
- ✅ Integration tests validated against live Canary API

**Phase 1 Validation Complete When:**

1. ✅ UNS developers can ask "Show me temperature data for Maceira kiln 6 last week" and MCP server successfully:
   - Infers the correct Canary tags
   - Retrieves data from correct dataset/namespace
   - Returns structured data to LLM

2. ✅ All 5 core MCP tools tested and validated against POC site

3. ✅ Error handling tested with API failures, network issues, invalid queries

4. ✅ Deployment process validated - can deploy to new site in <30 minutes

5. ✅ 95%+ query success rate during validation period

6. ✅ UNS developers confirm: "Ready for remaining 5 site deployments"

**Additional Acceptance Criteria:**
- 100% of core MCP tools functional
- <5 second median query response time
- Zero critical bugs blocking UNS validation
- Documentation sufficient for self-service by Phase 2 users
- Deployment automation tested on 2+ sites
- All tests passed with 75%+ coverage and 85%+ unit test pass rate

---

## Post-MVP Vision

### Phase 2 Features

**Additional MCP Tools (3-6 months):**
- **`aggregate_timeseries`** - Server-side rollups and resampling (avg, min, max, count, percentiles, time-weighted averages)
- **`interpolate_timeseries`** - Aligned data for correlation analysis and plotting
- **`export_timeseries`** - Structured export to CSV/Parquet for external analysis tools
- **Additional tools as needed** - Based on community feedback and real-world usage patterns (e.g., batch queries, computed tags, alarm history)

**Performance & Scale Enhancements:**
- Intelligent caching layer for frequently accessed tags and time ranges
- Query optimization engine for complex multi-tag requests
- Connection pooling and request batching for high-concurrency scenarios
- Streaming data subscriptions for real-time monitoring use cases

**Production Hardening:**
- Advanced monitoring dashboards (Grafana integration)
- Comprehensive audit logging for compliance
- Multi-tenant support with role-based access control
- Enhanced security features (encrypted credentials, certificate management)

### Long-term Vision

**Canary Ecosystem Leadership (12-24 months):**

**Industry Adoption:**
- Establish as the de facto MCP server for Canary Historian across industries:
  - **Manufacturing:** Discrete manufacturing, automotive, electronics
  - **Utilities:** Power generation, water treatment, energy distribution
  - **Food & Beverage:** Processing plants, quality control, supply chain
  - **Cement/Heavy Industry:** Current focus area, reference implementations
- Build showcase implementations and case studies demonstrating ROI across sectors

**AI Agent Integration:**
- **Autonomous operations:** Enable AI agents to monitor, analyze, and suggest operational adjustments without human intervention
- **Predictive maintenance:** AI agents continuously monitor equipment health indicators and schedule maintenance proactively
- **Optimization loops:** Closed-loop AI systems that test operational hypotheses and implement approved optimizations
- **Multi-agent collaboration:** Coordinate multiple specialized AI agents (process optimization, quality control, energy management) sharing Canary data

**Advanced Analytics Platform:**
- **ML model serving:** Expose trained models as MCP tools (anomaly detection, demand forecasting, quality prediction)
- **Feature engineering:** Automated feature extraction from timeseries data for ML pipelines
- **Model inference integration:** Real-time model scoring on streaming data
- **Federated learning:** Enable privacy-preserving ML across multiple sites

**Community & Commercial Considerations:**

**Open Source Foundation:**
- Maintain core MCP server as open source for maximum adoption
- Active community engagement via GitHub, forums, documentation
- Contribution guidelines and community-driven feature development

**Commercial Offerings (Non-Profit Focus Initially):**
- **Managed hosting:** Offer hosted MCP service for companies without DevOps resources
- **Enterprise support:** Premium support contracts for mission-critical deployments
- **Training & consulting:** Workshops and implementation services
- **Strategic positioning:** Revenue reinvested in product development, not profit extraction
- **Ecosystem building:** Commercial activities focused on expanding adoption and building industrial AI community

### Expansion Opportunities

**Cross-Industry Growth:**
- Tailor documentation and examples for specific industries
- Build industry-specific tag libraries and query patterns
- Partner with system integrators in different sectors
- Present at industry conferences (ISA, OPC Foundation, manufacturing summits)

**Technology Partnerships:**
- Collaboration with Canary Labs on official MCP integration
- Integration with popular LLM platforms (OpenAI, Anthropic, local LLMs)
- Partnerships with industrial AI vendors and consultancies
- Academic partnerships for research on industrial AI applications

**Platform Extension:**
- **Note:** Currently focused exclusively on Canary Historian ecosystem
- May remain Canary-specific to maintain deep integration quality
- Future assessment: Evaluate expansion to other historians (OSIsoft PI, InfluxDB) only if clear demand and resources permit
- **Strategic focus:** Master Canary integration first before considering multi-platform support

**Autonomous Operations Future:**
- AI agents as first-class operators with real-time data access
- Closed-loop control scenarios with human oversight
- Multi-site coordination via AI agent networks
- Digital twin integration for simulation-based optimization

**Innovation Lab Applications:**
- Generative AI for process optimization recommendations
- Natural language to SQL/query translation for complex analysis
- Automated root cause analysis engines
- Cross-domain correlation (production + weather + market data)

---

## Technical Considerations

### Platform Requirements

**Deployment Model:**
- **Phase 1 (MVP):** Local deployment on user machines
  - Users run MCP server on their own workstations/laptops
  - Direct connection from local LLM client to local MCP server
  - Minimal infrastructure dependencies

- **Phase 2 (Production Scale):** Cloud-hosted centralized server
  - Shared MCP server accessible by all users across sites
  - Reduced per-user setup complexity
  - Centralized monitoring and management

**Containerization:**
- Docker containerization for consistent deployment
- Dockerfile for single-container deployment
- Docker Compose for multi-container orchestration (MCP server + database + monitoring)
- Container registry for version management and distribution

**Scalability Target:**
- Support 25 concurrent users initially
- Architecture designed for horizontal scaling in Phase 2

### Technology Preferences

**Primary Stack:**
- **Python 3.13** (preferred) - Modern Python with latest performance improvements
- **uv** for dependency management - Fast, modern alternative to pip/poetry
- **Note:** Python/uv preferred but not mandatory - architect may propose alternatives if compelling rationale exists

**MCP Server Implementation:**
- **Recommended:** FastMCP or MCP Python SDK for standard MCP protocol implementation
- **Alternative:** Build on official Anthropic MCP reference implementations
- **Web framework:** FastAPI or similar for HTTP/SSE endpoints (if needed beyond MCP protocol)

**Data Storage & Caching:**
- **Lightweight database:** SQLite for local deployment (embedded, zero-config)
- **Phase 2 upgrade path:** PostgreSQL or Redis for cloud-hosted deployment
- **Use cases:**
  - Query result caching (frequently accessed tags/time ranges)
  - Tag metadata caching (reduce Canary API calls)
  - Query history/analytics
  - Session state management

**Monitoring & Observability:**
- **Logging:** Structured logging (JSON format) with log levels
- **Metrics:** Prometheus-compatible metrics endpoint
  - Request count, latency, error rates
  - Canary API call volume and response times
  - Cache hit/miss rates
- **Health checks:** HTTP health endpoint for container orchestration
- **Tracing:** OpenTelemetry integration for distributed tracing (Phase 2)

**Testing Framework:**
- **pytest** for unit and integration tests
- **pytest-asyncio** for async test support
- **pytest-cov** for coverage reporting (target: 75%+ coverage)
- **responses** or **httpx-mock** for mocking Canary API calls
- **Contract tests:** Validate against actual Canary API (gated by environment flag)

**Code Quality Tools:**
- **Ruff:** Linting and code formatting (fast, modern alternative to Black+Flake8)
- **Mypy:** Optional static type checking
- **Pre-commit hooks:** Automated formatting and linting on commit

### Architecture Considerations

**High-Level Architecture:**

```
User (Claude/ChatGPT)
    ↓ MCP Protocol
Local MCP Server (Python)
    ↓ REST API
Canary Views Web API
    ↓
Canary Historian Database
```

**Key Components:**
1. **MCP Protocol Handler** - Receives tool calls from LLM client
2. **Canary API Client** - Manages authentication, sessions, and API requests
3. **Tag Discovery Engine** - Infers correct tags from natural language queries
4. **Query Engine** - Translates user intent to Canary API calls
5. **Cache Layer** - SQLite-based caching for performance
6. **Error Handler** - Retry logic, circuit breaker, graceful degradation
7. **Metrics Collector** - Track usage and performance metrics

**Authentication Flow:**
- User provides Canary API token via environment variable or config file
- MCP server manages session token lifecycle (request, refresh, expiry)
- No user credentials stored persistently (security best practice)

**Configuration Management:**
- **Environment variables:** Canary base URL, API token, historian list
- **Config file (optional):** YAML or TOML for advanced settings
- **Defaults:** Sensible defaults for rate limits, timeouts, retry behavior
- **Multi-site support:** Config profiles for different Canary deployments

**Error Handling Strategy:**
- **Retry logic:** Exponential backoff with jitter (3-5 retries)
- **Circuit breaker:** Open circuit after N consecutive failures, auto-recover after cooldown
- **Timeouts:** Per-request timeout (10-30s), overall query timeout (60s)
- **Error messages:** LLM-friendly error descriptions for user troubleshooting

**Performance Optimization:**
- **Connection pooling:** Reuse HTTP connections to Canary API
- **Request batching:** Combine multiple tag queries when possible
- **Lazy loading:** Load metadata on-demand, not upfront
- **Background tasks:** Async cache warming, session keepalive

### Integration Requirements

**Primary Integration:**
- **Canary Views Web API** - REST API integration
  - Base URL: Configurable per deployment
  - Authentication: Token-based (managed by MCP server)
  - Endpoints: `/views`, `/views/data`, `/views/metadata`, etc.
  - API documentation: https://readapi.canarylabs.com/25.4/

**Authentication:**
- Canary API token-based authentication
- No additional SSO or Active Directory integration in Phase 1
- Session token lifecycle managed transparently by MCP server

**Future Integration Considerations (Phase 2):**
- UNS architecture components (MQTT, Sparkplug B)
- Enterprise SSO for cloud-hosted deployment
- Existing monitoring/logging infrastructure (Grafana, ELK stack)

### Constraints and Non-Functional Requirements

**Security (Phase 1 Scope):**
- ✅ Secure credential handling (environment variables, no hardcoding)
- ✅ HTTPS for Canary API communication
- ❌ Data encryption at rest (deferred to Phase 2)
- ❌ Certificate management (deferred to Phase 2)
- ❌ Role-based access control (deferred to Phase 2)

**Performance:**
- Median query response time: <5 seconds
- 95th percentile: <10 seconds
- Cache hit rate: 30%+ for repeated queries
- Canary API rate limiting: Respect API limits, implement client-side throttling

**Scalability:**
- Support 25 concurrent users in Phase 1 (local deployment)
- Architecture supports horizontal scaling for Phase 2 (cloud deployment)

**Reliability:**
- Target uptime: 99.5% (allowing for planned maintenance and updates)
- Graceful degradation when Canary API unavailable (cached data, clear error messages)
- Automatic recovery from transient failures

**Compatibility:**
- Works with any MCP-compatible LLM client (Claude Desktop, Continue, etc.)
- Compatible with Canary Views API v25.4+ (validate version requirements)
- Cross-platform: Windows, macOS, Linux

---

## Constraints and Assumptions

### Constraints

**Timeline & Resource Constraints:**
- **3-month development window:** Tight timeline aligned with 6-site Canary rollout schedule
- **Existing team capacity:** Development by current UNS OT team, no new hires budgeted
- **Digital transformation budget:** Part of existing budget allocation, limited incremental funding
- **Time pressure:** Balancing MVP quality with speed-to-deployment

**Technical Constraints:**
- **Existing Canary deployment:** Must work with current Canary Historian infrastructure and configuration
- **Phase 1 network:** Limited to company internal network (no external/public internet access initially)
- **Local deployment model:** Each user runs MCP server locally in Phase 1 (infrastructure simplicity)
- **Cross-platform support:** Must work on Windows, macOS, Linux (varied user environments)

**API & Integration Constraints:**
- **Canary API quality uncertainty:** ⚠️ **Known Risk** - Canary Views Web API may have:
  - Incomplete or unclear documentation
  - Non-standard REST patterns
  - Undocumented edge cases or limitations
  - **Mitigation:** Handle gracefully with robust error handling, comprehensive testing, and API behavior documentation
  - **Impact:** May increase development effort by 20-30%, but not a fatal blocker
  - **Approach:** Iterative validation, workarounds, and feedback to Canary Labs if needed

**Organizational Constraints:**
- **Universal design requirement:** Must be generic enough for any Canary deployment worldwide (no site-specific hardcoding)
- **Open architecture:** Design must support future open-source release and community adoption
- **No custom Canary modifications:** Cannot modify Canary Historian itself, must work with standard API

**Security Constraints (Phase 1):**
- Data encryption at rest: Deferred to Phase 2
- Advanced certificate management: Deferred to Phase 2
- Enterprise SSO integration: Deferred to Phase 2
- Focus: Secure credential handling and HTTPS communication only

### Key Assumptions

**User Adoption Assumptions (Validated):**
- ✅ **Users are adopting LLM-based workflows:** Current trend observed within organization
- ✅ **Natural language interface reduces friction:** Users prefer asking questions vs. building queries
- ✅ **Engineers comfortable with LLM tools:** Claude/ChatGPT usage already established

**Technical Assumptions (Require Validation):**

**🔍 CRITICAL ASSUMPTION: LLM Effectiveness with Plant Data**
- **Assumption:** LLMs can effectively interpret industrial timeseries data and provide useful operational insights
- **Validation Status:** ⚠️ **UNPROVEN** - Needs validation during MVP development
- **Risks:**
  - LLMs may struggle with numeric/timeseries pattern recognition
  - Industrial domain knowledge gaps may lead to incorrect conclusions
  - Complex correlations may require domain-specific prompting
- **Validation Plan:**
  - Test with real plant scenarios during Phase 1
  - Gather UNS developer feedback on insight quality
  - Iterate on data formatting and context provided to LLM
  - Document best practices for effective plant data queries

**🔍 CRITICAL ASSUMPTION: Tag Discovery from Natural Language**
- **Assumption:** MCP server + LLM can effectively infer correct Canary tags from human language queries
- **Validation Status:** ⚠️ **UNPROVEN** - Core MVP capability requiring validation
- **Challenge:** User asks "Show me kiln 6 temperature" → MCP must find tag like "Maceira.Cement.Kiln6.Temperature"
- **Dependencies:**
  - LLM understands domain terminology (kiln, temperature, pressure, etc.)
  - `search_tags` and `list_namespaces` tools provide sufficient discovery capability
  - Tag naming conventions are somewhat consistent across sites
- **Validation Plan:**
  - Build comprehensive tag search with fuzzy matching and metadata filters
  - Test with diverse natural language query patterns
  - Provide rich tag metadata to help LLM make correct inferences
  - User feedback loop to refine search algorithms

**Infrastructure Assumptions:**
- **Reliable connectivity:** Stable network connection between MCP server and Canary API within company network
- **Canary availability:** Canary Historian and Views API maintain high availability (>99%)
- **Client environment:** Users have Python runtime or Docker available on their machines
- **Sufficient resources:** User machines can run MCP server alongside LLM client without performance issues

**Data & API Assumptions:**
- **Tag metadata completeness:** Canary tags have sufficient metadata (units, descriptions) for LLM interpretation
- **Consistent data quality:** Historian data is reliable with quality flags where applicable
- **API rate limits:** Canary API rate limits are sufficient for 25 concurrent users in Phase 1
- **Namespace structure:** Canary namespace/hierarchy is logical and discoverable

**User Behavior Assumptions:**
- **Query patterns:** Most queries will be straightforward time-range + tag requests (80%+)
- **Complex analysis:** Users will iterate with LLM (ask follow-up questions) rather than expecting single-query answers
- **Feedback provision:** UNS developers will provide timely feedback on API issues and tag discovery accuracy
- **Learning curve:** Users willing to learn MCP server setup and basic troubleshooting

**Deployment Assumptions:**
- **Local deployment viability:** Phase 1 local deployment is acceptable temporary solution before cloud hosting
- **Docker adoption:** Users can run Docker containers or are willing to learn
- **Configuration complexity:** Users can handle basic environment variable configuration
- **Update distribution:** Can push updates via container registry without complex deployment process

### Assumptions Requiring Validation During Development

**High Priority Validation:**
1. **LLM insight quality** - Do LLMs provide actionable insights from plant data?
2. **Tag discovery accuracy** - Can we reliably map natural language to correct tags?
3. **Canary API completeness** - Does API provide all needed functionality?
4. **Query performance** - Can we meet <5 second response time target?

**Medium Priority Validation:**
5. User adoption rate and satisfaction with MCP-based workflow
6. Cache hit rates and effectiveness of caching strategy
7. Error rate and retry success rate with Canary API
8. Concurrent user scalability within Phase 1 limits

**Continuous Validation:**
- API behavior and edge cases (ongoing as usage grows)
- Tag naming consistency across sites (as new sites onboard)
- User query pattern evolution (may require tool enhancements)

---

## Risks and Open Questions

### Key Risks

{{key_risks}}

### Open Questions

{{open_questions}}

### Areas Needing Further Research

{{research_areas}}

---

## Appendices

### A. Research Summary

**Hackathon Case Analysis:**
- Case objective: Develop proof-of-concept MCP for Canary Views Web API access
- Success criteria: Authentication, historical data queries, real-time access, metadata retrieval
- Technical foundation: Python 3.13, uv, pytest, REST API integration

**MCP Protocol Research:**
- Model Context Protocol provides standardized way for LLMs to access external tools
- Proven pattern with existing implementations across various domains
- Anthropic-backed standard with growing ecosystem adoption

**Canary API Investigation:**
- Canary Views Web API documented at https://readapi.canarylabs.com/25.4/
- Key endpoints: /views, /views/data, /views/metadata
- Authentication: Token-based with session management
- Known concerns: Potential documentation gaps and non-standard REST patterns (requires validation)

**Industrial AI Trends:**
- Growing adoption of LLM-based operational intelligence in manufacturing
- Natural language interfaces reducing barrier to data-driven decision making
- MCP protocol emerging as standard for industrial tool integration

### B. Stakeholder Input

**UNS OT Development Team:**
- Priority: Validate Canary historian implementation across 6-site rollout
- Need: Rapid testing and data quality validation tools
- Timeline: 3-month window for POC validation before additional site deployments
- Concern: Canary API quality and documentation completeness

**Digital Transformation Leadership (60+ person initiative, Year 3):**
- Strategic priority: AI adoption and massification across organization
- Goal: "Catch the AI train" for long-term sustainability and competitiveness
- Investment: Part of existing digital transformation budget
- Success metric: Demonstrate practical AI value with operational impact

**Plant Engineering Teams:**
- Pain point: Hours-long delays for operational data analysis
- Use cases: Root cause analysis, efficiency optimization, cross-site comparisons
- Example questions: "Why did kiln 5 underperform by 10%?", "Show temperature trends for kiln 6"
- Expectation: Real-time insights vs. waiting for scheduled reports

**Data Analytics Team:**
- Challenge: 3-5 hours per report spent on data extraction vs. analysis
- Opportunity: 3-5x increase in analysis frequency with automation
- Vision: Enable ad-hoc analysis without manual data wrangling

**Executive Sponsors:**
- Business case: EBITDA improvement through data-driven operational optimization
- Strategic value: Industry leadership in industrial AI, talent attraction/retention
- Risk mitigation: Avoid competitive disadvantage as industry adopts AI-driven operations

### C. References

**Initial Context - Source Documents:**
- MCP Canary - Process Historical Data.md (Hackathon case description)
- Canary info, Tests, Configs.md (Technical configuration and testing guide)
- Canary Views Web API Documentation: https://readapi.canarylabs.com/25.4/

**Key Insights from Documents:**

**Problem Context:**
- Industrial facilities use Canary Historian to record real-time and historical process data
- This data is critical for performance, quality, and efficiency analysis
- Currently, accessing this data programmatically requires direct API integration
- Need: Structured, secure way for applications and AI agents to consume Canary industrial data

**Solution Direction:**
- Build an MCP (Model Context Protocol) server that provides tools to access Canary Views Web API
- Enable authentication, historical data queries, real-time streaming, and metadata retrieval
- Validate that Canary API is robust, well-documented, and ready for seamless MCP server integration
- Create proof of concept that demonstrates practical data access patterns, evolving to production-ready implementation

**Target Capabilities:**
1. Authenticate and connect to Canary API (token management)
2. Query historical data from predefined views
3. Access real-time data streams
4. Retrieve metadata about tags and properties

**Success Criteria from Case:**
- Functional MCP with authentication, historical, real-time, and metadata tools
- Demonstrate real data access from existing views
- Show integration example (e.g., comparing historical vs real-time data)
- Explain scalability for production use

**Technical Stack Indicators:**
- Python 3.13 with uv for dependency management
- REST API integration (Canary Views Web API)
- Testing: pytest with unit, integration, and contract tests
- Linting: Ruff and Black
- Type checking: Mypy

{{references}}

---

_This Product Brief serves as the foundational input for Product Requirements Document (PRD) creation._

_Next Steps: Handoff to Product Manager for PRD development using the `workflow prd` command._
