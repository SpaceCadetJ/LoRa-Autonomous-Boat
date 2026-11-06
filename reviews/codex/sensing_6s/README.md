# SENSE-01 — 6S voltage and current sensing review

[Annotated measurement boundary](sensing_boundary.svg) | [Calculated limits](RESULTS.md) | [Captured evidence](evidence.json) | [Preserved native Power sheet](../power_sheet_polish/native/svg/LoRa_Boat_Controller_V2-Power.svg)

The current sensing paths are **not ready for operational telemetry**. This review identifies what the two channels measure, the available ADC margin, an unqualified direct amplifier-output capacitance and a shunt rating inconsistency. It is a review of the preserved VSERVO-01 electrical candidate and POWER-DOC-01 presentation. Expected and actual electrical/copper deltas are zero. No native generation, firmware change, hardware test or purchasing release occurred.

## What the signals mean

| Channel | Captured circuit | Meaning and exclusions |
|---|---|---|
| `/VBAT_SENSE`, U1 PA2/pad16 | VIN_RAW → R31 47k → ADC node; R32 6.8k and C36 100nF to GND | Voltage **after D12**, with upstream diode/fuse/wiring drops; not direct battery-terminal voltage |
| `/ISENSE`, U1 PA4/pad20 | R33 20mΩ from VIN_RAW to VIN_BUCK; U8 INA180A1 gain20; OUT directly on PA4/C37 | Converter-input branch current, including downstream capacitor charging; not whole-vehicle battery or converter-output current |
| VDDA/VREF | +3V3 through FB1, with C21/C22 decoupling | LQFP64 ties ADC references internally to VDDA/VSSA; nominal 3.3V is not a calibrated reference |

The raw-side divider and C1/C2 currents bypass R33. External propulsion wiring is not routed through this shunt. In BEC_ONLY, J2/D9 supplies VSERVO outside the measured branch; in ONBOARD, +5V_BUCK/D4 loading contributes through the converter input. The ACT-01 source populations remain exclusive and unqualified. PA0/PA1 remain LoRa UART, not these ADC channels.

## Range and accuracy are separate gates

The nominal divider is 6.8/53.8, so 25.2V **at VIN_RAW** produces 3.18513V. Independent ±1% resistor extremes raise this to 3.24120V. At 26V raw input, the upper ratio produces about 3.34410V. Compare against guaranteed **minimum actual VDDA/VREF**, not a nominal rail label. The [results](RESULTS.md) show both 3.3V and an explicitly illustrative 3.135V reference. Neither value is an accepted board minimum. No diode-drop credit is used to manufacture headroom.

