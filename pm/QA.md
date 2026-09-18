# Viewer delivery verification — 2026-09-17

## Current isolated IMU candidate edition

The V2 Design selector includes the annotated 1.8 V IMU candidate with explicit pending PCB integration. Its project link opens the isolated candidate; the live PCB link is omitted for that view. Desktop 1440 x 1000 and phone 390 x 844 checks pass candidate selection/image load, guide opening, correct project link and no page overflow or browser errors. [Results](../reviews/codex/imu_interface/viewer_check.json).

The changed A2 Navigation SVG was rasterized with CairoSVG and visually inspected after correcting supply-label spacing, annotation length and title-block scope. [Visual evidence](../reviews/codex/imu_interface/visual_review.json). Packaging contains 75 documents, 53 images and 224 indexed paths; 236 local HTTP links pass. The candidate is not included in the live PCB or buying lists.

## Current application and diagnostic edition

The viewer reads the integrated V2 board's [native review](../reviews/codex/design_completion/native-review/REVIEW.md), the [Stage A build manifest](../firmware_v2/evidence/stage_a_build.json), five application guides and six component-limit findings. V2 now has zero unconnected PCB items; the strict native review and hardware release gates remain failed/open. Purchasing data reflects 74 candidate / 33 held / 11 bare-feature V2 references.

Headless Edge checks at 1440 x 1050 and 390 x 844 passed: five guide cards, V2 guide dialog, application search, diagnostic instructions, no browser errors and no page-level overflow. [Recorded results](../reviews/codex/design_completion/ui/application-ui.json) and desktop/phone screenshots preserve the checked view. The six electrical findings use expandable cards for phone readability. The server exposes reviewed V2 source and evidence paths, while firmware build outputs remain unavailable over HTTP. Direct-file mode and physical hardware behavior were not tested.

Earlier counts and missing-V2-image statements below describe their dated snapshots. Current source/input hashes are in [status.json](status.json). The clean source archive rebuilt 74 documents, 52 images and 222 indexed paths; live HTTP validation passed 234 paths. The [current handoff](../reviews/codex/design_completion/HANDOFF.md) records the 27 passing tests, evidence checks and refreshed PCB preview provenance.

## Earlier portable publication edition

The viewer now uses the publication native review (52 active CAD inputs), tracked V1 build evidence and tracked primary reports. All fifteen schematic inputs reproduce without the old local build cache. A clean staged-source archive rebuilt and validated the viewer with 60 documents, 200 indexed paths, 52 drawings/images and two valid scripts. Its revision is explicitly `source-archive`. The local HTTP check passed all 212 links and blocked-path probes. No new browser interaction test or hardware test is implied; desktop/mobile behavior was checked in the preceding edition below.

## Earlier build and programming edition

This update supersedes the earlier limitations below where explicitly addressed. The Build & program section presents separate V1/V2 cards, candidate imports for one/five boards, held and external parts, orientation/position evidence, four assembly maps and the build/flashing guides. It displays manifest freshness and the latest numbered native review with its strict failed gate visible. Copied review inputs are excluded from the document library.

The integration subtask checked desktop 1440 × 1050 and mobile 390 × 844 in headless Edge: all four assembly images loaded, the flashing document dialog opened, verification headings rendered, no browser errors and no page-level mobile overflow. At that checkpoint, all 192 HTTP links and blocked-path probes passed. After restarting the server and adding final documentation, packaging and all **203 HTTP links** passed; the snapshot has 63 documents, 191 indexed paths, 52 design images/PDFs and two valid embedded scripts. No inputs changed during capture. No external hosting or actual hardware programming was performed.

Current schematic PDFs/SVGs were separately rendered and visually reviewed on all fifteen pages. See [visual review](../reviews/codex/professionalization/VISUAL_REVIEW.md). Fresh independent CAD evidence is candidate 04; V1 compile results concern the preserved source and do not qualify its existing behavior. The V2 image remains unavailable.

