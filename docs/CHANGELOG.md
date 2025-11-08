# Changelog

## 2025-11-01

- Standardised MCP tool → HTTP method usage, switching namespace/time-zone lookups to GET while keeping multi-parameter calls on POST.
- Added a global 1 MB response guardrail (configurable via `CANARY_MAX_RESPONSE_BYTES`) that logs truncations and returns compact previews.
- Documented the method matrix and payload guardrails in `docs/API.md` for quick operator reference.
