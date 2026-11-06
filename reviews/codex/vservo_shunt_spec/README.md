# VSERVO-03 — independent local-shunt specification

[Proposed cell](v2_shunt_spec.svg) | [Interactive requirements](index.html) | [Calculated bounds](RESULTS.md) | [Source ledger](sources.json) | [Explicit contract](contract.json)

This packet specifies a **proposed switched-resistor shunt across VSERVO and local GND**. A rail-derived detector/reference and gate driver would control a low-side NMOS independently of MCU firmware. The brake resistor would sit between VSERVO and the switch drain; its source would return to local GND. Names in the drawing are functional labels, not component references or a native circuit. No resistor, transistor, comparator or control supply is selected.

Expected and actual candidate/live electrical and copper deltas are zero. [VSERVO-01](../vservo_reservoir/README.md) remains the electrical candidate; [POWER-DOC-01](../power_sheet_polish/README.md) remains its readable native presentation. Both converters, C11 identity/lands, ACT-01 source populations and disabled missing qualifications are preserved. Native tools were not rerun. All 532 captured inputs remain unchanged.

## Why this cell, and where it connects

The captured native VSERVO node contains C11.1, C12.1, D4.1, D9.1, J3.2 and TP4.1. D4 feeds from the board 5 V buck; D9 feeds from BEC_IN. BEC_ONLY fits D9 and omits D4; ONBOARD fits D4 and omits D9; the master marks both DNP. No released population or source-return path is created here. The proposed shunt is downstream of the exclusive source diode, across the local reservoir, so both populations need separate source/fault envelopes.

