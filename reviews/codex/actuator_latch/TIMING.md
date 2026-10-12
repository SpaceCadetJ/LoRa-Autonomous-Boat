# ACT-04 timing and power contract

This is a conditional latch/OE subcell on an isolated schematic. It does not implement the ACT-03 supervisor, receiver observation, watchdog, qualification interval or service-history requirements. QUAL_OK and ACK have no driver in this packet and remain pulled low. No hardware operating procedure is released.

The exact source facts, pin maps and test conditions are in [source_review.json](source_review.json). The chosen latch is **SN74LVC1G74DCUR**, not SN74LVC2G74; do not substitute the latter's timing table.

## Functional inference

U12 captures NOT ARM on a rising ACK edge. QUAL_OK low clears U12. U14 drives OE from QUAL_OK AND ARM AND READY. PRE_N stays tied to +3V3; it is never another reset source. R40 remains directly on translator OE.

With valid, settled inputs and an adequate reset:

| Event | Consequence |
| --- | --- |
| QUAL_OK low | READY clears; OE is inhibited independently through U14. |
| QUAL_OK recovers with ACK/ARM held | No fresh ACK edge; READY remains cleared. |
| New ACK rise with ARM low | READY becomes set after propagation. |
| Later ARM rise, QUAL_OK still high | OE can become high. |
| ARM returns low | OE becomes low; READY is retained. |
| ACK rises while ARM high | READY clears and OE becomes low. This deliberately differs from ACT-03. |

Normal disarm therefore allows a later arm request while the qualified epoch remains healthy. A fault destroys that permission. The proof assumes the fault actually reaches the latch with sufficient width.

## Required future interface

QUAL_OK must come from a reviewed circuit combining local supply supervision, actual receiver readiness, stop continuity and command freshness. A missing driver remains disabled. The source must retain each detected fault long enough to reset the latch, including propagation and distribution uncertainty. An arbitrarily short low pulse is insufficient: it can momentarily inhibit OE without clearing READY, so restoration could enable again.

ACK must be a deliberate, conditioned edge. ARM remains PC4's request, rather than an assertion that operation is safe. Neither a raw switch nor a slowly moving RC node is accepted as ACK. An eventual open-drain source must meet transition limits after its pull resistor and total node capacitance are included. This packet does not implement debounce, synchronization or edge conditioning.

Power-up must first establish valid local logic power while QUAL_OK is held low. Keep ACK and ARM low through reset release. Leave explicit guard time before the next ACK, then wait for READY to settle before ARM rises. This sequence is an integration requirement, not an implemented sequencer. Supply disappearance must make the qualification source inhibit before the logic leaves its validated range; that behavior is not yet designed.

## Pin-level timing constraints

[TI's latch specification](https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf) is recorded in the JSON. Its minima are component limits under stated conditions, not board acceptance margins. Use this order when constructing the later timing budget:

1. Clear reaches U12, remains asserted for the required width, and establishes READY low.
2. With ACK low, QUAL_OK rises cleanly. Allow the clear-release recovery interval plus distribution uncertainty before ACK rises.
3. ARM low propagates through U13 and makes U12 D stable before ACK. Preserve D through the hold interval.
4. After ACK, wait for the maximum U12 clock-to-Q delay plus interconnect/load uncertainty before a later ARM rise.
5. Account for U14, TXU0102, receiver load and actuator response separately when establishing a stop deadline.

The inverter's [specified propagation bound](https://www.ti.com/lit/ds/symlink/sn74lvc1g04.pdf) plus the latch setup minimum yields a **5.5 ns arithmetic screen** from ARM-low to ACK under the source test conditions. This excludes routing/skew and is not a chosen guard interval. Applying this number directly to an unmeasured board is not accepted. Hold time must be checked at U12 D; do not assume a nominal inverter delay supplies it.

No independent reset-removal number is invented. Keep clock edges away from reset deassertion and obtain a complete timing analysis for the chosen qualification source. A simultaneous fault/ACK/ARM event is not represented by the discrete priority of ACT-03: real gates have unequal delays and may produce a pulse. The [AND gate's propagation specification](https://www.ti.com/lit/ds/symlink/sn74lvc1g11.pdf) does not establish glitch rejection or an end-to-end stop time.

## Remaining power and fault checks

Power-off leakage limits apply only under their specified zero-supply conditions. They do not define behavior throughout a collapsing or rising rail. The pulldowns limit floating-node voltage; they are not substitutes for supervision. Include every receiver, driver, MCU and contamination leakage term before accepting their values.

Do not infer an initial READY value. A valid clear is required after power-up. Tie unused logic inputs to defined levels; leave the specified unused outputs/pins unconnected. Verify local bypass placement, output loading, ringing and all pin-voltage limits on the eventual layout.

Even a correctly disabled translator does not prove a motor has stopped, nor does its partial-power feature protect an unpowered external actuator from a powered signal. Remote input injection, receiver supply loss, accepted stop latency, stuck-high qualification, broken grounds and shorted gate/output faults remain open. One shared qualification line has no redundancy or self-test.

The next useful packet is a bounded qualification/reset-release interface with exact thresholds, fault retention, edge conditioning and timing margins. It must preserve default disable until those dependencies are genuinely implemented. Native ERC and Boolean tests remain evidence of their respective scopes only.
