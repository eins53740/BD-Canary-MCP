# Prompt Workflow Playbooks

This document captures the canonical steps for the two MCP prompts: `tag_lookup_workflow` and `timeseries_query_workflow`. Both workflows assume the Secil Maceira/Outão datasets and the auxiliary resource `docs/aux_files/Canary Resources/Canary_Path_description_maceira.json`.

### Language & domain guidance

All MCP clients should search using bilingual keywords—English plus the site's native Portuguese terms—so that the tag catalog is queried with every plausible synonym. For the Portuguese sites (Maceira, Outão, Pataias, Montijo, Rio Maior, and Martingança) make sure Portuguese keywords are included alongside the English ones. Translating the user's natural-language prompt is acceptable if it helps surface the right tags, variables, and ancestor paths within the Canary historian datasets.

Keep in mind this database documents industrial-process telemetry: PLCs, temperature sensors, pressure transmitters, and other control systems feed raw operational data that is normalized, processed, filtered, or aggregated into derived metrics. It also stores KPIs aggregated over weekly, monthly, and other intervals. That context—plant performance, maintenance, product quality, and environmental compliance—should steer interpretations so the MCP clients can surface actionable insights for engineers and operators.

---

## `tag_lookup_workflow`

**Inputs**
- Natural-language description (equipment, measurement, site, units)
- Optional hints collected during prior clarification

**Outputs**
- `most_likely_path` (if confidence ≥ 0.70)
- Ranked `candidates` and `alternatives`
- `confidence` (0‑1) and `confidence_label` (`high`, `medium`, `low`, `no_match`)
- `clarifying_question` and `next_step` when additional context is required

**Deterministic Steps**
1. Parse the description → entities (equipment, measurement, location, units). Remove stop words and normalize synonyms (rpm↔speed, °C↔degC, shell↔casing).
2. Query `resource://canary/tag-catalog` via `get_asset_catalog` using the strongest keywords. Retain matching entries (path, unit, description).
3. If fewer than three matches remain, call `search_tags` with the best literal keyword (avoid wildcards) scoped to `Secil.Portugal` or the user-provided site.
4. For each candidate path:
   - Call `get_tag_properties` to pull units, description, and other metadata.
   - Score keywords (name weight > path > description > metadata). Record matched keywords per field.
5. Compute confidence using the top score plus the margin over the runner-up.
   - `confidence ≥ 0.80` → `next_step = "return_path"` (safe to proceed).
   - `0.70 ≤ confidence < 0.80` → `next_step = "double_check"` (suggest verifying units/section).
   - `confidence < 0.70` → `next_step = "clarify"` and include a `clarifying_question` (ask for site, equipment, units, or time window).
6. Return an actionable response:
   - Populate `message` with guidance (“Proceed to read_timeseries”, “Double-check units via get_tag_properties”, or the clarifying question).
   - Include `alternatives` so agents can offer backup options.
   - Always echo the interpreted keywords so the operator can confirm the workflow understood their intent.

**Example**
```
User: “Need kiln 6 shell temperature in section 15”
Workflow:
  - Keywords → kiln, shell, temperature, section, 15
  - Catalog + search_tags → Secil.Portugal.Kiln6.Section15.ShellTemp
  - Metadata confirms units = degC
  - Score = 23.4 (high), confidence = 0.91 → return path
Response: success, confidence high, message “High-confidence match…”, next_step “return_path”
```

**Actionable Errors**
- Empty description → ask for the site/equipment explicitly.
- No candidates → prompt for site/equipment/units.
- Metadata failures → explain which call failed and suggest retrying with `bypass_cache=true`.

---

## `timeseries_query_workflow`

**Inputs**
- Tag path (preferably produced by the lookup workflow)
- Natural-language start/end or relative expressions
- Optional view or sampling hints

**Outputs**
- Canonical start/end ISO timestamps
- `read_timeseries` payload parameters
- Summary of returned samples (count, units, gaps, continuation tokens)
- Suggested next action (e.g., “compute min/max”, “compare with kiln pressure”)

**Deterministic Steps**
1. If a tag description is provided instead of a path, call `tag_lookup_workflow`. Obey its `clarifying_question` before querying data.
2. Parse the natural-language time window using `resource://canary/time-standards`:
   - Interpret expressions in Europe/Lisbon.
   - Echo the normalized ISO timestamps back to the user.
3. Build the `read_timeseries` payload:
   - `tag_names`: list of fully qualified paths (ensure list, not JSON string).
   - `start_time` / `end_time`: ISO strings.
   - `views`: optional site-specific view; page_size ≤ 1 000.
4. Call `read_timeseries` (POST). If `continuation` is returned, loop until the request range is exhausted.
5. Summarise the results:
   - Mention tag units, sample count, any data gaps or quality flags.
   - Include the interpreted time window and any adjustments made.
   - If no samples, fall back to `get_last_known_values` and state that explicitly.
6. Provide the recommended next step (e.g., “Run rolling average”, “Ask for a narrower window”, “Compare against shell pressure tag”). Ensure every error includes remediation guidance (“Check CANARY_VIEWS_BASE_URL”, “Provide ISO timestamps”, etc.).

**Example**
```
User: “Show kiln 6 shell temperature for the last 2 hours”
Workflow:
  - tag_lookup_workflow → Secil.Portugal.Kiln6.Section15.ShellTemp
  - Time parsing → start=Now-2Hours, end=Now (echoed as ISO)
  - read_timeseries called with POST, page_size=600
  - Result summary: 720 samples, units degC, no continuation
  - Suggested next step: “Need aggregate statistics?”
```

---

These playbooks ensure every MCP client follows the same deterministic, auditable sequence, making outputs explainable and keeping plant engineers in control. Update this document whenever workflow prompts evolve so documentation, prompts, and tests stay in lockstep.
