# Professionalization handoff — 2026-09-17

## Result and authority

Jay requested professional readable schematics, practical ordering/assembly, V1/V2 flashing procedures and a reviewable CI/CD workflow, and stated the other agent is inactive. The [ownership record](../../../FILE_OWNERSHIP.md) records the resulting takeover and disjoint subtask scopes. This packet completes the schematic/documentation/build-tool pass; it is **not a manufacturing or firmware release**.

Working context: branch `v2-design`, HEAD `a6316e9216cc55656e3fbb7c4f173895151ac4ff`. Files are uncommitted. No branch, index, commit or tag changes were made. Pre-existing `v1_design.py`, V2 PCB and routing-tool changes were preserved; Allegro source evidence was not edited. All three implementation/review subtasks have finished.

## Deliverables to review

| Packet | Entry point | Result |
| --- | --- | --- |
| Schematic presentation | [schematic editing guide](../../../docs/build/SCHEMATICS.md), [visual review](VISUAL_REVIEW.md) | Fifteen grouped and annotated pages; spacing, label directions, title/footer and panel collisions corrected; PDF/SVG exports refreshed |
| Generator safety | [final quality](FINAL_QUALITY.json), [quality handoff](QUALITY_HANDOFF.md) | `gen_v2.py sch` preserves PCB/project/BOM; explicit `pcb`/`all` retain full-rebuild semantics; isolated regression passed |
| Ordering and assembly | [build entry point](../../../docs/build/README.md), [procurement handoff](../../../docs/build/PROCUREMENT_HANDOFF.md) | Full review BOMs, partial one-board/fleet-five candidate imports, holds/optional/external parts, top/bottom location maps and staged inspection/assembly |
| V1 firmware | [firmware handoff](../../../docs/build/FIRMWARE_HANDOFF.md) | Reproducible reconstruction compiles/links twice to identical ELF/HEX/BIN; backup/program/readback/recovery guide; unqualified image |
| V2 firmware | [V2 programming plan](../../../docs/build/FLASHING_V2.md) | Actual SWD wiring and implementation/bring-up gates; no V2 project or qualified image exists |
| Viewer | [workspace](../../../pm/index.html), [viewer README](../../../pm/README.md) | Build & program page, maps/imports/guides, source freshness and latest independent review beside historic evidence |
| CI | [review workflow](../../../docs/build/REVIEW_WORKFLOW.md) | Read-only CAD review and 16 acceptance tests; manual opt-in KiCad and pinned V1 compile jobs; definition only, no activation/publication |

## Exact acceptance evidence

[Candidate 04](candidate-review-04/review.json) is the final native snapshot. Its SHA-256 is `1d3476ecc0ef3687604da40cc9359b0c70b8d29ace7825b2386202883bc59c2f`. [FINAL_QUALITY.json](FINAL_QUALITY.json) includes input/tool hashes and the final isolated dispatcher report. The [PDF/SVG manifest](../../../docs/img/schematic_export_manifest.json) and [visual review](VISUAL_REVIEW.md) identify the displayed drawings separately.

| Check | V1 | V2 |
| --- | --- | --- |
| Electrical preservation | 44 components / 172 pins: PASS | 114 electrical components / 361 pins: PASS; 4 mounting holes account for physical BOM count 118 |
| Component/net metadata | No value, footprint or net-name changes | No value, footprint or net-name changes |
| ERC | 0 errors, 0 warnings | 0 errors, 1 existing U6 AD0 pin-type warning |
| DRC violation errors / warnings | 0 / 67 | 0 / 101 |
| Unconnected report entries | 0 | 3 |
| Schematic-parity entries | 139 | 212 |

The strict combined review gate remains **FAIL**, solely because its zero-ERC-violations rule includes the pre-existing V2 warning. Fabrication is **NOT APPROVED**. No warning or parity exception was added. All 15 page-coordinate/coverage checks pass, and all final pages were visually inspected. Coordinate checks do not measure glyphs or qualify circuitry.

Candidates 01 and 02 are intentionally retained: they caught disconnected interior MCU supply pins from an early shared-rail drawing implementation. Candidate 03 fixed connectivity; candidate 04 retains it after final visual corrections. Do not use an earlier candidate as the current electrical drawing.

