# VSERVO-01 - native identity correction and reservoir limits

[Guide](README.md) | [Explorer](index.html) | [Source conditions](source_review.json) | [Native checks](validation.json)

## Captured native result

KiCad 9.0.7 exports retain all **429 physical pin memberships** and all **127 other component records**. C11 alone changes identity, value, datasheet, description and footprint. C11.1 remains VSERVO; C11.2 remains GND. ERC reports **zero errors and one unchanged U6 AD0 warning**. Both converter sheets, actuator sheets, D4/D9 DNP state and exclusive source population contract are preserved.

The explicit candidate land has two 3.2 x 1.6 mm pads at x = +/-2.5 mm, 1.8 mm inner gap and 8.2 mm outer span. Native pcbnew inspection and portable geometry checks agree. This is an isolated schematic/library amendment: no PCB layout or DRC, assembly, procurement or hardware qualification is claimed. The separate IMU2 candidate is not integrated.

## Allocated load-step example

Start 5 V; floor 4.5 V; capacitor current deficit 0.5 A for 100 us; allocated constant series resistance 0.2 ohm. These are illustrative allocations, not measured loads, receiver limits or an ESR specification. The catalog 360 mOhm value is AC impedance and is not used as ESR.

| Capacitance illustration | Capacitive drop (V) | ESR allocation drop (V) | Endpoint (V) | Margin to allocated floor (V) |
|---|---:|---:|---:|---:|
| 56 uF | 0.892857 | 0.100000 | 4.007143 | -0.492857 |
| 80 uF | 0.625000 | 0.100000 | 4.275000 | -0.225000 |
| 100 uF | 0.500000 | 0.100000 | 4.400000 | -0.100000 |

All three illustrative load cases exhaust the allocated floor. Strictly positive arithmetic margin needs **C > 125 uF** under the fixed assumptions. Equality gives zero margin; it does not pass. This threshold is not a part recommendation.

The candidate's nominal 100 uF has initial +/-20% capacitance tolerance at 120 Hz and 20 C. The separate endurance criterion allows +/-30% change from the initial value after the specified test and restoration to 20 C. Stacking those limits gives 56 uF only for that post-test condition; it is not an all-temperature, in-operation lifetime or effective-capacitance lower bound. The 100 uF case is nominal reference only. C12 receives zero effective-capacitance credit. None of the cases establishes an all-temperature, in-operation bound.

## Net returned energy

The ideal capacitor endpoint is sqrt(V_start^2 + 2 E_net / C). Net energy must already account for source contribution, load absorption and any sink. The endpoint omits ESR/inductive peaks and is not a transient peak prediction.

| C (uF) | Net energy (mJ) | Ideal endpoint (V) | Margin to allocated 5.5 V ceiling (V) |
|---|---:|---:|---:|
| 56 | 0.1 | 5.345225 | 0.154775 |
| 56 | 0.25 | 5.824824 | -0.324824 |
| 56 | 1 | 7.791937 | -2.291937 |
| 80 | 0.1 | 5.244044 | 0.255956 |
| 80 | 0.25 | 5.590170 | -0.090170 |
| 80 | 1 | 7.071068 | -1.571068 |
| 100 | 0.1 | 5.196152 | 0.303848 |
| 100 | 0.25 | 5.477226 | 0.022774 |
| 100 | 1 | 6.708204 | -1.208204 |

| Net energy (mJ) | Equality capacitance threshold (uF) |
|---|---:|
| 0.1 | 38.095238 |
| 0.25 | 95.238095 |
| 1 | 380.952381 |

Positive margin requires capacitance strictly greater than the threshold and valid assumptions. At 80 uF the allocated 5 to 5.5 V energy budget is 0.210 mJ. No regenerative event or receiver voltage envelope has been measured.

## Remaining circuit obligation

D4/D9 forward-feed the rail; neither defines a controlled energy sink. The 16 V capacitor rating does not establish the permitted servo voltage, reverse-voltage immunity or pulse/ripple lifetime. The next packet must bound a sink or source-return path for both exclusive source populations, with unknown receiver/source/energy/inductance inputs explicitly unavailable. Native electrical checks, arithmetic tests and viewer checks do not release ordering or powered use.
