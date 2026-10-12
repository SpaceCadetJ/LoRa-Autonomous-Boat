# BUCK33-A1 — first 3.3 V converter, 2026-10-12

**The complete first 3.3 V converter is now an editable, independently checked schematic candidate.** It replaces the old cell only in a copy of INPUT-A1. Open the [annotated native sheet](v2_buck_3v3.svg), [KiCad project](source/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pro), [expected electrical contract](expected_contract.json) or [native comparison](validation.json). In the workspace choose **Design → V2 → BUCK33-A1**; zoom or open the SVG for detailed inspection.

This is a design checkpoint, not a finished or powered board. Live CAD, corrected copper, V1, procurement and firmware are unchanged. The copied input protection remains unqualified, and IMU2 remains a separate candidate. The 6S requirement and optional on-board actuator supply are retained.

## Circuit and exact expected delta

The new `/Power/Buck3V3/` sheet uses **LMR36520ADDAR**, an adjustable synchronous converter, with a 1.2 A logic-rail design goal. Its parent VIN port preserves `/Power/VIN_BUCK`; +3V3 and GND remain the existing global nets. The model uses 7–25.2 V battery intent and a **44 V protected-rail target**, not a verified TVS clamp ceiling. TI specifies 4.2–65 V recommended VIN operation, with a −0.3 V absolute lower limit that still requires negative-rail closure. [TI SNVSBF0C, November 2025, §§6–8](https://www.ti.com/lit/ds/symlink/lmr36520.pdf).

| Connection / identity | BUCK33-A1 contract |
|---|---|
| U2 VIN2 and EN3 | Both to /Power/VIN_BUCK; always enabled while input is present; no pack discharge cutoff |
| U2 PGND1 and exposed pad9 | Both GND; the thermal pad is not the sole electrical return |
| U2 VCC6 | C48.1 only; C48.2 GND; no external VCC load |
| U2 BOOT7 / SW8 | C3.2 to BOOT; C3.1 and L1.1 to SW; C3 directly across BOOT/SW |
| U2 FB5 | R4.2/R5.1; R4.1 +3V3 and R5.2 GND |
| U2 PG4 | Explicit no-connect marker; no assumed power-good supervision |
| L1.2, C5.1, C6.1, C47.1 | +3V3; output capacitor second terminals GND |
| C44/C45/C46 | Each terminal1 /Power/VIN_BUCK, terminal2 GND |
| Removed | R2, R3, C4, D3: old EN resistor, series bootstrap resistor, feed-forward capacitor and external catch diode |
| Replaced identities | U2, L1, C3, C5, C6, R4, R5 |
| New references | C44, C45, C46, C47, C48; C43 remains reserved by IMU2 |

The predeclared boundary contains 11 old references. Native export verifies **112 → 113 components, 356 → 361 physical pins**, ten changed existing memberships (including private-net hierarchy changes), eight removed pins and thirteen added pins. **All 330 pins outside the boundary preserve exact membership, part identity and sheet path.** ERC has **zero errors and the same single AD0 warning**. No PCB/DRC result is claimed for this circuit. [Validation](validation.json) and [native command/hash capture](native_manifest.json) distinguish these observations from the calculations below.

## Candidate parts and package evidence

These 12 references are held design candidates, not additions to an approved order. Embedded schematic properties carry exact MPNs, manufacturer, footprint and source link; [expected_contract.json](expected_contract.json) is the machine-readable part/pin list. Names in the table are procurement identities, not interchangeable generic values.

| References | Exact part | Value / role | Footprint disposition |
|---|---|---|---|
| U2 | Texas Instruments LMR36520ADDAR | 400 kHz, adjustable 2 A converter | Project-local TI_DDA0008B_LMR36520 |
| L1 | Coilcraft XAL6060-103MEC | 10 µH ±20%, shielded | Captured KiCad XAL6060 lands; orientation hold |
| C3 | KYOCERA AVX 06033C104KAT2A | 100 nF / 25 V, BOOT–SW | Captured 0603; EVM identity |
| C44, C45 | TDK C5750X7S2A106K230KB | 2 × 10 µF / 100 V local input | CAP-01 exact-part 2220 proposal |
| C46 | Murata GRM21AR72A224KAC5L | 220 nF / 100 V high-frequency input bypass | Captured 0805; EVM identity |
| C48 | TDK C1608X5R1E105K080AC | 1 µF / 25 V VCC bypass | Captured 0603 |
| C5, C6, C47 | TDK C3225X7R1E226M250AB | 3 × 22 µF / 25 V output | New exact-part 1210 proposal |
| R4 | Vishay CRCW0603100KFKEA | 100 kΩ, 1% feedback top | Captured 0603 |
| R5 | Vishay CRCW060343K2FKEA | 43.2 kΩ, 1% feedback bottom | Captured 0603 |

Primary references: [TI EVM SNVU677 schematic/BOM](https://www.ti.com/lit/ug/snvu677/snvu677.pdf), [Coilcraft XAL60xx drawing](https://www.coilcraft.com/getmedia/ea51f14b-7f32-4dc6-8dfe-d4b70549040f/xal60xx.pdf), [Vishay CRCW family](https://www.vishay.com/docs/20035/dcrcwe3.pdf), [TDK local input](https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C5750X7S2A106K230KB), [TDK output](https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C3225X7R1E226M250AB), [TDK VCC](https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C1608X5R1E105K080AC). Stock, pricing and exact generic-land compatibility are not asserted.

The custom output lands use **2.2 mm gap and 1.1 × 2.2 mm pads**, within TDK's recommended 2.0–2.4 / 1.0–1.2 / 1.9–2.5 mm ranges. Proposed courtyard: 4.9 × 3.3 mm. The input 2220 keeps the previously reviewed **4.4 mm gap and 1.3 × 4.6 mm pads**, 7.5 × 5.9 mm courtyard. Native dimensions and source hashes are recorded in [native_geometry.json](native_geometry.json); they establish geometry, not solder-process acceptance.

The TI footprint follows **DDA0008B, 4214849/B 09/2025**: 1.55 × 0.60 mm signal lands on 1.27 mm pitch, 5.4 mm column spacing; exposed copper 2.95 × 4.9 mm, mask/paste 2.71 × 3.4 mm. The unnumbered mask/paste aperture is not an extra electrical pad. The paste example assumes **0.125 mm stencil thickness**; another process needs its own aperture review. Thermal vias and board heat spreading are not designed yet. [TI package drawing appended to the datasheet](https://www.ti.com/lit/ds/symlink/lmr36520.pdf).

Coilcraft library pads measure 1.43 × 5.50 mm, centers ±2.02 mm. Manufacturer dimension-arrow orientation was not independently resolved in this packet; no exact-land acceptance is claimed. The manufacturer identifies a preferred start/short lead for the switching connection. L1.1 is SW in the contract, but the captured footprint does not establish the physical assembly orientation. Close this before placement release.

## Calculations, separated from hardware qualification

The [reproducible model](analysis.json) and eight limiting/rejection tests screen initial values. Feedback is **3.3148 V nominal**, with **3.21994–3.41200 V** from TI's 0.985–1.015 V VFB limits and ±1% resistors. TCR, aging, leakage, layout and dynamic regulation are excluded. Check all +3V3 consumers against the complete accepted envelope; do not label this exactly 3.300 V.

TI's 3.3 V / 400 kHz quick-start uses **6.8 µH and 3 × 22 µF rated output capacitance**. This candidate deliberately uses **10 µH** to reduce high-input ripple. At assumed 44 V input, 3.3 V / 1.2 A output, initial minimum 8 µH and 340 kHz, the ideal screen gives **1.12224 A peak-to-peak ripple, 0.63888 A valley, 1.76112 A peak and 1.24296 A RMS**. The 29.82 mΩ, 25°C DCR screen gives 46.07 mW winding loss; it excludes hot resistance, AC and core loss. Nominal 44 V ripple is 38.2% of the 2 A rating; the initial worst screen is 56.1%, beyond the 20–40% selection guideline. Therefore the nominal choice does not prove all-corner compliance. [TI §§8.2.1.2.2–8.2.1.2.3](https://www.ti.com/lit/ds/symlink/lmr36520.pdf).

Coilcraft's 7.6 A Isat describes a **typical 30% inductance drop at 25°C**, not a guaranteed hot minimum. The TI low-side ILIMIT is a **valley limit**; its separate high-side ISC maximum is 3.6 A. Their comparison does not prove safe hot short-circuit behavior. The Eq.5 minimum-L screen reaches 4.215 µH at the upper feedback bound and 340 kHz; actual L under current/heat remains unknown. Validate load steps, startup, fault recovery and loop stability for the changed LC network. [Coilcraft table/footnotes](https://www.coilcraft.com/getmedia/ea51f14b-7f32-4dc6-8dfe-d4b70549040f/xal60xx.pdf).

The shortest ideal on-time screen is 159.09 ns; TI's 92 ns minimum-on-time entry is **nominal only**. This cannot guarantee fixed-frequency operation. At 4.2 V converter input the upper-output-bound off-time screen is 407.87 ns versus 102 ns maximum minimum-off-time, but real losses and regulation need verification. A 7 V battery provides 2.8 V gross headroom above 4.2 V before fuse, diode, shunt, harness and sag. Tying EN to VIN implements no pack undervoltage discharge protection.

The current TI §8.1 recommends X7R or better and treats application capacitances as effective unless stated otherwise. C44/C45 are X7S and C48 is X5R: these are explicit **dielectric exceptions under review**, based on the screening/EVM precedent, not accepted substitutes. Establish effective VCC and BOOT bypass against the 1 µF / 100 nF application values across bias, temperature, tolerance and aging, or revise the exact parts in a new contract. Neither an EVM identity nor a nominal marking clears this gate.

C44/C45 must provide **≥4.7 µF combined effective local input capacitance**, separate from C46 and the remote reservoir. The three output capacitors total **66 µF rated**, with no established effective lower bound. Bias, temperature, tolerance, aging, ripple and assembly stress remain open for both banks. Do not treat an EVM BOM or these native connections as capacitor qualification. See the [CAP-01 requirements and source-damping study](../input_capacitors/README.md).

## Placement and acceptance work

Place C46 closest to U2 VIN2/PGND1, followed by C44/C45 with short shared return. Place C48 beside VCC6/PGND1 with a short return. Keep the switching-current loop compact; place C3 directly between BOOT7 and SW8, then L1 and the output bank. Keep SW copper away from FB and the radio/IMU signals. Sense the output bank with the divider and route its quiet return without sharing high-current drop. Connect both PGND1 and pad9, with a reviewed thermal-via/plane strategy and actual temperature model. These are routing instructions for the next candidate, not a claim that the 80 × 46 mm PCB has room.

Before board integration, close hot magnetics, regulator junction temperature, input and output effective capacitance, loop response, real harness hot-plug/damping, and enabled startup across the operating range. The copied input still has polarized C1 and unresolved full-circuit reverse leakage. The old 5 V buck, sense/ADC range/sequencing and buffer circuits remain uncorrected. The 44 V target does not establish TVS clamping or downstream-pin survival. No hardware was powered, flashed or tested.

## Efficient restart and reproduction

**Next smallest circuit packet: the isolated 5 V converter cell**, retaining the optional on-board actuator variant and a separate external-BEC configuration. Begin from this exact BUCK33-A1 source, choose exact regulator/supporting parts with 6S headroom, record only the intended second-cell delta and preserve all first-cell pins/identities. Reconcile the 7 V simultaneous-load/fuse/diode/thermal budget before promising 5 V / 2 A operation. Then address the nonpolar reservoir plus complete negative-rail/damping amendment, sense/ADC and buffer corrections; merge IMU2 only with an explicit combined contract. Do not redo the completed first-cell nominal part search or overwrite corrected copper with a full generator/router run.

V1 inspection, V2 boat/rover/telemetry applications and the future handheld remain distinct. The handheld requires **voice, text and location**, with measured voice/RC coexistence before hardware selection. Ordering and application guides retain their current holds; no new flashable control image is produced here.

Read [packet_manifest.json](packet_manifest.json) and [review_notes.json](review_notes.json) first. Portable checks from the repository root:

```text
python -B reviews/codex/buck_3v3/verify_candidate.py --check
python -B reviews/codex/buck_3v3/test_candidate.py
python -B reviews/codex/buck_3v3/model.py --check
python -B reviews/codex/buck_3v3/test_model.py
python -B reviews/codex/buck_3v3/inspect_packages.py --check
node pm/tools/validate.mjs
python -B tools/quality/check_publication.py
```

The recorded native capture used KiCad 9.0.7 netlist/ERC/SVG exports on the captured source, followed by independent contract comparison; it has nine sheets. `build_candidate.py` and `export_native.py` document the construction/capture procedure, but should not be rerun over this frozen packet just to refresh documentation. Use a new packet for subsequent changes. Preserve the two unrelated local generator/routing edits. CI checks the captured evidence and software; hosted CI execution and fabrication acceptance are separate claims.
