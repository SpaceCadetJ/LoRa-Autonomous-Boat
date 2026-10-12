# Choosing the next 6S power circuit — 2026-10-12

**Advance the wider-voltage topology to the next isolated schematic study. Keep the active-cutoff alternative as a comparison.** This is an engineering recommendation, not a selected production BOM or a circuit release. The comparison retains 7–25.2 V / 2S–6S operation and the optional on-board actuator supply. The external-BEC application remains the initial load-planning default. No live CAD, BOM, purchasing status or firmware changes occur here.

Open the [interactive load budget](load_budget.html), [two power paths](v2_power_topologies.svg), [calculated cases](comparison.json) and [proposed connection contract](proposed_connections.json). These are proposed circuits and analytical results; they are not native schematics, simulations or measured hardware behavior. The current native IMU candidate is still [IMU2](../imu_bias_filter/README.md).

## Resolve the power claim first

The requirements simultaneously contain a ≤1 A board-feed default and proposed 3.3 V/1.2 A plus 5 V/2 A converter capacities. Those rail capacities cannot be promised simultaneously throughout the input range. At 7 V, even lossless conversion needs **1.994 A** for the two stated outputs, with no auxiliary load.

The following examples assume 85% efficiency for each converter and an additional 20 mA on 5 V for control circuitry. Both are adjustable planning assumptions, not measured specifications. They exclude front-end losses, quiescent input current, inrush and faults. The external BEC's servo energy is outside this board-feed model; the ESC motor is always fed directly from the battery.

| Case | Logic / on-board servo demand | Input at 7 V | Input at 25.2 V | Consequence |
|---|---|---:|---:|---|
| External BEC, logic ceiling | 1.2 A / 0 A | 0.682 A | 0.190 A | Leaves arithmetic room under 1 A; hardware and transients still unqualified. |
| Illustrative mixed operation | 0.35 A / 0.5 A | 0.631 A | 0.175 A | Example only; actual radio/GNSS/servo loads need measurement. |
| Simultaneous advertised capacities | 1.2 A / 2 A | **2.363 A** | 0.656 A | Violates 1 A at low input; 2 A servo plus 20 mA auxiliary also exceeds a 2 A converter. |

At the logic ceiling and 7 V, this model allows at most **0.378 A of on-board servo current** under the 1 A feed goal, before omitted losses. At full demand, predicted conversion losses are 0.699 W on 3.3 V and 1.782 W on 5 V. These numbers motivate a thermal design; they are not temperature predictions. Do not convert the existing 3 A fuse marking into a continuous-current permission.

## A — wider-voltage input and parallel converters

Proposed path: fuse → bidirectional input TVS and reverse-blocking controller/NMOS → VIN_RAW → shunt → VIN_BUCK → independent 3.3 V and 5 V converters. Both sense taps are on the reverse-protected side. The battery-divider tap also moves into this reviewed boundary. The bidirectional input TVS is intentional: a unidirectional diode placed before reverse protection would conduct on a reversed pack. The present D1 symbol/MPN ambiguity must be resolved in the candidate.

