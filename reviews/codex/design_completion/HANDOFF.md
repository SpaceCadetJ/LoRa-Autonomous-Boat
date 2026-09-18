# Design completion and application packet — 2026-09-17

This packet follows published integration `07c0f35`. Jay requested continued work toward a finished design and application-specific use guides. It delivers application navigation, a separate diagnostic build, independent circuit-limit findings and a localized ground repair review. **No operational vehicle or handheld release is claimed.**

## Start here

- [Application handbook](../../../docs/applications/README.md): V1 bench, V2 boat, steering rover, position/telemetry and handheld voice/text/location; each distinguishes available work from physical release gates.
- [V2 diagnostic](../../../firmware_v2/README.md): real Stage A C application and build recipe, seven-pin contract, nine rejection/acceptance tests, separate ELF/HEX/BIN. No control, radio or navigation drivers.
- [Electrical review](electrical/README.md): six manufacturer-backed blockers and proposed circuit corrections; these are not cleared by ERC/DRC.
- [Ground repair](ground/README.md): localized pad/copper analysis, candidate and native before/after evidence. The final [MCU ground escape](mcu_ground/README.md) candidate is integrated.

## Integrated PCB evidence

The live V2 PCB is SHA-256 `49a8aa88cf61e8b6272ce13a0d5a5a6a3c6b81aeba057ebcd4ca15a6262c37b2`, corrected from `6595d3b58e4a54b1d3ecbf93a69c93202503dbabcf9d279a6a578df1601d0d26`. Intended structural changes are two added GND vias, one relocated GND via and a four-segment NRST detour replacing one segment (+0.960947 mm). All 118 footprints, pad assignments, net names and rules are unchanged. The final board has 1,077 segments and 166 vias.

The [fresh full native review](native-review/REVIEW.md) captures 52 current inputs and preserves all 533 electrical pins. V1 remains ERC 0, DRC 0 errors / 67 warnings / 0 unconnected / 139 parity findings. V2 remains ERC one warning and DRC 0 errors / 101 warnings / 212 parity findings; its unconnected count improves from three to **zero**. The strict review remains FAIL because of the existing V2 ERC warning and because its presentation-preservation check detects this intentional PCB correction against the older baseline. That preservation result is expected and is not waived or silently rebased. Component-limit findings, parity disposition, silkscreen and physical acceptance remain open; fabrication is not approved.

## Software evidence

Two final Stage A builds with recorded GNU Arm 13.3.1 produced identical ELF, HEX and BIN. BIN: **1,328 bytes**, SHA-256 `c95f9b0352e05971dd269cfaee4962d08d611866886a2e57ab7b403347f5afcd`. The manifest is [stage_a_build.json](../../../firmware_v2/evidence/stage_a_build.json). The firmware uses ST CMSIS/startup/linker inputs already in the repository; V1 application sources remain unchanged. Source hashes, compiler outputs and vectors are recorded. Independent disassembly/pin review found a target-label guard gap; explicit target/schema/mode rejection and three tests corrected it. [Independent review](electrical/FIRMWARE_STAGE_A_REVIEW.md).

No device was connected, reset, erased or flashed. The expected heartbeat and low actuator-pin states are implementation intent, not observed board behavior. Fault handlers cannot guarantee execution after a stack or bus failure. The nine pin-contract tests verify evidence consistency and rejection, not real-time execution.

## Application and purchasing evidence

Seven application documents include wiring intent, prerequisites, startup/use/shutdown sequences, troubleshooting and a per-unit acceptance template. The five application cards, guide dialogs, search and Stage A instructions passed headless Edge checks at 1440 × 1050 and 390 × 844 with no browser errors or page overflow. Guide procedures for future modes are explicitly gated; there are no invented handset controls, V2 console commands or range results.

The procurement policy now holds every reference implicated by E-01–E-06, in addition to existing footprint and optional-population holds. This is an ordering review update, not a circuit repair or a complete approved cart. V2 now has 74 candidate / 33 held / 11 bare-feature references, with 40 candidate order lines; V1 remains 20 / 18 / 6. Regenerated summaries and manifests use the integrated PCB and are authoritative for counts; older publication totals describe their earlier snapshot.

## Remaining work and restart order

1. Implement the documented IMU 1.8 V supply, bus and interrupt translation as one circuit revision, with an explicit expected pin delta, readable drawing and native checks. U6 AD0 tied to ground is valid for I2C address selection; the actual defect is VDDIO/interface overvoltage.
2. Resolve buffer supply, buck EN, current-sense output loading and inductor margins. Preserve the stated 6S requirement unless Jay chooses a different envelope; coordinate surge protection against every exposed component.
3. Reconcile the operational protocol's CRC/encoding/version fields, watchdog bounds and timing. Stage A does not implement that protocol. Add Stage B output supervision, then test with instruments and loads disconnected after electrical acceptance.
4. Qualify the selected radio, battery, ESC/BEC, servo and harness. Jay was asked for model numbers; no new model selection is inferred from silence. Voice/text/location and measured voice/RC coexistence remain required before handheld hardware selection.

Resume with Git status and FILE_OWNERSHIP.md. Existing local edits in `hardware/kicad/tools/v1_design.py` and `hardware/kicad_v2/tools/route_v2.py` remain outside this packet. Do not run the old full routing generator over a reviewed correction. Preserve Allegro and V1 evidence, distinguish native findings from component-limit review and bench results, and update the viewer only from recorded inputs.

## Integration and portability checks

Engineering integration: `5a95a6a1e8e01463e74fe14806165b7ee4f885c9`, with a tested source tree `b9b83c596e29b66f0585fefab2b191f979222725`. A clean Git source archive passed all 18 quality-tool tests and all 9 diagnostic-contract tests, 290 native/schematic/firmware input/output hash checks, 21 linked guide pages, both procurement packages and the 12-entry / 36-pin connector atlas. The archive rebuilt the viewer as `source-archive` with 74 documents, 52 images, 222 indexed paths and two valid scripts; the live loopback viewer passed 234 HTTP links and blocked-path probes. These checks do not qualify physical hardware.

Top and bottom V2 PCB previews were then refreshed from the integrated board and visually inspected. [Render manifest](pcb_render_manifest.json) records the exact board/image hashes and commands. Existing silkscreen overlaps and missing/assumed component models remain visible; fabrication approval is not implied. Publication validation now checks this image provenance as well. Subsequent changes in this closeout are preview assets, provenance checks and review records; original CAD and firmware evidence remain unchanged. KiCad local session state is excluded from the source package.

The hourly continuation task now starts from this packet and the next IMU correction, preserves quiet notifications and Jay's ordinary commit/push authorization, and retains prohibitions on orders, powering/flashing hardware and history rewrites. GitHub workflow definitions exist; hosted execution must be verified against the actual run rather than inferred from local success.

## IMU candidate follow-up - 2026-09-18 UTC

The newer packet is reviews/codex/imu_interface/README.md. It adds an isolated 1.8 V IMU supply, I2C translator and interrupt translator: exactly five existing pin changes, 12 added components, 37 added pins and 356 preserved memberships. Native ERC retains only the original AD0 warning. The TI DCT-8 land-pattern mismatch was identified and a project-local footprint was dimension-checked. Live schematics/PCB/BOM/firmware are unchanged; E-01 and the other five electrical blockers remain open. Next: assess placement and local routing of the 12 additions on a copy of the corrected board, including space for remaining power corrections, before live integration. Reproduction, capacitor/part holds, supply-sequencing limits and exact hashes are in the new packet. The unrelated v1_design.py and route_v2.py edits remain excluded.
