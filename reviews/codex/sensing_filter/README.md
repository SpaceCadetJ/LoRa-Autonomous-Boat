# SENSE-02 — isolated sensing filter correction

[Revised native Power sheet](native/svg/LoRa_Boat_Controller_V2-Power.svg) | [Baseline Power sheet](../power_sheet_polish/native/svg/LoRa_Boat_Controller_V2-Power.svg) | [Isolated KiCad project](source/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pro) | [Verification](validation.json) | [Filter calculations](RESULTS.md)

This isolated candidate adds an output filter and a local supply bypass for the INA180 current-sense amplifier. It replaces the two unresolved sensing-capacitor identities with exact manufacturer-confirmed parts and reconciles the shunt's rating annotation. The change is limited to the copied Power schematic. Live PCB copper, BOM, firmware and V1 behavior remain unchanged. **This is a schematic candidate, not a fabrication, assembly or powered-use release.**

## Read the actual change

| Item | Baseline | Isolated candidate |
|---|---|---|
| U8 OUT | Directly shares `/ISENSE` with C37 and MCU PA4 | Moves to `/Power/ISENSE_DRV`; R44 connects it to the original `/ISENSE` node |
| R44 | Absent | Yageo RC0603FR-071KL, 1kΩ ±1%, in series with the ADC/filter node |
| C37 | Nominal 100nF directly on amplifier output; unresolved identity | 100nF TDK C1608X7R1H104K080AA, now on the ADC side of R44 |
| C36 | Nominal 100nF; unresolved identity | Same nominal capacitance, exact TDK C1608X7R1H104K080AA identity; divider wiring unchanged |
| C59 | Absent | TDK C1608X7R1E105K080AB, nominal 1µF/25V X7R, between +3V3 and GND for U8 bypass |
| R33 | `0.02R 1W`, exact Bourns MPN unchanged | `0.02R 3W`, matching CRA2512-FZ-R020ELF manufacturer's rating at 70°C; no current uprating |

The [expected contract](expected_contract.json) declares one existing pin move, four new pin memberships and two added components. C37 and PA4 retain their original net; C59 does not create a new supply rail. All other old pin memberships, both converters, ACT-01 exclusive source populations and C11's identity/lands are preserved. The separate IMU2 candidate is not merged. Native verification must match the declared delta; unchanged ERC alone is insufficient. Independent comparison passes with 130 components, 433 physical pin memberships, 122 nets and 11 sheets. Captured ERC has zero errors and the unchanged AD0 warning. All 27 mutation tests pass; 37 of 38 source files remain byte-identical.

## Why these parts and values

TDK confirms the exact 100nF/50V and 1µF/25V X7R parts in 0603 packages. Yageo confirms the 1kΩ/1% resistor. [Manufacturer evidence](sources.json) records exact URLs, ratings, dates and remaining limits. These are candidate identities, not supplier stock or ordering claims.

The INA180 application guidance recommends an output RC filter for a high-impedance receiver and requires at least 0.1µF local supply bypass. R44 separates the amplifier output from the large ADC-node capacitor. C59's nominal 1µF provides nominal margin over 0.1µF; its effective capacitance, frequency behavior and physical placement still need qualification. Its schematic proximity is not PCB placement. [TI SBOS741H §§9.1.1, 9.1.3, 9.4.1](https://www.ti.com/lit/ds/symlink/ina180.pdf).

The old 100nF direct loading was 100 times TI's **listed typical** 1nF capacitive-load capability. That entry is not a guaranteed hard maximum, and oscillation was never measured. The new topology is a deliberate correction; it does not by itself prove amplifier stability or ADC accuracy.

Nominal R44/C37 gives τ=100µs and a single-pole cutoff near 1.59kHz. The [calculations](RESULTS.md) separate nominal and initial-tolerance arithmetic from actual X7R bias, temperature, aging, amplifier impedance, ADC sampling and scan interactions. No acquisition rate or sample-time setting is released.

## What remains unqualified

- **Power-off and faults:** R44 is not a clamp or a proven isolation switch. PA4 TTa and PA2 FT still need separate analog/reset/supply-off analysis. Internal MCU diodes and the unpowered INA180 output are not accepted protection paths.
- **Voltage envelope:** the 47kΩ/6.8kΩ divider remains unchanged. The SENSE-01 6S reference-margin and INA180 26V common-mode concerns remain open. A filter does not establish transient protection or reduce the 6S requirement.
- **Capacitance and layout:** exact part identity is resolved for the new candidate, but effective C37/C59 and bypass effectiveness are not measured or guaranteed by typical curves. TI's minimum bypass requirement must be met at actual bias, temperature and age.
- **Land pattern and assembly:** existing generic 0603 footprints are retained. Current C36/C37 board pads are 0.90×0.95mm with a 0.65mm inner gap; they are not an exact match to TDK's published 0.60–0.80mm reflow dimensions. Land/stencil/assembly review remains held. New R44/C59 have no routed PCB implementation.
- **Current and calibration:** R33's 3W component rating does not establish board thermal limits. The channel still observes converter-input current, excluding BEC_ONLY servo and external propulsion current. Voltage remains post-D12 VIN_RAW. Neither is whole-vehicle battery telemetry.

The [Stage A firmware](../../../firmware_v2/README.md) is unchanged and implements no ADC acquisition. Future software must retain invalid-data handling, calibration/reference tracking and actual measurement-boundary names described in [SENSE-01](../sensing_6s/README.md). Missing receiver/arm qualifications stay disabled. V1 inspection, V2 vehicles and the future voice/text/location handheld remain distinct; measure voice/RC coexistence before handheld hardware selection.

## Review and continue

Open the isolated project above to inspect the new Power sheet. Use the native SVG for readable navigation and the baseline link for comparison. [Build record](build_manifest.json), [native capture](native_manifest.json), [verification](validation.json), [review notes](review_notes.json) and [packet hashes](packet_manifest.json) separate recorded native results, independent comparisons, conditional analysis and untested hardware.

**Next bounded task: divider scaling and power-off protection.** Establish the relevant source/transient and guaranteed minimum VDDA envelopes, then specify a divider/interface that respects PA2's analog and unpowered behavior. Do not infer that the 6S battery maximum alone bounds VIN_RAW transients or that an MCU internal diode is a designed clamp. U8 common-mode protection, full input feed, leakage/damping, VSERVO and combined IMU2 remain open.

```text
python -B reviews/codex/sensing_filter/test_candidate.py
python -B reviews/codex/sensing_filter/verify_candidate.py --check
python -B reviews/codex/sensing_filter/packet.py --check
python -B tools/quality/check_publication.py
node pm/tools/validate.mjs
```

Check FILE_OWNERSHIP.md, Git status and the newest handoff before editing. Never overwrite an earlier candidate or run primary routing/generation to update documentation. Preserve the unrelated local v1_design.py and route_v2.py edits. Use ordinary selective commits and fast-forward publication only to the authorized existing repository.
