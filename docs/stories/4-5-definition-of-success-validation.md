[x] # Story 4.5 — Definition of Success Validation

Context & Constraints:
- Validate end-to-end outcomes without altering production historians.
- Prefer offline fixtures where live data is unavailable.

Acceptance Criteria (Checklist):
- Test cases demonstrate: multi-tag correlation, accurate retrieval, and summarized insights.
- Ambiguity handling: LLM prompts for clarification; documented example.
- Example plots/text summaries include tag paths, units, sites, and ranges.
- Performance target: p95 latency < 10000 ms for common calls.
- tag_lookup_workflow batch: ≥90% correct mapping across 200 NL descriptions; if confidence <0.7 → ask a clarifying question.

Validation:
- Re-run documented scenarios and verify consistent outputs.
- Keep artifacts small and linkable from docs (not checked-in binaries).

Deliverables:
- Success scenarios documented with steps and expected outputs.
- Lightweight artifacts (images/HTML) referenced from docs as needed.

---

## Implementation Snapshot (2025-11-07)

- `read_timeseries` now emits a deterministic `summary` block (site hint, start/end ISO timestamps, per-tag sample counts, duration). This powers text/table summaries without re-querying Canary.
- New coverage at `tests/e2e/test_success_validation.py` exercises:
  - Multi-tag correlation and summary reporting.
  - 200-query batch accuracy with enforced clarifying questions when confidence <0.7.
- Artifact `docs/artifacts/story-4-5-tag-lookup-batch.json` tracks the latest batch run (182 / 200 high-confidence matches, 18 clarifications).
- Scenario handover guide: `docs/validation/story-4-5-success-scenarios.md`.

## How to Re-Validate

| Scenario | Command | Expected Outcome |
| --- | --- | --- |
| Multi-tag correlation | `uv run pytest tests/e2e/test_success_validation.py::test_timeseries_multi_tag_correlation_summary -q` | Summary shows `site_hint=Secil.Portugal`, ISO range, and per-tag sample counts (2 vs 1). |
| Batch accuracy (200 NL) | `uv run pytest tests/e2e/test_success_validation.py::test_tag_lookup_batch_accuracy_and_clarifications -q` | ≥90 % success rate, clarifying prompt for the remaining 18 cases (see artifact JSON). |
| Performance guardrail | `uv run python scripts/benchmark.py --scenarios single` | p95 latency recorded in `docs/artifacts/benchmark-results-20251101-094941.json` stays ≪ 10 000 ms. |

**Example Analyst Summary (text-only excerpt)**
```
Site: Secil.Portugal • Window: 2025-10-30T10:00Z → 11:00Z (3600 s)
- Kiln6.ShellTemp (degC): 2 samples, trending 832 → 833 °C
- Kiln6.ShellPressure (bar): 1 sample at 3.2 bar
Next step: compare vs kiln draft pressure if spikes continue.
```

**Ambiguity Handling Template**
`Can you specify the site, equipment, or engineering units for kiln, shell, temperature? For example: 'Maceira kiln 6 shell temperature in section 15 (°C)'.`
Use this phrasing whenever `confidence < 0.7` so the operator understands exactly what context is missing.

> 🧩 *Extra Scholar Info:* Storing scenario outputs as small JSON/Markdown artifacts keeps history auditable and lets junior engineers rerun every acceptance test with three commands.
