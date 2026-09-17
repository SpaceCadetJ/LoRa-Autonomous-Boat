# Schematic presentation and review

The September 17 presentation update reorganizes both designs into functional panels with separate space for symbols, net labels, references, values and engineering notes. The root sheets are navigation indexes. Dense MCU and power sheets use A2; the remaining sheets use A3. Review at native size or zoom in the viewer rather than shrinking the full drawing to A4.

V1 notes call out preserved defects and actual firmware/header roles. V2 notes identify power domains, nominal divider/gain values, optional populations, interface intent and open qualification work. These annotations describe the current circuit; they do not certify device ratings or implemented firmware.

## Reading the sheets

Matching named nets are electrically connected. Cross-sheet signals use hierarchical ports; supply names are global. Component groups keep related functions together, but the drawings still use named-net connections rather than complete point-to-point circuit diagrams. Check the whole named-net group when following a regulator's switching loop or an interface path.

Connector pin numbers are electrical numbers. They are not mating-face drawings or a guarantee about a bought cable. Use the version's [assembly guide](README.md) and physical pin-1 inspection before wiring. Test point labels are expected nodes, not measured voltages.

## Editing source and exporting

The shared presentation plan is [schematic_layout.py](../../hardware/kicad/tools/schematic_layout.py). It assigns functional groups, notes, label clearance and page size. [gen_sch.py](../../hardware/kicad/tools/gen_sch.py) supplies the shared drawing primitives. V1 reads the hash-verified [tracked input capture](../../hardware/kicad/evidence/v1_schematic_inputs/README.md); V2 reads [v2_design.py](../../hardware/kicad_v2/tools/v2_design.py). Neither schematic-only command requires a pre-existing ignored `_build` directory or a PCB regeneration.

For an authorized schematic-only change, use the installed KiCad Python from the repository root:

```powershell
& 'C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/python.exe' hardware/kicad/tools/gen_sch.py
& 'C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/python.exe' hardware/kicad_v2/tools/gen_v2.py sch
& 'C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/python.exe' hardware/kicad/tools/export_review.py
```

The first two commands change schematic sources and schematic-path bookkeeping. The third only exports existing sources to the two PDFs and fifteen SVGs in `docs/img/`. It checks that CAD bytes stayed unchanged and records input/output hashes in [schematic_export_manifest.json](../img/schematic_export_manifest.json). `--cli <full-path>` selects another KiCad CLI installation. It does not regenerate PCB, BOM or library files.

The paths above describe the validated workstation. On another installation, use Python 3.10 or later and set `KICAD_SYMBOL_DIR` to the installed KiCad 9 `share/kicad/symbols` directory; the generator embeds those symbols. Schematic generation uses Python's standard library and the tracked project libraries. Exporting requires KiCad CLI; using its matching bundled Python is a convenient default. The standard library version and content matter for exact reproduction. A successful run with a newer symbol library still needs a source diff, electrical review and rendered-page inspection.

V1 defaults to the tracked capture even when a stale local `_build` exists. For an intentional source reconstruction, supply the complete local input directory explicitly:

```powershell
& 'C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/python.exe' hardware/kicad/tools/gen_sch.py --input-dir hardware/kicad/_build
```

This mode reads `v5_board.json`, `netmap.json` and optional `mpn.json` from that one directory, preserving the legacy reconstruction workflow. It does not merge missing local inputs with captured ones. The full V1 build passes that directory explicitly; full reconstruction also replaces CAD and exports, so use schematic-only commands for presentation work.

The [isolated regeneration check](../../hardware/kicad/evidence/v1_schematic_inputs/reproducibility_report.json), run with Python 3.11.5 and the recorded KiCad standard-library hashes, regenerated all fifteen current schematic files byte-for-byte with both `_build` directories absent. It also verified explicit reconstructed inputs, ignored stale local inputs in default mode and rejection of a modified captured input before CAD writes. All 24 protected CAD/project/library/BOM files matched the working originals after the isolated commands; the working originals remained untouched. This is a reproduction result, not a new electrical or fabrication approval.

The corrected V2 dispatcher treats `check`, `bom`, `sch`, `pcb` and `all` separately. **`pcb` creates an unrouted board; `all` also replaces libraries/project/BOM.** Neither command belongs in a presentation-only update. The isolated [dispatcher regression check](REVIEW_WORKFLOW.md#generator-dispatch-regression) verifies that `sch` preserves existing PCB/project/BOM bytes.

## Required review

Run the [quality workflow](REVIEW_WORKFLOW.md) against its immutable before-edit baselines. Compare components, values, footprints and every pin group, including isolated pins. Capture ERC at all severities and DRC with warnings, unconnected entries and schematic parity. Do not reset a baseline or suppress findings to make a layout change pass.

Exporting a sheet or passing coordinate bounds does not detect all text overlap. Inspect every rendered PDF page for readability, boundary clipping, title-block collisions, power rails, reference/value placement and notes. Preserve the PDF/SVG hashes and the visual review record. The initial layout regression caught incomplete shared power-rail connections; rails now use explicit wire segments at each pin and junctions at internal branches.

Electrical equivalence to the prior design is a preservation test, not electrical qualification. Fabrication, assembly and firmware release remain separately gated. See the current [quality handoff](../../reviews/codex/professionalization/QUALITY_HANDOFF.md) and the [professionalization handoff](../../reviews/codex/professionalization/HANDOFF.md) for exact evidence and remaining work.
