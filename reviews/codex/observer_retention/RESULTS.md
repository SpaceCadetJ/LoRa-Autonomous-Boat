# ACT-09 retention and handover calculations

This is a conditional architecture and request model. Native circuitry is unchanged. No physical output-disable, indefinite brownout or hardware acceptance is established. Read the [architecture contract](README.md), [explicit assumptions](contract.json) and [interactive request traces](index.html).

## Same-rail observation deadline

Allocated overdrive point 3.071938003 V minus ACT-08 reference-validity boundary 3.005 V leaves **66.938003 mV**. At 400 ns total allocated response, the zero-margin ceiling is **0.167345007 V/us**. A strictly lower slope and qualified waveform response are required; this is not an accepted hardware slew specification.

`residual = overdrive_voltage - validity_floor - slew_V_per_us * response_ns / 1000`

| Illustrative falling slew (V/us) | Residual (mV) | Arithmetic disposition |
|---|---:|---|
| 0.01 | 62.938003 | Fits allocation only |
| 0.1 | 26.938003 | Fits allocation only |
| 1 | -333.061997 | Exhausts allocation |

This tightens the prior 3.000 V corridor calculation to the 3.005 V sourcing-test boundary. It applies to the same-rail proposal only. A separately held island changes supply/common-mode conditions and needs its own source applicability review. ACT-07's overvoltage and threshold/hysteresis gates remain open.

## Separate held-island charge budget

The proposed island starts from 3.219942244 V minimum source, subtracts 0.100 V maximum allocated blocking loss, then 0.510000 mV initial ESR sag. Result: 3.119432244 V. The model uses 5.100 mA total allocated discharge, including reverse leakage, and stops at 3.005 V.

`T = C_effective * (V_source_min - blocking_drop - I_total*ESR - V_valid_floor) / I_total`

| Effective capacitance (uF) | Time to validity floor (us) | Margin to 100 us allocation (us) | Arithmetic disposition |
|---|---:|---:|---|
| 1 | 22.437695 | -77.562305 | Exhausts allocation |
| 4.7 | 105.457166 | 5.457166 | Fits allocation only |
| 10 | 224.376949 | 124.376949 | Fits allocation only |

Zero-margin effective capacitance is 4.456786 uF. Strictly positive margin is needed. Effective values are not nominal component selections. A reference load, logic, conditioner, pin loads, bypass, storage leakage and reverse paths must all fit the current budget. A main-rail short needs actual reverse isolation; a capacitor across the shorted rail does not satisfy this equation.

The 3.005 V floor comes from reference sourcing-test headroom. This screen assumes every island guard, retention, conditioner and interface remains valid down to that voltage; the actual floor must be the highest applicable requirement across them. A higher floor reduces hold-up. The 100 us handover-finish budget is an unverified allocation. It does not permit a 100 us undefined-OE interval: the physical boundary must first suppress invalid U14 drive before main logic leaves its applicable supply range, then maintain disable continuously through handover. Observer hold-up does not relax the fast end-to-end inhibit deadline. A positive result does not bound a switch, reverse current, OV surge, recharge or unknown hold duration. A separate physical disabled condition must take over before the island becomes invalid. **Physical disable after hold-up remains unproven in every case.**

## Request-level sequence traces

| Scenario | Events/ticks | Modeled guard checks | Final output-enable request |
|---|---:|---|---|
| healthy startup ack arm | 5 | Modeled guards met | High requested |
| fault bounce fresh requalification | 12 | Modeled guards met | High requested |
| held ack blocks | 8 | Modeled guards met | Low requested |
| coincident release ack unqualified | 4 | Outside modeled guards | Low requested |
| unknown receiver blocks | 2 | Modeled guards met | Low requested |
| guard loss reference off | 6 | Modeled guards met | Low requested |

Only the listed events advance the model. The model defaults absent/unknown health inputs low, starts reference power from the independent guard, requires a fresh healthy interval with ACK/ARM low, and separates QUAL release, ACK and ARM. Faults invalidate requested READY. Conflicting edges latch the trace outside its modeled guard checks. ACK high/low pulse width and debounce are not modeled or qualified. These conservative software requests do not predict analog glitches, actual fault capture, metastability, physical OE or real motor stopping.

The model's allocated delays are not a timing characterization. A reference-valid predicate must be established externally; the healthy interval cannot make an invalid reference valid. All native and physical acceptance flags remain false.

## Reproduction

`python -B reviews/codex/observer_retention/test_model.py`

`python -B reviews/codex/observer_retention/model.py --check`

`python -B reviews/codex/observer_retention/build_packet.py --check`

[analysis.json](analysis.json) binds contract/model/prior allocations. [packet_manifest.json](packet_manifest.json) binds 257 preserved inputs and all packet artifacts. No native tools are invoked for this zero-delta packet.
