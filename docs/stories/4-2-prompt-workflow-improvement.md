# Story 4.2 — Prompt Workflow Improvement

Context & Constraints:
- Brownfield UX: avoid static path guessing; ask clarifying questions when ambiguous.
- Document deterministic steps for `tag_lookup_workflow` and `timeseries_query_workflow`.
- Keep examples realistic for Maceira/Outão (namespaces, units, time windows).
- Use the on-disk resource `docs/aux_files/Canary Resources/Canary_Path_description_maceira.json` as the canonical index (no new RAG infra).

Acceptance Criteria (Checklist):
- Workflows documented with inputs, outputs, and decision points (clarification prompts).
- Canonical pseudocode implemented for `tag_lookup_workflow` with confidence gating (≥0.80 select; <0.70 ask question).
- Examples provided that run end-to-end with current tools.
- Errors are actionable (“what failed & how to fix”).

Validation:
- Reproduce examples in README/docs and confirm the same tool calls are issued.
- Verify NL time parsing and tag-resolution steps are visible to the user/LLM.

Deliverables (Checklist):
- Updated workflow docs and examples (README/docs).
- Brief “when to use” guidance embedded per tool.
 - E2E harness: `tests/e2e/test_tag_lookup.py` with sample fixtures.
