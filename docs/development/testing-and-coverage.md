# Testing, Linting, and Coverage Playbook (Story 4.7)

This guide explains the day-to-day workflow for keeping Canary MCP Server compliant with the coding-standards and coverage requirements introduced in Epic 4 Story 4.7.

---

## 1. Pre-commit Stack

Run once per workstation:

```bash
uv tool install pre-commit  # or pip install pre-commit
pre-commit install
```

Hook summary:

| Hook | Purpose |
| --- | --- |
| Ruff (`ruff`, `ruff-format`) | Fast linting + auto-fix for Python style issues. |
| Black (`black`) | Enforces canonical formatting (PEP 8/PEP 257). |
| isort (`isort`) | Keeps import ordering deterministic for easier diffs. |
| Misc (`trailing-whitespace`, `check-yaml`, etc.) | Catches common paper cuts before a PR. |

> 🧩 *Extra Scholar Info:* Ruff can lint/format most cases, but running Black + isort in pre-commit keeps parity with teams that depend on those exact tools for auditing code drops.

No TypeScript/React packages live in this repo yet, so ESLint/Prettier is not required. If a TS package is added later, extend `.pre-commit-config.yaml` by mirroring the same hook pattern (eslint + prettier).

---

## 2. Lint Commands (manual runs)

```bash
uvx ruff check .
uvx black --check .
uvx isort --check-only .
```

To auto-fix formatting issues:

```bash
uvx ruff check --fix .
uvx black .
uvx isort .
```

---

## 3. CI Test Splits

| Job | Command | Notes |
| --- | --- | --- |
| Unit | `uv run pytest -m "unit or not integration" -q` | Fast feedback; no Canary credentials required. |
| Integration | `uv run pytest -m integration -q --maxfail=1 --durations=10` | Requires valid `CANARY_*` env vars (token, URLs). |
| Coverage | `uv run pytest --cov=canary_mcp --cov-report=term --cov-report=html --cov-report=json:coverage.json` | Generates HTML (`htmlcov/index.html`) plus `coverage.json` for policy checks. |

When running locally, export `CANARY_API_TOKEN`, `CANARY_SAF_BASE_URL`, and `CANARY_VIEWS_BASE_URL` (or populate `.env`) before invoking the integration suite.

---

## 4. Coverage Policy & Checks

1. Run the coverage suite (see table above). This creates:
   - Terminal summary
   - `htmlcov/index.html` (line-by-line drill-down)
   - `coverage.json` (machine-readable output)
2. Enforce Story 4.7 policy:
   ```bash
   python scripts/ci/check_coverage.py coverage.json \
     --baseline-file docs/coverage-baseline.json
   ```
   - Fails if new coverage regresses by **>5 percentage points** vs the baseline file.
   - Prints a warning (but does not fail) if overall coverage is **<75 %**.
3. Update `docs/coverage-baseline.json` after a successful run on the default branch so future work compares against the latest number.

> 🧩 *Extra Scholar Info:* Using the JSON report keeps the workflow cross-platform—no need for `jq` or shell-specific parsing, and CI jobs can consume the same script.

---

## 5. Contributor Checklist (Every PR)

1. `pre-commit run --all-files`
2. `uv run pytest -m "unit or not integration" -q`
3. (If credentials available) `uv run pytest -m integration -q`
4. `uv run pytest --cov=canary_mcp --cov-report=term --cov-report=html --cov-report=json:coverage.json`
5. `python scripts/ci/check_coverage.py coverage.json --baseline-file docs/coverage-baseline.json`
6. Inspect `htmlcov/index.html` for gaps on touched modules and mention notable misses in the PR description.
7. Attach the coverage regression summary to the PR (copy from the script output).

Following these steps keeps the repo within the Story 4.7 guardrails without blocking contributors who are still raising the overall coverage.

## 6. CI/CD Wiring (Story 4.11)

In CI, run the same sequence as step 5 and treat warnings as non-blocking:

```bash
uv run pytest --cov=canary_mcp --cov-report=html --cov-report=json:coverage.json
python scripts/ci/check_coverage.py coverage.json --baseline-file docs/coverage-baseline.json --warn-threshold 75
```

- The script exits with `0` when coverage ≥75 % **even if** the repo-wide number drops, but prints `WARNING` so the build log surfaces the dip.
- It exits non-zero only when the measured coverage regresses by more than 5 percentage points versus the tracked baseline.
