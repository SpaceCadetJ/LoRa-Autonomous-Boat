# LoRa engineering workspace

## Current verification packet — ACT-06, 2026-10-13 UTC

The [supervisor comparison](../reviews/codex/supervisor_comparison/README.md) now provides concrete divider values, five verified integrated-window identities, recovery/error-budget calculations and a [proposed local-permission path](../reviews/codex/supervisor_comparison/v2_supervisor_comparison.svg). Nineteen tests pass for this conditional screen. Neither option closes the complete timing/power boundary; ACT-04 stays native and default disabled. Next: one 3.3 V observation subcell with applicable maximum detection delay and positive divider/reference guard. This supersedes earlier next-task text below.

## Current verification packet — ACT-05, 2026-10-12

The [rail-supervision selection review](../reviews/codex/rail_qualification/README.md) and [interactive interval explorer](../reviews/codex/rail_qualification/index.html) show why the first fixed-window proposal is held: assertion/recovery conflicts, unknown maximum detection delay and an illustrative input-edge violation. Calculations include a separate accuracy-basis sensitivity; no silicon or hardware acceptance is inferred. ACT-04 remains the latest native circuit, with qualification and ACK default low. Next: compare an adjustable window with an integrated window/reset candidate and conditioned edges. This supersedes earlier next-task text below.

## Current actuator packet - ACT-04, 2026-10-12

The [isolated arm latch and annotated native sheets](../reviews/codex/actuator_latch/README.md) separate PC4 from OE while retaining R40 at OE. Native ERC is zero errors / the original AD0 warning; 396 existing memberships are preserved and exactly two change. The qualification and ACK sources remain unimplemented and default low. ACK while armed disables, a documented difference from ACT-03. Next: qualification/reset-release circuitry with fault retention and conditioned ACK; receiver readiness and watchdog sources remain held. This supersedes older next-task text below.

## Current actuator packet - ACT-03, 2026-10-12

The [interlock behavior and observability prototype](../reviews/codex/actuator_interlock/README.md) adds interactive fault scenarios, an executable deliberate-rearm contract and a receiver acceptance worksheet. Exact ACT-02 pin evidence confirms no receiver sensing and unused converter PG pins. No CAD/firmware change or new native acceptance is claimed. Next: isolated fault-dominant latch/OE gate with the PC4 request separated from OE and R40 retained; unimplemented qualifications must remain default-disabled. This supersedes older next-task text below.

## Current actuator packet - ACT-02, 2026-10-12

The [default-disabled translator and sequencing contract](../reviews/codex/actuator_enable/README.md) now has an annotated native schematic: TXU0102DCUR, PC4 arm signal and 10k hardware pulldown. Independent checks preserve 383 outside-boundary pins, both converters and ACT-01 source populations; 41 tests pass and ERC adds no findings. Firmware, ordering and live PCB are unchanged. Next: receiver-power observation and a hardware arm interlock, including independent ESC readiness in both populations. This supersedes older next-task text below.

## Current actuator packet - ACT-01, 2026-10-12

The [buffer supply and population review](../reviews/codex/actuator_supply/README.md) moves exactly four buffer/bypass pins to the dedicated 5 V converter, preserves both converter sheets and adds exact SMC diode identities with mutually exclusive BEC_ONLY/ONBOARD proposals. All 380 outside-boundary pins are preserved; no new ERC findings. A new C11 identity hold changes V2 ordering to 68 candidate / 39 held / 11 feature references, 35 candidate lines. Next: default-disabled buffer enable and power sequencing, followed by reservoir/transient and remaining integration gates. This supersedes older next-task text below.

## Current converter packet — BUCK5-A1, 2026-10-12

The [5 V converter and shared-feed review](../reviews/codex/buck_5v/README.md) now includes an annotated native LM76003 sheet: 119 components, 398 physical pins, all 339 outside-boundary pins preserved, zero ERC errors and the original warning. The first 3.3 V sheet is byte-identical. New SS34 SMC/SMA package findings are added to existing ordering holds; the 7 V full-load feed remains unqualified. Next: isolate the buffer supply from VSERVO and resolve exact OR-ing parts and supply population variants, then input-feed/leakage/damping and remaining integration gates. This entry supersedes older next-task text below.

## Current converter packet — BUCK33-A1, 2026-10-12

The [complete first 3.3 V converter](../reviews/codex/buck_3v3/README.md) now has a separate annotated sheet, exact supporting parts and native validation: 113 components, 361 pins, all 330 outside-boundary pins preserved, zero errors and the original ERC warning. This is an isolated INPUT-A1-derived candidate; live CAD, copper, purchasing and firmware remain unchanged. Capacitance, thermal, loop, input leakage and ADC gates remain open. Next: the isolated 5 V converter and its simultaneous-load budget, retaining 6S and the optional on-board actuator configuration. This entry supersedes older next-task text below.

## Current input-network packet — 2026-10-12

