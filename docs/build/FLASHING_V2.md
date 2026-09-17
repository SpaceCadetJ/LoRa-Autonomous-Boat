# V2: firmware readiness and staged bring-up

**There is no qualified V2 firmware image.** A separate [Stage A diagnostic](../../firmware_v2/README.md) now builds in `firmware_v2/`, with board identity, heartbeat and inactive actuator signals. It has not been run on hardware. [V2_FIRMWARE_PLAN.md](../../firmware/V2_FIRMWARE_PLAN.md) is a design plan, not an executable implementation. The reconstructed V1 ELF builds, but is **not approved for V2**. No V2 flash, boot, USB, radio, watchdog or actuator test has been run.

This page defines the connection and acceptance procedure for the existing Stage A diagnostic and later reviewed V2 images. Hardware power prerequisites and image review still apply before any programming or execution. Use each candidate's own manifest and image; the V1 image is not a substitute.

## Current pin contract to reconcile before code generation

The current hardware source is [v2_design.py](../../hardware/kicad_v2/tools/v2_design.py); compare it with the generated schematic, routed PCB and final assembly revision before using this table. The source is being developed and is not itself manufacturing approval.

| Function | V2 source connection | Firmware consequence |
|---|---|---|
| ESC | PC6/TIM3_CH1 → level shifter → J2 pin 1 | Start safe; verify both MCU and connector waveform |
| Servo | PA8/TIM1_CH1 → level shifter → J3 pin 1 | Start neutral only at the approved stage |
| Radio | PA0 TX, PA1 RX; reset PA3 | Acknowledged configuration, reset recovery, model/baud confirmation |
| GNSS | PC10 TX, PC11 RX; PPS PB0 | Dedicated UART; PB0 **input**, not V1's driven-low GPIO |
| IMU | PB6 SCL, PB7 SDA; interrupt PB5 | Driver and measured sensor identification required |
| Battery ADC | PA2; R31 47 kΩ / R32 6.8 kΩ in current source | Use actual divider/calibration, not the older 30 kΩ / 10 kΩ plan |
| Current ADC | PA4, current-sense output | Scale from actual gain/shunt and calibration |
| USB | PA11 D− / PA12 D+; divided VBUS at PA9 | Resolve VBUS-sense handling with selected USB stack; USB/CAN pin conflict |
| Link/fix/fault LEDs | PC1 / PC2 / PC3 | Power LED is hardware-wired, not a PC0 firmware LED |
| BOOT0 | U1-60 → R16 pull-down | No boot jumper appears in current net source; do not assume one exists |

The V2 plan and requirements still disagree in places: CRC-8 versus CRC-16, packet encoding/version flags, battery-divider values, and USB/console assumptions must be reconciled before implementation. Binary data through a line-oriented AT interface requires an explicit framing/escaping contract and tests. Treat promised latency and state transitions as requirements until measured.

## Debug connection

V2 keeps the STM32F446RET6 and uses **J7** for SWD. Electrical numbering below is from the current hardware generator. Verify the footprint, pin-1 mark, cable orientation and final schematic on the actual assembly; never infer physical position from this table alone.

| J7 pin | Signal | MCU package pin | Use |
|---|---|---|---|
| 1 | +3V3 | VDD rail | Target voltage reference |
| 2 | SWDIO | U1-46 / PA13 | Probe SWDIO |
| 3 | GND | Ground | Probe ground |
| 4 | SWCLK | U1-49 / PA14 | Probe SWCLK |
| 5 | GND | Ground | Ground |
| 6 | SWO | U1-55 / PB3 | Optional trace |
| 7 | NC | — | Leave open |
| 8 | NC | — | Leave open; differs from V1's TDI |
| 9 | GND | Ground | Ground |
| 10 | NRST | U1-7 | Probe reset |

Use the [V1 procedure](FLASHING_V1.md) sections 2–4 for adapter mapping, reference-voltage checks, programmer installation, serial selection and two main-Flash backups, substituting **J7/U1 and a `bench_v2_...` record folder**. Do not use its V1 image path. Even a nominally blank board gets an identity/option-byte record. Keep ESC/servo harnesses and unnecessary modules disconnected. Validate V2 assembly power rails first; +3V3 on debug pin 1 is not permission to power the board from a probe.

