# V2: boat control and navigation

**Current use: wiring review and staged development.** V2 is intended to operate one ESC and one steering servo with local control supervision, power monitoring and positioning. A separate Stage A identity diagnostic now has source and a build recipe; operational firmware and a completed physical acceptance record remain required. The sequence below defines the operator behavior that the implementation must earn.

## Build and wire the vehicle profile

Prepare an accepted V2 board/population, selected ESC and motor, steering servo/linkage, separate approved actuator power arrangement, identified radio and antenna, GNSS, enclosure/harness, ST-LINK and a matched controller endpoint. Obtain exact parts from the [ordering guide](../build/ORDERING.md) and complete its held/external parts; the controller BOM does not include the entire vessel.

| Interface | Current source intent | Required confirmation |
|---|---|---|
| ESC signal | PC6 → level shifter → J2 pin 1 | Signal polarity, idle pulse and ground against actual ESC |
| Rudder signal | PA8 → level shifter → J3 pin 1 | Center, travel, direction and ground against actual servo/linkage |
| Radio | PA0 TX / PA1 RX, reset PA3 | Exact socket/module mating map, voltage, antenna and accepted profile |
| GNSS / PPS | PC10 TX / PC11 RX; PB0 input | Exact selected module pinout, supply, UART configuration and PPS level |
| SWD | J7 | Electrical pin map and adapter view in [V2 flashing](../build/FLASHING_V2.md) |
| Power | Separate logic and actuator supply design | Frozen BEC/on-board-converter population and measured back-feed behavior |

The main propulsion current is intended to go directly through its rated battery/ESC wiring, not the board's logic feed. Do not join BEC and on-board servo supplies until the selected power tree is verified. Current design defaults are not electrical qualification for every battery, ESC or servo.

Follow [V2 assembly](../build/ASSEMBLY_V2.md) through unpowered and rail checks. Begin firmware bring-up through SWD with actuators and unnecessary modules absent. A USB connector does not establish USB power, a console or a supported flashing route. Do not load the V1 image: it drives PB0 as an output and implements the wrong safety/interface contract for this use.

The [electrical hold list](../../reviews/codex/design_completion/electrical/README.md) includes incompatible IMU interface voltage, actuator-buffer supply limits, input surge coordination, converter-enable voltage and current-sense/output-stage issues. The existing 2S–6S requirement is not an accepted input envelope. Read the exact findings and correction proposals before selecting a physical power test; this guide does not silently substitute a smaller battery range.

## Stage A: diagnostic work available now

From the repository root, with the prerequisites in [the diagnostic guide](../../firmware_v2/README.md):

```text
python firmware_v2/tools/build.py check
python firmware_v2/tools/build.py build
```

Use a new output directory for another build, as that guide specifies. The default successful build produces `firmware_v2/build/stage_a/v2_stage_a_unqualified.elf`, `.hex`, `.bin` and `manifest.json`. Inspect the manifest and exact image hash; these names identify a diagnostic, not a vehicle-control release.

The recorded [Stage A build evidence](../../firmware_v2/evidence/stage_a_build.json) reports a successful unqualified build. This is software evidence; no board has been flashed or accepted through this guide.

After electrical corrections and approved SWD programming, inspect `v2_diagnostic` through the matching ELF symbols. PC1 is expected to toggle every nominal 500 ms, PC3 to remain on as the diagnostic marker, and PC6/PA8 to remain low with no PWM. Observe both MCU and header outputs with loads absent; record rails, reset flags, device ID and timing. These are expected observations, not completed hardware tests. The diagnostic initializes no radio, USB, GNSS, IMU or control supervisor, and supplies no arm or mode command.

## Startup and use after release

1. With propulsion isolated, inspect the vessel, harness, antenna and power source. Match the firmware/application profile to this boat and its calibration. Select the intended peer with throttle at the recorded idle position.
2. Start the vehicle on its approved power arrangement. It must report **Disarmed**, the correct profile/peer, power health and reset cause before arming is possible. Observe fault/link indications defined by the released UI.
3. Confirm fresh control reception and correct steering response under the approved pre-run check. A GNSS fix is required for a navigation mode; it must not be presented as a prerequisite for manual RC unless that is the released policy.
4. Arm explicitly only when the physical operating area and vehicle are ready and the selected ESC's idle requirements are met. Arming must not happen merely because the radio reconnects.
5. Use manual throttle/rudder first. Enable heading hold or waypoint operation only after their separate sensor, calibration, manual-override and fault cases pass. The project name does not establish implemented autonomy.
6. Watch link age, power warnings and mode/fault state. A link or control fault must invoke the locally defined safe output without depending on a successful return transmission.

These are required behaviors, not existing `arm`, `stat` or `cfg` shell commands. Such commands in the older firmware plan are proposals. Actual button actions and commands belong here only after matching peer software exists.

## Shutdown after release

Command the approved idle state, disarm explicitly and confirm the local disarmed indication/output. Isolate propulsion and actuator power using the accepted hardware procedure, then turn off the vehicle and controller. Save faults and mission logs before any erase/update. Returning the joystick to center is not proof of disarm, and turning off the transmitter first must not be the normal stop action.

## Troubleshooting and acceptance

| Symptom | Required diagnosis / response |
|---|---|
| Cannot arm | Show an actionable reason: stale peer, non-idle input, incompatible profile, power fault or failed self-check; do not bypass it |
| Correct MCU pulse, wrong connector pulse | Inspect level-shifter supply, output polarity and selected actuator rail |
| Resets when servo moves | Capture rail dip/current, ground return and source contention before further operation |
| Position freezes | Mark fix stale and leave navigation under the defined recovery policy; do not hold an old waypoint command indefinitely |
| Reconnect restores motion | Release failure: invalidate old session/setpoint and require explicit re-arm |

Before release, record scope traces for first pulse, reset/brownout, disarm, radio loss, wrong sender, malformed/duplicate/stale packets and watchdog recovery. Measure timeout from the **last accepted control packet**, not from the last byte of any traffic. Record the actual safe pulse for the selected ESC; the proposed 1000/1500 microsecond motor/servo values are not universal equipment settings.

Navigation additionally needs fix-age, sensor loss, calibration, manual override and bounded path testing. The smallest next task is to resolve the electrical holds, validate Stage A on the accepted assembly and freeze the [control protocol contract](../build/FLASHING_V2.md) before adding the Stage B supervisor and PWM. Keep outputs inactive until the applicable unloaded checks pass.

References: [requirements](../V2_REQUIREMENTS.md), [firmware plan](../../firmware/V2_FIRMWARE_PLAN.md), [latest project handoff](../../HANDOFF.md), [record template](ACCEPTANCE_RECORD.md).
