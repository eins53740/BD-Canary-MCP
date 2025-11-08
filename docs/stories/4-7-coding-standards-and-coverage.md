[x] # Story 4.7 — Coding Standards and Coverage

Context & Constraints:
- Enforce linters/formatters and minimum coverage, but do not block PRs below threshold.
- Structured logging only (no print/console.log).
 - Pre-commit: black + isort + flake8 + (optional) mypy; Ruff acceptable alternative if already in repo.

Acceptance Criteria (Checklist):
- Pre-commit hooks configured for Ruff/Black (Py) and ESLint/Prettier (TS if present).
- Coverage target ≥75% for changed lines with HTML report documented.
- CI commands documented and runnable locally.
- CI splits: unit, integration (requires Canary test creds), and coverage.
- Coverage policy: fail if PR decreases coverage by >5%; warn if repo coverage <75%.

Validation:
- Run: `ruff check .`, `uv run pytest --cov=canary_mcp --cov-report=html`.
- Confirm non-zero coverage report and clean lint output for changed files.

Deliverables:
- Updated testing and linting sections in docs.
- Short contributor guide snippet for day-to-day workflow.

---

## Implementation Snapshot (2025-11-07)

- `.pre-commit-config.yaml` runs Ruff (lint/format), Black, and isort. ESLint/Prettier will be added when the repository includes TypeScript.
- Coverage checks now flow through `scripts/ci/check_coverage.py`, which enforces the “warn <75 %, fail if regression >5 pp” policy using `docs/coverage-baseline.json`.
- Contributor workflow + CI job matrix documented in `docs/development/testing-and-coverage.md` and summarised in the README.
- HTML reports (`htmlcov/index.html`) plus JSON output (`coverage.json`) are generated via `uv run pytest --cov=... --cov-report=html --cov-report=json:coverage.json`.