A controlled resistor/FET brake is a documented energy-dissipation approach. The proposed firmware-independent control is this project's requirement, not a copied reference design. The cited examples do not establish the unidentified servo's returned energy, transfer propulsion energy through its BEC, or supply applicable component values. [TI SLVAF66 §§7.1.2–7.1.3](https://www.ti.com/lit/an/slvaf66/slvaf66.pdf), [MPS AN132 Fig.4 and Appendix 2](https://media.monolithicpower.com/document/AN132_r1.1.pdf).

## Threshold and response contract

Use terminal-referred worst-case bounds over temperature, supply, tolerances and sense/reference errors. `normal_max` includes the worst sensed normal source voltage, feed ripple and signed sensing disturbance. `noise_pp` bounds the disturbance between switching decisions. Separate rising and falling thresholds reduce chatter, but only when the complete tolerance/noise window is positive. [TI SBOA219B, design notes](https://www.ti.com/lit/pdf/sboa219).

| Necessary condition | Purpose |
|---|---|
| `off_min > normal_max` | Allow release above the highest normal sensed rail; avoid a shunt fighting a healthy source |
| `on_min > off_max + noise_pp` | Preserve hysteresis despite bounded disturbance |
| `on_max + remaining_rise < allowed_local_max` | Reserve positive upper-voltage margin at full sink response |
| `off_min - further_fall > allowed_local_min` | Bound lower-voltage excursion through turn-off delay and recovery; not calculated without evidence |

`remaining_rise` includes the entire sense/filter, comparator, driver and gate-enhancement delay, loaded behavior, ESR and local inductance. Comparator propagation measured at a particular overdrive or 50% output is not the total delay to useful sink current. `further_fall` separately covers continued discharge during turn-off delay, parasitics and recovery; a positive upper margin does not qualify undervoltage behavior. Local and remote limits are distinct. Threshold equality grants no design margin.

## Current authority before nominal resistance

Let `Iexcess` bound the simultaneous positive current into the local capacitor node after justified load/return credits. Include every still-conducting source and the J3 return contribution. Do not assume a diode is blocking at the falling threshold without source/diode I–V evidence.

At the lowest release voltage, require `off_min / (Rnom*(1+tolerance) + Ron_max) > Iexcess`. Otherwise a resistor sized only at the upper ceiling may never discharge to release. Separately bound branch peak current by `rail_max / (Rnom*(1-tolerance) + Ron_min) < Ipath_allocation`.

These inequalities define a strict **necessary nominal resistance interval**, not a component choice. The allocated branch-current ceiling is not a transistor rating or SOA proof. The assumed rail maximum must itself be established; it cannot be inferred from this unimplemented clamp. `Ron` bounds apply only with sufficient gate drive over the stated temperature/supply conditions. Gate threshold voltage is not proof of full enhancement. [Nexperia AN11158 §§2.5–2.6.1](https://assets.nexperia.com/documents/application-note/AN11158.pdf).

The illustrative 8.2 ohm branch in the explorer is a calculation input, not a selected part. Its conservative resistor instantaneous-power bound is almost 3.9 W even though a separate small repeated-event example might average milliwatts. Pulse rating, repeated energy, hot-start temperature and sustained fault loading need distinct evidence. Fully-on FET loss excludes switching overlap and partial-drive linear operation; check the full VDS/ID/time trajectory and hot SOA, not only Rds(on) or mean watts. [Nexperia AN50006 §§4–6](https://assets.nexperia.com/documents/application-note/AN50006.pdf).

## Startup, disabled operation and faults

The controller's supply must be available and its output defined whenever energy can arrive, including MCU-off, disarmed and externally fed states. A gate pulldown provides an intended discharge path with high-impedance drive. It cannot override a powered driver stuck high, an active startup glitch or unbounded Miller injection. POR, UVLO, input behavior and recovery are device-specific and remain unimplemented. [TI comparator startup/POR lesson](https://www.ti.com/video/5465094248001).

| State or fault | Required evidence / disposition |
|---|---|
| Normal rail | Switch stays off; bounded leakage and threshold/noise margin |
| Returned-energy event | Valid control power, full sink authority, bounded turn-on/off dynamics and receiver terminal voltages |
| MCU off or PWM disarmed | Protection remains autonomous where exposure exists; disarm does not erase stored or externally returned energy |
| Control supply ramp, UVLO or restart | No protection credit before guaranteed behavior; cover the gap with independently qualified exposure prevention or protection, including stored energy |
| Open resistor/switch/path | No controlled sink; independently prevent exposure or provide an accepted backup |
| Shorted switch or stuck-high drive | Resistor becomes a continuous load; bound source/capacitor current, resistor temperature and fault duration/clearing energy |
| Shorted resistor | Intended current limit is lost; separately assess switch, feed, traces and fault interruption |
| Sense/reference fault | Classify actual resulting off/on/chatter behavior; do not presume a safe off state |
| Negative rail, ground loss or remote ringing | Separate reverse-voltage and remote-terminal contract; positive local shunt is insufficient |

The proposed NMOS body diode can conduct from GND through the device and brake resistor toward a negative VSERVO. This topology inference is neither reverse isolation nor a qualified negative clamp. Polarized C11's retained reverse-voltage restriction and actual receiver limits still require a separate solution. A lost ground can also invalidate sensing and drive. [Nexperia AN11158 §2.2](https://assets.nexperia.com/documents/application-note/AN11158.pdf), [retained VSERVO-02 lower-bound review](../vservo_transients/README.md).

No new actuator permission is implemented. Protection readiness would be a separate prerequisite where needed; it cannot establish receiver readiness or arm the actuator. Existing unimplemented permissions stay disabled, and fault recovery must not bypass the retained deliberate-rearm contract.

## Energy, thermal evidence and future verification

Maintain a declared local control volume and integrate every signed port once. The maximum cumulative energy excursion determines peak capacitor energy; later load absorption cannot hide an earlier peak. Repeated events require restoration between events, with no repeated credit for the same finite capacitor storage. Retain [VSERVO-02's accounting](../vservo_transients/RESULTS.md).

Before choosing parts, supply a bounded waveform and hot-start condition for resistor pulse energy, switch transition/SOA, repeated thermal cycling and continuous operation. Fault-on duration is not automatically finite: the upstream fuse or current limit must demonstrably interrupt the actual fault, or the branch must withstand it continuously. An external BEC and the on-board converter need different source models. The 6S input feed remains a separate open requirement.

Future verification must capture local capacitor voltage, remote supply/return voltage, shunt current, gate drive and control-supply state with defined bandwidth/loading. Include turn-on, turn-off undershoot, supply ramp/dropout, repeated bursts and declared fault states. Freeze actual source/receiver/harness identities, initial temperature, thresholds and allowed waveforms before acceptance. No hardware measurement, simulation waveform, assembly, ordering or flashing result is claimed here.

## Immutable viewer replay

The previous POWER-DOC-01 check was reproduced failing after the shared viewer builder changed: its browser record correctly pinned that older builder. The [historical Power replay](replay_power_viewer.py) now verifies the unchanged packet and deterministic outputs against the exact captured template and an archived builder from commit 9b9d087. All other browser inputs retain their original paths and hashes. Historical checking does not rerun the old browser or native tools.

This packet captures both its own PM template and builder for later immutable replay. The current-viewer registry separately checks those inputs against the live files. Future packets must preserve archived evidence instead of refreshing historical hashes.

## Next smallest independent task and restart

The functional shunt specification is now reviewable; actual receiver/source envelopes still block device selection and native insertion. **Next independent circuit packet: review full 6S battery/current sensing and ADC range/protection using the preserved Power sheet.** Establish divider, current-amplifier common-mode/output and MCU pin limits before an isolated amendment. Keep both converters, ACT-01 exclusive populations, C11 lands and the separate IMU2 lineage intact. Leakage/damping and full input-feed gates remain open.

V1 inspection, V2 vehicle nodes and the future voice/text/location handheld remain distinct. Measure voice/RC coexistence before handheld hardware selection. Do not repeatedly ask for unanswered receiver identities.

Read [review notes](review_notes.json), [input hashes](input_manifest.json), [browser evidence](viewer_check.json) and [packet manifest](packet_manifest.json) with the latest handoff and FILE_OWNERSHIP.md. Preserve both unrelated local tool edits. Portable restart:

```text
python -B reviews/codex/vservo_shunt_spec/test_model.py
python -B reviews/codex/vservo_shunt_spec/build_packet.py --check
python -B reviews/codex/vservo_shunt_spec/test_replay_power_viewer.py
python -B reviews/codex/vservo_shunt_spec/replay_power_viewer.py --check
python -B tools/quality/check_viewer_replay.py --check
python -B tools/quality/check_publication.py
node pm/tools/validate.mjs
```
