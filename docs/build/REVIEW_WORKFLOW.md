# Review workflow and acceptance gates

The local runner checks that schematic presentation changes preserve the captured electrical design, exports reviewable sheets, and records native ERC/DRC results. **A successful documentation review is not fabrication approval.** It does not run CAD generators, fill zones, update a board from a schematic, alter the primary project, or upload anything.

## Local commands

From the repository root, using the installed KiCad 9 Python on this workstation:

```powershell
& 'C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\bin\python.exe' -m unittest discover -s tools/quality -p 'test_*.py' -v
& 'C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\bin\python.exe' tools/quality/review.py --profile review
```

On another machine, Python 3.10+ is sufficient for the runner; set `KICAD_CLI` to a KiCad 9 executable or place `kicad-cli` on PATH. `--kicad-cli <path>` overrides discovery. Native checks also need the project libraries and installed KiCad symbol/footprint libraries referenced by their tables. Tests use only Python's standard library.

Each run creates a fresh timestamped directory under `reviews/codex/professionalization/quality-runs/`. Use `--output reviews/codex/professionalization/<unique-name>` for a chosen empty directory. Existing nonempty output directories are refused to prevent old exports being mistaken for new results. The runner exits 0 only if the requested gate passes; missing tools, invalid reports or incomplete execution produce a failed report.

Use `--design v1` or `--design v2` to limit the review; the default checks both. `--profile fabrication` requests the stricter readiness gate and currently returns failure. There is no ignore-warning, ignore-unconnected or waive-parity switch.

## What each gate means

| Evidence | Documentation/layout review | Fabrication readiness |
| --- | --- | --- |
| Stable captured inputs; CLI major version 9; complete run | Required | Required |
| Same parts, values, footprints and complete pin grouping as the pre-edit baseline | Required | Required |
| Preserved PCB/project/custom-rule bytes during this presentation-only change | Required | Inherited from review |
| Native ERC with all severities | Must have zero violations | Must have zero violations |
| Schematic page-coordinate anchors and box corners | Must fit on the declared page | Required, but insufficient for visual approval |
| SVG export for every sheet | Required | Required |
| DRC errors, unconnected items, parity differences, warnings/exclusions | Recorded separately, never hidden | All must be resolved; no automatic waivers |
| Text extents, overlap, readable labels, assembly information and fabrication/drill evidence | Human review still required | Explicit engineering and visual acceptance still required |

The final human/engineering acceptance is deliberately left pending by this runner. It never turns a passing command into permission to manufacture. Until a separate release record is reviewed, `fabrication` remains false even if the automated tests become clean. Known V2 unrouted connections are reported as actual failures of fabrication readiness; a documentation check can still pass while those failures remain visible.

The coordinate check tests actual top-level primitive anchors, wire vertices and explicit box corners. It **does not** measure rendered text glyphs or symbol extents, detect collisions, assess reading order, or judge engineering correctness. Review the exported SVGs at normal reading scale and inspect all sheets, especially connectors, power paths and MCU labels. Do not call this check an automatic visual-quality pass.

## Baseline identity and scope

The pre-edit capture is in `reviews/codex/professionalization/quality-baseline/`. Its manifest records SHA-256 hashes taken before and after copying 26 V1/V2 design files. Both original and copied hashes agreed. KiCad exported the baseline netlists from these copies before schematic professionalization.

Compact acceptance data lives in `tools/quality/baselines/v1.json` and `v2.json`. It includes the original input hashes, XML hashes, component identities and all physical pin groups. V1 uses the explicit `Allegro_RefDes` property; V2 uses native references where that property is absent. Isolated NC pins remain individual groups and are checked, not discarded. Net-name changes with identical pin membership are reported separately. A pin reassignment, missing isolated pin, part substitution, changed footprint or duplicate physical pin fails the check.

At capture, V1 contains 44 electrical components / 172 pins. V2 contains 114 electrical components / 361 pins; its 118-part physical BOM includes four mounting holes that are absent from the electrical netlist. A recorded Git HEAD describes context only: working-file hashes identify the actual captured input.

`capture_baseline.py` is an explicit one-time utility, never invoked by review or CI. It refuses to overwrite the canonical baselines. A deliberate electrical design change needs a reviewed new baseline and a documented reason; regenerating the acceptance baseline merely to make a failing test pass defeats the check.

## Reports and evidence transfer

Every completed or failed run saves `review.json` and `REVIEW.md`. The JSON contains command arguments, stdout/stderr, tool version, Git context, source hashes, output hashes, separate gate results and detailed counts. Per-design folders contain exported netlists, connectivity comparisons, ERC, DRC with schematic parity, page-coordinate results and SVGs. Native tools operate on the copied `inputs/hardware/...` tree. The runner checks both the original files and copied inputs for unexpected mutations.

A clean handoff records:

1. The report path and exact source hashes, plus the released revision if one exists.
2. Whether the **review** gate passed and why **fabrication** remains open.
3. ERC counts, DRC errors/warnings, unconnected count and schematic-parity count as separate quantities.
4. Which rendered sheets were visually inspected, by whom, and remaining readability issues.
5. The next bounded correction and its file owner. Do not substitute a moving checkout for the recorded inputs.

## Generator dispatch regression

The existing V2 command dispatcher was found to regenerate the PCB, project and BOM even for a `sch` request. Once the dispatcher is fixed, this explicit regression command tests it in a separate copy:

```powershell
& 'C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\bin\python.exe' tools/quality/check_generator_dispatch.py
```

The command copies the generator and libraries, runs only `gen_v2.py sch` inside that copy, and compares the copied PCB/project/BOM before and after. It also checks that those working-tree files remained unchanged. This tool is separate from the read-only review runner and is never invoked implicitly. Its report does not replace the netlist/ERC/render checks.

## Optional GitHub Actions

Publication update: `.github/workflows/repository-checks.yml` adds automatic portable checks on pushes and pull requests. It runs the 18 acceptance-logic tests, committed evidence/portfolio checks, manufacturing reconciliation, atlas checks and a viewer rebuild. A green repository check establishes package consistency only. It does not erase the existing V2 ERC/DRC findings, run a programmer or approve fabrication. The native/manual workflow below remains separate.

`.github/workflows/design-review.yml` is a **manual-only definition**. No workflow was activated or pushed as part of this work. If the repository owner later enables and dispatches it, the standard-library tests run on a hosted Linux runner. Native KiCad checks are separately opted into and require a trusted self-hosted Windows runner labeled `kicad-9`, with the KiCad 9.0 per-user install path shown above. Adjust that path deliberately for another installation. Workflow permissions are read-only; there is no deployment step. It uploads reports even when a check fails.

The separate `run_firmware` option compiles **preserved V1 only** on a trusted self-hosted Windows runner labeled `gnu-arm-13-3`. It pins Python 3.12.14 and verifies the recorded GNU Tools for STM32 13.3.rel1 / GCC 13.3.1 compiler banner before building. Set `ARM_GCC_BIN` on that runner if the helper cannot discover the matching installed toolchain. It runs `firmware/tools/build_v1.py preflight` and `build --out firmware/Debug/ci_v1_unqualified`, then verifies the unqualified/software-only manifest state and preserves image/log/map/hash evidence. There is no programmer command, hardware connection or V2 build claim. See [firmware build](FIRMWARE_BUILD.md) and [actual firmware handoff](FIRMWARE_HANDOFF.md) for the two completed local builds, vector checks, matching BIN/HEX/ELF hashes and remaining defects. This workflow does not turn those images into a deployable release.
