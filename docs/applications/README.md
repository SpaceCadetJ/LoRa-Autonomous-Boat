# Application handbook

Use this project as a documented route from the existing boat controller to a reusable vehicle and communications platform. Choose an application below, identify its hardware and software revision, then follow its preparation, operating sequence and acceptance checks.

**The current release is an engineering review edition.** V1 has a reproducible preserved-source firmware build and an instrument-only bench procedure. V2 is a developing vehicle board. Powered vehicle operation and the handheld have not been qualified. A drawing, compiled image or passing software test alone does not release a physical application.

## Choose an application

| Application | Available now | Required before normal operation | Guide |
|---|---|---|---|
| Existing V1 boat controller | Inspect the circuit, preserve firmware, reproduce the build and characterize unloaded signals | Board-specific electrical corrections; corrected control supervisor; measured output and fault tests | [V1 bench and legacy RC](V1_BENCH.md) |
| Updated V2 boat controller | Review power/wiring and build the Stage A identity diagnostic | Accepted board revision, operational V2 firmware and successful first-article tests | [V2 boat](V2_BOAT.md) |
| Rover with one ESC and steering servo | Plan reuse of the two vehicle outputs and document the selected motor-controller behavior | Rover profile, verified neutral/braking behavior and measured tests | [Rover adaptation](ROVER.md) |
| Remote position / telemetry node | Inspect V1 position-message behavior and prepare an unloaded receiver demonstration | Fix freshness, message identity, bounded reporting and receiver implementation | [Position and telemetry](TELEMETRY.md) |
| Handheld communicator | Develop the voice, text and location specification and coexistence test | Two endpoints, firmware, audio hardware, delivery behavior and measured radio budget | [Voice, text and location](HANDHELD.md) |

Each guide distinguishes **source behavior**, **work that can be performed now**, and **operation after release**. “After release” is a procedure to implement and test, not a hidden existing command or feature. Follow the linked current engineering evidence when a design changes; record any disagreement before connecting hardware.

## Start with a complete build identity

Create an [acceptance record](ACCEPTANCE_RECORD.md) for each unit. Record the board revision and serial, population option, harness labels, firmware commit and SHA-256, radio/module identity, protocol version, calibration and test results. Keep photographs and measured traces with that record. A V1 image and V2 circuit must never be paired just because both use an STM32F446.

Use the [ordering guide](../build/ORDERING.md) for candidate BOM imports and held parts, then the [V1](../build/ASSEMBLY_V1.md) or [V2](../build/ASSEMBLY_V2.md) assembly procedure. The purchasing exports are partial review lists. Antennas, fitted radio/GNSS modules, connectors and cable mates, enclosure, power source, programmer and application loads also need exact identities. Do not infer a complete kit from the controller BOM.

The [V2 electrical review](../../reviews/codex/design_completion/electrical/README.md) identifies unresolved IMU voltage-domain and power/interface component-limit conflicts. Resolve these against the actual assembly before powering it, including for the new [Stage A diagnostic](../../firmware_v2/README.md). Its low MCU output state does not repair the circuit or qualify an external actuator signal.

## V1 and V2 are different wiring contracts

| Function | Preserved V1 | Current V2 source intent |
|---|---|---|
| Motor-command output | PC6/TIM3_CH1 → **STEERINGSERVO1 pin 2** | PC6/TIM3_CH1 → level shifter → **J2 pin 1 (ESC)** |
| Steering output | PA8/TIM1_CH1 → **SPEEDCONTROLLER1 pin 2** | PA8/TIM1_CH1 → level shifter → **J3 pin 1 (SERVO)** |
| Actuator power | Both header pin-1 connections are **+3V3**; no assumed BEC compatibility | Separate actuator rail and power-source choices; qualify the actual population |
| Radio | UART4 PA0 TX / PA1 RX, 115200 8N1; PA3 reset is unconfigured | Same UART pins with acknowledged setup and reset recovery to implement |
| GNSS | USART3 PC10 TX / PC11 RX, 9600 8N1; debug shares TX; PB0 drives header pin 3 LOW | Dedicated GNSS UART and PB0 as PPS input; baud belongs to the frozen module/profile |
| Programming | JTAG1, verified electrical SWD pin mapping | J7, reviewed V2-specific image required |

This is an electrical comparison, **not a cable-face or left-to-right view**. Check physical pin 1, viewing side and mating connector independently. The [V1 atlas](../atlas/README.md) and [V2 programming contract](../build/FLASHING_V2.md) give the source detail. Hardware source, schematic, PCB, harness and firmware must agree at the same revision.

## What “finished” means for an application

An application is ready when its exact assembly can be ordered, assembled, programmed, operated and recovered by another person using the release package, and the named acceptance cases have measured passing results. Release requires:

1. Accepted electrical and PCB review, complete selected BOM, final manufacturing files and assembly orientation record.
2. Reproducible board-specific firmware and matching peer software, with backup/restore instructions and a versioned interface contract.
3. Measured startup, shutdown, reset, loss-of-link, malformed-message, power and application tests on the actual unit.
4. Operating limits, controls, fault indications and recovery steps demonstrated to match this handbook.

The [review workflow](../build/REVIEW_WORKFLOW.md) handles source and evidence checks; the [acceptance record](ACCEPTANCE_RECORD.md) handles physical results. Failed or unperformed cases remain open. The [application index](applications.json) exposes the same status and next task to the viewer and portfolio tooling.

## Current design gate: IMU placement

The [placement review](../../reviews/codex/imu_placement/README.md) finds physical courtyard space but 136 native copper/mask/clearance errors on the isolated study. This does not advance any application to powered acceptance. Live board, purchasing and Stage A contracts are unchanged; resolve the bias-filter amendment and 6S power envelope before final routing and application bring-up.
