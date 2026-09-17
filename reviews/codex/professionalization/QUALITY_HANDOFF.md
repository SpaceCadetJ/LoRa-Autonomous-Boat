# Quality tooling handoff

State: **final candidate 04 preserves every baseline connection and component.** V1 ERC is clean; V2 retains one pre-existing pin-type warning, so the strict combined review gate still fails. Fabrication remains unapproved. The final isolated `sch` dispatcher regression passed. Earlier candidates remain preserved as evidence of the regression caught and corrected.

## Final candidate 04 — handoff identity

Final hash packet: [FINAL_QUALITY.json](FINAL_QUALITY.json). Native report: [candidate-review-04/review.json](candidate-review-04/review.json), with [readable checklist](candidate-review-04/REVIEW.md). Every recorded current CAD input still matched the reviewed snapshot when the final packet was written.

| Design | Connectivity / metadata | ERC | PCB DRC / parity |
| --- | --- | --- | --- |
| V1 | PASS: 44 components, 172 pins; zero net-name/value/footprint changes | 0 errors / 0 warnings | 0 errors / 67 warnings / 0 unconnected / 139 parity |
| V2 | PASS: 114 electrical components, 361 pins; zero net-name/value/footprint changes | 0 errors / 1 pre-existing warning | 0 errors / 101 warnings / 3 unconnected / 212 parity |

All 15 independently exported SVG sheets pass page-anchor/box-corner bounds and sheet-coverage checks. PCB/project/custom-rule preservation, source stability and read-only snapshot checks pass. The remaining strict review failure is solely V2 ERC's existing U6 SDO/AD0 pin-type warning; no exception was added. Root's separately rendered PDF/SVG presentation assessment remains a separate result from these automated geometry checks.

Final dispatcher regression: [generator-guard/20260917T203740404372Z/dispatch.json](generator-guard/20260917T203740404372Z/dispatch.json), **PASS**, including copied and working PCB/project/BOM hashes. It was repeated after the final renderer changes.

| Artifact | SHA-256 |
| --- | --- |
| Candidate 04 review JSON | `1d3476ecc0ef3687604da40cc9359b0c70b8d29ace7825b2386202883bc59c2f` |
| Final dispatcher report | `4a01ebc292cf4b534fafa44e17e0acb05eba2e851ad4b2f5ba84008dd8fa31cc` |
| V1 root schematic | `b2f4a6ecc46b403bdf71a5335e9f95d78885b525ca46f8d94d156afea0bc9497` |
| V2 root schematic | `9f8754f2d40612077a687448ca6a3ae10855176f9c796f19831109b043c532eb` |

The complete sheet/project/library hashes and relevant generator/review-tool source hashes are in the final packet. No CAD was edited by this quality task.

## Candidate 03 — previous independent result

Report: [candidate-review-03/review.json](candidate-review-03/review.json), with [readable checklist](candidate-review-03/REVIEW.md).

| Design | Electrical preservation | ERC | PCB DRC, separately recorded |
| --- | --- | --- | --- |
| V1 | PASS: all 44 components / 172 pins; no value or footprint changes | 0 errors / 0 warnings | 0 errors / 67 warnings / 0 unconnected / 139 parity |
| V2 | PASS: all 114 electrical components / 361 pins; no value or footprint changes | 0 errors / 1 pre-existing pin-type warning | 0 errors / 101 warnings / 3 unconnected / 212 parity |

Both projects preserve the captured PCB/project/custom-rule bytes. Source captures were stable throughout the run; KiCad did not change captured inputs. All 15 pages pass the limited coordinate check and export to SVG. The only failing **review** check is the V2 ERC warning: U6 SDO/AD0 has the generic `Bidirectional` pin type while tied to the ground power flag. It was also present in the before-edit source. No warning was suppressed or waived. Review the sensor's selected interface/pin intent and symbol treatment as a separate engineering decision; do not infer a fabrication pass from its pre-existing status.

Candidate 02 also failed, with V1 U3 pins 13/48/64 and V2 U1 pins 32/48/64 detached from +3V3; its [full report](candidate-review-02/review.json) is retained. Candidate 03 corrected the regression by segmenting the shared power rail and normalizing coordinate grouping, while preserving component and net membership.

## Firmware and manual CI integration

