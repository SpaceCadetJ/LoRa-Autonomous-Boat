# ACT-12 - verified connector paths and conditional timing

[Guide](README.md) | [Explorer](index.html) | [Future measurement plan](MEASUREMENT_PLAN.md)

## Captured native topology

Checked 30 explicit pin memberships, four complete output signal nets and 10 component values against ACT-04 XML. These are captured schematic facts, not a new native or board test.

| Channel | Driver through series resistor | Connector signal / pull / ESD | Supply / ground |
|---|---|---|---|
| ESC | U4.8 through R10 (100R) | J2.1; R11 (10k); D10 (PESD5V0S1BA) | J2.2 /BEC_IN; J2.3 GND |
| servo | U4.1 through R12 (100R) | J3.1; R13 (10k); D11 (PESD5V0S1BA) | J3.2 VSERVO; J3.3 GND |

U4 VCCB remains /Power/+5V_BUCK before D4. J2/J3 are schematic pin identities; harness orientation and real receiver identities remain unverified.

## Preserve the existing time allocation

100 ns sensing + 55 ns detector + 245 ns for the entire downstream path = **400 ns**. Origin: the upstream rail reaches the allocated overdrive point, under the inherited conditional monotone-ramp assumptions. Endpoint: a physical inhibit boundary that remains unqualified. This is not a measured connector-low or actuator-stop deadline. The separate 100 us handover allocation permits no undefined-output interval.

| Screen | Overdrive point (V) | Validity boundary (V) | Headroom (mV) | Zero-margin slew ceiling (V/us) |
|---|---:|---:|---:|---:|
| UV | 3.071938003 | 3.005 | 66.938003 | 0.167345007 |
| OV | 3.564040210 | 3.600 | 35.959790 | 0.089899476 |

Slew must be strictly below the ceiling with explicit margin. The UV boundary comes from ACT-09 (3.005 V), while OV retains ACT-07 (3.6 V). These are model applicability boundaries, not measured failure thresholds.

| Slew (V/us) | UV residual (mV) | OV residual (mV) | Arithmetic only |
|---|---:|---:|---|
| 0.01 | 62.938003 | 31.959790 | Both margins positive |
| 0.10 | 26.938003 | -4.040210 | At least one allocation exhausted |
| 1.00 | -333.061997 | -364.040210 | At least one allocation exhausted |

`residual = headroom - slew * 0.4 us`. Positive residual does not qualify the actual ramp response, partial-power behavior, output waveform, receiver pulse rejection or physical stop.

## Receiver evidence remains incomplete

| Port | Missing field groups | Record completeness | Hardware acceptance |
|---|---:|---|---|
| J2 / ESC | 10 | Incomplete | Unavailable |
| J3 / servo | 10 | Incomplete | Unavailable |

Required fields: `receiver_identity`, `receiver_supply_range`, `signal_voltage_limits`, `input_thresholds`, `input_feed_and_capacitance`, `pulse_acceptance`, `signal_loss_response`, `readiness_observation`, `stop_deadline`, `harness_definition`.

Completeness is a documentation check only. Neither populated fields nor the source-only topology check grant circuit, fabrication or hardware acceptance. No measurement rows have been executed.

The inherited pulldowns require bounds for receiver thresholds, feed, capacitance and ground offsets. A truncated PWM pulse includes its pre-fault high interval. No universal no-pulse response or stop command is assumed. Fault recovery must clear READY and require fresh acknowledgement; normal disarm retains READY under ACT-04.
