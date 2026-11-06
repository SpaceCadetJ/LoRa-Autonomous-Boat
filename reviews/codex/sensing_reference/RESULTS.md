# SENSE-03 — conditional reference and divider results

[Review guide](README.md) | [Annotated boundary](reference_boundary.svg) | [Captured evidence](evidence.json)

## Reference corner, not actual VDDA

Nominal converter feedback output: 3.314814815 V. Reference/initial-resistor corners: 3.219942244 to 3.412002432 V. VFB limits apply at VIN=24 V, -40 to125 C; the calculation does not establish the full-line or actual VDDA envelope.

Vlow = VFBmin × [1 + R4min/R5max]; Vhigh = VFBmax × [1 + R4max/R5min]. Independent initial resistor tolerances are ±1%. No separate PFM system percentage is added. Distribution drop, drift, aging, leakage, ripple, dropout and transitions are absent.

## Divider and inverse threshold

Worst initial divider ratio kmax = 0.128619049403. Margin = reference_floor - reserve - VIN_RAW × kmax. Required R31 nominal > R32 × (1+t32)/(1-t31) × [VIN_RAW/(reference_floor-reserve) - 1], with positive usable reference. Equality has zero margin. These equations select no resistor or protection circuit.

| Illustrative VIN_RAW | Worst divider | Conditional margin, zero reserve | Strict R31 threshold |
|---|---|---|---|
| 24.0 V | 3.086857186 V | 133.085059 mV | > 44770.687174 ohm |
| 25.2 V | 3.241200045 V | -21.257801 mV | > 47356.090220 ohm |
| 26.0 V | 3.344095284 V | -124.153040 mV | > 49079.692250 ohm |
| 44.0 V | 5.659238174 V | -2439.295929 mV | > 87860.737934 ohm |

At25.2 V, conditional overlap is -21.257801 mV. Existing-divider zero-reserve crossing: 25.034722766 Vraw. The44 V row uses the previous unqualified protected-rail target; it is not an actual transient bound or an ADC stress permission.

An explicitly allocated50 mV reserve raises the25.2 V nominal R31 threshold to >48212.469608 ohm. This reserve is not an accepted error budget, and the threshold does not select an available part or establish acquisition/source impedance.

## Actual acceptance remains unavailable

Actual source maximum, transient maximum, minimum VDDA/VREF+, required reserve and power-sequence envelope remain null. Positive illustrative margin does not release a range. A lower resistor ratio alone does not qualify startup/reset/shutdown, analog activation, retained C36 charge or a clamp into an unpowered rail. PA2 FT absolute VDD+4 V must not be confused with active conversion0..VREF+ or a universal off-stateVDD+0.3 V rule.

## Preservation and next task

Checks cover 26 pins,12 identities and658 prior hashes. SENSE-02, both converters, ACT-01 populations, disabled qualifications and all live CAD/copper/firmware are preserved. No native commands or hardware checks were rerun.

Next specify the ADC interface state/threshold/discharge contract before component selection or a new isolated SENSE-02 amendment. Preserve6S and separateIMU2; no procurement, fabrication or powered-application release.
