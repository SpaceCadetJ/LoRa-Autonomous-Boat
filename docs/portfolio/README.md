# LoRa controller: from legacy board to reviewable platform

**Embedded systems, PCB reconstruction and engineering documentation.** This project turns an existing university boat-controller design into an inspectable KiCad workspace, with an evolving multifunction vehicle node and a future handheld. The current milestone is a documented engineering review edition with application guides and a separate V2 identity diagnostic. It is not a production release.

> A LoRa vehicle-controller project combining STM32 firmware, PCB reconstruction and an interactive engineering workspace. The repository preserves the original boat hardware, presents fifteen annotated schematic pages, traces connectors and parts to source evidence, and provides a reproducible V1 firmware build. A second-generation controller and voice/text/location handheld are under development, with verification results and unresolved design decisions recorded alongside the design.

[Explore the workspace](../../pm/index.html) · [Build and assembly guide](../build/README.md) · [Structured portfolio data](portfolio.json) · [Latest engineering handoff](../../reviews/codex/design_completion/HANDOFF.md)

## Context and contribution boundaries

The original University of Arkansas EECS senior-design team developed the boat controller in Cadence OrCAD/Allegro; the repository identifies May 2025 fabrication evidence. The present work reconstructs that legacy design in KiCad 9, investigates its defects, improves navigation and documentation, and prepares a V2 redesign. Original provenance and conversion limits are recorded in [A0_PROVENANCE.md](../A0_PROVENANCE.md).

The reconstruction, tooling and documentation include AI-agent-assisted development and independent review packets. This page describes repository deliverables, without assigning the original team's individual hardware or firmware contributions to Jay. Confirm his original role before writing a first-person portfolio account.

## Design and software

The V1 source implements a UART-connected Reyax LoRa radio interface, NMEA GPS parsing and 50 Hz PWM outputs for an ESC and steering servo around an STM32F446. Its bare-metal C firmware uses STM32 HAL/CMSIS and STM32CubeIDE/CubeMX project inputs. These are implementation facts, not newly measured radio or navigation performance. The handset source is absent from this repository. See the [firmware review](../research/FIRMWARE_REVIEW_NOTES.md).

```mermaid
flowchart LR
  H[Handset: external to this repository] <-->|LoRa link| R[Reyax UART radio]
  R <-->|UART| M[STM32F446 vehicle controller]
  G[GNSS receiver] -->|NMEA UART| M
  M -->|PWM| E[ESC / propulsion]
  M -->|PWM| S[Steering servo]
  B[Battery / power conversion] --> M
```

The V2 CAD draft expands power protection, actuator-rail separation, sensing and debug provisions. Fail-safe control, watchdog behavior, corrected parsing, heading hold and waypoint navigation remain implementation/acceptance work. The proposed handheld must support **voice, text and location** alongside RC control; radio airtime and worst-case control blocking must be validated before selecting its hardware. [Requirements](../V2_REQUIREMENTS.md) and the [platform concept](../../reviews/codex/PLATFORM_CONCEPT.md) distinguish these targets from delivered capabilities.

Python tools generate and review CAD, assemble purchasing evidence and compile preserved firmware. The local viewer uses HTML, CSS and JavaScript with embedded data; Node.js builds and validates the workspace. GitHub Actions defines automatic repository/evidence checks and separately opted-in native CAD/firmware jobs. A repository check is not hardware acceptance; consult the actual published run before claiming hosted execution. See [review workflow](../build/REVIEW_WORKFLOW.md).

## Demonstrated results

| Result | Evidence and scope |
| --- | --- |
| Fifteen grouped, annotated schematic pages | [Visual review](../../reviews/codex/professionalization/VISUAL_REVIEW.md); all pages inspected after PDF/SVG export |
| Presentation edits preserve all 533 electrical pins | [Final independent review](../../reviews/codex/professionalization/QUALITY_HANDOFF.md): V1 44 components / 172 pins, V2 114 electrical components / 361 pins; no value, footprint or net-name changes |
| Reproducible V1 compile and link | [Firmware evidence](../build/FIRMWARE_HANDOFF.md): two same-host builds produced identical ELF/HEX/BIN hashes; BIN 36,528 bytes, RAM reservation 4,496 bytes; preserved behavior remains unqualified |
| Traceable ordering and assembly material | [Procurement evidence](../build/PROCUREMENT_HANDOFF.md): 44 V1 / 118 V2 physical references reconciled; held/optional/external parts separated from partial candidate import lists |
| Navigable engineering workspace | [Viewer QA](../../pm/QA.md): searchable BOM, selected datasheets, connector evidence, drawings, build guides and review results; desktop/mobile checks and 203 local HTTP links passed at the recorded checkpoint |
| Regression checks for the editing workflow | [Publication review](../../reviews/codex/publication/QUALITY_PORTABILITY.md): 18 acceptance tests passed; isolated schematic generation preserves PCB/project/BOM |

