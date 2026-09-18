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

## Codex active claim — 2026-09-17T01:26:21.7991985Z

Codex claims exclusive write in pm/**, docs/atlas/**, reviews/codex/** for interactive viewer, generated source/connector data, independent S2 validation, and protocol correction prototype. Primary's explicit release is acknowledged. Child agents have disjoint subscopes assigned by Codex. Root coordination remains append-only. No primary generators or firmware/CAD writes.


## Codex packet checkpoint — 2026-09-17T19:16Z

Viewer/portable-atlas packet finished; child writes completed. Released-to-Codex scope remains pm/**, docs/atlas/** and reviews/** for subsequent bounded packets. No claim is made on primary CAD/firmware. Shared coordination stays append-only. Primary may selectively integrate the delivered Codex files; see latest HANDOFF.


## User-authorized takeover — 2026-09-17

Jay explicitly stated Codex is the only active agent and requested professional schematics, ordering/assembly, V1/V2 flashing and a reviewable CI/CD workflow. This supersedes the earlier primary-agent write reservations for this work. Codex root claims hardware/kicad/tools/gen_sch.py, a shared schematic layout module, hardware/kicad_v2/tools/gen_v2.py, generated schematic exports, pm integration and review handoff. Existing dirty PCB/v1_design/route tool changes are preserved. Child scopes: docs/build flashing files + firmware/tools; manufacturing exports + assembly/order docs; tools/quality + .github/workflows + quality review evidence. Allegro remains immutable. No orders, publishing, hardware flashing, branch switches or history changes are implied.

## Codex review packet complete — 2026-09-17T20:42Z

The user-authorized schematic, ordering/assembly, programming-documentation, viewer and quality-tool scopes above are complete and available for review. No child agent has an active write claim. The latest handoff identifies all source/generated outputs and unchanged PCB hashes. Subsequent Codex packets may continue within Jay's authorized task after checking newer claims; the previous primary-only reservations do not silently resume merely because this packet ended. Coordinate a new bounded claim before CAD/circuit or firmware implementation changes. Allegro remains immutable; Git integration, external orders/publication and hardware flashing were not performed.

## Publication authorized — 2026-09-17

Jay explicitly requested committing and pushing the project to the existing GitHub repository so his portfolio agent can use it. Codex claims the integration/documentation/portability scopes necessary for that publication. Current V2 PCB will be included as the reviewed pre-existing draft snapshot. Unfinished pre-existing v1_design.py and route_v2.py edits will remain local and unstaged; their consumed definitions/current evidence do not depend on those edits. Allegro source evidence is preserved. Commit/push authorization supersedes the earlier no-publication/no-Git constraints for this delivery; hardware fabrication/flashing remains outside this publication task.

## Design completion and application guides — 2026-09-17

Jay requested continued improvement toward a finished design and guides for different applications. Root claims V2 correction integration, `tools/quality` readiness checks, `pm/**`, current documentation and review coordination. Child claims are disjoint: `reviews/codex/design_completion/ground/**` for isolated copper analysis/candidate; `reviews/codex/design_completion/electrical/**` for manufacturer-backed circuit audit; `docs/applications/**` for application guides/index. Live Allegro and V1 evidence remain preserved. The existing dirty `v1_design.py` and `route_v2.py` remain excluded. Verified updates may be committed/pushed to the already authorized repository. Physical programming, purchasing and fabrication are not performed by this packet.

## Design/application review complete - 2026-09-17

Root integrated the reviewed V2 ground candidate and separate firmware_v2 Stage A diagnostic. Child scopes docs/applications, electrical, ground and mcu_ground are released; their handoffs identify exact inputs and limits. Root retains current documentation, viewer and selective publication integration through final checks. Later packets may implement reviewed V2 corrections after checking newer claims. The existing v1_design.py and route_v2.py local edits remain outside this packet. Preserve original Allegro/V1 evidence; no orders, real hardware programming or history rewrite.

## IMU candidate packet - 2026-09-18 UTC

Codex root claims reviews/codex/imu_interface/**, the current review handoff and viewer integration for an isolated E-01 schematic correction candidate. The live V2 circuit and corrected PCB remain unchanged until candidate electrical delta, symbol/package review and native checks are recorded. Independent child imu_interface_review is read-only. No V1/Allegro, unrelated generator/routing edits, full PCB generation, hardware access or ordering.


## IMU candidate review checkpoint - 2026-09-18 UTC

Candidate generation, native exports, independent pin/part validation and eight rejection tests are complete. Child scopes are released. Root closes out the candidate viewer/portfolio records and ordinary selective publication. Live CAD, BOM and firmware remain unchanged. The next authorized packet is placement feasibility on a copy of the corrected PCB; the prior two unrelated local tool edits remain excluded.

## IMU placement feasibility claim - 2026-09-18 UTC

Codex root claims reviews/codex/imu_placement/** and current viewer/handoff integration for a placement study on an isolated copy of the corrected PCB. Existing live CAD, circuit memberships, purchasing exports and Stage A evidence remain unchanged. Child imu_placement_review is read-only. Preserve all existing copper and the 80 x 46 mm outline in the study; record collisions and routing constraints instead of silently deleting or rerouting. Placement is not electrical integration or fabrication approval. Existing v1_design.py and route_v2.py local edits remain excluded.

## IMU placement checkpoint - 2026-09-18 UTC

Read-only child review is complete and released. Root completes the isolated placement packet, viewer, captured-evidence CI and selective commit/push. No live CAD or circuit changes were made. Subsequent circuit work starts with the imu_placement handoff; the existing two unrelated local tool edits remain excluded.
