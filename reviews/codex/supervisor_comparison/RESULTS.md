# ACT-06 calculated comparison

Generated from [analysis.json](analysis.json) by [build_results.py](build_results.py). Values are conditional engineering screens; all dynamic/hardware acceptance remains false. See [assumptions and next task](README.md).

## Integrated TPS3703 windows

Nominal-trip hysteresis is the main screen; the data file retains actual-trip sensitivity. Positive static margins do not establish acceptable fault response.

| Part | UV assertion V | OV assertion V | Screened recovery interval V | Initial static screen |
|---|---:|---:|---:|---|
| TPS3703A4330DSER | 3.144900–3.191100 | 3.408900–3.455100 | 3.216444–3.381444 | Fails: no_trip_upper, recovery_upper |
| TPS3703A5330DSER | 3.111900–3.158100 | 3.441900–3.488100 | 3.183180–3.414180 | Pass, conditional only |
| TPS3703A6330DSER | 3.078900–3.125100 | 3.474900–3.521100 | 3.149916–3.446916 | Pass, conditional only |
| TPS3703A7330DSER | 3.045900–3.092100 | 3.507900–3.554100 | 3.116652–3.479652 | Pass, conditional only |
| TPS3703A5500DSER | 4.715000–4.785000 | 5.215000–5.285000 | 4.823000–5.173000 | Fails: recovery_upper |

## Stated maximum-delay test amplitudes

Eq7 uses nominal threshold in the overdrive denominator: UV = latest low trip − 5% of nominal UV trip; OV = latest high trip + 5% of nominal OV trip. Negative corridor margin means the required test amplitude is already outside the corridor, before allocating any propagation time. This does not predict actual device failure.

| Part | UV test V | OV test V | UV corridor margin mV | OV corridor margin mV |
|---|---:|---:|---:|---:|
| TPS3703A4330DSER | 2.986500 | 3.626700 | -13.500 | -26.700 |
| TPS3703A5330DSER | 2.955150 | 3.661350 | -44.850 | -61.350 |
| TPS3703A6330DSER | 2.923800 | 3.696000 | -76.200 | -96.000 |
| TPS3703A7330DSER | 2.892450 | 3.730650 | -107.550 | -130.650 |
| TPS3703A5500DSER | 4.477500 | 5.547500 | -22.500 | -47.500 |

## Adjustable TPS3700 divider comparison

Initial tolerance and the illustrative temperature budget apply independently to each resistor. Threshold-node bias applicability, selected resistor identities, aging and full converter behavior remain unqualified. Each recovery interval must contain the full recorded converter interval; each latest trip must remain inside its comparison corridor.

| Rail / budget | UV assertion V | OV assertion V | Recovery interval V | Lower recovery margin mV | Upper recovery margin mV | Late OV margin mV |
|---|---:|---:|---:|---:|---:|---:|
| 3V3 / ±0.10% | 3.051792–3.165698 | 3.506175–3.589963 | 3.197353–3.426487 | 22.589 | 14.484 | 10.037 |
| 3V3 / ±0.35% | 3.038501–3.179561 | 3.490663–3.605933 | 3.211355–3.411327 | 8.587 | -0.676 | -5.933 |
| 5V / ±0.10% | 4.596600–4.769002 | 5.335923–5.464298 | 4.816689–5.214647 | 49.614 | 24.738 | 35.702 |
| 5V / ±0.35% | 4.575603–4.790901 | 5.311284–5.489662 | 4.838807–5.190569 | 27.496 | 0.660 | 10.338 |

## 3V3 overvoltage ratio feasibility

For a nominal 1k bottom resistor, arbitrary positive top resistance and the stated threshold/bias assumptions:

| Independent resistor budget | Required ratio greater than | Required ratio less than | Nonempty interval |
|---|---:|---:|---|
| ±0.10% | 7.832496376 | 7.894792283 | Yes |
| ±0.35% | 7.871757910 | 7.855417352 | No |

The fixed 7.87k/1k proposal reaches zero static guard at approximately **0.257266%** error per resistor. Optimizing the continuous ratio extends this to approximately **0.298050%**. These suprema are not acceptable component specifications: strict positive margin is required, with dynamic/aging budgets still unallocated.

The four dividers also add load. The exact top/bottom branch-current intervals are retained in analysis.json; these are calculated currents, not bench readings.

**Disposition:** no part selection or qualification-driver connection. Continue with the bounded 3V3 observation subcell specified in README.md.