A 25.2V example corresponds to six conventional 4.2V cells; actual chemistry, source tolerance, transients and terminal-to-VIN_RAW drops still need bounds. U8's common-mode operating maximum is 26V, leaving only 0.8V above that illustrative raw voltage. An upstream fuse or a voltage-divider change does not establish this amplifier's transient protection. Negative or reverse current is not reliably measured by this ground-referenced unidirectional channel. [TI INA180 §§7.1/7.3, 8.4 and 9.3](https://www.ti.com/lit/ds/symlink/ina180.pdf).

At 3A, ideal current-channel output is 1.2V, with 60mV shunt drop and 0.18W shunt loss. These are arithmetic, not a validated range or thermal result. The tempting 3.3V/0.4V/A = 8.25A ignores gain/offset, output swing, reference margin, current direction, shunt/trace/fuse thermal limits and sampling. TI specifies gain error over an output interval bounded away from both rails; that accuracy condition is distinct from output swing. Input offset, common-mode dependence and temperature prevent a simple whole-range 1% claim.

## Correct output loading before adding acquisition

C37 is **100nF directly on U8 OUT**, while the INA180 table lists 1nF in the **typical** column for maximum capacitive load without sustained oscillation. The nominal load is 100× that listed typical capability. This is a stability concern requiring correction/verification, not proof of oscillation or a guaranteed 1nF threshold. There is no independent passive current-channel RC resistor in this captured circuit, so a supposed “1k/100nF filter” is not implemented. TI recommends output RC filtering for a high-impedance receiver. [TI §7.5 p8 and §9.1.3 p23](https://www.ti.com/lit/ds/symlink/ina180.pdf).

C36's nominal divider time constant is about 594µs; it describes external input-step settling, not the ADC's track-and-hold acquisition. The results separately evaluate ST's resistive-source acquisition equation with explicitly allocated 30MHz, 7pF and 6kΩ. That screen does not model C36 charge sharing, scan order or repeated sampling. Actual ADC clock, sampling cycles, sequence and rate remain unset. [ST DS10693 Table74/Equation1 pp140–141](https://www.st.com/resource/en/datasheet/stm32f446re.pdf).

## Power states and pin types

PA2 is FT; PA4 is TTa with an ADC/DAC path. FT digital tolerance is not permission to apply that voltage during analog conversion. ADC conversion requires 0…VREF+. ST's injected-current stress ratings differ between FT and TTa and do not guarantee measurement accuracy or qualify internal diodes as protection. [ST DS10693 Tables10/13/14/16/74](https://www.st.com/resource/en/datasheet/stm32f446re.pdf), [ST AN4899 §§4.2, 5.2, 5.3.6, 6.3](https://www.st.com/resource/en/application_note/an4899-stm32-microcontroller-gpio-hardware-settings-and-lowpower-consumption-stmicroelectronics.pdf).

VIN_RAW can remain present while VDDA or U8 supply is absent or ramping. Neither sensing net has a dedicated external clamp/isolation device. Review reset digital state, analog-enabled state, supply loss and reverse polarity separately. Do not assume one universal VDD+0.3V off-state rule for both pins. INA180 explicitly tolerates its specified differential input with or without supply, but its unpowered output is not specified as isolated; high-impedance paths remain. Qualification must bound pin voltage, injection/backfeed, reference tracking and settling in every transition, without relying on firmware being alive. [TI §§8.4.3 and 9.3](https://www.ti.com/lit/ds/symlink/ina180.pdf).

## BOM identity and assembly implications

The captured R33 field says `0.02R 1W`; the exact Bourns MPN `CRA2512-FZ-R020ELF` is specified as 20mΩ, ±1%, **3W at 70°C**, subject to mounting and derating. Record this as an annotation/identity inconsistency. It does not authorize increasing board current or replacing the exact part with an arbitrary 1W device. The live BOM and native fields are preserved for a separately reviewed correction. Yageo exact-part sheets confirm R31/R32 at ±1%; temperature, working voltage and derating still apply. C36/C37 retain `KGM15ACG1H104KT`, whose exact orderable combination was not verified. Nominal 100nF calculations do not qualify that identity or effective capacitance. Manufacturer evidence is in [sources.json](sources.json).

## Software and application contract

At the captured baseline, the [V2 Stage A diagnostic](../../../firmware_v2/README.md) does not initialize ADC, sampling, calibration or telemetry conversion. Keep its inactive-output behavior. Before a future sensing stage:

1. Correct and independently check the analog circuit, power states and full 6S common-mode boundary.
2. Establish measured VDDA/reference behavior, selected ADC clock/sequence/sample time, external-filter recovery and channel interaction.
3. Calibrate voltage-divider ratio and current gain/offset against known instruments over the intended range and temperature. Track saturation, under-range/reverse behavior, stale samples and configuration identity.
4. Use explicit proposed names such as `vin_raw_mV` and `converter_input_mA`. Do not label these as battery-terminal voltage, propulsion current, whole-vehicle charge consumption or state of charge.
5. Keep data invalid until the circuit and acquisition contract is met. Invalid sensing must not supply an actuator-ready permission; existing missing qualifications remain disabled.

V1 inspection, V2 vehicle applications and the future voice/text/location handheld remain separate. This review changes no operating, assembly, flashing or ordering instructions. Measure voice/RC coexistence before choosing handheld hardware.

## Next bounded correction and restart

First qualify exact C36/C37 identities and U8 filter/bypass parts and values. Then create a **new isolated POWER-DOC-01 copy** for U8 output isolation/filter and local supply-bypass correction, with a declared pin/net delta and native netlist/ERC capture. Review candidate values against stability, ADC settling and power-off injection; a proposed 1kΩ resistor is not yet an accepted value. Reconcile R33's exact MPN/rating annotation without granting a higher operating current. Preserve both converter sheets, corrected copper, ACT-01 populations, C11 lands, 6S and separate IMU2. Divider scaling/protection, U8 common-mode headroom and full input-feed, leakage/damping and physical acceptance remain open.

```text
python -B reviews/codex/sensing_6s/test_model.py
python -B reviews/codex/sensing_6s/build_packet.py --check
python -B tools/quality/check_publication.py
node pm/tools/validate.mjs
```

Check Git status and FILE_OWNERSHIP.md first. [Input hashes](input_manifest.json), [review](review_notes.json) and [packet manifest](packet_manifest.json) bind this review; original Allegro/V1 evidence and both unrelated local tool edits stay preserved. Shared PM template/builder remain unchanged; the document library discovers this guide automatically. Older candidate names and next-task statements are historical.