USB-C is not currently a tested flashing path. A physical USB connector does not establish a working CDC application, ROM-DFU entry route, or power path. The current source places VBUS on the connector/ESD/sense network; it must not be assumed to power the board's main rails. Use SWD for initial bring-up, with the validated board power source.

## Images to develop, in order

| Stage | Deliverable | Required evidence before the next stage |
|---|---|---|
| A: board identity | Implemented CMSIS diagnostic with preserved ST startup/linker inputs and a checked V2 pin contract; actuator pins remain inactive. No V2 `.ioc` exists; CubeMX integration is future work. | Build evidence exists; image/revision review, SWD connect/reset and measured rails remain required before hardware acceptance |
| B: safe outputs | PWM startup, disarmed state, timeout supervisor, watchdog and reset handling | Instrument captures at MCU and connector; safe first pulse, boot/brownout/reset, timeout and re-arm tests |
| C: radio/control | Radio driver + common handset protocol and parser tests | Module/version/settings readback; malformed/old/wrong-sender packets rejected; measured command age and link-loss behavior |
| D: navigation/power | GNSS validity/age, PPS, IMU, ADC calibration | Sensor disconnect/stale-data behavior; no traffic mixed into GNSS; voltage/current sweep |
| E: multifunction profiles | Explicit RC, telemetry and handheld messaging profiles | Profile identity on screen/log; RC scheduling protected from message bursts; reconnect, mode-switch and rollback tests |

The first image should prove pins, clocks and diagnostics while holding actuator outputs inactive. Defer autonomous navigation and unrestricted messaging until the control supervisor and firmware/hardware contract are tested. The next implementation must specify its exact radio-module model, supported AT firmware, antenna/band and regional operating profile; this document does not claim range or control latency.

## Programming once a V2 candidate is reviewed

1. Complete the staged image's build manifest and review source revision, V2 board revision, pin map, option-byte policy, radio profile and startup output behavior. Have a rollback/known diagnostic image and verify its hash.
2. Follow the two-backup/read-protection procedure in [V1 flashing](FLASHING_V1.md) for the actual V2 MCU. Record option bytes separately; main-Flash backup does not include them.
3. In CubeProgrammer choose SWD, the recorded probe serial, 1000 kHz, Under Reset and Hardware Reset. Open the **V2 candidate ELF/HEX** named in its manifest. Check addresses against its V2 Flash linker before programming. Select verify-after-programming; leave automatic execution disabled. Program and require a successful verification log.
4. Read back the exact BIN length from the manifest's load address and compare SHA-256 against that BIN. This assumes a contiguous Flash image as explicitly declared by that build; do not reuse `0x08000000` blindly if a later V2 bootloader changes the memory layout.
5. Release reset deliberately, with loads physically disconnected and probes already attached. Measure startup waveform and supply current. Archive programmer, readback and scope evidence with the manifest.
6. If verification or first execution fails, leave loads disconnected. Check supply/reset/debug wiring and candidate identity, then reconnect under reset. Restore only the verified image for that board with verification/readback; do not change protection or erase-all as a connectivity fix.

The CLI equivalents are the connect/backup/write/verify/readback sequence in V1, substituting the V2 candidate and its manifest addresses. The [Stage A guide](../../firmware_v2/README.md) names its existing build outputs. A successful Stage A build does not release the present assembly for power or execution; complete the electrical corrections, candidate review and bench prerequisites first.

## Acceptance record and release gate

For stages B/C, test without actuators: power cycling, reset during radio traffic, brownout, watchdog starvation, loss of handset, stale/duplicate commands, malformed frames, wrong sender, radio reset, and reconnect at nonzero throttle. Record measured response time, expected state, both output widths and any unintended startup pulse. The proposed 1 s timeout/20 ms response and watchdog limits must be reconciled with the final requirements and measured; they are not existing behavior.

Handheld communication needs its own data-delivery, pairing/authentication, congestion, UI, power-management and regional-radio requirements. Do not let a messaging mode inherit the authority to arm an RC actuator implicitly. CRC detects transmission errors; it does not authenticate a sender.

Every release record must state board revision, assembly/rework, firmware revision and SHA-256, compiler and build recipe, protocol/profile version, calibration, programmer/probe, backup/rollback identity and passed bench cases. Until that evidence exists, label every V2 image **development / loads disconnected**.

Smallest next step: resolve the electrical power/IMU/interface holds, review the existing Stage A diagnostic and record its bench acceptance before implementing Stage B. Existing V1 sources stay preserved.
