# ACT-09: retained permission and power-loss handover

**Separate fault detection, fault retention and physical output disable.** A held observer can finish a bounded operation; it cannot keep an indefinitely stalled main rail safe by itself. This packet specifies a proposed observer island and a request-level sequencing contract. ACT-04 remains the latest native candidate; all missing qualification and ACK sources remain disabled.

Open the [annotated architecture](v2_observer_retention.svg), [sequence explorer](index.html), [calculated limits](RESULTS.md), [contract](contract.json) and [source ledger](sources.json). Candidate/live electrical and copper delta is zero. No reference, gate or power net is rewired; no exact new part, assembly or application is released.

## Concrete power and signal proposal

| Domain / path | Proposed responsibility | Required before native insertion |
|---|---|---|
| Main +3V3, sensed upstream | Supply under test; preserve ACT-07 UV/OV observations | Actual fault amplitude, pulse width, slew and sense/common-mode applicability |
| Reverse-blocked observer island | Supply reference, comparator, fault memory and edge conditioner | Exact blocking/charge/OV paths, effective capacitance, ESR, total load, reverse leakage and independent guard |
| Reference enable | Start from independent island-power authority while output permission remains disabled | No dependency on reference-valid or QUAL_OK; defined shutdown and off-state input paths |
| Fast inhibit + fault memory | Capture detected loss, force a low request and retain it while raw comparator outputs change | Maximum capture/distribution delay, minimum pulse width and valid retention supply |
| Physical permission boundary | Prevent unqualified U14 output from enabling TXU0102 during brownout | Exact series/enable isolation behavior, current, leakage and off-state authority; retain R40 |
| Existing ACT-04 latch | Clear READY; later capture NOT ARM only on a fresh valid ACK edge | Qualified edges, clear width, recovery/setup/hold and output loading |
| Remote receiver and other qualifications | Actual receiver-ready, local 5V, watchdog and stop continuity | Independent implemented sources; local VSERVO alone is insufficient |

A capacitor placed directly across main +3V3 cannot provide isolated hold-up during a short on that rail. Reverse blocking prevents one discharge path; it does not protect the island from input overvoltage or every injected signal. Keep main rail, observer island and receiver supply separate in analysis.

The held island does **not** silently move U12/U13/U14 or translator VCCA onto a new supply. An observer-only change cannot validate U14 while its original +3V3 disappears. Do not connect a new active low clamp directly against U14's push-pull output; contention and invalid supply behavior would remain unresolved. The next native delta must explicitly replace or isolate that permission path, after an exact circuit satisfies the boundary.

## Startup, loss and recovery

1. Start with output isolation requested and QUAL/READY low. An independent power guard may request reference enable even while reference-valid is false. Requiring reference-valid to turn on the reference creates a startup dependency loop.
2. Establish actual reference validity, main-rail validity, local 5V, receiver readiness, fresh-command watchdog and stop continuity. Unknown or missing inputs count as unavailable. The allocated 1 ms healthy interval begins **after** these predicates are true; it does not replace a bounded reference startup specification.
3. Complete the allocated 1 us clear hold and the healthy interval with ACK and ARM low. Release QUAL as a distinct event, then wait the allocated recovery guard. A later conditioned ACK with ARM low can request READY; a still later ARM edge can request output enable.
4. Any observed loss requests immediate inhibit and clears requested READY. Retain the fault despite reference shutdown or changes in raw comparator outputs. Observer guard loss also requests reference disable. The request model has no propagation, analog pulse capture or physical OE guarantee.
5. Finish physical isolation while the island is still valid. When finite stored energy expires, a separately characterized disabled condition must already exist. An arbitrary long brownout or stall cannot be covered by a finite capacitor alone.
6. On recovery or bounce, establish a fresh healthy interval. Held ACK is not a new acknowledgement. ACK while ARM is high clears READY, matching ACT-04. Close ACK/ARM/reset edges are rejected by the model's timing contract; discrete event priority is not a race proof.