| Function | Candidate and verified limits | Design consequence |
|---|---|---|
| Two converters | LMR36520ADDAR: VIN 4.2–65 V recommended / 70 V absolute; 2 A output class. HSOIC-8 DDA, 4.9 × 6 mm including leads. [TI SNVSBF0C, pp. 3–7](https://www.ti.com/lit/ds/symlink/lmr36520.pdf). | Replace U2/U3 converter cells and select new magnetics/feedback/bypass parts. A 2 A device does not cover 2 A servo plus auxiliary load. Do not reuse old pin numbers or 4.7 µH assumptions. |
| Current sensing | INA281A1IDBVR: gain 20, common mode −4…110 V operating / −20…120 V absolute, supply 2.7–20 V; A variant retains the current five-pin functional order. [TI SBOSA29A, pp. 3–5](https://www.ti.com/lit/ds/symlink/ina281.pdf?ts=1781346687194). | Preserve the 20 mΩ nominal scaling, add supply bypass and a reviewed output RC. Offset/gain/temperature error, unpowered behavior and ADC calibration remain open. B variant is not pin-equivalent. |
| Reverse control | LM74700QDBVRQ1: use the table's ±60 V recommended ANODE range and 70 V recommended CATHODE−ANODE limit; absolute limits are ±65 V and 75 V respectively. [TI SNOSD17G, pp. 3, 5, 17](https://www.ti.com/lit/ds/symlink/lm74700-q1.pdf). | Replaces the P-FET/gate-zener approach; external N-FET, charge-pump and local input capacitors require selection. It is an ideal-diode controller, not positive overvoltage cutoff or inrush limiting. |

A positive clamp number alone is insufficient: with a charged 25.2 V output and a −53.3 V input pulse, controller differential stress would be **78.5 V**, beyond its 75 V absolute limit. This is a calculated exclusion case, not an expected measured waveform. Bound positive, negative and charged-output cases together, or change the controller/protection topology. Likewise, 50 V input capacitors cannot be retained behind an unqualified 53.3 V clamp point. The [previous envelope](../power_envelope/README.md) remains applicable.

CSD19538Q3A was screened as a 100 V / ±20 V, 3.3 × 3.3 mm N-FET; its 61 mΩ maximum at 10 V and 3.2 V typical threshold do not establish a suitable match to the controller's low-threshold guidance or thermal budget. **It is not selected.** Keep MOSFET voltage/SOA, gate-drive, conduction and startup requirements open. [TI product specifications](https://www.ti.com/product/CSD19538Q3A).

## B — active cutoff retaining the existing bucks

The alternate controller is **LTC4365ITS8#TRMPBF**, 2.5–34 V operating, −40…60 V protection range, with two common-source back-to-back N-FETs ahead of the entire shunt/divider/converter island. TS8 pin order is VIN/UV/OV/GND/SHDN/FAULT/VOUT/GATE; the DFN differs. The 2.90 × 2.80 mm lead-span envelope excludes both FETs and passives. [ADI LTC4365 Rev. B, pp. 2–4, 18](https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4365.pdf).

For separate UV/OV dividers, an illustrative 539 kΩ/10 kΩ OV pair, each ±0.1%, and ±10 nA leakage give trip **26.9798–27.9219 V** and minimum recovery **25.2265 V**. Only **78.1 mV** remains below the TPS54202 28 V operating ceiling; one-percent resistors fail the joint restart/trip requirement. Resistor temperature drift, board leakage, ripple and dynamics are excluded; comparator threshold and hysteresis limits cover their specified temperature range. Its 2 µs comparator limit uses 50 mV overdrive; the 4 µs gate turn-off specification uses 2.2 nF. Neither proves near-threshold surge protection. [ADI Rev. B, pp. 3–4](https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4365.pdf#page=3).

The calculation assumes automatic restart at a fully charged 25.2 V pack. Accepting restart only at a lower input permits a lower cutoff threshold; cutoff is therefore **not universally infeasible**. INA180 still needs replacement or independently demonstrated protection. Existing enable, inductor, buffer supply and ADC-loading blockers remain even when a cutoff is added. Both FETs and protection energy are unselected.

## Proposed connection changes and package budget

The [machine-readable contract](proposed_connections.json) assigns functional node names and candidate package-specific pins. It allocates no new board reference numbers and is not an exhaustive native netlist. Shared intended changes include:

- Move U4.5/U5.5/C13.1/C14.1 from VSERVO to regulated +5V_BUCK before D4. A control 5 V supply remains necessary with external BEC; actuator sourcing is a separate population decision.
- Insert a 1 kΩ study resistor between U8.1 and existing ISENSE (U1.20/C37.1); add U8 supply bypass. Keep R33 at 20 mΩ pending pulse/thermal qualification.
- Replace the battery-divider ratios/protection for its selected raw/protected envelope and minimum VDDA. Preserve U1.16 as ADC input; do not expose it to a high-voltage surge merely because the converters tolerate it.
- Correct the recorded C1/F1 package conflicts and D1/D2 identities in the new candidate. B removes the old Q1/R1/D2 cell; A also removes it. Preserve MCU signal allocations, the repaired ground escape and all V1 evidence.

The two wider-voltage converter packages occupy **58.8 mm²** of nominal lead-span rectangle, versus about **24.0 mm²** for the current two courtyard boxes. These are different geometric measures, not a clearance comparison. TI's DDA0008B example has signal-land row centres 5.4 mm apart, 1.55 × 0.60 mm pads at 1.27 mm pitch and a 2.71 × 3.4 mm thermal land; its 6.95 × 4.41 mm signal-land bounding box is **30.65 mm² per IC**. Extra mask-defined copper, local bypass, magnetics, feedback and thermal spreading are still required. [TI package drawing 4214849/B, pp. 38–40](https://www.ti.com/lit/ds/symlink/lmr36520.pdf#page=38).

Controller B's 8.12 mm² lead-span rectangle likewise excludes two MOSFETs and dividers. Neither architecture has a qualified whole-cell area or proven fit in 80 × 46 mm. Reuse the recorded [placement conflicts](../power_envelope/v2_power_envelope.svg); don't treat the previous 10 mm planning boxes as footprints or free space. Native footprint, stencil and thermal review must precede placement acceptance.

## Next smallest implementation packet

Start an isolated **A-input-stage schematic candidate** on the corrected live revision, with exact fuse/TVS/controller/FET/capacitor identities and positive/negative/charged-output limits. Resolve the LM74700 differential exclusion before adopting it; a different controller is allowed. Preserve 7–25.2 V and the separate on-board-actuator option. Use the external-BEC variant to bound the first logic-feed design while the optional high-load variant remains held. Produce the complete pin-delta contract and native netlist/ERC, then an actual package/thermal layout budget. Final IMU2 routing waits for this power region.

No user choice is inferred about reducing 6S or abandoning on-board actuator power. Actual pack/charger, BEC, servo stall current, radio/GNSS consumption, harness/source impedance and enclosure temperatures remain qualification inputs. Voice/text/location handheld hardware remains separate; measure voice/RC coexistence before its selection.

## Reproduce and limitations

`python reviews/codex/power_topology/model.py --check` reproduces the cases; `python reviews/codex/power_topology/test_model.py` checks conservation, impossible feed combinations, tolerance and invalid inputs. The HTML exposes the same budget formula and is checked against recorded cases in desktop and phone browsers. It uses no external service or stored user data. Input values are assumptions; a green arithmetic result is never board acceptance.

The packet manifest hashes model, diagrams, connection contract, comparison and validation records. All 52 current CAD hashes and prior review artifacts remain unchanged; expected live electrical/copper delta is **zero**. No new native checks were run on unchanged CAD. No hardware, orders, branch/history rewrites or unrelated-tool changes occurred. Hosted CI remains unverified until its actual run is inspected.

Browser reproduction uses `node reviews/codex/power_topology/verify_viewer.cjs` with Playwright installed; set `PLAYWRIGHT_MODULE` and `BROWSER_EXECUTABLE` only when using a non-default local installation. Run `node pm/tools/build.mjs` first. The check compares all seven cases, rejects invalid inputs and opens the V2 map at 1440 × 1000 and 390 × 844. [Recorded browser results](viewer_check.json), [review notes](review_notes.json) and [packet manifest](packet_manifest.json) preserve the checkpoint. The renderer is optional and requires CairoSVG; arithmetic and publication checks use Python's standard library.
