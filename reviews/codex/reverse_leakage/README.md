# Reverse leakage: the complete input boundary — 2026-10-12

**A bleeder alone does not close INPUT-A1's reverse-voltage requirement.** The review found a second constraint: C1 is polarized, and Panasonic prohibits applying reverse voltage. A calculation that stays above a converter's −0.3 V absolute limit still cannot accept that capacitor. The [interactive review](index.html) compares the leakage cases and the separate ADC problem. [Captured native connections](capture.json) identify every affected boundary.

This packet is a design disposition, with **zero live or candidate electrical/copper change**. It preserves [INPUT-A1](../input_stage/README.md), the separate IMU2 candidate and the corrected PCB. No new native ERC or DRC run is claimed because no circuit changed. Manufacturer limits were independently reviewed; the calculations are reproducible analytical results, not SPICE or measurements. All parts and powered-use procedures remain held.

## What changed in our understanding

| Boundary | Supported limit | Consequence |
|---|---|---|
| C1, EEEFK1J470P | Panasonic says “Do not apply a reverse voltage to the capacitor.” | Neither −69 mV nor a conventional diode clamp establishes C1 acceptance. Its −55…105°C rating also cannot inherit the rectifier's 125°C test condition. [Part](https://industrial.panasonic.com/ww/products/pt/aluminum-cap-smd/models/EEEFK1J470P), [guidance p. 4, 2025-09-01](https://industrial.panasonic.com/cdbs/www-data/pdf/RDE0000/DME0000COL75.pdf#page=4). |
| Proposed LMR36520 VIN and EN | Absolute minimum −0.3 V; normal VIN starts at 4.2 V. | Use −0.1 V as a proposed fault-design target with margin, not an operating voltage. The brief −3.5 V exception applies to SW only. [TI SNVSBF0C, p. 5](https://www.ti.com/lit/ds/symlink/lmr36520.pdf#page=5). |
| Proposed INA281 inputs | Common mode −4…110 V operating, −20…120 V absolute; supply and output retain their own limits. | Its input range is wider than the buck's. Input-bias maxima are stated under specific powered conditions; typical VS=0 curves do not bound every unpowered, negative-input and temperature case. [TI SBOSA29A, pp. 3–6](https://www.ti.com/lit/ds/symlink/ina281.pdf?ts=1781346687194). |

The original INPUT-A1 copy still contains INA180 and the old buck circuits. INA281 and LMR36520 are future candidates, not secretly integrated substitutions. Raw-rail sinks include the rectifier, both sense inputs, VIN/EN paths, divider/protection and externally powered connections. The total must be established for each supply state. Ignoring a helpful resistor path is conservative; ignoring an unknown sink current is not a protection proof.

## A useful candidate, with a specific limit

The screened alternative is **STTH2R02U** (silicon rectifier, SMB, 200 V / 2 A) and a proposed **3.3 kΩ bleeder** from VIN_RAW to GND. D12 terminal polarity would remain unchanged. ST specifies reverse leakage maxima of 3 µA at 25°C and 20 µA at 125°C at 200 V, and a loss equation giving 0.74 W at 1 A DC. These points do not establish a 175°C leakage limit or complete transient behavior. [ST DS4744 Rev. 3, pp. 2–3, 11](https://www.st.com/resource/en/datasheet/stth2r02.pdf).

**CRCW25123K30FKEG** is a concrete resistor candidate: 2512, 3.3 kΩ, ±1%, ±100 ppm/K, 1 W at 70°C. The study adds a declared 2% service-drift allowance and 1.3% temperature allowance, yielding 3158.1–3441.9 Ω. These are design assumptions, not an unlimited-life guarantee. At 44 V, worst arithmetic dissipation is 0.613 W. An 85°C local-ambient derating gives 0.824 W, conditional on permitted film temperature and actual PCB heat removal. [Vishay 20035, pp. 1–3, 6](https://www.vishay.com/docs/20035/dcrcwe3.pdf).

| Assumed total negative-rail sink | Calculated steady voltage at Rmax | Disposition |
|---|---:|---|
| 1000 µA, original Schottky's hot leakage point | −3.4419 V | The proposed resistor is inadequate for that budget |
| 20 µA, replacement diode alone | −0.068838 V | Below the proposed magnitude target; downstream currents omitted |
| 25 µA, hypothetical complete budget | −0.086048 V | Only 5 µA beyond the diode; that allowance is unverified |
| 80 µA, sensitivity example | −0.275352 V | Fails −0.1 V target; only 24.648 mV above buck absolute minimum |

The 80 µA case illustrates why the two sense inputs matter; it is **not** a guaranteed sum for the actual reversed/unpowered circuit. The total budget allowed by the −0.1 V target is about 29.05 µA. No row accepts polarized C1, fast undershoot, the full board, or procurement. A lower resistor consumes more power and cannot solve a strict zero-reverse capacitor requirement. A generic Schottky clamp also needs a guaranteed cold/current voltage bound; its name is not evidence of a ≤0.3 V clamp.

## ADC and startup remain a separate correction

The preserved 47 kΩ / 6.8 kΩ divider produces 3.185 V at 25.2 V and 5.561 V at 44 V, nominally. Illustrative ±1% corners raise these to 3.241 V and 5.659 V. U1.16 is PA2/ADC123_IN2, an FT pin; its digital tolerance does not establish ADC operation outside 0…VREF+ (VDDA for this package). With VDD=0, the FT absolute upper limit is 4 V, so the 44 V case fails even that separate limit. Do not invent an inevitable internal positive clamp/backpower path for FT pins. An external clamp must handle a dead VDDA rail explicitly. [ST DS10693 Rev. 11, pp. 47, 73–77, 140, 144](https://www.st.com/resource/en/datasheet/stm32f446re.pdf).

C36 and the divider give a nominal 0.594 ms time constant. The tool distinguishes nominal calculations, illustrative tolerance corners, the ADC conversion window and an FT absolute check. None of those is a startup/shutdown waveform measurement.

## Next smallest implementation packet

Select a **nonpolar input reservoir together with the first wider-voltage buck's local bypass**, including effective capacitance at 25.2/44 V, temperature, ripple, source-lead resonance/damping and inrush. Then close the rectifier/bleeder or alternative clamp design using the complete powered/unpowered sink budget. Do not substitute a nominal 47 µF MLCC and assume equivalent behavior. If a polarized reservoir is retained, its voltage must remain nonnegative under the defined faults.

The follow-on schematic must record D12/C1 identity changes, each new part and exact added/changed pin memberships before native export. Reserve reference R40 only if the bleeder is retained; it has not been added or allocated in CAD. Keep all other INPUT-A1 connections intact and retain the 6S requirement and optional on-board actuator variant. Check at least: discharged reversal; charged reversal; positive-then-negative pulses; logic absent/present; external USB/BEC backfeed; falling VDDA with C36 charged; minimum 7 V input with worst drops. A 4.2 V buck input minimum alone does not promise a regulated 5 V output.

Reproduce with `python -B reviews/codex/reverse_leakage/capture.py --check`, `model.py --check` and `test_model.py`; use `build_view.py --check` for the saved interactive artifact. [Analysis](analysis.json), [independent review](review_notes.json) and [hash manifest](packet_manifest.json) retain assumptions and restart evidence. The handheld voice/text/location and measured voice/RC coexistence requirement is unchanged. No powering, flashing, ordering or hardware acceptance occurred.