The [current native check](../../reviews/codex/design_completion/native-review/REVIEW.md) records V1 ERC 0 errors/0 warnings and V2 ERC 0 errors/1 existing warning. The integrated ground repair reduces V2 unconnected items from three to zero with zero ordinary DRC errors; all 118 footprints and pad assignments remain unchanged. PCB warnings and schematic-parity findings remain. The strict combined review also flags the intentional PCB correction against the older preservation baseline. Six component-limit blockers still prevent fabrication approval. No physical assembly, flashing, bench qualification or range testing was performed during this edition.

## Portfolio visuals

Use the labels below when copying assets into a portfolio. PCB renders show CAD geometry, not photographs of a tested assembly. The V2 render is a draft, not a released product.

| Asset | Suggested caption |
| --- | --- |
| [V1 PCB render](../img/v1_pcb_top.png) | Legacy boat-controller PCB reconstructed in KiCad from preserved source evidence |
| [V2 PCB render](../img/v2_pcb_top.png) | Multifunction vehicle-controller CAD draft; electrical and layout review ongoing |
| [V1 schematic overview](../img/v1_sch_Root.svg), [V2 overview](../img/v2_sch_root.svg) | Functional sheet organization for the existing controller and redesign |
| [V1 schematic PDF](../img/v1_schematic.pdf), [V2 schematic PDF](../img/v2_schematic.pdf) | Annotated circuit drawings with subsystem notes and explicit review status |
| [V1 assembly map](../../hardware/manufacturing/v1/assembly_top.svg), [V2 assembly map](../../hardware/manufacturing/v2/assembly_top.svg) | Reference-designator maps for locating candidate parts during assembly review |

A separate [V2 Stage A diagnostic](../../firmware_v2/README.md) now builds reproducibly for board identity, heartbeat and inactive actuator outputs. The [application handbook](../applications/README.md) covers five use cases with explicit release gates. The [component-limit review](../../reviews/codex/design_completion/electrical/README.md) identifies six electrical blockers that remain after copper cleanup.

The [IMU correction candidate](../../reviews/codex/imu_interface/README.md) now provides a concrete 1.8 V supply and translated I2C/interrupt schematic, with exact pin-delta checks and a reviewed TI-specific footprint. It is separate from the live PCB and purchasing package; placement, routing and physical qualification remain pending.

## Next engineering milestones

1. Implement the recommended wider-voltage input-stage schematic with exact protection identities and bounded surge limits, then complete the power corrections and route the isolated IMU2 candidate.
2. Extend the implemented Stage A diagnostic after electrical acceptance: freeze the operational protocol, implement output supervision and measure failsafe behavior.
3. Finish the V2 connector atlas, exact-part qualification and complete population/purchasing decisions; perform recorded staged board bring-up.
4. Measure voice quality, airtime and RC coexistence, then develop the handheld and application interfaces.

For portfolio updates, preserve the distinctions in [portfolio.json](portfolio.json): **source-implemented**, **independently checked**, **proposed** and **not tested**. Pin the portfolio's repository link to the actual integration commit after publication; this handoff deliberately does not invent a commit, public site URL or individual team role.

## Power architecture and interactive study — 2026-10-12

The [annotated comparison](../../reviews/codex/power_topology/v2_power_topologies.svg) and [interactive load calculator](../../reviews/codex/power_topology/load_budget.html) explain two proposed 6S architectures and their constraints. Independent review checked candidate pin maps and arithmetic. The study identifies a conflict between simultaneous rail capacities and the low-voltage 1 A feed goal; it recommends the wider-voltage input stage for the next schematic packet. These are analytical design artifacts, not an integrated circuit, measured efficiency or a fabrication release. [Evidence and restart task](../../reviews/codex/power_topology/README.md).

## Native input-stage implementation — 2026-10-12

[INPUT-A1](../../reviews/codex/input_stage/README.md) advances the power study into an editable, wired schematic with specific fuse, TVS, diode and capacitor candidates. Native comparison verifies the exact delta and preserves all 344 connections outside the input section; ERC adds no findings. Fourteen tests reject wiring and identity regressions. The [drawing](../../reviews/codex/input_stage/v2_input_stage.svg) is an isolated engineering candidate: it is not routed, integrated, power-ready or fabrication-approved. Reverse-leakage protection and thermal/surge qualification remain open.

## Reverse-leakage design disposition — 2026-10-12