The [nonpolar reservoir and local bypass specification](../reviews/codex/input_capacitors/README.md) now includes exact screened identities, an annotated connection drawing, capacitance requirements and a native-checked TDK land-pattern proposal. No circuit changed; source damping, effective capacitance and complete leakage remain integration gates. Next: the isolated first 3.3 V wider-voltage converter cell with explicit pin delta and those holds retained. This entry supersedes older next-task text below.

## Current decision: reverse leakage and startup — 2026-10-12

The [boundary review](../reviews/codex/reverse_leakage/README.md) and [interactive cases](../reviews/codex/reverse_leakage/index.html) show why a diode/bleeder amendment cannot yet be accepted: C1 prohibits reverse voltage, and a diode-only current budget omits downstream paths. No circuit changed. Next: select a nonpolar reservoir with the first wider-voltage buck bypass, then close complete powered/unpowered leakage and ADC sequencing before native amendment. INPUT-A1 remains the preserved schematic candidate.

## Current circuit packet: INPUT-A1 — 2026-10-12

The [wired input-stage schematic](../reviews/codex/input_stage/README.md) implements an isolated fuse/TVS/100 V series-diode candidate. Exact native delta passes: 112 components, 356 pins, all 344 outside-boundary memberships preserved; no new ERC findings. Live CAD, ordering and the separate IMU2 candidate remain unchanged. Next: resolve discharged-output reverse leakage against downstream pin limits, then implement the wider-voltage converter cells. Surge energy, footprint/thermal qualification and physical acceptance remain open.

## Current power architecture study — 2026-10-12

The [topology comparison](../reviews/codex/power_topology/README.md) recommends a wider-voltage input stage for the next isolated schematic study. The [interactive load budget](../reviews/codex/power_topology/load_budget.html) exposes why the simultaneous rail goals cannot fit a 1 A feed at 7 V. Exact package-pin proposals, cutoff tolerance calculations and an annotated power-path map are recorded. No live circuit or ordering changes. Next: one captured input-stage schematic, exact protection identities and a bounded surge/stored-energy envelope; preserve 6S and the on-board actuator option.

## Current power review — 2026-10-12

The [6S power envelope](../reviews/codex/power_envelope/README.md) records voltage boundaries, new C1/F1 package conflicts and D2 value drift. Its viewer map is a planning review, not a PCB revision. V2 purchasing now has 69 candidate / 38 held / 11 board-feature references and 36 candidate order lines. Earlier totals below describe previous checkpoints. The newer topology study above supersedes this checkpoint’s next task.

## Latest circuit revision: IMU2

The [IMU2 bias-filter amendment](../reviews/codex/imu_bias_filter/README.md) is the current isolated schematic candidate. C43 adds two connections; all 398 previous memberships and the original ERC finding are preserved. Live hardware and ordering remain unchanged. Coordinate final routing with the current power-architecture study above.

## Current IMU placement review

The [placement review](../reviews/codex/imu_placement/README.md) maps the twelve additions and a filter reserve. Courtyards fit, but 136 native errors identify required copper work; complete 6S fit is unresolved. The V2 Design viewer includes the obstacle map. Start with the new circuit/power/routing restart order.

## Current IMU correction candidate

The [isolated 1.8 V IMU circuit](../reviews/codex/imu_interface/README.md) is available in the V2 Design viewer. Exactly five existing connections change; native comparison and ERC checks pass their scoped acceptance. It is not integrated into the PCB, BOM or firmware contract. Start with its placement/routing handoff; the six live electrical blockers remain open.

## Current application and diagnostic edition

Use **Use by application** for the [application handbook](../docs/applications/README.md), with separate V1 bench, V2 boat, rover, telemetry and handheld guides. The separate [V2 Stage A diagnostic](../firmware_v2/README.md) builds for board identity and inactive actuator outputs; it is not operational control firmware. The [component-limit review](../reviews/codex/design_completion/electrical/README.md) identifies six circuit blockers beyond the CAD warning count. Current affected parts are held in the ordering package. The integrated ground repair now has zero unconnected items and zero ordinary DRC errors, with unchanged warning/parity counts. V2 ordering has 74 candidate, 33 held and 11 bare-feature references. Start at the [current handoff](../reviews/codex/design_completion/HANDOFF.md); the next circuit packet is the IMU 1.8 V supply/interface correction. Earlier ground-count, no-V2-image and no-publication statements below describe previous checkpoints.

Open [index.html](index.html) directly in a browser. The generated page contains its data and application code; no install or build step is required to view it. Keep it in this repository so images, schematics and evidence links resolve.

For the local HTTP viewer, run from the repository root:

```powershell
node pm/tools/serve.mjs
```

Then open <http://127.0.0.1:8765/pm/>. The server binds only to this computer, serves selected project paths and does not modify repository files. Stop it with Ctrl+C. This does not publish the project.

## What to explore