## Earlier viewer-only checkpoint

Scope: local project viewer and portable V1 evidence. Repository branch `v2-design`, captured HEAD `a6316e9216cc55656e3fbb7c4f173895151ac4ff`. Primary CAD/tool working changes remain outside this packet. Input hashes and capture time are in [status.json](status.json); those hashes include uncommitted input bytes, not just HEAD.

## Checks completed

- `node pm/tools/build.mjs`: successful; no hashed inputs changed during capture. Generated data contains 44 V1 parts, 67 V2 component groups (118 physical parts), 12 V1 atlas entries, 35 findings, 45 requirements and 52 image/PDF views.
- `node pm/tools/validate.mjs --http`: successful. Both inline scripts parse; executing only the data assignment reproduces status.json exactly. Indexed paths and independent evidence exist; local HTTP evidence links return 200. Atlas citations are embedded. V2 aggregate TOTAL row is excluded and source quantities reconcile. Unique finding IDs checked.
- Browser at 1280 × 900 and 390 × 844: overview renders, phone view has no page-level horizontal overflow (document width equals viewport; individual tables/nav can scroll).
- V1 BOM search U3 → Inspect → STM32 manufacturer reference; V2 R1240 search → U2 → explicit R1240 datasheet mapping.
- V2 top render loads at 1992 × 1120; Power schematic SVG loads and zoom reaches 350%.
- V1 LoRa atlas opens with five pins; a preserved netmap citation opens at its source line.
- Findings search REQ-CTL-01 → acceptance detail shows the actual 1.0 s default and 20 ms response requirement from the source document.
- Verification displays historic V1 evidence separately from working primary reports. Evidence arrays render as usable links.
- HTTP Refresh reports success. Export handoff now opens reviewable Markdown with a Save link and a copyable text fallback; its content and current revision were checked.

## Repairs made during verification

Embedding JSON through a replacement string expanded firmware dollar sequences and broke HTML. A replacement callback now preserves bytes; the data equality check catches recurrence. V2 TOTAL was formerly counted as a component. Datasheet mapping now uses explicit MPNs rather than a fuzzy prefix. Atlas evidence buttons now open embedded sources and scroll to cited lines; ignored netmap/XML artifacts were preserved under docs/atlas/evidence by the atlas packet. Long stat text wraps on phone screens. Phase status text comes from the current primary report; manual intake dispositions are labelled as such.

## Limits and discrepancies

- Browser automation policy blocks file:// navigation. Direct double-click mode was therefore not exercised in this browser. The page embeds its scripts/data, has no startup fetch or third-party assets, and passes packaging checks; HTTP mode was exercised directly.
- The in-app browser did not deliver a download event for the former automatic Blob download. The revised export exposes the complete Markdown for copying and a Save link. Actual saved-download completion is not claimed.
- Complete manufacturer datasheet coverage, V2 connector pages and independently verified V2 CAD remain later packets.
- Current docs/BOM_V2.csv has 67 numbered component rows; REPORT.md says 68. Both agree on 118 parts. The viewer displays this discrepancy. Working drc.rpt and drc_all.rpt also differ (3 versus 2 unconnected entries); the report describes two. Resolve against a stable hashed V2 snapshot.
- V1 S2 results apply only to 639e08f. The 139 native parity warnings describe classified metadata differences; no electrical mismatch was found. No-change Update-PCB behavior, V5 drill sizes, independent full-film XOR, firmware compilation and bench operation remain unverified.
- REQ-CTL-01 says 1.0 s default command loss, while PROMPT_FOR_CODEX.md says 500 ms. Resolve the requirement before voice/RC coexistence acceptance tests.

Next bounded packet: independently snapshot and verify V2 ERC/DRC and inventory, then inspect one power/control subsystem. Preserve Allegro evidence and primary CAD/firmware ownership throughout.