The [interactive boundary review](../../reviews/codex/reverse_leakage/index.html) shows why a component-level calculation is insufficient for board acceptance. Manufacturer review identified the polarized reservoir's zero-reverse-voltage requirement; a tested analytical model compares proposed leakage budgets and ADC startup limits. [Sources and restart contract](../../reviews/codex/reverse_leakage/README.md) preserve the distinction between calculated cases and verified hardware. INPUT-A1 and the live board remain unchanged.


## Input-network specification and footprint — 2026-10-12

The [annotated capacitor network](../../reviews/codex/input_capacitors/v2_input_capacitors.svg) and [interactive sensitivity tool](../../reviews/codex/input_capacitors/index.html) document separate nonpolar storage and local converter bypass. Native KiCad inspection found that the generic 2220 lands differ from the selected TDK part’s recommendations; a dimension-checked isolated footprint is supplied. Analytical tests cover capacitance thresholds and RLC limiting cases. [Evidence and next implementation task](../../reviews/codex/input_capacitors/README.md) retain unverified bias/temperature, damping, leakage and assembly gates. No live circuit or hardware acceptance is claimed.

## First converter schematic milestone — 2026-10-12

[BUCK33-A1](../../reviews/codex/buck_3v3/README.md) adds an annotated, editable 3.3 V converter study with exact candidate parts, package dimensions, reproducible feedback/current calculations and independent native connectivity checks. All 330 outside-boundary pins remain unchanged; native ERC adds no findings. The [SVG](../../reviews/codex/buck_3v3/v2_buck_3v3.svg) is suitable for illustrating the design-review process. It depicts a held schematic candidate, not a manufactured or tested board. Live copper, ordering and firmware remain preserved; the next isolated circuit task is the 5 V rail and load budget.

## Second converter and power-budget milestone — 2026-10-12

[BUCK5-A1](../../reviews/codex/buck_5v/README.md) adds the editable LM76003 5 V candidate, [annotated SVG](../../reviews/codex/buck_5v/v2_buck_5v.svg), exact part/pin contract and a source-loss model. Native validation preserves all 339 outside-boundary pins and the first converter. The review also identifies an output-diode package mismatch and quantifies why the current low-voltage feed cannot promise both full rail loads. Present this as an engineering review milestone; PCB integration, assembly and hardware performance remain unqualified.

## Latest actuator supply candidate - ACT-01

The [annotated actuator revision](../../reviews/codex/actuator_supply/README.md) separates buffer power from servo energy, preserves both reviewed converters and defines explicit BEC/onboard population proposals. Independent checks verify four pin changes, two exact diode identities, both master DNP markers and 380 untouched outside-boundary pins; 31 mutation tests pass. Live PCB and operational firmware are unchanged. Enable/sequencing, load and fabrication acceptance remain open.

## ACT-02 signal-enable checkpoint — 2026-10-12

The [annotated actuator candidate and sequencing guide](../../reviews/codex/actuator_enable/README.md) adds a dual-supply translator, default-low PC4 enable and a proposed firmware arm/disarm contract. Native checks preserve 383 outside-boundary pins and both converter sheets; 41 mutation tests pass. This is isolated schematic evidence: Stage A does not drive PC4, live firmware/PCB and purchasing exports are unchanged, and no application is released for powered actuator use. Next: hardware arm interlock and receiver-power observation, then the remaining 6S, C11/transient, ADC and combined IMU2 gates. Keep V1 inspection, V2 vehicle nodes and future handheld work distinct.

## ACT-03 interlock prototype — 2026-10-12

The [interactive arm/fault demonstrator](../../reviews/codex/actuator_interlock/index.html) and [review guide](../../reviews/codex/actuator_interlock/README.md) define deliberate rearming after power/command faults and expose the stale-periodic-strobe blind spot. The [receiver worksheet](../../reviews/codex/actuator_interlock/RECEIVER_ACCEPTANCE.md) captures exact ESC/BEC/servo limits before receiver-ready interface selection. Current connectors have no receiver-ready sensing; converter PG pins are unused. These are independently checked captured connections and tested software proposals, not an implemented hardware interlock. ACT-02, live CAD, firmware and ordering are unchanged. Next: isolated latch/OE gate; receiver interfaces and hardware timing remain held.


## ACT-04: native actuator arm latch

The [annotated latch candidate](../../reviews/codex/actuator_latch/README.md) now separates the MCU arm request from translator enable. Independent native checks verify exactly two changed memberships, 396 preserved, nine added parts and no new ERC findings. The recorded Boolean and footprint checks cover their declared scopes. Qualification/ACK inputs remain default low until supervisory and receiver interfaces are implemented. The circuit intentionally disables on ACK while armed, unlike the older ACT-03 simulator. No live PCB, operational firmware, purchasing or hardware acceptance is implied. Next: qualification/reset-release, fault retention and conditioned ACK.
