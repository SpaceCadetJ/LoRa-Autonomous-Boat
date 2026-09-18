# IMU placement feasibility and routing obstacles

**Result: the 12 proposed parts and one reserved filter site fit within courtyard envelopes on the existing 80 × 46 mm outline. This placement is rejected for integration on untouched copper.** Native DRC reports 136 errors. The complete board's 6S power redesign still has no selected package envelope, so whole-board fit remains unresolved.

Open the [annotated placement map](v2_imu_placement.svg), [placement-only KiCad board](study/IMU_PLACEMENT_STUDY.kicad_pcb) or matching [project](study/IMU_PLACEMENT_STUDY.kicad_pro). These are mechanical review artifacts. The [electrical candidate](../imu_interface/README.md) remains a separate, frozen schematic revision. Live schematics, board, BOM, purchasing exports and Stage A firmware contract are unchanged.

## Exact scope and preservation

The starting live board is `49a8aa88cf61e8b6272ce13a0d5a5a6a3c6b81aeba057ebcd4ca15a6262c37b2`, captured from revision `fced70600455243e510a8affd21f67f5a3ee0a78`. [Study manifest](study_manifest.json), [packet hashes and native commands](packet_manifest.json), [structural comparison](preservation.json).

Expected electrical delta for **this study**: none to existing pads, nets, tracks or zones. Twelve new footprints have 37 deliberately unassigned pads (net 0). C43 is a reserved drawing envelope only, not a PCB component. The eventual circuit integration must still make the five U6 changes documented in the electrical candidate; do not copy this mechanical board into a manufacturing package.

Native comparison preserves all 118 original footprint blocks and 1,331 other PCB blocks exactly after normalizing both copies with the same KiCad writer. This covers all 1,077 segments, 166 vias, outline, net definitions, rules, zones and stored fill polygons, including the repaired ground vias and NRST detour. The study contains 130 footprints. All 52 live CAD inputs and both unrelated local tool edits are hash-checked for preservation.

## Placement coordinates

Absolute board coordinates are millimeters; the outline is x=50–130, y=50–96. Rotations follow KiCad. All additions are on the front. These are trial sites, not approved assembly coordinates.

| Reference | X | Y | Rotation | Purpose |
|---|---:|---:|---:|---|
| U9 | 110.5 | 67.3 | 0° | 1.8 V regulator |
| C38 | 108.5 | 64.4 | 0° | Regulator input bypass |
| C39 | 113.65 | 67.0 | 90° | Regulator output bypass |
| R39 | 116.0 | 66.8 | 90° | 1.8 V bleeder |
| U10 | 115.3 | 71.6 | 90° | I2C translator |
| R36 | 114.6 | 75.3 | 0° | Sensor SCL pull-up |
| R37 | 112.6 | 72.8 | 90° | Sensor SDA pull-up |
| R38 | 118.0 | 68.6 | 90° | Translator bias |
| U11 | 110.0 | 72.4 | 90° | Interrupt translator |
| C41 | 107.4 | 73.6 | 90° | U11 low-side bypass |
| C42 | 107.4 | 70.3 | 90° | U11 high-side bypass |
| C40 | 115.5 | 88.9 | 0° | U6 VDDIO bypass; obstructed by vias |
| C43? | 118.0 | 72.0 | 90° | Reserved 0603 site; no footprint added |

[Native geometry](geometry.json) uses conservative axis-aligned bounds of front courtyard graphics, including stroke width and the complete mounting-hole circles. No new envelope overlaps another envelope or crosses the outline. The smallest remaining gaps include only 0.02 mm at R28/C39, 0.07 mm at U9/C39 and 0.09 mm at R22/C40. Non-overlap does not qualify soldering access, manufacturing tolerances, height, screw heads, connector insertion or routing space. Amber in the overview marks the existing power region; it is not a measured free-space reservation.

[Pad-center distance bounds](routing_distances.json): C40–U6 VDDIO 1.509 mm; regulator bypasses 2.662/2.571 mm; U11 bypasses 1.850/1.661 mm. Sensor SCL/SDA links are at least 10.952/11.024 mm, and the interrupt link at least 15.263 mm. These are straight-line lower bounds, not routed lengths. The single-side, fixed-original-placement constraint pushes the translators north of the sensor; final routing may justify relocating trial parts.

## Native checks and concrete obstacles

| Native check | Captured baseline | Placement study |
|---|---:|---:|
| Ordinary errors | 0 | **136** |
| Warnings | 105 | 109 |
| Unconnected entries | 0 | 0; new pads have no nets |
| Schematic parity | Not run | Not run |

The baseline's four library-resolution warnings explain its difference from the earlier 101-warning live-project report. The study has five such warnings. They are retained, not suppressed. Existing zone fills are intentionally frozen. Native reports: [baseline](drc_baseline.json), [study](drc_study.json).

