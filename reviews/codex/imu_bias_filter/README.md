# IMU2: translator bias-filter amendment

**C43 is implemented and independently verified in this isolated schematic revision.** It adds the recommended 100 pF filter between the PCA9306 bias node and ground. All 398 connections from the preceding IMU candidate are preserved. Live CAD, PCB copper, purchasing exports and firmware remain unchanged; this is not a fabrication release.

Open the [annotated Navigation schematic](v2_imu_bias_filter.svg) or [IMU2 KiCad project](source/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pro). The [previous IMU1 circuit review](../imu_interface/README.md) and [placement obstacle study](../imu_placement/README.md) remain frozen evidence. IMU2 is the current schematic candidate; the placement study has not been electrically integrated or rerouted.

## Intended and verified electrical delta

| Comparison | Expected / native result |
|---|---|
| New component | Only C43, 100pF, Device:C, 0603 footprint |
| C43 pin 1 | /Navigation/PCA9306_BIAS: U10 VREF2/EN and R38 bias node |
| C43 pin 2 | GND |
| Existing component properties and connections | Unchanged |
| Electrical parts | 126 → 127 |
| Physical schematic pins | 398 → 400; all previous 398 memberships preserved |
| Added net names | None |
| Native ERC | 0 errors; the same one AD0 warning |

The cumulative check against the corrected live design still finds exactly the previously reviewed five U6 pin changes, plus thirteen added components / 39 pins. It preserves the other 356 original memberships. U6 VDD remains 3.3 V; VDDIO/CS and the sensor side of I2C/INT remain on the reviewed 1.8 V domain. MCU pin allocations are unchanged. Native evidence: [validation](validation.json), [netlist](native/netlist.xml), [ERC](native/erc.json), [export manifest](native_manifest.json).

## Why and how C43 is used

TI recommends 100 pF at VREF2 and placement close to that pin. VREF2 and EN remain tied together and fed through R38=200 kOhm from 3.3 V. Increasing the filter capacitance increases the bias-node turn-on/off delay. [TI PCA9306 rev O, sections 9.2.2.1 and 11.1](https://www.ti.com/lit/ds/symlink/pca9306.pdf#page=18).

C43's **project selection targets** are C0G/NP0, ±5%, at least 25 V, in a 0603 package. These are project choices; TI's cited sections do not prescribe those tolerance, dielectric or rating values. The exact manufacturer/MPN remains blank and held. Do not substitute 100 nF for 100 pF. No supplier inventory, assembled part or order approval is claimed.

The nominal 200 kOhm × 100 pF product is 20 microseconds. This is an ideal RC estimate, not a guaranteed enable or settling time: device bias behavior, actual capacitance, leakage and supply ramps still matter. Retain the startup/shutdown and unpowered-domain tests in the IMU1 guide. Keep bus use and interrupt handling inhibited until the required power/device initialization sequence completes; no new firmware delay is qualified here.

For a future layout, connect C43 directly to the VREF2/EN node with a short ground return. The placement study reserved a site near U10, but that study used unassigned pads and reported 136 native errors before adding a physical C43. Its count is historical placement evidence, not an IMU2 PCB DRC result. Do not infer that the new circuit fits electrically because a rectangle fit geometrically.

## Source and verification

Starting repository revision: `10a07dd7e41b1645a7ad70490f2d3d18b2a3a5b0`. The amendment copies seventeen hashed CAD/library inputs from the frozen IMU1 packet and edits only Navigation plus the root revision/comment. No schematic generator or routing generator runs. The five other schematic sheets and all copied library/project files remain byte-identical. Deterministic symbol/wire UUIDs make the seventeen outputs repeat identically on a second build. [Build manifest](build_manifest.json), [reproducibility record](reproducibility.json).

The builder hash-checks 147 protected files, including prior IMU/placement evidence, all 52 live CAD inputs and the two unrelated local tool edits. The unrelated-edit hashes document this workstation's preservation only; portable CI excludes those two files from that historical guard because their edits are intentionally not published.

An independent reviewer compared complete native component XML and memberships, checked all protected hashes and inspected the Navigation render. C43 and its added startup note have no observed new overlap or clipping. All seven pages pass coordinate bounds. Seven tests reject wrong capacitance, wrong package, wrong rail, an existing-connection change, missing pins and duplicate pins, in addition to accepting the exact recorded delta. [Independent/visual review](review_notes.json).

Native ERC and pin preservation do not establish analog timing, solderability, procurement readiness or hardware operation. No board was ordered, powered, programmed or flashed. The six live electrical blockers remain open until appropriate integration and qualification.

## Reproduce and review

Use the recorded KiCad 9 bundled Python and CLI. Run from the repository root:

```text
python reviews/codex/imu_bias_filter/build_amendment.py
python reviews/codex/imu_bias_filter/export_native.py
python reviews/codex/imu_bias_filter/verify_amendment.py
python reviews/codex/imu_bias_filter/test_amendment.py
```

The builder writes only within this packet and rejects changed source evidence. Native exports bind reports to before/after input hashes. The verifier independently checks the incremental two-pin change and the cumulative IMU contract. The SVG comes directly from the native Navigation export; the review PNG uses CairoSVG. Publication CI validates captured evidence and the same contract; hosted native execution is not implied.

## Next smallest packet

**Define the 6S input-protection and power-package envelope before final IMU routing.** Begin with the [electrical findings](../design_completion/electrical/README.md): record normal/full-charge/transient voltages and the operating/absolute limits of every exposed component. Determine which parts must change or require coordinated protection, then quantify candidate package/courtyard areas and routing constraints. Do not silently reduce the 6S requirement or assume existing footprints remain suitable. This can proceed from the documented requirement while physical battery/BEC/module identities remain separate qualification inputs.

After that envelope is reviewed, route the complete IMU2 circuit on a fresh copy of the corrected PCB, resolving the recorded C40 via and translator-corridor obstacles. Record exact intended pad/track deltas; preserve repaired ground paths; refill and check ERC/netlist/DRC/parity on the same captured revision. Only reviewed integration should update live BOM, ordering exports and Stage A source-evidence contracts. Keep V1 inspection, V2 vehicle use and the future voice/text/location handset distinct; handset hardware still requires measured voice/RC coexistence.

## Viewer and packaging checks

The viewer contains 77 documents and 55 design images. Headless Edge checks at 1440 × 1000 and 390 × 844 passed loading all three IMU/placement revisions, correct candidate-project links, absence of misleading live-PCB links, current-guide opening and no page overflow or script errors. All 231 indexed local HTTP paths passed. [Viewer record](viewer_check.json). Publication/evidence checks pass locally; hosted CI execution remains unverified.
