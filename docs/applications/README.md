# Application handbook

The latest V2 [ACT-12 connector fault contract](../../reviews/codex/connector_fault_contract/README.md) and [interactive explorer](../../reviews/codex/connector_fault_contract/index.html) distinguish an inactive driver, connector voltage, receiver pulse/loss behavior and actual actuator response. The future unloaded measurement plan is preparation only; exact ESC/BEC/servo evidence remains missing. V1 procedures and V2 wiring, flashing, assembly and powered-application release remain unchanged. Next independent circuit review: C11 identity and VSERVO reservoir/transients. Older checkpoint tasks below are historical.

The latest [ACT-11 supply-shutdown review](../../reviews/codex/vcca_shutdown/README.md) shows that translator power cycling alone does not reset the existing READY latch. The proposed switch also lacks an accepted fast shutdown bound. Wiring, assembly, flashing and powered-application release remain unchanged. Next define the connector-level fault acceptance contract, including fresh acknowledgement after recovery. Older checkpoint tasks below are historical.

The latest [ACT-10 circuit review](../../reviews/codex/oe_isolation/README.md) holds the proposed enable-isolation switch: R40 discharge has a tight capacitance budget, and continuous brownout isolation is unqualified. Wiring, assembly, flashing and powered-application release do not change. Next assess the translator supply-isolation alternative before any native amendment. Older checkpoint tasks below are historical.


Use this project as a documented route from the existing boat controller to a reusable vehicle and communications platform. Choose an application below, identify its hardware and software revision, then follow its preparation, operating sequence and acceptance checks.

**The current release is an engineering review edition.** V1 has a reproducible preserved-source firmware build and an instrument-only bench procedure. V2 is a developing vehicle board. Powered vehicle operation and the handheld have not been qualified. A drawing, compiled image or passing software test alone does not release a physical application.

## Current V2 design checkpoint

[ACT-09](../../reviews/codex/observer_retention/README.md) adds a [startup/fault sequence explorer](../../reviews/codex/observer_retention/index.html) and a proposed observer-island handover contract. These are requested states, not measured output waveforms. A fresh acknowledgement follows recovery; held ACK and power bounce cannot grant permission in the model. Physical output isolation during brownout remains unimplemented, so wiring, flashing and powered-application acceptance remain unchanged. The next task is the exact U14-to-translator permission boundary; older checkpoint tasks below are historical.

[ACT-08](../../reviews/codex/observer_power/README.md) now defines the reference load, proposed input resistors and [power-state calculation limits](../../reviews/codex/observer_power/RESULTS.md). Passive discharge cannot establish safe shutdown while unknown current continues feeding the node. The next task is a retained-low observer-valid interface and an explicit reference shutdown/injection path; the source-test headroom boundary is 3.005 V. The calculations do not change wiring, flashing, assembly or application release. Earlier next-task wording below is historical; ACT-04 remains the latest native candidate and missing qualifications remain disabled.

[ACT-07](../../reviews/codex/observation_3v3/README.md) adds a concrete 3.3 V comparator/reference allocation and [power/waveform acceptance worksheet](../../reviews/codex/observation_3v3/ACCEPTANCE.md). Positive static margins remain conditional; the proposed 400 ns response budget fails the 0.1 V/us overvoltage example. Reference startup and observer backfeed are unresolved. This changes design evidence, not wiring, flashing or application release. Next: close those source and power-state conditions before native insertion.

[ACT-06](../../reviews/codex/supervisor_comparison/README.md) narrows the local-supervision design with tested divider and integrated-window comparisons. Initial static fits do not establish fault response across temperature or power loss. The next subcell is 3.3 V observation; receiver/watchdog permission and powered vehicle operation remain held. See the [calculated margins](../../reviews/codex/supervisor_comparison/RESULTS.md).

The [ACT-05 supply-qualification screen](../../reviews/codex/rail_qualification/README.md) now documents voltage/recovery conflicts and detector/edge limits before part selection. Explore the [calculated rail intervals](../../reviews/codex/rail_qualification/index.html). No circuit or application is released; local rail validity does not establish remote receiver readiness. Next is a bounded window/reset/edge comparison, with all unimplemented permissions disabled.

