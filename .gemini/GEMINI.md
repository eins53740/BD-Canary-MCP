# 🧭 Codex Agents — Universal Development & Contribution Guide

> **Audience:** all contributors (human or agent).
> **Scope:** entire repository and subdirectories.
> **Priority:** deepest `AGENTS.md` file prevails if multiple exist.
> **Last Updated:** 2025-10-21

---

## 1️⃣ Purpose & Principles

- Guarantee **consistency, testability, and maintainability** of all Codex Agents.
- Educate contributors: every section ends with an **Extra Scholar Info** note for junior developers.
- Encourage **small, safe, incremental** delivery (≤200 LOC per task).
- Follow the **Golden Rule:** *Start small, work incrementally, test continuously.*

---

## 2️⃣ Development Environment

| Tool | Requirement | Notes |
|------|--------------|-------|
| **Node.js** | Latest LTS | Required for TypeScript/React packages |
| **Python** | ≥3.11 | Modern typing, async & performance |
| **Package Manager** | `pnpm` | Fast, workspace-aware |
| **Linters/Formatters** | `Ruff` + `Black` (Py) / `ESLint` + `Prettier` (TS) | Mandatory |
| **Test Runners** | `Pytest`, `Vitest` | Required |
| **Version Control** | Git (manual only — see §3) | Commit discipline required |

> 🧠 *Why:* Standardised tooling ensures deterministic builds and CI/CD consistency.

---

## 3️⃣ Git & Commit Discipline (Manual Commands Only)

> ⚠️ **Do not sync to Git automatically.**
> Tools or scripts must only **print** Git commands; contributors run them manually.

**Rules**
- No `--amend` or destructive `rebase`.
- Only committed code is reviewed — confirm clean state:
  ```bash
  git status
  ```
