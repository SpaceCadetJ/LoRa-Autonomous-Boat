# BUCK5-A1 — 5 V converter and shared-feed review

**The second converter is now an editable LM76003 schematic candidate with a separate annotated sheet.** Open the [native drawing](v2_buck_5v.svg), [KiCad project](source/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pro), [part/pin contract](expected_contract.json) or [native comparison](validation.json). The workspace exposes it under **Design → V2 → BUCK5-A1**.

This copy includes the preceding 3.3 V candidate unchanged. Live CAD/copper, V1 and firmware are preserved; IMU2 is still separate. It is not a fabrication, ordering or powered-use release. The retained 6S requirement and optional on-board actuator configuration remain design requirements.

## What changed and what native checks establish

The boundary is U3, L2, C7–C10, R6, R8 and R9: nine old components with 22 physical pins. R6 is removed; U3 and seven supporting identities change; C49–C55 are added. The resulting candidate has **119 components and 398 physical pins**, compared with 113/361 before. Eleven retained pin memberships change, two disappear and 39 are added. **All 339 outside-boundary pins, identities, sheet paths and native pin metadata are preserved.** The earlier Buck3V3 source sheet is also byte-identical.

Native KiCad 9.0.7 ERC reports **zero errors and the original single AD0 warning**. The independent checker has 27 contract/rejection tests. These results establish captured schematic agreement, not electrical performance or PCB readiness. A PWR_FLAG on +5V_BUCK tells ERC that the converter drives through passive L2; it is an explicit design annotation, not measured output evidence. See [native commands and hashes](native_manifest.json) and [review record](review_notes.json).

| U3 physical pins | Intended connection |
|---|---|
| PVIN 20/21/22; EN18 | /Power/VIN_BUCK, EN always enabled with supply present |
| SW1–5 | L2.1 and C7.1; all five physical pins retained |
| BOOT6 | C7.2; 470 nF directly to SW |
| VCC8 | C54.1; 2.2 µF to GND, no external load |
| BIAS9 | Own /Power/+5V_BUCK with local C55, 1 µF to GND |
| FB12 | R8.2/R9.1; R8.1 senses +5V_BUCK before D4 |
| RT10 / SS11 / PGOOD16 | Three explicit no-connects: default frequency, internal soft start, unused flag |
| SYNC17 | GND, automatic light-load mode |
| AGND13–15, PGND24–26, EP31 | GND; EP is a thermal path as well as the analog reference connection |
| NC7/19/23/27–30 | GND per manufacturer instruction |