Protected PCB SHA-256 values still match before-edit records:

- V1: `2f604d1691ebde874075baecc2d1aa2985afa0db1a89ca277dec5d2156a553f2`.
- V2: `6595d3b58e4a54b1d3ecbf93a69c93202503dbabcf9d279a6a578df1601d0d26`.

V1 firmware BIN is 36,528 bytes, SHA-256 `9b90f0322089d997f1498ee634d4880005bd85fd5337d7a013a5609954239e17`. RAM reservation is 4,496 bytes. All 95 build-input hashes and four existing artifact hashes were independently rechecked. Three existing HAL unused-parameter warnings remain. This reconstructed build does not establish the original deployed image, fix failsafe/parser/GPS defects or qualify hardware. No probe connection, reset, erase, flash, readback or bench run occurred.

Manufacturing exports reconcile 44 V1 and 118 V2 PCB references against source BOMs. Candidate/hold/board-feature counts are 20/18/6 and 90/17/11. Partial candidate imports have 9 V1 / 49 V2 order lines. Exact source/output hashes and selected board count are in [run_manifest.json](../../../hardware/manufacturing/run_manifest.json). No stock, supplier selection, order, physical orientation or fabrication release is implied.

## Reproduce without overwriting unrelated work

1. Read current ownership and Git status. Review changes in `gen_sch.py`, `schematic_layout.py` and `gen_v2.py` with their generated sheets. Do not run `pcb`, `all`, full V1 build or routing to refresh documentation.
2. Follow [SCHEMATICS.md](../../../docs/build/SCHEMATICS.md) for the explicit schematic-only generation/export path; use [REVIEW_WORKFLOW.md](../../../docs/build/REVIEW_WORKFLOW.md) for fresh immutable native reviews and isolated dispatcher tests.
3. Use `firmware/tools/build_v1.py preflight` / `build` for software-only reproduction with the recorded compiler. No actual flashing belongs in CI.
4. Use the ordering guide's generator/checker for an intentional BOM/assembly refresh; preserve holds and source provenance.
5. Rebuild `pm/index.html` with `node pm/tools/build.mjs`, then validate with `node pm/tools/validate.mjs --http` while its loopback server runs. Restart the server after allowlist changes. Do not edit the generated page directly.
6. Review and selectively commit generator, generated artifacts, tests and handoff together in a later integration step. Avoid staging unrelated pre-existing changes or ignored build outputs.

Final viewer check: stable input capture, two valid embedded scripts, 63 documents, 191 indexed paths and all **203 local HTTP links** passed. Desktop/mobile interaction checks and their limits are in [pm/QA.md](../../../pm/QA.md). The final refresh includes candidate 04 and the current build/assembly/handoff documents.

## Next smallest task

Produce a read-only V2 ground-connectivity disposition from candidate 04's exact PCB snapshot. The three native `unconnected_items` are **zone-to-zone entries** using the front/back GND zone UUIDs; their reported `(50,50)` coordinates are zone anchors, not proven defective pad positions. Identify the actual isolated copper islands and affected pads before proposing via locations. Do not repeat the old claim that exactly two specific pads need stitching.

In parallel or next, review U6's selected interface, voltage domains and AD0 pin intent against its manufacturer datasheet before deciding whether the existing ERC warning represents only a symbol-mode issue. Then freeze the V2 pin/protocol contract (including divider scaling, USB VBUS handling, BOOT0 access and CRC/framing) for a separate diagnostic firmware project. Full device/footprint qualification, V2 atlas/datasheets, fail-safe integration and board layout review remain open.

Future handheld scope remains **voice, text and location**, plus RC control. Compare measured voice airtime/quality and worst control-blocking intervals before choosing radio/codec/hardware. The circuit drawing and BOM here are vehicle-node artifacts; no handheld release is claimed. Reconcile `REQ-CTL-01`'s current 1.0 s default with older 500 ms prompt summaries before timing tests.

The existing hourly continuation automation remains active with this handoff as an entry point. It now reflects Jay's authorized scope and stays quiet on unchanged/non-actionable runs. Nothing was externally published.
