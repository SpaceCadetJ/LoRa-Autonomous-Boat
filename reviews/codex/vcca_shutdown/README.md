# ACT-11 - translator supply shutdown

**Decision: the reviewed VCCA-gating proposal is not accepted as the primary fast inhibit.** Static supply isolation is useful, but a bounded shutdown response has not been established. Secondary shutdown remains a proposal. ACT-04 remains the latest native candidate, with missing qualifications disabled.

[Annotated connection diagram](v2_vcca_shutdown.svg) | [Supply states and calculations](RESULTS.md) | [Source ledger](sources.json) | [Exact preservation contract](contract.json)

## What was checked

This completes ACT-10's requested VCCA alternative screen. It checks one load switch, TPS22919DCKR, against the existing TXU0102 and its local bypass. The source review began on 2026-10-22 and this bounded packet was finalized on 2026-10-27. No third part search, CAD regeneration, routing, hardware operation or ordering was performed.

The captured ACT-04 native netlist independently confirms U4.3 and C13.1 on **+3V3**, U4.7 and C14.1 on **/Power/+5V_BUCK**, C13/C14 at 100 nF, and U4.6/R40.1/U14.4 on ACT_OE. VCCB is the board buck rail before D4; it is not moved to VSERVO. The validator rechecks these exact recorded memberships and values.

## Explicit proposal, not an implemented delta

| Proposed connection | Role |
|---|---|
| TPS22919 IN1 to +3V3; GND2 to ground | Feed the translator A supply only |
| ON3 to independent SUPPLY_PERMIT, with external 10 kOhm pulldown | Default disabled; authority unimplemented |
| NC4 floating; QOD5 directly to VOUT6 | Enable internal output discharge when applicable |
| VOUT6 to new VCCA_SW | Would move exactly U4.3 and C13.1 from +3V3 |
| C13 remains 100 nF to ground; proposed local input bypass 100 nF | Preserve local decoupling; identities/effective values unqualified |
| U4.7/C14.1 remain /Power/+5V_BUCK | Preserve ACT-01 supply and population contract |
| U12/U13/U14 remain main +3V3; OE and R40 unchanged | Preserve the existing permission logic |

**Expected and actual candidate/live electrical and copper delta: zero.** The table is a proposal only; no new designator or net has been written into CAD. Both converters, exclusive source populations, corrected copper, Allegro/V1, firmware and purchasing files remain preserved. Only a closed circuit contract can justify a new isolated native copy and an explicit two-pin supply amendment.

## Source conditions that prevent a fast-inhibit claim

The [TXU0102 datasheet](https://www.ti.com/lit/ds/symlink/txu0102.pdf) describes supply isolation below 100 mV with the complementary supply valid, and a separate disconnected-supply condition. The latter defines an externally undriven node with at most 10 nA external leakage; a discharge-connected node is a different case. Glitch-free sequencing is documented. No maximum collapse-to-high-impedance time was established. The OE delay cannot be reused for supply collapse. Port leakage tests also do not establish total current into an arbitrary partial VCCA node.

The [TPS22919 datasheet](https://www.ti.com/lit/ds/symlink/tps22919.pdf) gives typical discharge resistance and switching times, without the needed maximum shutdown bound. Its recommended input range starts at 1.6 V. Section 8.3.3.1 also states that QOD strength decreases as input voltage falls. The reviewed QOD behavior cannot therefore be assumed to persist during arbitrary input collapse. Input shutdown current is not a complete output-feed specification. The smart ON pulldown does not replace independent fault authority. Ambient and junction ranges are recorded separately in the ledger.

The [state matrix](RESULTS.md#supply-state-applicability) keeps powered OE disable, low-VCCA isolation, qualifying float, intermediate rails and recovery distinct. Neither a permitted endpoint nor a typical curve establishes the transition between endpoints. External receiver readiness and actual actuator stopping remain separate requirements.

## What the capacitor calculation does establish

A single nominal 100 nF capacitor and typical 24 ohm discharge path take about **9.136 us** to reach an allocated 80 mV from 3.6 V with no feed and ideal immediate disconnection. This is a scale illustration, not an accepted lower or upper timing bound. Switch-command delay and translator isolation delay are omitted. The 80 mV target leaves a proposed 20 mV margin below the source condition; no actual rail measurement or feed budget has been accepted.

The same nominal capacitor stores 352 nC of charge above that target. Removing it in the entire 245 ns downstream allocation would require 1.437 A average net sink before allowing any other delay. The arithmetic shows why ordinary rail discharge cannot simply replace the proposed fast permission path. It does not select a higher-current part or authorize reducing bypass capacitance. [Calculated feed sensitivity and limits](RESULTS.md#scale-illustration-using-typical-qod-resistance).

## Restart must clear the existing permission

Switching only U4's supply leaves U12's READY latch powered. Consider QUAL high, ARM high and READY high before shutdown: interrupting VCCA alone changes none of those three inputs to U14. When VCCA returns, the old enable request can resume without a new acknowledgement. This is a logical counterexample from the preserved topology, not a measured pulse or claim that every actual fault follows this trace.

The shutdown source must also drive an independently qualified fault clear. Recovery must keep outputs disabled while supplies and receiver qualifications become valid, reset the healthy interval after bounce, and require a fresh ACK with ARM low before later ARM. If the main rail loses validity, retained state and startup must be re-established rather than assumed. A load-switch timer, completed discharge or local VSERVO voltage cannot grant permission.

## Next smallest task

Write one **connector-level fault acceptance contract** before selecting a third isolation device. Separate (1) fast inhibition before main logic becomes invalid, (2) continuous disabled hold through any allowed partial-power dwell and feed, and (3) recovery with no stale READY/ACK. Map the current 400 ns total / 245 ns downstream allocation back to its rail-slew assumptions and specify the permitted fault waveforms and externally observable result. Keep that allocation unchanged until an explicit, evidence-backed architecture revision replaces it.

Include receiver voltage thresholds, pulse acceptance/rejection, missing-signal response, and a non-operational measurement plan. Unknown receiver identities or bounds must stay marked unavailable; do not invent rejection widths or test outcomes. This should resolve which requirement the fast path must satisfy and which can be handled by secondary shutdown. The purpose is to prevent repeated part screening against an unclosed interface contract. No native insertion follows from this packet.

## Evidence and restart

The [manifest](input_manifest.json) preserves 298 prior-file hashes. [Review notes](review_notes.json), [source states](states.json), [calculation record](analysis.json), [viewer checks](viewer_check.json) and [packet manifest](packet_manifest.json) separate verified source/topology/arithmetic from proposed circuitry and untested hardware. No hosted CI run is claimed.

```text
python -B reviews/codex/vcca_shutdown/test_packet.py
python -B reviews/codex/vcca_shutdown/build_packet.py --check
python -B tools/quality/check_publication.py
node pm/tools/validate.mjs
```

Recheck Git and FILE_OWNERSHIP before writing; preserve the unrelated v1_design.py and route_v2.py changes. Missing local-5V, receiver, watchdog, stop and ACK qualifications remain disabled. Island charge/blocking/OV/reference shutdown, C11/VSERVO reservoir/transients, full 6S input feed, leakage/damping, ADC and combined IMU2 remain open. V1 inspection, V2 vehicle nodes and the future voice/text/location handheld remain distinct; measured voice/RC coexistence precedes handheld hardware selection.
