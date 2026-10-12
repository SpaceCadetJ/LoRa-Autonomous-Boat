# ACT-02 — default-disabled actuator signals

**An isolated schematic now replaces both always-enabled PWM buffers with a dual-supply translator and a hardware OE pulldown.** Open the [annotated actuator schematic](v2_actuator_enable.svg), [KiCad project](source/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pro), [expected electrical contract](expected_contract.json), or [native validation](validation.json). The viewer lists this as **Design → V2 → ACT-02**.

This extends ACT-01 on a new copy. Live CAD/copper, V1 behavior, source BOM, ordering exports and firmware are preserved. This candidate is not an assembly or powered-use release; current purchasing files do not incorporate its new U4/R40. Both converter sheets, the Power sheet and the exclusive source-population contract remain byte-identical. IMU2 remains separate.

## Electrical change

| Reference / connection | ACT-02 candidate |
|---|---|
| U4 | TXU0102DCUR, dual fixed-direction translator; local TI DCU footprint |
| U5 | Removed; its steering channel is now U4's second channel |
| U4.3 / C13.1 | +3V3, with C13 retained as local 100 nF bypass |
| U4.7 / C14.1 | Board +5V_BUCK before D4, with C14 retained as local 100 nF bypass |
| U4.5 → U4.8 | ESC PWM PC6 input → retained ESC series-resistor network |
| U4.4 → U4.1 | Servo PWM PA8 input → retained servo series-resistor network |
| U4.6 / R40.1 / U1.24 | New ACT_EN_PC4; active high, hardware 10 kΩ pulldown R40 to ground |
| U4.2 / R40.2 | Ground |

PC4 was a singleton no-connect on the captured ACT-01 MCU. Only that no-connect is removed. U1's identity and every other MCU pin remain intact. R40 reuses the existing 10 kΩ/0603 resistor identity `RC0603FR-0710KL`; its assembly release is held with the candidate. No signal connector, series resistor, protection diode or output pulldown is electrically changed.

The explicit boundary retains **119 components / 398 physical pins**, preserving **383 outside-boundary pins**, including their native metadata. The new translator uses a new footprint, so this is not a drop-in board substitution. See [package record](package_review.json), [native geometry](native_geometry.json) and [native commands/hashes](native_manifest.json). Forty-one independent contract/mutation tests pass. Native ERC has zero errors and the original AD0 warning; native and independent contract checks establish the captured schematic only.

## What the replacement establishes

