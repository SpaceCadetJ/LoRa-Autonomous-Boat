# ACT-08: reference load, discharge and observer power states

**A 2.49 kΩ reference load and 1 kΩ series resistors are useful candidates, but passive discharge alone cannot establish default disable.** This packet narrows ACT-07's power boundary without changing the ACT-04 native candidate. ACT-04 remains the latest native candidate; QUAL_OK and ACK remain undriven and pulled low.

Open the [power-path proposal](v2_observer_power.svg), [calculated cases](RESULTS.md), [source ledger](sources.json), [allocation contract](contract.json), or [engineering workspace](../../../pm/index.html). All curves and values are analytical screens, not measured shutdown waveforms. Candidate/live electrical and copper delta is zero; no parts or powered applications are released.

## Proposed connection and what it resolves

Investigate powering TLV3202AIDGKR and REF3425IDBVR from the observed +3V3 rail. Preserve ACT-07's two independent sensing dividers. At the reference output, tie force/sense correctly, propose a 2.49 kΩ bleeder to ground and an output capacitor whose **effective** capacitance stays between 0.1 and 0.264 µF. A nominal 100 nF part with negative tolerance is insufficient to establish the reference's 0.1 µF stability minimum. Exact capacitor/resistor identities and input bypass remain unselected.

Each comparator reference input gets its own proposed series resistor. A 1 kΩ example fits the single-pole settling allocation; 10 kΩ does not. Do not wire the comparator's push-pull outputs together. Neither raw output drives QUAL_OK or establishes receiver readiness. Supply/enable control, a retained-low valid signal and the remaining permission combination are still missing.

With the allocated reference voltage, resistor tolerance and comparator bias, the bleeder requests about 1 mA of sourcing current. This avoids relying on full-temperature **sinking** regulation during the modeled settled state. It does not cover startup, bias outside the verified common-mode conditions, transient load, off-state leakage or reference overshoot. The same source must also supply capacitor charging current during startup.

## Source conditions constrain the budget

[REF34 SBAS804G](https://www.ti.com/lit/gpn/REF34) specifies its electrical table at VIN = VOUT + VDO, not the 12 V used for typical plots. The model conservatively charges the entire line-regulation test span, from minimum allocated reference + 50 mV to 12 V. It adds the sourcing-load term to ACT-07's compounded initial/BOX allowance. Remaining error allocation is for assembly, aging, noise and other unbounded terms; a positive remainder does not qualify those terms.

The sourcing-load table uses 500 mV headroom. Applying that condition to the allocated maximum reference requires +3V3 at least **3.005 V**. This is a conservative test-condition boundary, not a prediction of actual dropout. It lies above the previous 3.0 V logic timing boundary: retention must already be established before the observer loses its applicable conditions. Normal rail corners leave headroom, but normal voltage says nothing about a shutdown ramp.

The reference describes a high-impedance shutdown output, yet provides no accepted bound here for output reverse/leakage current in every partial-power state. Its startup time is typical. The proposed effective output capacitor range differs from the 10 µF electrical-table condition; transient applicability must be established. The manufacturer also warns of slow-input startup/shutdown anomalies and recommends input rise/fall near 6 V/ms. EN tied to IN is permitted for an unused shutdown function, but is not a proof of valid startup or shutdown under our rail waveforms.

## Why the resistor does not prove shutdown

After the reference has stopped driving, an idealized bounded-feed model gives:

```text
Vref(t) = I_feed * R + (V_initial - I_feed * R) * exp(-t / (R * C))
```

A chosen discharge endpoint is reachable in finite time only if the feed floor lies below it (for the starting conditions used here). The 0.3 V endpoint is a calculation target, not an accepted comparator pin limit. With 1 mA continuing feed, this example never reaches it. Reference leakage, other supplies, input clamps, converter reverse paths and retained charge must all be accounted for before assigning a real maximum feed current. A graph for zero feed cannot be substituted for that evidence.

For series resistors, `Vref_max / R_min` bounds current only under the stated nonnegative receiving-node assumption. Two reference pins can feed the shared supply. The [TLV3202 input clamp limit](https://www.ti.com/lit/ds/symlink/tlv3202.pdf) is an absolute stress condition, not a powered-off guarantee. Comparator behavior below 2.7 V is unspecified, and the application guidance warns against differential input voltage exceeding the supply. Neither condition is closed by an absolute current limit. Limiting current without bounding the supply's sink impedance/capacitance cannot bound the resulting phantom rail voltage.

## Power-state acceptance and next step

| State | Required behavior / evidence | Current result |
|---|---|---|
| Settled normal +3V3 | Defined sourcing load, reference error, valid comparator supply/common mode | Conditional arithmetic; exact parts and applicability open |
| Supply rises slowly or stalls | LOCAL_3V3_OK held low through invalid reference/observer states | No circuit or bounded maximum startup implemented |
| Rail falls while reference remains charged | Bound both input injection paths and every rail source/sink | Passive current ceilings only; no rail-voltage proof |
| Reference stops but another path feeds it | Bound total feed and verify finite discharge to a defined endpoint | Feed-floor cases show why zero-feed inference fails |
| Reference falls before rail | Fault retained even if raw comparator indications change | Retained-low interface still missing |
| Rail crosses 3.005 V during fall | Clear already valid and retained while source conditions disappear | Deadline and waveform qualification remain open |
| Power bounces or returns | Fresh valid interval then deliberate ACK; no auto-rearm pulse | Missing qualification/ACK remain disabled |
| Receiver power disappears | Independent receiver-ready loss inhibits signal drive | Local observation cannot establish ESC readiness |

**Next smallest circuit task:** design the explicit retained-low observer-valid interface together with a reference shutdown/discharge or isolation path. Declare its monitor power source, total sink/hold-up, allowed feed, assertion and release conditions before selecting exact parts or wiring a new native subcell. Preserve ACT-07's threshold/timing/hysteresis holds; do not restart a broad component search or treat a passive RC result as acceptance. Then predeclare the exact pin/part delta on a fresh ACT-04 copy and capture native checks if those conditions are met.

## Reproduce and preserve

Run `python -B reviews/codex/observer_power/test_model.py`, `model.py --check` and `build_packet.py --check` at the same folder path, followed by the repository publication and viewer validators. Manifests bind prior input and new artifact hashes. No native commands are rerun for this zero-delta packet. The unrelated v1_design.py and route_v2.py edits stay excluded.

C11/VSERVO transients, full 6S input feed, leakage/damping, ADC and combined IMU2 remain open. V1 inspection, V2 vehicle applications and the future voice/text/location handheld stay distinct; measured voice/RC coexistence precedes handheld hardware selection.
