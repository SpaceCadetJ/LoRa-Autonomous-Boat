# IMU 1.8 V interface candidate

This packet implements E-01 as an **isolated schematic candidate** based on published revision `a66980c`. The live V2 schematic, corrected PCB, firmware pin contract and purchasing package are unchanged. The live board still has all six electrical release blockers. This packet supplies a concrete circuit for the next CAD integration, not an order or fabrication release.

[Open annotated navigation drawing](v2_imu_candidate.svg) · [Native project schematic](source/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_sch) · [Electrical comparison](validation.json) · [Export provenance](native_manifest.json)

## What changed

The ICM-20948 receives a dedicated 1.8 V I/O supply, separate I2C translation and a translated interrupt. Its main VDD stays at 3.3 V. MCU PB6/SCL, PB7/SDA and PB5/interrupt allocations remain unchanged.

| Existing pin | Published connection | Candidate connection |
|---|---|---|
| U6.8 VDDIO | +3V3 | +1V8_IMU |
| U6.22 CS | +3V3 | +1V8_IMU |
| U6.23 SCL | MCU I2C1_SCL | IMU_SCL_1V8 through U10 |
| U6.24 SDA | MCU I2C1_SDA | IMU_SDA_1V8 through U10 |
| U6.12 INT1 | MCU IMU_INT | IMU_INT_1V8 through U11 |

The native comparison checks all physical pins: 114 to 126 electrical components, 361 to 398 pins, exactly these five changes and 356 preserved existing memberships. All existing values, footprints, MPNs and library identities remain unchanged. AD0 and FSYNC stay grounded; AD0 selects address 0x68. The existing AD0 pin-type ERC warning remains recorded. No ERC rule was relaxed.

## Added circuit and part holds

| Reference | Candidate | Connection or purpose |
|---|---|---|
| U9 | TLV75518PDBVR, SOT-23-5 | IN and EN to 3.3 V; OUT supplies +1V8_IMU; pin 4 NC |
| U10 | PCA9306DCTR, project-local DCT-8 footprint | Low-side reference to 1.8 V; VREF2 and EN tied together through R38 to 3.3 V |
| U11 | SN74AXC1T45DBVR, SOT-23-6 | VCCA and DIR at 1.8 V, VCCB at 3.3 V; A receives INT1, B drives PB5 |
| R36 / R37 | 4.7 kOhm | Sensor-side SCL/SDA pull-ups to 1.8 V; existing R23/R24 remain on 3.3 V |
| R38 | 200 kOhm; exact ordering part held | PCA9306 reference/enable bias; do not directly strap that node to 3.3 V |
| R39 | 100 kOhm | 1.8 V rail bleeder: nominal 18 uA, above the nominal 4.5 uA translator reference bias |
| C38 / C39 | 2.2 uF nominal, 0805; exact ordering parts held | LDO input/output. Select parts that retain at least 1 uF effective after DC bias, tolerance and temperature |
| C40 / C41 / C42 | 100 nF | U6 VDDIO and both U11 supply bypasses |

Twelve parts are added in this candidate. Their complete proposed properties are in [candidate_manifest.json](candidate_manifest.json); none has been added to the live ordering CSVs. The three IC suffixes are explicit circuit candidates, not verified supplier inventory. C38/C39 use a larger nominal value to provide starting margin; the effective-capacitance requirement is still a selection hold.

## Footprint finding

TI's current PCA9306 appendix drawing **DCT0008A, 4220784/D, October 2025** gives a 2.9-3.1 mm square body and a 0.65 mm pitch. Its example land pattern uses 1.1 x 0.4 mm pads with row centers 3.8 mm apart. The installed `SSOP-8_2.95x2.8mm_P0.65mm` has different pad widths and row spacing; it was not accepted as a verified match. [TI PCA9306, pages 28-30](https://www.ti.com/lit/ds/symlink/pca9306.pdf#page=28).

The [project-local footprint](source/hardware/kicad_v2/LoRa_Boat_Controller_V2.pretty/TI_DCT0008A_PCA9306_3x3mm_P0.65mm.kicad_mod) implements the TI example coordinates: x = +/-1.9 mm, y = -0.975/-0.325/+0.325/+0.975 mm; pins 1-4 descend the left, pins 5-8 ascend the right. Native loading checks all eight pad numbers, positions and sizes in [footprint_check.json](native/footprint_check.json). Stencil, courtyard, orientation and assembled-part qualification remain open. No 3D model is claimed.

## Electrical review and acceptance limits

