# ACT-08 calculated power-state screens

These calculations are conditional proposals. They do not establish startup, shutdown, diode behavior, rail voltage, valid outputs or hardware acceptance. Read the [connection and power-state guide](README.md), [source conditions](sources.json) and [explicit allocations](contract.json).

## Settled reference load and error allocation

| Quantity | Calculated value |
|---|---:|
| Bleeder minimum / maximum | 2481.285 / 2498.715 ohm |
| Sourcing current including two allocated input biases | 0.998503236 .. 1.009567548 mA |
| Bleeder maximum dissipation | 2.528942 mW |
| Sourcing-test supply boundary | 3.005 V |
| Minimum normal-rail headroom above that boundary | 214.942244 mV |
| Initial accuracy plus full-span BOX allocation | 1490.495000 ppm |
| Full line test span | 9.455 V |
| Line term at 15 ppm/V | 141.825000 ppm |
| Sourcing-load term at 30 ppm/mA | 30.287026 ppm |
| Linear sum | 1662.607026 ppm |
| Remaining within 0.2% allocation | 337.392974 ppm |

The REF34 electrical header uses VIN = VOUT + VDO. The 12 V endpoint is charged across the whole line-test span, not treated as the initial-accuracy test point. The 3.005 V boundary preserves 500 mV sourcing-test headroom at maximum allocated reference voltage; it is not actual dropout. The remaining allocation does not qualify aging, noise, assembly or unverified application conditions. The proposed effective capacitor range differs from the 10 uF table condition; transient applicability remains open.

## Discharge with constant feed

Worst allocated R = 2498.715 ohm, effective C = 0.264 uF, initial = 2.505 V. Maximum RC time constant = 659.660760 us.

`V(t) = R*I_feed + (V_initial - R*I_feed)*exp(-t/(R*C))`

| Assumed continuing feed (uA) | Final floor (V) | Time to 0.3 V (ms) |
|---|---:|---:|
| 0 | 0.000000000 | 1.399973 |
| 10 | 0.024987150 | 1.450727 |
| 100 | 0.249871500 | 2.510915 |
| 1000 | 2.498715000 | Unreachable |

Finite discharge requires the floor to be strictly below the target. The 0.3 V endpoint is a calculation target, not a permitted pin voltage. All rows assume the reference has stopped driving, initial voltage is bounded and feed is constant. No listed feed is an accepted real leakage limit. Startup/shutdown anomalies or an active source invalidate this model.

## Series resistance tradeoff

Two independent reference inputs; each allocated 5 nA bias and 10 pF capacitance. Current ceilings assume a nonnegative receiving node and reference no higher than 2.505 V. They do not model a diode threshold or bound phantom supply voltage.

| Series resistance (ohm) | Current ceiling per input (mA) | Two-input ceiling (mA) | Added bias error per input (uV) | 1% settling (ns) | Against 100 ns allocation |
|---|---:|---:|---:|---:|---|
| 1000 | 2.513798 | 5.027597 | 5.0175 | 46.212883 | Fits this pole only |
| 10000 | 0.251380 | 0.502760 | 50.1750 | 462.128828 | Exceeds allocation |

This single-pole calculation excludes reference source impedance and other parasitics. The 1 kOhm option fits only that calculation; the 10 kOhm option exceeds it. Neither establishes total fault delay, a powered-off state or common-mode/bias applicability. Do not use TLV3202 absolute input-current limits as Ioff qualification. Comparator behavior below 2.7 V, differential input exceeding supply and both injection paths require explicit review.

## Reproduce

Run `python -B reviews/codex/observer_power/test_model.py`, `python -B reviews/codex/observer_power/model.py --check`, and `python -B reviews/codex/observer_power/build_packet.py --check`. The [analysis](analysis.json) binds the exact contract; the [packet manifest](packet_manifest.json) binds preserved inputs and artifacts. No native circuit or hardware check is represented by these commands.
