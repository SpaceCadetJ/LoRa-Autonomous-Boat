# ACT-12 - future unloaded fault measurement plan

**Preparation only; no board was powered, flashed or connected during ACT-12.** Hardware acceptance gates must close before execution. An instrument-only result cannot release an ESC, servo, powered vehicle or handheld. Link future records to the [unit acceptance form](../../../docs/applications/ACCEPTANCE_RECORD.md) and [receiver worksheet](../actuator_interlock/RECEIVER_ACCEPTANCE.md).

## 1. Freeze the evidence and limits

Record board/netlist/BOM/firmware hashes, source population, schematic pin numbers and verified harness orientation. Identify every receiver and its firmware. Link each applicable limit to a document revision/page or a separately reviewed characterization record. Declare temperature, supply, source impedance, load, signal capacitance, leakage, ground offset and permitted fault envelope. Leave unknown limits **unavailable**, not zero. Do not run an acceptance test without its numerical or behavioral limit.

Use an unloaded board and qualified passive/electronic receiver emulation for board-level measurements. Do not attach propulsion or steering loads in this phase. An emulated load proves behavior only within its declared electrical envelope; it cannot demonstrate a real receiver's interpretation or actuator stop. Future receiver/motion tests are a separate application gate.

## 2. Define synchronized observation points

Capture upstream +3V3 at the sense tap, actual sensing node, detector output, QUAL at U12 clear, U12 READY, conditioned ACK, ARM, U4 OE, U4 VCCA/VCCB, U4 outputs before R10/R12 and J2.1/J3.1 after those resistors. Observe receiver-side supply/ground only with a qualified harness/emulator. Record each probe's loading, reference, bandwidth, sample rate, calibration and channel skew. Include measurement uncertainty in the allocated margin; do not invent instrument bandwidth from the 400 ns number.

Do not bridge independent grounds through instrument clips. A broken-ground test needs an independently reviewed fixture and bounded injection paths; it is not performed by casually unplugging a live return.

## 3. Assign distinct time origins and endpoints

| Quantity | Origin | Endpoint / recorded quantity |
|---|---|---|
| Conditional rail response | Upstream rail crosses the allocated overdrive voltage | Defined physical inhibit endpoint; compare the full declared allocation and remaining rail headroom |
| Connector settling | Driver enters its verified inactive state | Signal satisfies actual receiver low threshold with ground offset, noise and uncertainty margins |
| Pulse interpretation | Original relevant rising edge, including time before the fault | All later threshold crossings, pulse width/amplitude/history and applicable rejection rule |
| Signal-loss response | Last command actually accepted by the receiver | Defined receiver response and deadline; not a packet's transmit timestamp |
| Actuator response | Application's declared fault/command origin | Required mechanical/current/torque/position criterion, only in later qualified testing |
| Fault retention/rearm | Fault assertion at physical clear input | READY cleared, health established, fresh ACK with ARM low, later ARM and first permitted output |

Do not collapse these clocks into one 400 ns measurement. If the physical inhibit definition changes, update the contract and reviewers before interpreting a trace.

## 4. Predeclare the case matrix

Cover both source populations and all permitted supply orders: local 3.3 V/5 V, external BEC, emulator supply and signal power. Include slow/fast UV and OV ramps, steps, short excursions, faults before/during/after a PWM high interval, MCU reset/stall, stuck request/ACK, missing readiness/watchdog/stop sources, simultaneous fault/ACK/ARM, power bounce, translator-only interruption, positive external feed and prolonged dwell beyond finite island hold-up.

Each row needs an exact injected waveform, expected outcome, permitted envelope, acceptance limit and capture method. Mark unsupported cases **not covered**, with the resulting application restriction. Do not label a hard short, stuck-high qualification or broken ground as handled merely because the software scenario requests disable. No arbitrary-ramp or single-fault-tolerance claim is made here.

## 5. Record results without promoting them across scopes

Save synchronized raw waveforms, instrument setup, fixture/harness diagram, environmental conditions, start state and all source/firmware hashes. Report numerical margins with uncertainty, verdict per case (PASS / FAIL / NOT RUN / NOT COVERED), reasons and reviewer. Finite test duration alone cannot establish indefinite partial-power hold; combine applicable steady-state component bounds with the measured transient evidence.

A valid clear must persist long enough to reset READY under the actual supply/load/timing conditions. On recovery, show the output stays inhibited until fresh qualification/ACK/ARM sequencing. Check faults at every relevant edge; a Boolean model's priority is not analog timing evidence. Repeated normal disarm/arm within a healthy epoch is a separate ACT-04 behavior, not a fault-recovery test.

Default disposition: **NOT RUN; receiver contract incomplete; hardware and application acceptance unavailable.** No row in the explorer records a physical result.
