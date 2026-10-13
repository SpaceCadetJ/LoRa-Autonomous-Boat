# ACT-07 calculated allocation

These are conditional requirements calculations. No component, circuit, arbitrary ramp or powered application is qualified. Source conditions and unverified allocations are in [the guide](README.md) and [contract](contract.json).

## Threshold bounds

| Event | Minimum V | Maximum V |
|---|---:|---:|
| UV assert | 3.096952985 | 3.145635291 |
| UV recover | 3.099447511 | 3.148136789 |
| OV assert | 3.476999596 | 3.535943732 |
| OV recover | 3.474201205 | 3.533134084 |

Reference 2.5 V +/-0.2%; comparator equivalent offset +/-10 mV; full hysteresis 0..4 mV; signed bias 5 nA; independent resistor errors+/-0.35%. Divider 249 ohm / 1k for UV and 402 ohm / 1k for OV. These are allocations, not sourced guarantees.

| Margin | mV |
|---|---:|
| normal_UV_assert | 74.307 |
| normal_OV_assert | 64.997 |
| normal_UV_recovery | 71.805 |
| normal_OV_recovery | 62.199 |
| latest_UV_assert_to_corridor | 96.953 |
| latest_OV_assert_to_corridor | 64.056 |

## Overdrive before the time budget

Use latest assertion and maximum divider multiplier independently: a conservative cross-corner envelope, not necessarily one physical corner. Reserve 20 mV input overdrive converted to the rail, then 400 ns (55 ns detector + 245 ns downstream + 100 ns sensing allocation).

| Direction | Rail at allocated overdrive V | Headroom mV | Zero-margin slope ceiling V/us |
|---|---:|---:|---:|
| UV | 3.071938003 | 71.938 | 0.179845007 |
| OV | 3.564040210 | 35.960 | 0.089899476 |

| Illustrative slew V/us | UV residual mV | OV residual mV | Arithmetic disposition |
|---|---:|---:|---|
| 0.01 | 67.938 | 31.960 | Fits allocation |
| 0.1 | 31.938 | -4.040 | Exhausts allocation |
| 1 | -328.062 | -364.040 | Exhausts allocation |

Strictly positive margin is required. The zero-margin slope ceiling is not an accepted waveform specification. This model does not establish that a step-test delay applies to ramps. Sense dynamics, pulse duration, supply/common mode/loading, retention, monitor shutdown and receiver response remain open. Negative residual means this allocation fails, not a prediction of measured hardware failure.

## Reproduction

Run `python -B reviews/codex/observation_3v3/model.py --check` to reproduce [analysis.json](analysis.json). The adjacent test_model.py exercises numerical fixtures and rejected claims. Follow [ACCEPTANCE.md](ACCEPTANCE.md) for unresolved conditions.
