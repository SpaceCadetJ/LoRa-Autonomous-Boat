# SENSE-03 — divider, reference and power-state review

[Annotated boundary](reference_boundary.svg) | [Calculated limits](RESULTS.md) | [Evidence](evidence.json) | [Manufacturer sources](sources.json) | [Latest native candidate: SENSE-02](../sensing_filter/README.md)

**The existing voltage divider has no demonstrated margin against the converter/reference envelope.** An independent cross-check gives a conditional low converter output of 3.219942 V and a worst initial-tolerance divider output of 3.241200 V at 25.2 V VIN_RAW: **−21.257801 mV**. This exposes an overlap in the design screens; it does not prove measured clipping or establish a guaranteed VDDA floor across 6S operation. No circuit, BOM, firmware or copper changes are made here.

## Follow both sides of the measurement

U2 is the LMR36520ADDAR logic converter. R4=100 kΩ and R5=43.2 kΩ set its feedback ratio. +3V3 passes through FB1 to U1 VDDA, with C21/C22 decoupling. On this LQFP64 MCU the ADC reference is internally tied to VDDA/VSSA. Separately, R31=47 kΩ and R32=6.8 kΩ divide post-D12 VIN_RAW into C36 and PA2. Battery terminals, VIN_RAW, converter input and VDDA are distinct measurement points.

The captured SENSE-02 netlist checks four complete nets, eight additional supply/return pins and twelve identities. Its new U8 output resistor and bypass are preserved, along with both converters, C11 lands and exclusive ACT-01 source populations. The separate IMU2 candidate remains separate.

## What the numbers establish

TI specifies the feedback-reference range at VIN=24 V over −40…125°C. Combining those limits with independent initial ±1% feedback resistors gives 3.219942–3.412002 V. This is a reference/resistor screen with an ideal VDDA feed. TI's separate PFM system-regulation table is not an independent error to add again. Ripple, line/load behavior, dropout, startup, FB1/trace drop, ground offset, resistor drift and ADC error remain outside this calculation. [TI SNVSBF0C, pp.6–8,14–15](https://www.ti.com/lit/ds/symlink/lmr36520.pdf).

The zero-reserve divider crossing is 25.034723 V VIN_RAW. With R32 retained, the inverse calculation requires nominal R31 **greater than 47,356.090220 Ω** merely for positive margin at the illustrative 25.2 V point. Equality has no headroom. This is not a selected resistor or a completed correction: actual source/transient, reference and error-margin bounds are still unavailable. The [results](RESULTS.md) include a separate 50 mV allocation example and the existing unqualified 44 V protected-rail target to show sensitivity; neither is an accepted operating envelope.

## Keep power states distinct

| State | What must be bounded | Present disposition |
|---|---|---|
| Powered, ADC enabled | Input within actual 0…VREF+ range, source/reference margin and acquisition accuracy | Unqualified; conditional overlap identified |
| Reset or inactive analog peripheral | PA2 floating FT pad, pull configuration, source transients and device-specific stress limits | No conversion or off-state acceptance inferred |
| Startup, brownout or shutdown | ADC switch/peripheral state, VDD/VDDA tracking, retained C36 charge and reference collapse | No timing or discharge/isolation qualification |
| Supply off, source present | Device-specific FT stress, leakage/backfeed and all possible analog paths | No permission inferred from a resistor ratio |

PA2's FT absolute maximum is VDD+4.0 V, giving 4.0 V at VDD=0; it is **not** the active ADC range. FT injection ratings do not allocate positive internal-diode clamp current. Input pulls and the 300 mV VDD/VDDA sequencing limit also matter. [ST DS10693, Tables13/14/16/74](https://www.st.com/resource/en/datasheet/stm32f446re.pdf).

The analog switch depends on peripheral state; GPIO analog-mode selection alone does not prove isolation. Internal analog diodes are not characterized protection components. Neither “all passive dividers fail at zero supply” nor a universal off-state VDD+0.3 V rule is supported here. A proposed external diode into VDDA needs its own sink/backfeed proof. Disconnecting a source also does not instantly discharge C36. [ST AN4899, §§4.2,5.2.2,5.3.6,6.3](https://www.st.com/resource/en/application_note/an4899-stm32-microcontroller-gpio-hardware-settings-and-lowpower-consumption-stmicroelectronics.pdf).

## Next correction contract

Before choosing parts, specify a state-based ADC interface: qualified source/reference envelope and reserve, reference-valid assertion/release thresholds, startup/shutdown timing, analog-path state and retained-charge discharge. Decide whether passive sequencing is sufficient or a default-disabled isolation/discharge cell is required from those bounds. Missing qualification must grant no acceptance. Only then amend a **new isolated SENSE-02 copy**, with an explicit electrical delta and native checks.

The Stage A diagnostic still has no ADC implementation. U8 common mode, full 6S feed/leakage/damping, effective filter/bypass behavior, VSERVO and combined IMU2 remain open. No order, assembly, flashing or powered application is released. Keep V1 inspection, V2 vehicles and future voice/text/location handheld distinct; measure voice/RC coexistence before handheld hardware selection.

Review [captured hashes](packet_manifest.json) and [independent notes](review_notes.json). Restart with `python -B reviews/codex/sensing_reference/test_model.py`, `python -B reviews/codex/sensing_reference/build_packet.py --check`, publication checks and PM validation. Read ownership and Git first; preserve both unrelated tool edits. No primary generation/routing is needed for this analytical packet.