TI specifies TXU0102 for separate 1.1–5.5 V rails, Schmitt inputs and active-high OE. Its partial-power Ioff limit is ±2.5 µA through 125°C when either supply is zero, the other is 0–5.5 V and the signal port is 0–5.5 V. The separate floating-supply test holds the port at ground and requires a disconnected supply with no more than 10 nA leakage; it cannot be applied to an externally driven port on an arbitrary collapsing rail. Supply isolation below 100 mV does not establish behavior throughout brownout. [TI datasheet SCES941A, §§7.5 and 9–11](https://www.ti.com/lit/ds/symlink/txu0102.pdf).

The footprint uses the manufacturer's example 0.85 × 0.30 mm lands at ±1.55 mm, 0.50 mm pitch; pad 1 is B2Y. It differs from the installed KiCad library's alternate land pattern. Board fit, stencil, soldering and placement still require review. [TI DCU0008A drawing](https://www.ti.com/lit/pdf/MPDS050E). [Exact active ordering identity](https://www.ti.com/product/TXU0102/part-details/TXU0102DCUR).

Using a conservative 2 µA OE leakage screen and a 10 kΩ ±1% pulldown gives 20.2 mV. This calculation excludes MCU, contamination and external leakage; the complete default-state bound is `V_OE = total sourcing leakage × 10.1 kΩ`. It is a static screen, not a measured reset or ramp result. C13/C14 effective capacitance and placement remain held.

## Power and signal sequencing contract

| Condition | Candidate behavior / remaining requirement |
|---|---|
| Both board rails valid; OE low | Translator outputs are high impedance. Existing output pulldowns discharge nodes; external sources and capacitance can keep them nonzero. |
| Both board rails valid; OE high | Outputs follow PWM inputs. Actual actuator thresholds and harness loading must be qualified. |
| Ordinary MCU peripheral reset / PC4 input HiZ | R40 requests disable. Verify total leakage and reset waveform before accepting this provision. |
| One translator supply at zero; complementary rail valid | Apply the specified Ioff conditions. This protects the translator from bounded external signal drive. |
| Supply between 0.1 V and the minimum operating range | Unqualified interval; do not treat the device's isolation feature as a board brownout supervisor. |
| Board powered; actuator unpowered | Enable prohibited until receiver injection is bounded or interrupted. Ioff does not solve this reverse direction. |
| Firmware stalled with PC4 high | No independent command-loss or watchdog disable is implemented by this circuit. |
| Hot-plug / missing ground / negative signal excursion | Unqualified; retained TVS and resistors do not establish transient acceptance. |

No finite delay alone proves that an actuator is powered. The current J2 signal/BEC/GND connection and J3 signal/VSERVO/GND connection provide no independent receiver-ready indication. In ONBOARD, a valid VSERVO says nothing about the ESC's internal control supply. Do not substitute BEC voltage for an unverified ESC readiness contract.

Keep ACT-01's physical variants: **BEC_ONLY: D4 absent, D9 fitted; ONBOARD: D4 fitted, D9 absent**. The master has both DNP. Both variants still require the board's own battery and converters for logic; neither diode selection enables the signals. The 6S requirement belongs to the protected board battery input, never J2.2/J3.2. [Preserved population contract](population_contract.json).

## Proposed firmware integration — not implemented

PC4 is U1 pad 24 on this STM32F446RET6 package. Its normal reset input state supports the pulldown design; debug/core-only resets or inherited firmware state must be handled separately. [ST datasheet](https://www.st.com/resource/en/datasheet/DM00141306.pdf) and [RM0390 GPIO registers](https://www.st.com/resource/en/reference_manual/dm00135183-stm32f446xx-advanced-arm-based-32-bit-mcus-stmicroelectronics.pdf).

1. Enable GPIOC's peripheral clock. Write BSRR bit 20 to latch PC4 low **before** making PC4 a push-pull output.
2. Configure PC4 as low-speed output, no internal pull. Initialize known-valid PWM while ACT_EN stays low.
3. Require qualified board rails, receiver power, application arm state and fresh valid commands before writing BSRR bit 4 to enable.
4. Deassert ACT_EN first on disarm, stale command, fault or commanded shutdown; then stop PWM. Hardware must cover faults that prevent this code from executing.
5. Qualify startup, reset, watchdog, debugger handoff, supply collapse and external receiver backdrive with propulsion disconnected and recorded waveforms before any actuator-use release.

Stage A's existing seven-pin diagnostic contract is unchanged and does **not** drive PC4. It will leave this candidate unarmed under an ordinary reset, but it is not an actuator test or proof of reset safety. Existing V1 and V2 programming guides retain their own build/hardware gates; this packet provides no new flashable image.

## Resume / next smallest task

**Next: define and prototype the hardware arm interlock and receiver-power observation on a new isolated copy.** Record exact observable rails, supervisor thresholds/hysteresis, disable truth table and startup/fault timing. Preserve ACT-02, both converter sheets and the ACT-01 population contract. First resolve how ESC readiness can be known in each population; a local VSERVO monitor alone is insufficient. Actual ESC/BEC/servo identities and powered-off input limits remain required for eventual acceptance. Do not invent them or claim a full failsafe from this packet.

C11 identity, VSERVO reservoir/regenerative energy and transient clamps, full simultaneous-load 6S feed, negative-rail leakage/damping, ADC/sense and explicit combined IMU2 integration remain open. Preserve corrected copper for subsequent controlled PCB integration. Handheld voice/text/location remains separate and requires measured voice/RC coexistence before hardware selection.

Reproduce portable checks with `python -B reviews/codex/actuator_enable/verify_candidate.py --check`, `test_candidate.py`, `inspect_packages.py --check`, `python -B tools/quality/check_publication.py` and `node pm/tools/validate.mjs`. Native export is isolated and captured; never run primary generation/routing just to refresh documentation. [Packet hashes](packet_manifest.json) and the [design handoff](../design_completion/HANDOFF.md) are the restart record.
