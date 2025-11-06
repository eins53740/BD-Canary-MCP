# Story 4.8 — Write API Implementation (Test Datasets Only)

Context & Constraints:
- Production is read-only; allow writes strictly to approved test datasets.
- Must confirm dataset/site context before writing.
 - Follow Write API docs in `docs/aux_files/Canary API` (SaF v25.3). Use `apiToken` and ensure Tag Security permissions. If remote SaF, configure it with a valid token.
 - Optionally use `autoCreateDatasets=true` on session token creation for test environments.

Acceptance Criteria (Checklist):
- New write tool records: success/failure (bool) and original prompt (string).
- Writes allowed only to `Test/Maceira` and `Test/Outao`; attempts elsewhere are denied with actionable error.
- Usage documented for LLMs (intent, fields, safeguards).
 - Role-gated: only tester roles can invoke write tool.

Validation:
- Unit/integration tests verify allowed vs denied writes.
- Manual smoke with mock data confirms record shape and gating.

Deliverables:
- Tool spec and docs with safety notes.
- Example usage and clean-up guidance.
