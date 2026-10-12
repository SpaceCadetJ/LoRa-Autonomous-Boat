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

## IMU bias-filter amendment claim - 2026-09-18 UTC

Codex root claims reviews/codex/imu_bias_filter/**, current viewer/application/handoff links and captured-evidence CI for a new isolated schematic revision adding only C43 (100 pF) from PCA9306_BIAS to GND. Prior IMU and placement packets remain immutable. Read-only child imu_bias_review checks electrical intent and final native delta. Preserve all live CAD, BOM, firmware and the two unrelated local tool edits. No PCB generation/routing, hardware access, ordering or branch changes.

## IMU2 review checkpoint - 2026-09-18 UTC

Independent read-only review is complete; child claim released. Root finishes candidate viewer/CI records and ordinary selective publication. Live CAD, purchasing, firmware and historical candidate/placement evidence are preserved. The next bounded scope follows the imu_bias_filter handoff: 6S power envelope before final routing.

## 6S power envelope claim - 2026-10-12 UTC

Codex root claims reviews/codex/power_envelope/** and current viewer/application/handoff/portfolio links plus captured-evidence validation for a bounded 6S input and footprint review. Child power_limits_review is read-only. Expected electrical delta is zero: preserve all live CAD, BOM, firmware, historical evidence and the two unrelated dirty tools. No full generation/routing, physical hardware access, ordering or branch changes.

The power-envelope scope includes procurement holds and derived purchasing exports for newly verified part/package conflicts; original schematic/BOM source and V1 outputs remain preserved. This updates review eligibility only.

## 6S power review checkpoint — 2026-10-12 UTC

Independent read-only review passed and is released. Root closes the power-envelope/ordering/viewer packet with selective publication. New C1/F1 package and D2 value findings are held; live CAD and original BOM remain unchanged. Next bounded scope is the two-topology 6S load/protection/package comparison in power_envelope/README.md. No active child write claim remains.

## 6S power topology comparison claim — 2026-10-12 UTC

Codex root claims reviews/codex/power_topology/**, current viewer/guide/handoff/portfolio links and portable comparison checks. Child power_cutoff_review is read-only. This packet compares explicit proposed power boundaries and load/package budgets; expected live electrical/copper delta is zero. Preserve prior captured reviews, original CAD/BOM/firmware and the two unrelated dirty tools. No routing/generation, orders, hardware access or branch/history changes.

## Input-stage schematic claim — 2026-10-12 UTC

Codex root claims reviews/codex/input_stage/**, current viewer/guide/handoff/portfolio links and captured-evidence checks. Children input_protection_review and power_native_review are read-only. Build one isolated 6S input schematic with a fuse, bidirectional TVS and 100 V series reverse diode; the diode replaces the screened controller after coupled positive/negative pulse analysis. Explicit expected candidate delta is recorded before native export; live electrical/copper delta remains zero. Preserve all historical packets, original Allegro/V1 and both unrelated dirty tools. No primary generation/routing, orders, hardware access or branch/history changes.

Input-stage child power_native_review now owns only reviews/codex/input_stage/verify_candidate.py and test_candidate.py for independent delta validation. All other child work remains read-only.

## INPUT-A1 review checkpoint - 2026-10-12 UTC

The input-stage native candidate, fourteen mutation tests, independent claim review and desktop/phone viewer checks are complete. Child write scopes are released. Root closes selective publication of this isolated study and current viewer/guide records. All parts remain held; live CAD/copper/BOM/firmware are unchanged. The next bounded circuit task is an explicit negative-output/reverse-leakage amendment, as recorded in input_stage/README.md. Preserve INPUT-A1 and both unrelated dirty tools.

## Reverse-leakage boundary claim - 2026-10-12 UTC

Root claims reviews/codex/reverse_leakage/** and current viewer/guide/portfolio/check/handoff integration for a bounded negative-rail design disposition. No CAD amendment is accepted before coupled leakage, polarized capacitor and downstream startup limits are addressed. Expected live/candidate electrical and copper delta is zero; preserve INPUT-A1, all prior packets and unrelated v1_design.py / route_v2.py edits. Child power_native_review owns only reverse_leakage/model.py and test_model.py; input_protection_review remains read-only. No primary generators, routing, hardware access or ordering.

## Reverse-leakage review checkpoint - 2026-10-12 UTC

The bounded source review, seven analytical tests and desktop/phone scenario checks are complete. Child write scopes are released. Root closes selective publication; INPUT-A1 and all live CAD/copper/BOM/firmware remain unchanged. No new native or hardware acceptance is claimed. Next: reservoir and first-buck input-network selection, with complete leakage and sequencing constraints as recorded in reverse_leakage/README.md. Preserve both unrelated dirty tools.

## Input capacitor network claim - 2026-10-12 UTC

Root claims reviews/codex/input_capacitors/** and current viewer/guide/portfolio/check/handoff integration for a bounded nonpolar reservoir and first-converter local bypass specification. Child power_native_review owns only input_capacitors/model.py and test_model.py; input_protection_review remains read-only. Expected live/candidate electrical and copper delta is zero until complete leakage and capacitance bounds permit a native amendment. Add a separate reviewed footprint proposal and clear proposed connection drawing, without changing INPUT-A1, IMU2, live CAD, purchasing or firmware. Preserve historical evidence and unrelated v1_design.py / route_v2.py edits. No generators, routing, hardware access, ordering or branch/history changes.


## Input capacitor network checkpoint — 2026-10-12 UTC

Model, native footprint inspection, independent geometry/claim review and desktop/phone viewer checks are complete. Child write claims are released. Root closes selective publication of CAP-01. All live/candidate electrical and copper inputs, purchasing, firmware and historical packets remain preserved. Next scope: isolated first 3.3 V converter cell using input_capacitors/README.md, with effective-capacitance, damping, leakage and ADC gates retained. Exclude unrelated v1_design.py / route_v2.py edits.

## First 3.3 V converter claim - 2026-10-12 UTC

Root claims reviews/codex/buck_3v3/** and current viewer/application/portfolio/handoff/CI integration for an isolated INPUT-A1-derived first converter schematic. Preserve every live CAD/copper/BOM/firmware input, INPUT-A1/CAP-01/IMU2 and unrelated v1_design.py / route_v2.py edits. Expected candidate boundary is U2,L1,C3-C6,R2-R5,D3: remove R2/R3/C4/D3; replace U2 and supporting identities; add C44-C48 for local input, HF, output and VCC bypass. Exact pin/identity contract will be saved before native export. Child power_native_review and input_protection_review are read-only circuit-source reviewers; imu_candidate_validator is read-only pending a specific verifier scope. No primary generation/routing, live-board replacement, ordering, hardware access or branch/history changes. Capacitance, damping, negative-rail and ADC integration gates remain open.

First-converter child imu_candidate_validator owns only reviews/codex/buck_3v3/verify_candidate.py and test_candidate.py for independent expected-contract/native delta verification. Child power_native_review may write only buck_3v3/model.py and test_model.py for analytical screens. Root owns all remaining packet artifacts and integration.

## BUCK33-A1 review checkpoint — 2026-10-12 UTC

Independent native-contract review, source/claim review and native package inspection are complete; all child write claims are released. Root closes viewer/guide/evidence integration and selective publication of the isolated first-converter packet. Live CAD/copper/BOM/firmware and all older packets remain unchanged. The next bounded circuit scope follows buck_3v3/README.md: isolated 5 V converter and simultaneous-load budget, then named power/ADC/buffer integration gates. Preserve unrelated v1_design.py and route_v2.py edits. No primary generator, router, hardware, order or branch/history action is authorized by this checkpoint.

## Second converter claim — 2026-10-12 UTC

Root claims reviews/codex/buck_5v/** and current viewer/application/portfolio/handoff/CI integration for an isolated BUCK33-A1-derived 5 V converter and simultaneous-load budget. Baseline is commit358371e; preserve first-converter source and all live CAD/copper/BOM/firmware, previous packets, and both unrelated tool edits. No primary generators/routing or hardware actions. Exact regulator identity must be primary-source verified; expected old/new part and physical-pin delta precedes native capture. Children input_protection_review and power_native_review are read-only source reviewers; power_native_review may write only buck_5v/model.py and test_model.py. Preserve 6S and both external-BEC and optional on-board-actuator configurations. No release/power acceptance follows from ERC.

## BUCK5-A1 review checkpoint — 2026-10-12 UTC

All second-converter child write scopes are released after native-contract, numerical and package review. Root closes viewer/guide/CI publication and records the confirmed D4/D9 SMC/SMA finding in existing procurement holds plus derived review exports. Live CAD/copper/BOM source/firmware, V1 outputs, prior packets and both unrelated tool edits remain unchanged. Next scope follows buck_5v/README.md: isolated buffer/OR-ing supply correction before full input-feed and combined IMU2 integration. No live PCB replacement, primary generation/routing or hardware action.

## Actuator supply claim - 2026-10-12 UTC

Root claims reviews/codex/actuator_supply/** and current viewer/application/portfolio/CI integration for an isolated BUCK5-A1-derived buffer rail and diode population amendment at c3c38bd. Preserve both converter source sheets, all live CAD/copper/firmware/ordering and older packets. Child imu_candidate_validator writes only verify_candidate.py/test_candidate.py; input_protection_review and power_native_review initially review primary sources read-only. No primary generator/router, branch change, orders or hardware access. Preserve both unrelated tool edits. Exact expected pin/identity delta precedes native export.

ACT-01 scope update: the new unconfirmed C11 identity finding is recorded in current procurement holds and derived review exports. Source BOM/CAD and V1 outputs remain preserved; no part is released for ordering.

## ACT-01 review checkpoint - 2026-10-12 UTC

All child write scopes are released. Root closes viewer, guide, CI and selective publication of the isolated buffer supply/population candidate and the C11 procurement hold. Exact electrical delta, original ERC warning, 31 tests and remaining limits are recorded in actuator_supply/README.md and review_notes.json. Live CAD/copper/source BOM/firmware, V1 outputs, older packets and unrelated tool edits remain unchanged. Next bounded task is default-disabled enable and sequencing on a new copy; no hardware or primary generation/routing action.
