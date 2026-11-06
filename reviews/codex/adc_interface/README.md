# SENSE-04 — ADC isolation, discharge and reference-valid contract

[Explore the contract](index.html) | [Functional boundary](interface_boundary.svg) | [Necessary calculations](RESULTS.md) | [Evidence](evidence.json) | [Latest native candidate](../sensing_filter/README.md)

**Proposed architecture: isolate at the MCU pin, retain C36 on the source side, and qualify a separate MCU-side discharge path.** This makes the next component screen concrete. It is a functional proposal: no device, pin assignment, circuit, firmware or PCB change is implemented. All actual qualification inputs remain unavailable and the proposed acquisition permission defaults disabled.

## Where isolation belongs

The captured SENSE-02 `/VBAT_SENSE` net joins R31.2, R32.1, C36.1 and PA2/U1.16. Disconnecting VIN_RAW upstream still leaves C36 attached to PA2. If the source path is opened and only R32 discharges C36, the nominal time constant is R32×C36 = 680 µs. That simplified case is not instantaneous pin discharge.

The proposed boundary separates PA2 from that divider/filter node. C36 remains upstream; downstream pin, trace, switch and sampling capacitances still retain charge. A qualified discharge function must handle them. Any future native change must declare the exact new pins/nets and use a new isolated SENSE-02 copy. Both converters, source populations, C11 lands and the separate IMU2 lineage remain preserved.

## State contract

| State | Proposed signal command | Samples | Required evidence |
|---|---|---|---|
| HOLD | Open | Invalid | Missing qualification defaults disabled; physical parking still needs proof |
| QUALIFY | Open | Invalid | Source, actual reference, power states, isolation, discharge, transitions and acquisition qualified |
| SETTLE | Close only after qualification | Invalid | Correct discharge release/order, switch charge and source/ADC recovery |
| ACQUIRE | Closed while all conditions remain valid | Valid only after settling | Range, accuracy, time stamp and measurement-boundary checks |
| TRIP | Request open immediately | Invalidate immediately | Bounded physical detection/opening and residual-pin-voltage trajectory |
| REARM | Open | Invalid | Fresh stable qualification/request and full settling; no stale-valid reuse |

These are requirements, not a tested state-machine implementation. A command to open does not prove physical isolation; a command to park does not prove discharge. Hardware qualification must remain effective when firmware is absent, reset or stuck. No numerical threshold or timing is selected.

## Conditions a candidate must satisfy

- **Every supply state:** guaranteed analog and control-pin behavior at normal, zero and intermediate supplies; bounds on signed leakage and back-power separately. Powered-off high impedance is not zero leakage or discharge. A VDD=0 guarantee does not automatically cover brownout. [TI SCDA015C](https://www.ti.com/document-viewer/lit/html/scda015).
- **Reference loss:** while the analog path is exposed, bound `VPA2,max(t) + reserve ≤ VREF,min(t)`. Detection and physical opening take time. An unbounded or instantaneous reference collapse cannot be covered by a finite-delay calculation; qualified hold-up, reset or another interface mechanism is needed.
- **Residual charge:** bound the pin after opening as well as before it. Use minimum downstream capacitance for a worst charge-injection glitch, and maximum capacitance for slow discharge. Include capacitive feedthrough and both voltage polarities. [ADI switch guidance](https://www.analog.com/en/resources/analog-dialogue/articles/ask-the-applications-engineer-26.html).
- **Acquisition loading:** a permanent pulldown loads the divider when connected. Include switch resistance, leakage, pull resistance, ADC kickback and settling. Switched discharge avoids steady pull loading but adds qualified opening/closing order and break-before-make behavior.
- **Fault coverage:** address stuck-closed isolation, failed discharge, lost ground, control faults and divider faults, or explicitly exclude them from the accepted fault model. Invalidation alone does not protect an analog pin.

PA2's inactive FT stress envelope differs from the enabled ADC's 0…VREF+ range. Preserve SENSE-03's device-specific off-state and VDD/VDDA sequencing distinctions. Do not infer a universal VDD+0.3 V rule, a positive internal-diode clamp allowance or that every passive divider is invalid with power off. GPIO analog-mode selection alone is not proof that the analog path is disconnected. [ST device limits](https://www.st.com/resource/en/datasheet/stm32f446re.pdf), [ST analog-state guidance](https://www.st.com/resource/en/application_note/an4899-stm32-microcontroller-gpio-hardware-settings-and-lowpower-consumption-stmicroelectronics.pdf).

## Necessary calculations, with explicit limits

The explorer compares allocated examples, including slow versus rapid reference fall, retained-charge discharge and a permanent-pulldown conflict. Positive results are necessary arithmetic only. They do not validate timing, leakage or a device. The 3.35 V release level, 50 mV reserve, 0.3 V parking target, capacitances and delays are **illustrations, not selected thresholds or PA2 ratings**. A 3.35 V reference requirement may be unavailable at the existing converter's low corner.

For a permanent pull, acceptable loading sets a lower resistance bound while leakage/parking sets an upper bound. If they do not overlap, changing a resistor cannot meet both allocations. Evaluate switched discharge or another qualified arrangement. Missing actual inputs remain null; do not silently substitute example values.

## Next bounded task

Screen a small set of exact switch/discharge arrangements against this contract. Record guaranteed analog/control limits across supplies, signed leakage, resistance/loading, charge injection/feedthrough, timing and default states. Identify missing guarantees before selecting a part. Choose an arrangement only if its qualified source/reference envelope and every required transition close; otherwise record the specific missing constraint. Native insertion follows that review on a new SENSE-02 copy.

No ordering, assembly, flashing or powered application is released. Stage A still has no ADC acquisition. Full 6S input-feed, U8 common mode, filter/bypass behavior, VSERVO and combined IMU2 remain open. V1 inspection, V2 vehicle nodes and future voice/text/location handheld remain separate; measure voice/RC coexistence before handheld hardware selection.

[Review notes](review_notes.json) and [packet hashes](packet_manifest.json) preserve the evidence. Restart with `test_model.py` and `build_packet.py --check` in this folder, then publication checks and PM validation. Read ownership/Git first and preserve the unrelated local tools. Do not rerun primary routing or native generation for this requirements packet.
