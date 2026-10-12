# ACT-01 — buffer supply and actuator power variants

**The PWM buffers now use the board's 5 V converter in an isolated schematic candidate.** Open the [annotated actuator sheet](v2_actuator_supply.svg), [power/source sheet](native/svg/LoRa_Boat_Controller_V2-Power.svg), [KiCad project](source/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pro), [electrical contract](expected_contract.json) or [population contract](population_contract.json). The viewer lists this as **Design → V2 → ACT-01**.

This extends BUCK5-A1. Both converter source sheets remain byte-identical; their internal notes describe their earlier review scope. This guide and the revised parent sheets govern the new buffer connection. Live CAD/copper, V1, firmware and source BOM are unchanged. IMU2 remains a separate candidate. No assembly, fabrication or powered-use release is provided.

## Exact change and evidence

Only **U4.5, U5.5, C13.1 and C14.1** move from VSERVO to `/Power/+5V_BUCK`, before the source diode. The direct root-sheet connection carries power from Power to Actuators. Existing PWM, ground, output resistor, test-point and connector connections remain intact.

D4/D9 retain their pin wiring but now specify **Vishay SS34-E3/57T**, using a captured project-local **D_SMC** footprint. The master marks **both DNP**; it is a connectivity superset, not an assembly default. The old six-reference boundary contains 18 pins; the candidate retains **119 components / 398 pins** and preserves all **380 outside-boundary pins**, identities, sheet paths and native pin metadata. Native DNP markers and the two converter source hashes are independently checked.

KiCad 9.0.7 ERC records zero errors and the original AD0 warning. Thirty-one contract/mutation tests check these changes and reject invalid source populations. See [validation](validation.json), [native commands/hashes](native_manifest.json), [review notes](review_notes.json) and [package inspection](native_geometry.json). These are captured schematic and software results; no PCB or hardware result is inferred.

## Proposed assembly variants

Select a variant only after its remaining electrical and hardware gates are closed. Neither is released or the default.

| Variant | D4: board 5 V to VSERVO | D9: BEC_IN to VSERVO | Intended actuator energy source |
|---|---|---|---|
| BEC_ONLY | Absent / DNP | Fitted | ESC BEC at J2.2, through D9 to J3.2 |
| ONBOARD | Fitted | Absent / DNP | Board converter through D4 to J3.2 |

**Both fitted is prohibited by this candidate's assembly contract.** Both absent is the unselected master state. These are physical population choices, not firmware settings. DNP removes the selected power path, not signal or ground connections.

In both variants, the board battery and 5 V converter are still needed for the buffers. A BEC alone does not power the logic. The 6S board-input requirement is retained; it is **not** a permitted BEC or actuator voltage. Never connect the battery to J2.2 or J3.2. With ONBOARD, J2.2 is intentionally disconnected from VSERVO; isolate any unused BEC positive lead while retaining the required shared signal ground.

| Connector pin | Preserved function | Review obligation before use |
|---|---|---|
| J2.1 / J3.1 | ESC / servo PWM | Confirm receiver levels and powered/unpowered behavior |
| J2.2 | BEC_IN input | Confirm actual regulated BEC and variant; no battery input |
| J3.2 | VSERVO output | Confirm voltage at the load after diode/harness loss |
| J2.3 / J3.3 | GND | Confirm pin order, mating contacts, crimps and return-current path |

Before assembly release, record the selected variant, exact actuator/BEC identities, fitted diode/polarity, omitted position and harness drawing in the unit acceptance record. Then review stall/startup current, signal compatibility, supply sequencing and the remaining power gates. Existing application bring-up/flash holds remain; this packet introduces no new operational firmware.

## Why the rail change helps, and what remains open

The retained SN74AHCT1G125DBVR requires 4.5–5.5 V; its input thresholds are 2.0 V high and 0.8 V low. At 4.5 V and ±8 mA, output limits are at least 3.8 V high and at most 0.44 V low. Its input leakage is specified down to zero supply, but that does not establish powered-off output isolation: no Ioff specification is supplied, and output voltage is constrained relative to VCC. Both OE pins remain grounded, so passive pulldowns do not guarantee safe startup, brownout or shutdown. Retain close 100 nF bypass and design a default-disabled enable/sequencing amendment next. [TI buffer datasheet, pp. 4–5 and 8–10](https://www.ti.com/lit/ds/symlink/sn74ahct1g125.pdf).

The preceding converter's initial PWM envelope, 4.866303–5.189909 V, fits the buffer's static supply range. This is not an all-mode guarantee: the converter's no-load PFM offset is only typical, and ripple, transients, drift and startup remain unqualified. The existing [5 V analysis](../buck_5v/README.md) also shows why full simultaneous loads at a 7 V battery exceed the present feed budget. The optional onboard configuration remains a requirement; no reduced load or external-BEC-only requirement is silently substituted.

SS34-E3/57T is a confirmed manufacturer ordering identity. It is an SMC/DO-214AB, 40 V diode; its 3 A average rating has mounting/temperature conditions. The 0.5 V forward maximum is a pulsed 3 A/25°C test, not a universal drop. Reverse leakage can reach 20 mA at 40 V/100°C; zero backfeed is not established. [Vishay identity](https://www.vishay.com/en/product/88751/tab/quality/) and [datasheet](https://www.vishay.com/docs/88751/ss32.pdf).

The captured lands have 2.5 × 3.3 mm pads, 4.3 mm gap and 9.3 mm overall span. Pad 1 is the cathode; the marked side must face VSERVO. Selected dimensions meet the cited land-length/width/gap criteria but differ from the manufacturer's reference span. Placement, stencil, thermal and assembly qualification remain open. The master DNP cross does not reverse diode polarity.

After the four supply moves, VSERVO contains C11.1, C12.1, D4.1, D9.1, J3.2 and TP4.1. Either source diode can leave actuator regeneration charging this rail; no sink/clamp is established. Reversed-input leakage and polarized-capacitor stress also remain open.

**New purchasing hold:** C11's exact `EEE-FK1A101P` identity could not be confirmed in the current [Panasonic FK catalog](https://industrial.panasonic.com/cdbs/www-data/pdf/RDE0000/ABA0000C1181.pdf). Its source 100 µF/10 V marking is not a verified ripple, footprint or lifetime specification. No neighboring part was substituted. C12 remains a nominal 10 µF/16 V X5R; effective capacitance is unverified. [Murata specification](https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM21BR61C106KE15-01A.pdf). JST XH's 3 A condition uses AWG22; actual contacts, wire and thermal rise still matter. [JST specification](https://www.jst-mfg.com/product/pdf/eng/eXH.pdf).

## Resume and reproduce

**Next smallest circuit task: default-disabled buffer enable and power sequencing**, including externally powered actuator backdrive and powered-buffer injection into an unpowered actuator. Preserve this rail/population contract and both converter sheets on a new copy. Resolve C11/VSERVO reservoir and regenerative/transient behavior alongside actual load requirements; then complete the 6S input-feed, nonpolar reservoir/leakage/damping, ADC/sense and explicit combined IMU2 amendment before routing on a copy of corrected copper.

Read [packet_manifest.json](packet_manifest.json) and the handoff before editing. Run `verify_candidate.py --check`, `test_candidate.py`, `inspect_packages.py --check`, `python -B tools/quality/check_publication.py` and `node pm/tools/validate.mjs`. Native export is isolated and recorded; do not run primary generation/routing to refresh documentation. Preserve unrelated v1_design.py and route_v2.py edits.

Keep V1 inspection, V2 vehicle-node applications and the future handheld separate. Handheld **voice, text and location** still require measured voice/RC coexistence before hardware selection.