The installed symbol treated pins 7/23 as no-connects. This packet preserves the original library capture and amends those two pins to passive ground connections in the reviewed symbol. The parent hierarchical ports preserve `/Power/VIN_BUCK` and `/Power/+5V_BUCK`; D4/D9 and every actuator connection remain outside this amendment. Pin assignments and allowed configurations were checked against [TI SNVSAK0A §5](https://www.ti.com/lit/ds/symlink/lm76003.pdf).

## Exact candidate parts

Every part remains held. Embedded properties and the JSON contract carry orderable identity and source; the table is not a complete board order.

| References | Exact candidate | Value / purpose |
|---|---|---|
| U3 | Texas Instruments LM76003RNPR | 60 V / 3.5 A family, 30-pin WQFN plus EP; 2 A rail design goal |
| L2 | Coilcraft XAL6060-103MEC | 10 µH ±20% |
| C7 | TDK C1608X7R1E474K080AB | 470 nF / 25 V, X7R, 0603, BOOT |
| C54 | TDK C2012X7R1E225K125AB | 2.2 µF / 25 V, X7R, 0805, VCC |
| C55 | TDK C1608X7R1E105K080AB | 1 µF / 25 V, X7R, 0603, BIAS |
| C8, C9, C49, C50, C51 | TDK C3225X7R1E226M250AB | Five 22 µF / 25 V X7R output capacitors |
| C10, C52 | TDK C5750X7S2A106K230KB | Separate pair of 10 µF / 100 V X7S local input capacitors |
| C53 | Murata GRM21AR72A224KAC5L | 220 nF / 100 V HF input bypass |
| R8 / R9 | Vishay CRCW0603100KFKEA / CRCW060324K9FKEA | 100 kΩ / 24.9 kΩ, 1% feedback divider |

Exact new capacitor references: [BOOT](https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C1608X7R1E474K080AB), [VCC](https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C2012X7R1E225K125AB), [BIAS](https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C1608X7R1E105K080AB). Retained family evidence is linked in the [first-converter guide](../buck_3v3/README.md). No stock, price or assembly qualification is asserted.

## Why this regulator, and the limits of the calculations

The smaller LMR36520's minimum valley and peak comparator limits leave no common fixed-inductance solution for the particular ideal 2 A / 7–44 V corner screen. Initial L tolerance and frequency corners force the high-to-low ripple ratio to 6.296, while the two minimum-limit comparisons allow at most a ratio of two. This is a selection/qualification finding, not proof that every physical LMR36520 fails. The [model](model.py) records the derivation without confusing valley and peak thresholds. [LMR36520 electrical table and current-limit description](https://www.ti.com/lit/ds/symlink/lmr36520.pdf).

The selected LM76003 gives more initial current margin. Its 10 µH choice differs from the 6.8 µH typical 5 V/500 kHz selection and therefore needs loop/transient review. Across 24 initial corners at **converter-terminal** VIN 7/25.2/44 V, the largest calculated peak is **2.65025 A**. Feedback predicts **5.04616 V nominal**, with **4.86630–5.18991 V** including initial resistor/reference tolerances and a conservative feedback-leakage term. TCR, aging, dynamic regulation and automatic-mode light-load offset remain unbounded. The 44 V value is a target, not an accepted clamp ceiling. [TI electrical limits and application guidance](https://www.ti.com/lit/ds/symlink/lm76003.pdf).

The inductor's 7.6 A saturation entry represents typical 30% inductance loss at 25°C. It does not establish hot short-circuit capability against a converter whose high-side threshold can reach 6.8 A before propagation effects. Thermal loss estimates omit hot DCR, core and AC winding losses. [Coilcraft XAL60xx table and footnotes](https://www.coilcraft.com/getmedia/ea51f14b-7f32-4dc6-8dfe-d4b70549040f/xal60xx.pdf).

Five output capacitors total **110 µF rated, 88 µF at initial −20% tolerance alone**. Effective capacitance is unknown. TI's 100 µF typical selection is not a universal guaranteed minimum, nor does this bank prove a separately chosen 100 µF effective target. Determine required capacitance from load-step and loop requirements, then establish bias/temperature/tolerance/aging bounds. The local input network is also a proposal: do not import the first converter's 4.7 µF criterion into this different regulator. Its X7S parts and 220 nF HF bypass require an explicit review against this device's guidance. BOOT/VCC/BIAS effective values and placement also remain held.

## Whole-board current is a separate constraint

The source model includes both rail loads, assumed 85% converter efficiencies, nominal F1=36.7 mΩ and R33=20 mΩ, and ST's diode loss fit `P = 0.6 I_AV + 0.027 I_RMS²`. For the illustrative DC case it sets RMS=average and assumes zero harness resistance. The lower-current constant-power solution is used; ripple, warm resistance, cold diode drop, startup and dynamic stability are excluded. At 7 V the equation is `P_converter_input = 6.4 I − 0.0837 I²`. [STPS3H100 DS6597, p. 2](https://www.st.com/resource/en/datasheet/stps3h100.pdf).

| Planning case, all at 1.2 A logic load | Battery | Total 5 V load | Calculated board-feed current |
|---|---|---|---|
| External BEC carries actuator energy; illustrative auxiliary only | 7 V | 20 mA | 0.75375 A |
| Full 5 V rail goal | 7 V | 2.00 A total | 2.65862 A |
| 2 A servo plus auxiliary allowance | 7 V | 2.02 A total | 2.67838 A |
| Full 5 V rail goal | 25.2 V | 2.00 A total | 0.66915 A |

These use nominal **3.3 V/5 V planning powers**, not the full feedback envelopes. A 7 V battery is not 7 V at the converter: the full-load example leaves about **6.177 V** at the terminals and dissipates **1.786 W in D12**. A 1 A feed goal leaves only **0.28177 A total 5 V allocation** in this scenario, about 0.26177 A after 20 mA auxiliary demand. These are arithmetic screens, not permitted operating currents. The 2.02 A example intentionally exceeds the stated 2 A total rail goal and is shown to expose the distinction.

Even lossless simultaneous nominal outputs need 1.9943 A at 7 V. The present 2 A fuse starts at **1.5 A continuous screening** under the manufacturer's 25% derating guideline, before temperature adjustment. This guideline is not a 1.5 A trip threshold; fault interruption and pulse endurance need separate review. The on-board full-load variant therefore needs an input-stage redesign or an explicit reduced simultaneous-load specification. No user requirement is silently removed. [Littelfuse 451/453 datasheet](https://www.littelfuse.com/assetdocs/fuse-451-and-453-datasheet?assetguid=533cd5cc-956c-4243-867f-6ab5a62f6ba1).

## Existing actuator boundary: new package finding, unchanged circuit

D4 anode is +5V_BUCK; D9 anode is BEC_IN. Their cathodes join VSERVO. This arrangement selects through source voltages and diode drops; it provides no guaranteed priority or controlled sharing. The external-BEC arithmetic assumes actuator energy comes from the BEC. That assumption requires a reviewed population/voltage contract: a populated D4 can still contribute board current.

**D4/D9 declare Vishay SS34 but use D_SMA; the manufacturer's part is SMC/DO-214AB.** Existing ordering holds remain and now identify this mismatch. The datasheet's forward drop at one pulsed test point is not an all-temperature voltage allowance. [Vishay SS34, document 88751](https://www.vishay.com/docs/88751/ss32.pdf). Do not substitute footprints or similarly named diodes without revising exact identity, thermal and polarity evidence.

U4/U5 buffer supplies and C13/C14 still follow VSERVO. Their operating supply is 4.5–5.5 V; a 6 V BEC cannot be accepted by assuming an arbitrary fixed diode drop. Conversely, a nominal 5 V converter does not establish 5 V at the servo after D4. No actuator wiring/power instruction is released here. [SN74AHCT1G125 recommended conditions](https://www.ti.com/lit/ds/symlink/sn74ahct1g125.pdf).

BIAS9 uses the converter's own output, but its input-relative voltage limit still requires shutdown and backfeed analysis. Account for stored charge, falling VIN and BEC/USB paths. EN tied to VIN provides no pack discharge cutoff. Original polarized C1, full negative-rail leakage, input damping, ADC/sense and IMU integration remain open.

## Package/layout evidence and next task

[Native package inspection](native_geometry.json) verifies all seven footprint identities and 31 regulator electrical pad numbers. The captured RNP footprint matches 0.5 mm pitch and 1.8 × 4.5 mm EP, but its perimeter lands and paste windows differ from TI's example. This difference is documented rather than approved. TDK input/output custom dimensions remain the preceding reviewed proposals; generic passives, Coilcraft orientation, stencil, thermal vias, assembly and whole-board fit remain held. This packet routes no PCB copper.

Place local input/HF bypass tightly around PVIN/PGND, BOOT directly to SW, VCC and BIAS bypass at their pins, and keep FB away from switch copper. Connect every ground/NC thermal pad and provide a reviewed EP heat path. Keep 3.3 V, power-input and radio/IMU layout constraints visible together before local routing. Do not run a full generator/router over the corrected live board.

**Next smallest circuit packet: separate the PWM buffer supply from VSERVO and resolve exact D4/D9 identities plus the external-BEC/on-board population contract.** Begin from this captured source and preserve both converter contracts. Then close the appropriate 6S input-feed rating, nonpolar reservoir/leakage/damping, ADC/sense and combined IMU2 amendments before routing. The optional on-board full-load goal remains open; do not convert the 1 A initial feed goal into an accepted 2.66 A design.

For a clean restart, read [packet_manifest.json](packet_manifest.json), [review_notes.json](review_notes.json) and the contract first. Portable checks are `verify_candidate.py --check`, `test_candidate.py`, `model.py --check`, `test_model.py`, and `inspect_packages.py --check` under this directory, plus `python -B tools/quality/check_publication.py` and `node pm/tools/validate.mjs`. Native command/source hashes are recorded separately. Create a new packet for further circuit changes; leave this capture and the unrelated local v1_design.py/route_v2.py edits intact.

V1 inspection, V2 vehicle-node applications and future handheld work remain distinct. The handheld still requires **voice, text and location**, with measured voice/RC coexistence before hardware selection. No new operational firmware or hardware/flash test is claimed.
