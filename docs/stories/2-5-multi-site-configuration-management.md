# Story 2.5: Multi-Site Configuration Management

As a **UNS Developer**,
I want to manage configuration for multiple Canary sites,
So that I can easily deploy the MCP server to all 6 sites with site-specific settings.

**Acceptance Criteria:**
1. Multi-site configuration via config file (YAML or JSON)
2. Config structure: array of site configs with name, URL, credentials, settings
3. Site selection via environment variable or CLI parameter
4. Config validation on startup: checks all sites have required fields
5. Config templates for common deployment scenarios
6. Support for site-specific overrides (timeouts, cache TTL, connection pool size)
7. Secure credential management: environment variables take precedence over config file
8. Configuration documentation with examples for 6-site deployment
9. Validation test: `test_multisite_config.py` confirms config loading and site switching

**Prerequisites:** Story 2.3 (advanced error handling)
