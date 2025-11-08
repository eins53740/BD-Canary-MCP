# Story 4.5 — Success Validation Scenarios

This playbook documents how we validate the “definition of success” guardrails called out in Epic 4 and Story 4.5. Each scenario is automated (pytest or script) and mirrors the acceptance criteria: multi-tag correlation, accurate retrieval, summarised insights, ambiguity handling, and p95 performance <10 000 ms.

---

## Scenario A — Multi-Tag Correlation & Summaries

- **Command:**
  ```bash
  uv run pytest tests/e2e/test_success_validation.py::test_timeseries_multi_tag_correlation_summary -q
  ```
- **What it does:** Exercises `read_timeseries` with two tags (shell temperature vs shell pressure) and asserts the new `summary` block reports `site_hint`, ISO time range, and per-tag sample counts.
- **Expected summary payload:**
  ```json
  {
    "site_hint": "Secil.Portugal",
    "requested_tags": ["Kiln6.ShellTemp", "Kiln6.ShellPressure"],
    "total_samples": 3,
    "samples_per_tag": {
      "Secil.Portugal.Kiln6.ShellTemp": 2,
      "Secil.Portugal.Kiln6.ShellPressure": 1
    },
    "range": {
      "start": "2025-10-30T10:00:00Z",
      "end": "2025-10-30T11:00:00Z",
      "duration_seconds": 3600
    }
  }
  ```
- **Engineer-facing summary table:** (for handover decks or text-only reports)

  | Tag Path | Site | Units | Range | Samples |
  | --- | --- | --- | --- | --- |
  | `Secil.Portugal.Kiln6.ShellTemp` | Secil.Portugal | degC (from `get_tag_path` metadata) | 2025‑10‑30T10:00Z → 2025‑10‑30T11:00Z | 2 |
  | `Secil.Portugal.Kiln6.ShellPressure` | Secil.Portugal | bar (lookup metadata) | 2025‑10‑30T10:00Z → 2025‑10‑30T11:00Z | 1 |

> 🧩 *Extra Scholar Info:* The new summary block means LLMs can describe chart axes (site, units, time extent) without re-querying metadata, keeping answers deterministic.

---

## Scenario B — Tag Lookup Batch Accuracy (200 NL Queries)

- **Command:**
  ```bash
  uv run pytest tests/e2e/test_success_validation.py::test_tag_lookup_batch_accuracy_and_clarifications -q
  ```
- **Acceptance hook:** Ensures ≥90 % of 200 NL descriptions resolve to the correct path while the remaining low-confidence (<0.7) cases emit clarifying questions such as:
  `Can you specify the site, equipment, or engineering units for kiln, shell, temperature? For example: 'Maceira kiln 6 shell temperature in section 15 (°C)'.`
- **Artifact:** `docs/artifacts/story-4-5-tag-lookup-batch.json` captures the last run (182 high-confidence paths, 18 clarifications, 0 misses). Reference it in PRs/handovers instead of screenshots.
- **Usage tip:** Feed the clarifying prompt back into the workflow with site/unit context; the next invocation should move into the ≥0.9 confidence bucket.

> 🧩 *Extra Scholar Info:* Tracking clarifications is as important as accuracy—LLMs must show they *know when they do not know* to avoid silent misreads.

---

## Scenario C — Performance Ceiling (p95 < 10 000 ms)

- **Command:**
  ```bash
  uv run python scripts/benchmark.py --scenarios single
  ```
- **Reference artifact:** `docs/artifacts/benchmark-results-20251101-094941.json` (p95 = 0.12 s ≪ 10 000 ms).
- **What to note:** Keep response payloads ≤1 MB (guarded centrally) so latency remains dominated by Canary, not JSON marshalling. When p95 approaches 10 s, inspect cache hit rates via `get_cache_stats`.

> 🧩 *Extra Scholar Info:* Even though Story 4.5 allows a generous 10 s ceiling, holding p95 under 300 ms for metadata calls leaves plenty of headroom when Canary slows down.

---

## Scenario D — Documentation & Re-Runs

1. Validate MCP workflow prompts stay in sync: `docs/workflows/prompt-workflows.md` ↔ new tests.
2. Record every successful batch run by updating `docs/artifacts/story-4-5-tag-lookup-batch.json` (timestamp + accuracy).
3. If ambiguity increases, edit `_build_clarifying_question` once and re-run Scenario B.
4. Include summary snippets like the table above in `docs/examples.md` when showcasing new analyses.

> 🧩 *Extra Scholar Info:* Operators trust MCP responses when they can trace numbers back to site/time contexts—keeping the success scenarios “live” makes regressions obvious within a single pytest invocation.
