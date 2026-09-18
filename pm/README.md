# LoRa engineering workspace

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
