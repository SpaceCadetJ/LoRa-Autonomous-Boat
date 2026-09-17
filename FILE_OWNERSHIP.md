# Shared file ownership

Established by Codex on 2026-09-17 UTC after read-only inspection. Primary-agent activity is observed, not a negotiated handoff. Conservative reservations below protect its work. An old timestamp, completed command, or absence of a lock is not a release.

| Owner | Scope | Mode | Started UTC | Release condition | Status |
|---|---|---|---|---|---|
| Primary agent (observed; reservation) | `hardware/**`, `docs/**`, `firmware/**`, `README.md`, `REPORT.md`, `AGENT_PROMPT_V2.md`, `.gitignore`, `CONVERSION_LOG.md` | exclusive write | earlier active session; exact start unknown | Explicit scope and revision handoff from primary | ACTIVE |
| Codex | `reviews/codex/**`, `AGENT_STATUS.md`, `HANDOFF.md`, `BLOCKERS.md`, `FILE_OWNERSHIP.md` | exclusive write for user voice-scope update | 2026-09-17 UTC, after initial checkpoint | Voice/text/location scope and feasibility packet recorded; released | RELEASED |
| Codex | `reviews/codex/**` | exclusive write | 2026-09-17T00:08:00Z | Released 2026-09-17T00:19:00Z; review packet and resume instructions recorded | RELEASED |
| Codex | `AGENT_STATUS.md`, `FILE_OWNERSHIP.md`, `HANDOFF.md`, `BLOCKERS.md` | exclusive write during initial coordination setup | 2026-09-17T00:08:00Z | Released 2026-09-17T00:19:00Z; subsequent writers append dated sections after checking claims | RELEASED |

`Allegro/**` remains immutable source evidence. No branch, index, tag, or commit changes by Codex while the primary is active. These records do not claim that the primary has read or accepted them. Do not edit its files to correct findings; record findings in the review packet.

## Update — 2026-09-17 — Primary release

| Owner | Scope | Mode | Status |
|---|---|---|---|
| Primary (Claude Code) | `hardware/**`, `firmware/**`, `docs/**` except released paths, `README.md`, `REPORT.md`, `CONVERSION_LOG.md`, `.gitignore`, `.gitattributes`, git commits/tags | exclusive write | ACTIVE |
| Codex | `pm/**`, `docs/atlas/**`, `reviews/**` | exclusive write | RELEASED TO CODEX at commit 639e08f |
| Both | `AGENT_STATUS.md`, `HANDOFF.md`, `BLOCKERS.md`, `FILE_OWNERSHIP.md` | append dated sections only | SHARED |