- Overview: phases, evidence gates and the next review tasks.
- Design: V1/V2 schematic sheets, available PCB renders, PDF drawings and source KiCad files. Choose a view and zoom to inspect it.
- BOM: searchable V1/V2 parts, component details and selected manufacturer datasheets. An unmapped part explicitly says its exact datasheet is not yet linked. Prices are dated source estimates.
- Build & program: V1/V2 ordering candidates, held and external parts, assembly maps, inspection steps, firmware build and separate programming procedures. The guides distinguish the unqualified V1 image from the V2 Stage A diagnostic and future operational firmware.
- Connector atlas: V1 connector pins, firmware cross-references, voltage expectations and known defects. Bench readings are expectations, not measurements.
- Software: current source and proposed correction files, clearly separated from integrated firmware.
- Verification: independent V1 checks, primary reports and input fingerprints.
- Traceability: V1 findings linked to the primary's V2 requirements and acceptance methods.
- Decisions: working defaults, open choices and private browser notes. Notes stay in this browser; export the handoff to save a copy. They are not written back to project files.
- Documents: searchable embedded documentation and the repository file map.

## Refresh evidence

For the published edition, recorded firmware/primary reports are stored under `docs/build/evidence/`; V1 schematic generation has verified tracked inputs. Rebuilding the viewer no longer needs this workstation's ignored CAD/compiler caches. The current portable native snapshot is [design_completion/native-review](../reviews/codex/design_completion/native-review/REVIEW.md). Downloaded source archives can rebuild without Git, using a `source-archive` revision label. See the [publication record](../reviews/codex/publication/README.md).

Only after checking [ownership](../FILE_OWNERSHIP.md), current [handoff](../HANDOFF.md), Git status and primary release notes:

```powershell
node pm/tools/build.mjs
node pm/tools/validate.mjs
```

The builder reads evidence and writes only `pm/index.html` and `pm/status.json`. It never invokes CAD/firmware generators. In HTTP mode use Refresh after building; with a directly opened file, reload the page. Editing `index.html` directly loses changes on rebuild; edit `index.template.html` instead.

The snapshot records branch/HEAD and SHA-256 hashes of consumed text/report inputs. Working files may differ from HEAD. Changed-during-build detection covers hashed inputs, not a repository lock or a full media/CAD archive. Images and CAD links load current files from the repository; independent S2 results refer to the separately identified historic snapshot.

## Earlier schematic review edition — 2026-09-17

Jay authorized Codex to improve schematics, ordering/assembly and programming documentation while the other agent is inactive. This supersedes earlier conservative primary-only edit reservations for the delivered packet. Start at [build and programming](../docs/build/README.md) and the [professionalization handoff](../reviews/codex/professionalization/HANDOFF.md), then check the latest ownership before editing.

All fifteen schematic pages now have grouped components, separate label/property spacing and engineering annotations. PDF/SVG exports share a source/output hash manifest. The latest independent numbered review is captured automatically in the viewer: all 172 V1 and 361 V2 electrical pins preserve the prior design. V1 ERC is clean; V2 has one pre-existing pin-type warning, so the strict combined review remains failed. V2 PCB checks report three unconnected entries, 101 warnings and 212 parity entries. Fabrication is not approved.

The purchasing packet distinguishes complete BOM reviews from partial candidate import lists: V1 has 20 candidate / 18 held / 6 bare-feature references; V2 has 90 / 17 / 11. Assembly maps, optional population decisions and first-power procedures are linked. Existing firmware builds reproducibly on the recorded toolchain but preserves original defects; no hardware was flashed and there is no V2 firmware image. The manual CI definition is local and has not been activated or pushed.

**Next smallest task:** classify V2's three open PCB connections against their exact pad/net evidence, and review the pre-existing U6 AD0 warning against the selected sensor interface. Produce a correction proposal before changing circuit intent or routing. Then freeze the V2 pin/protocol contract for a separate diagnostic firmware project. Voice/text/location and RC coexistence remain required before handheld hardware selection.

## Historical evidence and remaining limits

V1 independent review is at `639e08f`: all 172 pin memberships agree, ERC has zero violations, and DRC has zero errors/zero unconnected with 67 warnings. Native schematic/PCB comparison adds 139 value/name warnings; these concern metadata and update workflow, not electrical pin connectivity. V5 drill diameters and independent whole-film XOR remain unresolved. See [S2 verification](../reviews/codex/S2_VERIFICATION.md).

V2 remains a draft. The latest CSV has 67 component rows totaling 118 parts; older reports said 68 lines and two open connections. Current independent checks supersede those counts. The V1 review has 35 distinct findings linked to 45 V2 requirements. Standalone protocol correction files remain proposals; they were not integrated by the preserved-V1 compilation. V2 connector coverage and complete datasheet mapping are subsequent packets.

The independent V2 snapshot/ERC/DRC inventory is now complete and separately identified from historic S2. The current `REQ-CTL-01` text governs proposed deadlines; reconcile its 1.0 s default with the older 500 ms prompt summary before timing acceptance.

Resume through this file and [Codex checkpoint](../reviews/codex/README.md). Work one bounded packet in owned paths, record exact evidence and limitations, then append the next task to the handoff.
