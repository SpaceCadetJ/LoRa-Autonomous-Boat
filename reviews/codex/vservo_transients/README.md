# VSERVO-02 - energy sink and reverse-voltage boundary

**The next circuit study is a local dissipative shunt across VSERVO and GND.** This is an architecture proposal, with no selected device or native insertion. Both present source populations lack a qualified return path. The [latest native candidate](../vservo_reservoir/README.md) remains VSERVO-01; its C11 correction, both converters and default-disabled permissions are preserved.

[Annotated boundary](v2_vservo_transients.svg) | [Protection explorer](index.html) | [Calculated examples](RESULTS.md) | [Source ledger](sources.json) | [Expected delta](contract.json)

## What the existing circuit actually permits

Captured XML puts C11.1, C12.1, D4 cathode, D9 cathode, J3.2 and TP4.1 on VSERVO. D4 anode receives the 5 V buck output; D9 anode receives BEC_IN at J2.2. BEC_ONLY fits D9 and omits D4; ONBOARD fits D4 and omits D9. The review master has both marked DNP. These remain proposed exclusive assembly variants.

U3 is LM76003RNPR, with SYNC/MODE pin 17 grounded. Its automatic light-load mode prevents negative inductor current; FPWM is a different configuration. Together with D4's direction, this means the existing buck cannot be credited as a regenerative sink. A synchronous converter and a battery connection do not establish a complete return path. No mode change is proposed. [TI datasheet, pin 17 and sections 7.4.5-7.4.8](https://www.ti.com/lit/ds/symlink/lm76003.pdf).

Energy returned at the **J3 servo supply boundary** is the subject of this packet. The actual servo behavior is unknown. Energy from the propulsion motor or ESC main battery cannot automatically be assigned to VSERVO through its BEC output. Motor regeneration is a possible mechanism, not a measured fact about these unidentified loads. [TI motor-system report, sections 7.1-7.1.3](https://www.ti.com/lit/an/slvaf66/slvaf66.pdf).

| Approach | What it would add | Current disposition |
|---|---|---|
| Local dissipative shunt | A qualified feedback/sink cell between VSERVO and GND | Carry forward for specification; threshold, current, thermal and failure behavior unknown |
| Return to source | A controlled bidirectional path and a source that can accept it in every required state | Held: BEC, buck, input protection and battery/BMS acceptance not established |
| Existing diodes and capacitors | Forward source feed and finite storage | Preserved; neither diode leakage nor capacitance supplies an indefinite controlled sink |

Bridging or reversing a source diode would change the isolation contract. A future return architecture must address absent/unpowered sources, battery state and the complete input path. Preserve the stated 6S requirement; do not connect a battery to either actuator supply pin.

## A voltage window before a part number

Define the maximum normal rail including tolerances, ripple and required operating margin. Define the lowest applicable upper voltage limit among the receiver and every exposed component, at the relevant temperature and waveform. C11's 16 V rating is one component limit; it cannot replace the missing receiver limit.

Require both inequalities with positive design margin:

- `maximum normal voltage < minimum turn-on threshold`
- `maximum turn-on threshold + all remaining voltage rise < allowed local maximum`

The second term must cover loaded clamp regulation/I-V behavior, response delay, ESR/ESL and local path effects. A breakdown or turn-on number is not the full-current clamping voltage. The explorer's combined-rise allocation is illustrative, not derived from a selected component or from delay alone. Continuous sink authority must also satisfy `I_sink,min > I_J3_into_bus,max + I_source,max - I_other_load,min - I_upstream_return,min` with deliberate margin under the chosen boundary. No actual bound is available yet.

For a constant net capacitor charging current during delay, `delta_V = I * delay / C`. This omits resistive and inductive peaks. Effective C, maximum delay and the returned-current waveform must be qualified separately. The 80 uF example retains VSERVO-01's limited initial measurement condition; C12 has no effective-capacitance credit.

## Account for energy once

Choose the local rail and its capacitor terminals as a control volume, with positive energy entering from J3 and the source:

`delta_E_C = E_J3 + E_source - E_other_load - E_local_sink - E_upstream_return`

Check the **maximum cumulative excursion over time**, not just the final event balance. Later load consumption can hide an earlier voltage peak. Keep the observation window and direction of each port explicit. Do not add motor/harness energy already included in measured port energy, subtract sink losses twice, or add charge and energy descriptions of the same event. Separate `L * I^2 / 2` belongs only when the declared boundary excludes that stored energy. An `L * di/dt` peak check adds a voltage constraint, not another energy source.

The example sink calculation uses a positive residual energy burst after other paths, with no later offset credited inside that burst. `C * (V_ceiling^2 - V_start^2) / 2` is finite storage. The resulting minimum sink energy is an **endpoint lower bound**, not a guarantee against an earlier peak. If the local sink alone restores the same starting rail before every identical event, it must eventually remove the entire residual burst energy, not only the amount exceeding storage. Mean power is then `E_burst * event_rate`; peak power, safe operating area, thermal recovery and fault duration remain separate. [MPS AN132, design procedure and Appendix 2](https://media.monolithicpower.com/document/AN132_r1.1.pdf).

## Positive clamping does not close the lower boundary

Record voltage directly across C11 and at the remote receiver relative to its own return. Polarized C11 must not receive applied reverse voltage under the retained [Panasonic guidance](https://industrial.panasonic.com/cdbs/www-data/pdf/RDE0000/DME0000COL75.pdf). Zero volts is a boundary, not positive design margin. Receiver lower limits, ground loss and contact sequencing remain unknown.

The board and remote actuator are different nodes connected through harness resistance, inductance and contacts. A board shunt alone does not bound a remote overshoot, negative ringing or ground offset. Cable energy and low-ESR capacitance can create insertion transients; no fixed multiplier from another application is assumed here. [ADI AN88](https://www.analog.com/media/en/technical-documentation/application-notes/an88f.pdf).

## Next cell and application impact

Specify one independent local shunt cell before selecting its parts. Its review contract must cover:

1. Source/receiver envelope, full-current clamp window and recovery hysteresis.
2. Control-power availability, startup and loss-of-power behavior while energy can still arrive. Disarming PWM does not prove that returned energy has ceased.
3. Maximum delay, sink-current authority, hot-start pulse SOA, repetitive dissipation and continuous-fault handling.
4. Failed-open and failed-short effects, upstream current limiting and isolation for each source population.
5. Local and remote positive/negative terminal limits, followed by a separate reverse-voltage solution if needed.

Missing actuator qualifications remain disabled. A proposed protection circuit must operate when required, or energy exposure must be prevented until it is ready; firmware state alone cannot establish that guarantee. Keep unknown receiver/BEC/harness values unavailable rather than filling them with examples. Existing requests for exact hardware identities remain unanswered and should not be repeated on every restart.

**Expected electrical and copper delta: zero.** No native commands were rerun, no part was selected, and no live BOM, ordering, assembly, flashing or powered-application release changed. Full 6S feed, leakage/damping, ADC, combined IMU2 and native C12 annotation polish remain open. V1 inspection, V2 vehicle applications and the future voice/text/location handheld remain distinct; measured voice/RC coexistence precedes handheld hardware selection.

[Input hashes](input_manifest.json), [review notes](review_notes.json), [browser checks](viewer_check.json) and [packet manifest](packet_manifest.json) support restart.

```text
python -B reviews/codex/vservo_transients/test_model.py
python -B reviews/codex/vservo_transients/build_packet.py --check
python -B tools/quality/check_publication.py
node pm/tools/validate.mjs
```