The 100 ns release and ARM guards, 1 us clear hold and 1 ms healthy interval are design allocations. They do not establish component, board or receiver timing. The recorded ACT-04 2.7 ns clear-width and 7.9 ns clear-to-Q conditions remain source facts under their stated supply/load conditions.

## Quantified architecture boundary

ACT-08's same-rail reference supply needs 3.005 V to preserve its sourcing-test headroom. ACT-07's 3.071938 V allocated UV overdrive point therefore leaves 66.938 mV to loss of observation applicability. With the existing 400 ns conditional response budget, the zero-margin ceiling becomes 0.167345 V/us. Strictly positive margin is necessary, and comparator ramp applicability is still unverified.

The proposed held island uses a separate charge budget. The illustrative 100 us handover-finish allocation is **not** a selected switch delay or measured deadline. A physical boundary must suppress invalid U14 drive **before main logic leaves its applicable range**, then maintain disable continuously. The 100 us interval does not permit undefined OE, and observer hold-up does not relax the fast end-to-end inhibit deadline. Effective capacitance, 100 mV blocking loss, ESR, total current and reverse leakage are assumptions to be closed. The 3.005 V island floor is inherited from the reference sourcing condition; it assumes every guard, retention element, conditioner and interface also remains valid down to that voltage. The final floor must be the maximum applicable requirement across the island, and any higher floor reduces the shown margin. No positive capacitor result establishes a physical disabled output, short-circuit survival, OV protection, recharge behavior or continued validity after hold-up expires. See [RESULTS.md](RESULTS.md) for exact values and formulas.

## Manufacturer sequencing support and board-level limits

[TXU0102 SCES941A](https://www.ti.com/lit/ds/symlink/txu0102.pdf), sections 9.3.6 and 11, explicitly supports glitch-free supply sequencing. Its separate isolation condition applies with one supply below 100 mV or disconnected and the complementary supply within its operating conditions. This does not validate an invalid OE waveform driven by upstream U14, or establish remote actuator readiness. Preserve that distinction.

[TLV3202 SBOS561C](https://www.ti.com/lit/ds/symlink/tlv3202.pdf), section 8.1.1, requires attention to differential input voltage relative to supply. A series-current ceiling alone does not close the reference-to-input path during collapse. ACT-08's reference startup, reverse/leakage and injection limits remain open; the island proposal moves the power boundary and requires fresh supply/common-mode validation.

## Next smallest implementation task

Close the **physical permission boundary between U14 and TXU0102 OE**. Compare a single explicit series/enable-isolation circuit against partial-power input/output behavior, maximum disable time, current contention and powered-off leakage. It must preserve R40 and remain disabled after the observer island exhausts its energy. Then resolve exact island blocking/charge/OV and reference shutdown paths. Predeclare the part/pin delta and capture native checks only once those conditions fit on a fresh ACT-04 copy. Do not repeat the passive RC study or promote the sequence simulator into hardware evidence.

Preserve both converter sheets, ACT-01 exclusive populations, corrected copper, V1/Allegro evidence and all earlier candidates. C11/VSERVO transients, full 6S feed, leakage/damping, ADC and combined IMU2 remain open. V1 inspection, V2 vehicle applications and the future voice/text/location handheld remain distinct; measured voice/RC coexistence precedes handheld hardware selection.

## Reproduction

Run `python -B reviews/codex/observer_retention/test_model.py`, `python -B reviews/codex/observer_retention/model.py --check` and `python -B reviews/codex/observer_retention/build_packet.py --check`, then the repository publication and viewer validators. The explorer reports only its modeled guard checks; ACK high/low pulse width and debounce remain unmodeled and unqualified. The request explorer advances only at listed events/ticks. A missing tick does not simulate continuous hardware. Manifests bind prior inputs and new artifacts. No native commands or real hardware actions are part of this packet.