- **Commit message convention:**
  ```
  <type>: <imperative short summary>
  [extra context]
  Refs: #<issue>
  ```
  Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`.

**Example**
```bash
git add -A
git commit -m "feat: add MQTT stoppage summarizer"
git pull --rebase
git push
```

> 🧩 *Extra Scholar Info:* Linear history accelerates audits and bisect debugging.
> Prefer **many small commits** over few large ones.

---

## 4️⃣ Code Structure & Conventions

```plaintext
src/          # Core agent logic
tests/        # Unit, integration, contract, e2e
docs/         # Design, schemas, testing specs
scripts/      # Tooling, mocks, fixtures
```

### 4.1 Python & TypeScript
- Follow **PEP 8/20/257** and TypeScript ESLint rules.
- Type hints required for all public functions.
- No `print`; use structured logging.
- Prefer dependency injection over global state.
- Errors must be **actionable** (“what failed & how to fix”).
- Configuration from `.env` (never hardcoded).

> 🧩 *Extra Scholar Info:* Explicit types and dependency injection make agents more testable.

---

## 5️⃣ Testing Philosophy (TDD & Layered Approach)

### 5.1 Testing Layers
| Layer | Scope | Example |
|-------|--------|----------|
| **Unit** | Pure logic | parsing, transforms |
| **Integration** | Boundaries | MQTT ↔ DB |
| **Contract** | Schemas | SparkplugB, JSON |
| **E2E** | Full flow | broker → DB → Canary |

### 5.2 Rules
- **Write the test first** (TDD).
- Mark slow tests for CI isolation.
- Use **AAA pattern** (Arrange–Act–Assert).
- Mock external calls — no live data.
- Target ≥80% coverage of changed lines.

### 5.3 Local Commands
```bash
pnpm test
uv run pytest -q
ruff check .
pnpm lint
```

> 🧩 *Extra Scholar Info:* TDD ensures correctness by defining “expected behaviour” first.

---

## 6️⃣ CI/CD Quality Gates

| Gate | Description |
|-------|-------------|
| **Lint/Format** | Black, Ruff, ESLint, Prettier |
| **Tests** | Unit + Integration + Contract |
| **Coverage** | ≥80% changed lines |
| **Secrets** | Gitleaks |
| **Vulnerabilities** | `pip-audit`, `npm audit`, Trivy |
| **SBOM** | Syft (optional signing: Sigstore) |
| **Branch Protection** | no force-push; all checks green |

> 🧩 *Extra Scholar Info:* Automating gates enforces discipline even for fast iterations.

---

## 7️⃣ Pull Request Workflow

**Checklist**
- [ ] ≤300 LOC (excluding tests/docs).
- [ ] One logical change only.
- [ ] CI green (lint/tests/coverage).
- [ ] Docs & changelog updated.
- [ ] No `console.log` or `print`.
- [ ] Secrets checked and redacted.

**PR Title:**
```
[project_name] <short descriptive title>
```

**PR Content:** summary, screenshots/logs (if relevant), issue link, checklist.

> 🧩 *Extra Scholar Info:* Small, isolated PRs reduce review fatigue and rollback risk.

---

## 8️⃣ Reliability & Resilience Standards

- **Rate limit:** ≤500 req/s to external APIs.
- **Retries:** exponential backoff + jitter.
- **Timeouts:** explicit for every call.
- **Circuit breaker:** isolate failing services.
- **CDC debounce:** 180 s post-transmitter refresh.
- **MQTT QoS:** metrics → 1; logs → 0.
- **Validation:** enforce schemas before processing.

> 🧩 *Extra Scholar Info:* Controlled retries prevent overload; schema validation avoids cascading failures.

---

## 9️⃣ Observability & Logging

- **Logs:** JSON structured, daily rotation (≤100 MB, 14 days).
- **Metrics (Prometheus):**
  - Counters: DBIRTH processed, retries, success/fail.
  - Histograms: latency p50/p95.
  - Gauges: backlog, circuit state.
- **Health events:** publish to `Ignition Cloud` or equivalent.
- **Tracing:** use OpenTelemetry spans if available.

> 🧩 *Extra Scholar Info:* Observability shortens time-to-diagnose and ensures reproducibility.

---

## 🔒 10️⃣ Security & Secrets

- TLS 1.3 end-to-end (MQTT, DB, REST).
- Postgres with `verify-full`.
- `.env` files → permissions 600.
- No credentials in repo/history.
- Secrets via Vault or AWS Secrets Manager.
- Mask sensitive data in logs.
- Run dependency & secret scans before merge.

> 🧩 *Extra Scholar Info:* A single leaked key can compromise infrastructure—always rotate and restrict scope.

---

## 📚 11️⃣ Documentation Discipline

Each change must update:
- `README.md` and/or `docs/` → testing steps, environment vars.
- `CHANGELOG.md` → user-facing or contract changes.
- `MQTT`/`UNS` topic tables if modified.

> 🧩 *Extra Scholar Info:* Living documentation reduces onboarding time by ~50 %.

---

## 🧩 12️⃣ Monorepo Hygiene

- One repo → many packages; no deep imports.
- Public APIs only.
- Shared `contracts/types` package (`@org/contracts`, `contracts`).
- Turbo builds run only affected packages.

> 🧩 *Extra Scholar Info:* Monorepo discipline keeps dependency graphs predictable and incremental builds fast.

---

## 🧱 13️⃣ Project Refactor Checklist (Solid State)

| Area | Target |
|-------|--------|
| **Structure** | Folders: `src/`, `tests/`, `docs/`, `scripts/` |
| **Ownership** | Assign module maintainers |
| **Contracts** | Central schemas/types; versioned |
| **Observability** | Logs + Prometheus + Alerts |
| **Security** | TLS, Vault, scans |
| **Quality** | Coverage & lint gates enforced |
| **PR hygiene** | One logical change per PR |
| **Smoke testing** | `docker-compose` with EMQX for local runs |
| **Legacy cleanup** | Remove deprecated integrations |

> 🧩 *Extra Scholar Info:* Continuous small refactors prevent technical debt accumulation.

---

## 🇵🇹 TL;DR (Resumo)

- Ambiente padronizado (Node LTS, Python 3.11, pnpm).
- Commits manuais, curtos e claros (sem sync automático).
- Código simples, validado nas fronteiras, testado antes de escrever.
- CI robusta com *gates* de segurança, cobertura e estilo.
- Observabilidade, TLS 1.3, e logs estruturados obrigatórios.
- Refactor contínuo → projecto sólido e sustentável.