[ACT-04's native latch and signal path](../../reviews/codex/actuator_latch/README.md) now separate PC4 from translator OE and preserve both converters and source populations. Its exact two-pin delta passes native comparison; missing qualification and ACK sources remain default low. Receiver sensing, watchdog and startup/timing qualification remain open. ACK while armed disables in ACT-04; the [older ACT-03 demonstrator](../../reviews/codex/actuator_interlock/index.html) is not an exact circuit model. Use the [receiver worksheet](../../reviews/codex/actuator_interlock/RECEIVER_ACCEPTANCE.md) to record actual loads. Stage A remains the only V2 diagnostic; no powered application is released. The chronological checkpoints below preserve earlier decisions.

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

## IMU2 circuit amendment

The [current IMU2 candidate](../../reviews/codex/imu_bias_filter/README.md) implements the translator bias filter with a verified two-pin delta. It remains unrouted and does not change application acceptance, physical flashing steps, live BOM or the Stage A contract. The next gate is the 6S protection/power-package envelope followed by reviewed routing.

## 6S power review — 2026-10-12

The [power envelope and package review](../../reviews/codex/power_envelope/README.md) retains 7–25.2 V / 2S–6S intent and finds C1/F1 package conflicts plus D2 value drift. Current ordering holds include these parts; live CAD and application readiness are unchanged. Use the new topology/load-budget task before IMU routing or powered bring-up. V1 inspection and future handheld voice/text/location remain separate; voice/RC coexistence is still unmeasured.

## Load planning before application bring-up — 2026-10-12

Use the [interactive power budget](../../reviews/codex/power_topology/load_budget.html) to distinguish external-BEC servo power from on-board servo demand. The [architecture recommendation](../../reviews/codex/power_topology/README.md) retains the 2S–6S and optional on-board actuator requirements. A 1 A board-feed goal cannot support the stated 3.3 V/1.2 A and 5 V/2 A capacities simultaneously at 7 V, even without losses. The first input-stage study uses external BEC for load planning; the higher-load variant remains open. No wiring or powered-use instruction is released by this calculation.

## Input-stage circuit candidate — 2026-10-12

[INPUT-A1](../../reviews/codex/input_stage/README.md) now provides a wired, native-checked input boundary with exact held candidate parts. It preserves 2S–6S and starts with the external-BEC load variant. The series diode adds loss excluded from the earlier calculator. This is not a powered-use revision: discharged-output reverse leakage needs a circuit disposition, and both buck cells, sensing/ADC, buffer and IMU corrections still need integration. Live ordering and flashing procedures remain gated.

## Reversal and startup gate — 2026-10-12

The [reverse-leakage review](../../reviews/codex/reverse_leakage/README.md) confirms that the polarized INPUT-A1 reservoir cannot be accepted for a negative rail, even when a converter's absolute limit is respected. [Interactive cases](../../reviews/codex/reverse_leakage/index.html) also distinguish ADC conversion limits from digital pin limits during startup. No application wiring, ordering or flashing gate is cleared. Next circuit work must select the reservoir/buck bypass and close the full leakage and power-sequencing budget.


## Reservoir and local bypass specification — 2026-10-12

The [capacitor network](../../reviews/codex/input_capacitors/README.md) separates input storage from each converter’s local bypass and provides a reviewed TDK footprint proposal. Its [interactive review](../../reviews/codex/input_capacitors/index.html) shows minimum effective-capacitance requirements and ideal source-wiring sensitivity. No powered-use, ordering, assembly or flashing gate is cleared; next is the isolated 3.3 V converter-cell design with qualification holds retained.

## 3.3 V converter checkpoint — BUCK33-A1

The [editable first converter](../../reviews/codex/buck_3v3/README.md) supplies an exact part/pin proposal for the V2 logic rail. Native validation preserves all 330 connections outside the converter boundary. Its calculations and package evidence remain separate from powered use. The PCB, ordering and application flashing procedures remain unchanged; V2 still has only the separate Stage A diagnostic. Next is the 5 V converter and its 7 V simultaneous-load budget, followed by unresolved input, ADC/buffer and combined IMU2 integration. The handheld voice/text/location requirement still needs measured voice/RC coexistence before hardware selection.

## 5 V converter and actuator-supply checkpoint — BUCK5-A1

The [5 V guide](../../reviews/codex/buck_5v/README.md) now separates converter capability from whole-board feed capacity. Its 7 V battery model needs about 2.66 A for both full nominal rail loads; the current feed does not support an accepted full-load claim. External-BEC and on-board variants require explicit population and voltage contracts. D4/D9 have an SMC/SMA identity mismatch, and U4/U5 remain on the unqualified VSERVO rail. Existing ordering/assembly/power/flashing holds remain. Next is the buffer/OR-ing correction, preserving both converter candidates and 6S. No new operational firmware or physical test is provided.

## Actuator supply checkpoint - ACT-01

The [buffer and source-variant guide](../../reviews/codex/actuator_supply/README.md) provides connector roles and two mutually exclusive proposed diode populations. Buffer VCC comes from the onboard 5 V converter in both variants; BEC-only actuator energy does not mean BEC-powered logic. Both positions default DNP in the review master. Native checks establish the four-pin correction only; default-disabled enable, startup/off-state and actual actuator qualification remain next. C11 identity is newly on hold, leaving 68 candidate / 39 held references. No powered-use or flashing procedure is released by this candidate.

## ACT-02 signal-enable checkpoint — 2026-10-12

The [annotated actuator candidate and sequencing guide](../../reviews/codex/actuator_enable/README.md) adds a dual-supply translator, default-low PC4 enable and a proposed firmware arm/disarm contract. Native checks preserve 383 outside-boundary pins and both converter sheets; 41 mutation tests pass. This is isolated schematic evidence: Stage A does not drive PC4, live firmware/PCB and purchasing exports are unchanged, and no application is released for powered actuator use. Next: hardware arm interlock and receiver-power observation, then the remaining 6S, C11/transient, ADC and combined IMU2 gates. Keep V1 inspection, V2 vehicle nodes and future handheld work distinct.

## ACT-03 interlock prototype — 2026-10-12

The [interactive arm/fault demonstrator](../../reviews/codex/actuator_interlock/index.html) and [review guide](../../reviews/codex/actuator_interlock/README.md) define deliberate rearming after power/command faults and expose the stale-periodic-strobe blind spot. The [receiver worksheet](../../reviews/codex/actuator_interlock/RECEIVER_ACCEPTANCE.md) captures exact ESC/BEC/servo limits before receiver-ready interface selection. Current connectors have no receiver-ready sensing; converter PG pins are unused. These are independently checked captured connections and tested software proposals, not an implemented hardware interlock. ACT-02, live CAD, firmware and ordering are unchanged. Next: isolated latch/OE gate; receiver interfaces and hardware timing remain held.
