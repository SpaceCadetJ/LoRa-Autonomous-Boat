# ACT-12 - actuator connector fault contract

**This packet defines the missing acceptance boundary before another isolation circuit is selected.** The existing 400 ns total / 245 ns downstream allocation is retained. No connector-low, receiver pulse-rejection or actuator-stop time is established. ACT-04 remains the latest native candidate; missing qualifications stay disabled.

[Interactive fault explorer](index.html) | [Annotated interface map](v2_connector_fault_contract.svg) | [Verified paths and timing](RESULTS.md) | [Future measurement procedure](MEASUREMENT_PLAN.md) | [Machine-readable contract](contract.json)

## What the native evidence proves

The validator reads the preserved [ACT-04 netlist](../actuator_latch/native/netlist.xml), verifies the exact memberships and component values, and rejects drift. This is a fresh comparison of captured evidence; native CAD commands were not rerun.

| Channel | Signal path in ACT-04 | Connector-side network |
|---|---|---|
| ESC | U1.37 / PC6 to U4.5; U4.8 to R10.1; R10 = 100 ohm; R10.2 to J2.1 | R11 = 10 kOhm to ground; D10 ESD device to ground |
| Servo | U1.41 / PA8 to U4.4; U4.1 to R12.1; R12 = 100 ohm; R12.2 to J3.1 | R13 = 10 kOhm to ground; D11 ESD device to ground |

J2.2 is **BEC_IN**, J3.2 is **VSERVO**, and both pin 3 connections are ground. U4's VCCB stays on **/Power/+5V_BUCK before D4**, separate from VSERVO. These are electrical pin numbers, not a verified physical harness orientation. BEC_ONLY fits D9 alone; ONBOARD fits D4 alone. The unselected master marks both DNP. The [existing receiver worksheet](../actuator_interlock/RECEIVER_ACCEPTANCE.md) remains the identity record.

**Expected and actual candidate/live electrical and copper delta: zero.** Both converters, source populations, corrected copper, earlier candidates, V1/Allegro, purchasing and firmware are preserved. No new part or net is inserted and no hardware operation is performed.

## Separate the five observable outcomes

| Outcome | Evidence required | Current status |
|---|---|---|
| Driver ceases actively driving | Applicable U4/isolation supply, input, load and timing conditions; no contention or invalid-power gap | Unqualified through the fault envelope |
| Connector reaches a valid low | Total feed and effective capacitance, R11/R13 tolerance, receiver low threshold and ground offset | Unavailable receiver/load bounds |
| Unintended waveform is rejected | Exact receiver amplitude, width, edge, protocol-history and recovery behavior | Unavailable |
| Receiver responds to missing commands | Documented/measured no-pulse, stuck-level and last-command policy | Unavailable |
| Actuator reaches the required state | Application-specific braking/neutral/position criterion, load and response deadline | Unavailable; no motion acceptance |

High impedance is a driver state. A nominal 10 kOhm pulldown does not establish the remaining outcomes. Interrupting a pulse can also create a valid but unintended shorter command: its width includes the high interval **before** the fault. Do not treat the 400 ns allocation as a rejected-pulse width or assume a universal PWM stop value.

## Three obligations, with separate clocks

**Fast inhibit:** the inherited calculation begins at a declared upstream overdrive point under conditional monotone-ramp assumptions, not at the last command or every possible fault onset. Its 100 ns sensing, 55 ns detector and 245 ns downstream allocations sum to 400 ns. The whole downstream path shares 245 ns; each device does not receive that allowance separately. The physical inhibit endpoint still needs an applicable implementation and must then be related to actual receiver acceptance. The source model does not bound steps, short pulses, arbitrary ramps or broken grounds.

ACT-09's same-rail UV boundary is 3.005 V; the retained OV ceiling is 3.6 V. The [recomputed timing table](RESULTS.md) preserves their different headrooms. Both require positive margin, not equality. Actual component delay, error, load and waveform applicability remain open. A slower end-to-end requirement would need an explicit evidence-backed architecture revision; this packet makes none.

**Continuous disabled hold:** after inhibition, the output interface must stay defined through every allowed supply order, partial-power dwell, bounce and external feed condition. Finite observer-island charge cannot prove indefinite hold. The older 100 us handover-finish allocation permits no undefined-output interval and cannot replace the fast path.

**Fresh rearm:** a fault must destroy READY. Supply recovery must hold the interface disabled until independent qualifications are valid, a fresh healthy interval completes, ACK occurs with ARM low, and a later ARM is accepted under a closed timing contract. Translator-only power cycling leaves the separately powered latch intact, as [ACT-11](../vcca_shutdown/README.md) documents. Normal ARM-low disarm retains READY by ACT-04 design; do not silently change that separate behavior. Missing, held or stale authority cannot rearm.

## Evidence needed for each receiver

`contract.json` has separate ESC and servo records. Their ten evidence fields are currently empty. `model.py` rejects missing, blank or unresolved records as incomplete. Filling a record establishes only documentation completeness; it cannot grant hardware acceptance. A release still requires applicable source limits, reviewed circuit/firmware, measured results and the selected application's acceptance process.

Record the exact device and firmware, supply/input limits, thresholds, feed/capacitance, pulse acceptance, signal-loss behavior, readiness observation, stop deadline and harness definition. Use [the procedure](MEASUREMENT_PLAN.md) to define trace origins and acceptance limits before any later authorized test. It specifies preparation and unloaded instrument captures; no test has been executed here.

## Restart and next task

The actuator interface is blocked on exact receiver evidence and an implemented physical inhibit/hold/rearm path. Do not repeat a third isolation-part screen against unknown pulse or leakage limits. Request the ESC/BEC/servo identities and complete the missing fields when evidence arrives.

The next independently actionable circuit packet is **C11 identity and the VSERVO reservoir/transient contract**, starting with the current ACT-04 candidate and existing ACT-01 identity hold. Preserve both converters, mutually exclusive source populations and all actuator permissions; record any proposed delta before a new isolated copy. Do not select an effective capacitance or transient rating without the load/regeneration envelope. Native insertion remains conditional on a closed amendment contract.

Full 6S feed, leakage/damping, ADC and combined IMU2 gates remain open. V1 inspection, V2 vehicle nodes and the future voice/text/location handheld remain distinct; measured voice/RC coexistence precedes handheld hardware selection.

[Input hashes](input_manifest.json), [review notes](review_notes.json), [browser evidence](viewer_check.json) and [packet manifest](packet_manifest.json) support efficient restart. Recheck Git and FILE_OWNERSHIP; preserve the unrelated v1_design.py and route_v2.py edits.

```text
python -B reviews/codex/connector_fault_contract/test_model.py
python -B reviews/codex/connector_fault_contract/build_packet.py --check
python -B tools/quality/check_publication.py
node pm/tools/validate.mjs
```
