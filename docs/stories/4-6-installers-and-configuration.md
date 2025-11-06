# Story 4.6 — Installers and Configuration

Context & Constraints:
- Non-admin Windows users; per-user install preferred.
- STDIO transport first; remote HTTP optional and documented.
- Include local references to API docs in `docs/aux_files/Canary API` for READ/WRITE endpoints.

Acceptance Criteria (Checklist):
- `.cmd` installers verified; README updated for STDIO and remote HTTP flows.
- Install validation steps clearly documented (success criteria, quick checks).
- No elevated privileges required for STDIO mode.

Validation:
- Follow docs/installation guides; confirm environment loads and `ping` works.
- Record known issues and mitigations in troubleshooting docs.

Deliverables:
- Updated installer notes and configuration sections in docs.
- Clear side-by-side paths: local STDIO vs remote HTTP.
 - README pointer to token creation and Tag Security notes; example `.env` entries.
