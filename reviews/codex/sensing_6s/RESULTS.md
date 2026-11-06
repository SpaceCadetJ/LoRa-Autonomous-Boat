# SENSE-01 — conditional ADC calculations

[Review guide](README.md) | [Measurement boundary](sensing_boundary.svg) | [Machine-readable evidence](evidence.json)

All actual supply, transient, sample-time and error-budget fields remain unavailable. These are nominal or resistor-corner calculations, not accepted limits. No native circuit or firmware was changed.

## Divider range

| VIN_RAW allocation | Assumed VDDA minimum | Worst resistor output | Arithmetic headroom |
|---|---|---|---|
| 25.200 V | 3.300 V | 3.241200 V | 0.058800 V |
| 25.200 V | 3.135 V | 3.241200 V | -0.106200 V |
| 26.000 V | 3.300 V | 3.344095 V | -0.044095 V |
| 26.000 V | 3.135 V | 3.344095 V | -0.209095 V |

R31/R32 nominal ratio 0.126394052; independent ±1% bounds 0.124202059…0.128619049. Both reference floors are illustration inputs, not measured or guaranteed board rails. Positive margin excludes leakage, temperature, reference and ADC error.

| Assumed reference | Raw-input equality ceiling at worst ratio |
|---|---|
| 3.300 V | 25.657164 V |
| 3.135 V | 24.374305 V |

Equality leaves zero margin. These ceilings do not supersede U8 common-mode limits or protection requirements. Battery-terminal voltage is different from VIN_RAW.

## Distinct settling models

Nominal Rth = 5940.520446 Ω; with assumed 100nF, τ = 594.052045 µs and cutoff = 267.914141 Hz. Exact C36 identity/effective capacitance remain unqualified.

| Ideal external RC step | Time to ¼ LSB at 12 bits / 3.3V |
|---|---|
| Full-reference ADC-node step, ideal nominal RC | 5.764717 ms |
| Zero to 25.2 V VIN_RAW, nominal divider and RC | 5.743670 ms |

Separately, ST's resistive-source expression with allocated 30MHz, RAIN=5940.520Ω, RADC=6kΩ, CADC=7pF and N=12 gives k_min=24.833022 cycles (0.827767µs). It does not model the external 100nF capacitor, amplifier dynamics, channel kickback or repeated scanning. No sample-time setting is selected or validated.

The current channel has no captured output-series resistor: do not assign it a fictitious passive RC cutoff. Direct nominal C37 load is 100× TI listed typical capability, with stability unmeasured.

## Current-channel ideal transfer

| Converter input current allocation | Ideal OUT | Shunt drop | Shunt loss |
|---|---|---|---|
| 0.0 A | 0.000 V | 0.000 V | 0.000 W |
| 1.0 A | 0.400 V | 0.020 V | 0.020 W |
| 3.0 A | 1.200 V | 0.060 V | 0.180 W |

Ideal 0.4V/A is not an accepted measurement range. Gain/offset/common-mode/swing, reverse current, thermal capability, sequence and ADC errors remain open. The exact R33 MPN 3W rating does not raise board-current permission.

## Evidence and next task

Portable comparison checks 35 pin memberships across four complete sensing/feed nets plus supply/return pins, seven component identities and exclusive source populations. It preserves 559 previous hashes and replays three captured Stage A files. No fresh native or hardware checks are claimed.

Next qualify exact C36/C37 identities and U8 isolation/filter/bypass values, then amend a new isolated copy with explicit net delta and native checks; reconcile R33 rating annotation. Preserve 6S, both converter sheets, C11 lands, populations, disabled qualifications and separate IMU2.