An independent datasheet review confirmed the regulator, I2C and interrupt pin maps. [TLV755P, pages 3-4](https://www.ti.com/lit/ds/symlink/tlv755p.pdf#page=3), [PCA9306, pages 4 and 13-15](https://www.ti.com/lit/ds/symlink/pca9306.pdf#page=13), [SN74AXC1T45, pages 3 and 17-18](https://www.ti.com/lit/ds/symlink/sn74axc1t45.pdf#page=3).

The AXC symbol reuses the geometry of the installed same-pin LVC drawing, with a project-local AXC identity and TI datasheet; its six pin names/numbers are explicitly checked. This is not a claim that LVC and AXC devices are interchangeable. The PCA9306 symbol similarly has an explicit TI identity and package. Its bias-net power flag documents the resistor-fed reference for ERC; it does not prove a measured voltage or independent power isolation.

Before powering a future accepted assembly, resolve the other electrical findings and qualify the selected capacitors. Then record:

1. 1.8 V operating limits and startup/shutdown waveforms at U6 VDDIO, CS, both bus lines and INT1. The always-enabled PCA9306 is not guaranteed isolation of an independently unpowered sensor domain.
2. TLV755 output staying within its input-plus-0.3 V reverse-current limit during rail collapse. Its internal discharge is not reverse-current blocking; add protection if measured conditions require it. [TI TLV755P, pages 12 and 17-18](https://www.ti.com/lit/ds/symlink/tlv755p.pdf#page=12).
3. Initial 100 kHz I2C timing, low-level voltages and rise/fall times on both sides. At address 0x68, read WHO_AM_I=0xEA after the documented startup delay. Keep CS/SCL high during startup; unsupported low conditions require the manufacturer's reset procedure. [TDK DS-000189 rev 1.6, manufacturer-authored mirrored datasheet](https://cdn.sparkfun.com/assets/8/4/6/4/2/ds-000189-icm-20948-datasheet-2024.pdf#page=19).
4. INT1 configured push-pull, PB5 input-only and interrupt handling inhibited until initialization. AXC internal data pull-downs avoid an extra strong interrupt pull-down. Its supply isolation does not replace a full board sequencing test.

No board was powered, programmed or measured. Native ERC cannot validate these analog and timing limits. Stage A firmware does not initialize the IMU.

## Reproduce and continue

The input capture contains the exact 16 source/library files from `a66980c`, including the clean committed V1 definition rather than the unrelated local edit. Once captured, the build does not require Git to retrieve those inputs. It requires the recorded KiCad 9 standard libraries and bundled Python; their hashes are informational in the manifest and native electrical verification remains mandatory after changing library versions.

```text
python reviews/codex/imu_interface/build_candidate.py
python reviews/codex/imu_interface/export_candidate.py
python reviews/codex/imu_interface/verify_candidate.py
python reviews/codex/imu_interface/test_candidate.py
```

The build invokes only the isolated schematic generator and checks preservation of all 52 live design inputs. The export captures all candidate schematics, project/library tables and footprint dependencies before invoking native netlist/ERC/SVG commands. The independent verifier rejects unexpected pin, component, value, MPN and ERC changes; its eight tests exercise corruption/rejection cases. Publication CI checks captured source/export hashes and reruns the comparisons; it does not claim to rerun native KiCad on the hosted runner.

**Next smallest task:** assess placement of these 12 parts and the required rerouting around U6 on a copy of the corrected PCB. Preserve the existing ground repair, board outline and unaffected copper. Record whether the 80 x 46 mm outline can accommodate these additions and the upcoming power corrections before integrating a new live circuit/layout. Keep E-01 open until that integration and hardware acceptance are complete. Do not update purchasing exports or the Stage A source-evidence contract to this unrouted candidate.

## Packet verification

Two same-host builds reproduce all nine generated schematic/library/footprint outputs and all seven isolated source scripts byte-for-byte; see [reproducibility.json](reproducibility.json). All 52 live CAD inputs remain unchanged. The changed A2 Navigation drawing was rasterized and visually inspected after separating supply labels, shortening notes and correcting the candidate title; [visual record](visual_review.json), [review image](navigation-review.png). The other six pages retain the original circuit and passed coordinate bounds, but this packet does not claim a fresh full visual review of every sheet.

The [desktop/phone viewer checks](viewer_check.json) passed candidate selection, image loading, guide opening, correct candidate-project linking and absence of a misleading live-PCB link, with no script errors or page overflow. Packaging currently includes 75 documents and 53 design views; 236 local HTTP links pass. Eight corruption/rejection tests pass. Hosted workflow execution remains separate from these local checks.

A clean staged-source archive also passed the publication hash checks, all eight candidate tests and viewer rebuild/validation with revision `source-archive`. This establishes packaging portability on the recorded host; it is not a hosted CI or hardware result.