The 136 errors comprise 42 clearance, 8 hole-clearance, 25 shorting and 61 solder-mask-bridge findings. [Routing review](routing_review.json) lists the exact 20 affected existing track/via UUIDs across `+3V3`, `I2C1_SCL`, `IMU_REGOUT`, `NRST`, `SWDIO`, `SWO` and `VBUS_SENSE`. Zero unconnected entries cannot establish connectivity for unassigned pads. Some net-0/GND findings will change after assignment and refill; none is waived here.

C40's trial pads conflict with IMU_REGOUT vias at (114.777,88.5198) and (116.0882,88.4201), and a +3V3 via at (115.876,89.2022). C41 conflicts with a +3V3 via at (106.84,74.1596). Eight hole findings represent four distinct pad/via pairs reported twice. Before using these sites, reroute or relocate the identified local copper while preserving REGOUT continuity, intended 3.3 V distribution and the previously repaired ground network. U6 endpoint-hit records identify where to begin the eventual five-pin separation; they are not a complete cut-set proof.

An independent reviewer reproduced 118 preserved original footprints, 130 total footprints, 37 new net-0 pads and zero new courtyard overlaps. It also identified the via conflicts, tiny courtyard gaps and ephemeral-file capture issue; the manifest now enumerates exact input files and excludes KiCad session files.

## Circuit and power dependencies

TI recommends a **100 pF filter from the PCA9306 VREF2/EN bias node to ground**, positioned close to VREF2. The frozen twelve-part schematic omits it. The C43 site reserves room for a separate reviewed electrical amendment; no purchasing part or live netlist has silently changed. Short sensor-side traces remain a layout priority. [TI PCA9306 rev O, sections 9.2.2.1, 9.2.2.3 and 11.1](https://www.ti.com/lit/ds/symlink/pca9306.pdf#page=18).

Keep the stated 6S requirement. E-03 protection and E-06 inductor/power-stage corrections have no qualified replacement package envelope yet. Do not assume the existing L2 courtyard (about 7.05 × 6.55 mm), Q1, D1, U2/U3 or U8 will remain footprint-compatible. E-02 buffer supply, E-04 EN configuration and E-05 current-sense output filtering also need routing/space. See the [electrical findings](../design_completion/electrical/README.md). All six live blockers remain open.

## Restart in small packets

1. **Next smallest circuit task:** adopt or explicitly disposition the 100 pF bias filter in a new isolated electrical revision. If adopted, expect one additional component and two added memberships (bias and GND); preserve the five already reviewed U6 changes and every unrelated connection. Keep the prior twelve-part evidence intact.
2. Establish a 6S protection and power-package envelope before spending a packet on final IMU routing. Record the supported transient/operating limits, prospective package areas and unresolved component selections. The board outline remains a requirement under review, not a demonstrated full-design fit.
3. For local routing, begin with C40/REGOUT/3.3 V via conflicts and the translator corridor. Capture an explicit track/pad delta, assign all new circuit nets, make the five U6 separations, refill zones on the candidate, and rerun native ERC/netlist/DRC/parity against that same captured revision. Do not run the full old routing generator.
4. Integrate only after reviewing the corrected electrical and copper evidence; then update BOM, purchasing, application guides and firmware source-evidence contracts together. Hardware/assembly acceptance stays separate.

## Reproduce

Use KiCad 9.0.7's bundled Python (with pcbnew); standard footprint-library hashes are recorded as host provenance. Start with a clean matching live baseline. `build_study.py` writes only inside this packet and refuses a changed live CAD context.

```text
python reviews/codex/imu_placement/build_study.py
python reviews/codex/imu_placement/compare_study.py
python reviews/codex/imu_placement/native_check.py
python reviews/codex/imu_placement/render_map.py
```

`native_check.py` runs both DRC commands with before/after input guards and records hashes in [native_manifest.json](native_manifest.json). Then run `python reviews/codex/imu_placement/capture_review.py`. The project settings are captured beside each board; schematic parity is deliberately absent for this mechanical study. Publication CI checks captured hashes and reruns the structural comparison; it does not run native KiCad or qualify assembly. The review PNG is rendered from the SVG with CairoSVG and visually inspected. No board was ordered, powered or flashed.

## Publication checks

Six preservation/rejection tests pass. The final map was visually inspected at 1600 × 1100. Headless Edge checks at 1440 × 1000 and 390 × 844 passed image loading, isolated CAD links, guide disclosure of the failed native check, and absence of page overflow or script errors. The longer view label exposed a phone-selector overflow; the flex sizing was corrected and retested. All 228 indexed local HTTP paths passed. These are local packaging checks; hosted CI execution is not inferred.
