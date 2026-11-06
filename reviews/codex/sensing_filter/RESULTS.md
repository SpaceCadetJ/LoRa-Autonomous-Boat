# SENSE-02 — native delta and conditional filter results

[Design guide](README.md) | [Native Power sheet](native/svg/LoRa_Boat_Controller_V2-Power.svg) | [Independent verification](validation.json) | [Manufacturer evidence](sources.json)

## Recorded native correction

KiCad 9.0.7 capture produced 130 components, 433 physical pin memberships, 122 nets and 11 sheets. ERC reports 0 errors and 1 inherited AD0 warning. This is captured native evidence, not a hardware result.

Independent comparison checks all 128 old component records under the declared three-reference field whitelist, preserves all 429 old node attributes and 428 unchanged pin memberships, and verifies exactly one moved old pin plus four new pins. Embedded symbols, sheet identities and all other complete net memberships are preserved.

| Pin | Baseline | Candidate |
|---|---|---|
| U8.1 | /ISENSE | /Power/ISENSE_DRV |
| R44.1 | Absent | /Power/ISENSE_DRV |
| R44.2 | Absent | /ISENSE |
| C59.1 | Absent | +3V3 |
| C59.2 | Absent | GND |

Only Power.kicad_sch differs in the 38-file copy; 37 files remain byte-identical, including both converters. ACT-01 population bytes and 580 prior input hashes remain unchanged. Live electrical/copper deltas are zero; no PCB, firmware or live BOM integration occurred.

## Filter arithmetic, not acceptance

| Quantity | Nominal | Initial R/C tolerance only |
|---|---|---|
| R44/C37 time constant | 100.000 us | 89.100–111.100 us |
| Ideal single-pole cutoff | 1591.549431 Hz | 1432.537742–1786.250764 Hz |
| Ideal full-scale step to quarter-LSB at 12 bits | 0.970406 ms | 0.864632–1.078121 ms |

Equations: tau=R*C; fc=1/(2*pi*tau); ideal full-scale residual below 1/(4*2^12) requires tau*ln(2^14). The interval uses only initial resistor +/-1% and capacitor +/-10%. It excludes X7R bias, temperature, aging, frequency, amplifier impedance, trace parasitics and switched-capacitor acquisition. It is not a guaranteed system interval or sampling-rate choice.

## Remaining acceptance gates

Exact TDK/Yageo candidate identities are confirmed. C59 nominal1uF provides nominal margin over TI minimum0.1uF, but effective capacitance and physical high-frequency bypass remain unqualified. Existing0603 lands differ from TDK reflow recommendations; new components are not placed/routed on the PCB. R33 rating annotation grants no board-current increase.

R44 is not a clamp or proven power-off protection. Divider reference/range, PA2/PA4 state-specific injection, INA18026V common-mode/transients, full6S feed, VSERVO and combinedIMU2 remain open. No ordering, assembly, flashing or powered-application release.

Next: establish source and minimum-VDDA envelopes, then address divider scaling and power-off protection on a new isolated copy.