Reviewed `firmware/tools/build_v1.py` and the completed firmware handoff. Added a separate manual opt-in `run_firmware` job in `.github/workflows/design-review.yml`, using Python 3.12.14 and checking the recorded GNU Tools for STM32 13.3.rel1 / GCC 13.3.1 compiler banner. It performs preflight and a software-only V1 build, checks the unqualified manifest status, and saves artifacts/logs. No programmer or hardware command is present; no workflow was activated or pushed.

Read-only verification of the existing completed firmware build: **all 95 input hashes and all four ELF/BIN/HEX/map hashes still match**; BIN is 36,528 bytes. This review did not recompile or access hardware. [firmware-build-evidence.json](firmware-build-evidence.json) records the check. All three PowerShell blocks in the workflow parse without syntax errors. The firmware agent's two actual successful builds and source safety limits remain documented in `docs/build/FIRMWARE_HANDOFF.md`.

## Candidate 01 — actual native results

Report: [candidate-review-01/review.json](candidate-review-01/review.json). Both input capture and original/copied-file stability checks passed. PCB/project/custom-rule bytes remained unchanged; all 15 SVG sheets exported and all page-coordinate checks passed.

| Design | Electrical preservation | ERC | PCB DRC, separately recorded |
| --- | --- | --- | --- |
| V1 | FAIL: U3 pins 32/48/64 detached from +3V3 into singleton nets | 6 errors / 11 warnings | 0 errors / 67 warnings / 0 unconnected / 142 parity |
| V2 | FAIL: U1 pins 19/32/48 detached from +3V3 into singleton nets | 6 errors / 18 warnings | 0 errors / 101 warnings / 3 unconnected / 212 parity |

No component value/footprint/reference changes were found. The new power-bus drawing is the relevant correction area. Off-grid flags and unconnected wire endpoints also need correction. The V2 bidirectional U6 SDO/AD0 pin tied to a ground power flag warning predates this layout edit: `quality-baseline/v2.erc.json` reproduces it on the before-edit source. That baseline ERC also has four library-link warnings caused by the deliberately small baseline copy omitting custom footprints; the full candidate review includes those footprints.

Dispatcher regression: [generator-guard/20260917T201425740527Z/dispatch.json](generator-guard/20260917T201425740527Z/dispatch.json), **PASS**. `gen_v2.py sch` in the isolated copy leaves PCB, project and BOM hashes unchanged; the corresponding working files also remained unchanged.

## Completed evidence

- Captured 26 pre-edit V1/V2 files into `quality-baseline/`; original-before/copy/original-after SHA-256 values agreed for every file.
- Independently exported V1/V2 XML netlists from those copies using KiCad 9.0.7.
- Created compact canonical baselines in `tools/quality/baselines/`: V1 44 electrical components / 172 pins; V2 114 electrical components / 361 pins. Four physical mounting holes explain the difference from the V2 118-part BOM.
- All 16 behavioral tests pass. They reject rewires, missing isolated pins, part substitutions, duplicate pins, off-page geometry, ERC warnings, unrouted boards and parity warnings. All three runner/helper files pass Python syntax compilation.
- Captured before-edit coordinate diagnostics: all 15 sheets have zero out-of-page primitive anchors/box corners. This check cannot establish that labels are readable or do not overlap; visual inspection remains essential.

## Deliverables

- `tools/quality/review.py`: read-only current-design snapshot, KiCad XML/ERC/SVG/DRC exports, canonical preservation comparison, page-coordinate check, source/output hashes and separate review/fabrication gates. No implicit generators.
- `tools/quality/check_generator_dispatch.py`: explicit isolated regression for `gen_v2.py sch`; requires PCB/project/BOM hashes unchanged. Never used on the working project directly.
- `tools/quality/capture_baseline.py`: explicit one-time baseline capture; refuses replacement of existing baselines.
- `tools/quality/test_review.py`: independent acceptance-logic tests.
- `.github/workflows/design-review.yml`: manual-only optional CI definition; no activation/push, native KiCad opt-in on a trusted self-hosted runner.
- `docs/build/REVIEW_WORKFLOW.md`: commands, acceptance criteria, interpretation, limitations and transfer steps.

## Resume commands

After any further intentionally reviewed generator/schematic changes:

```powershell
& 'C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\bin\python.exe' tools/quality/check_generator_dispatch.py
& 'C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\bin\python.exe' tools/quality/review.py --profile review
```

Report every native count separately. A review pass does not waive V2 unconnected items, DRC errors, parity differences or manufacturing review. The runner intentionally leaves fabrication approval false until a separate explicit release process exists.

No Git changes, primary CAD edits, source firmware edits, procurement actions or external workflow activation were performed by this quality subtask.
