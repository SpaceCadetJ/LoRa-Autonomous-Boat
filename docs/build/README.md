# Build, assemble and program

Start with the board you actually have. **V1 documents the existing boat controller; V2 is the developing multifunction vehicle node.** The future handheld must support voice, text and location alongside RC control. It does not yet have a released PCB, BOM or firmware image.

The [interactive workspace](../../pm/index.html) brings the drawings, parts, assembly maps, firmware and review evidence together. Use by application links the [application handbook](../applications/README.md); Build & program covers assembly and firmware. Keep this repository together so all linked artifacts remain available.

## Choose a build path

| Step | V1: inspect, repair and reproduce | V2: review and develop |
| --- | --- | --- |
| Read the circuit | [Annotated schematic PDF](../img/v1_schematic.pdf), [known design findings](../V1_DESIGN_REVIEW.md) | [Annotated schematic PDF](../img/v2_schematic.pdf), [requirements](../V2_REQUIREMENTS.md) |
| Select parts | [Ordering guide](ORDERING.md), [complete BOM review](../../hardware/manufacturing/v1/bom_review.csv), [held parts](../../hardware/manufacturing/v1/holds.csv) | [Ordering guide](ORDERING.md), [complete BOM review](../../hardware/manufacturing/v2/bom_review.csv), [held parts](../../hardware/manufacturing/v2/holds.csv) |
| Locate and inspect components | [Assembly procedure](ASSEMBLY_V1.md), [top map](../../hardware/manufacturing/v1/assembly_top.svg), [bottom map](../../hardware/manufacturing/v1/assembly_bottom.svg) | [Assembly procedure](ASSEMBLY_V2.md), [top map](../../hardware/manufacturing/v2/assembly_top.svg), [bottom map](../../hardware/manufacturing/v2/assembly_bottom.svg) |
| Check connector wiring | [V1 connector atlas](../atlas/README.md) and assembly guide | Assembly guide and current schematic; a complete V2 connector atlas is still needed |
| Compile | [Reproducible V1 build](FIRMWARE_BUILD.md): completed twice with identical image hashes on the recorded toolchain | [Stage A diagnostic](../../firmware_v2/README.md) builds; no operational/qualified image exists |
| Back up / program / verify | [V1 flashing procedure](FLASHING_V1.md): retain the existing image before changing hardware | [V2 bring-up and programming plan](FLASHING_V2.md): resolve the pin/protocol contract first |
| Review changes | [Review workflow](REVIEW_WORKFLOW.md), [schematic editing guide](SCHEMATICS.md) | Same checks, plus unresolved PCB routing, layout and device-level electrical review |

## From parts list to a working unit

1. Read the version's known defects and assembly prerequisites. V1 is a faithful reconstruction and retains original defects; its clean netlist comparison does not repair them.
2. Resolve the held and optional parts, then import the one-board or five-board candidate CSV from the ordering guide. These are partial quote lists, not complete approved carts. Include the external radio, GNSS, harness, power and mechanical decisions.
3. Freeze an accepted PCB/parts/population revision before requesting fabrication or assembly. The current exports are review artifacts; no Gerber, drill or pick-and-place release is approved here.
4. Inspect the unpowered board and connector polarity, then follow the assembly guide's staged power checks with actuators disconnected. Record actual measurements against board identity and input hashes.
5. Follow the version-specific firmware procedure. The V1 build is unqualified and preserves existing behavior. The V2 procedure is a development sequence, not an instruction to load the V1 binary.
6. Record backup, programming verification, reset behavior, failsafe, link loss, sensor and application tests. Passing a compiler or CAD check alone cannot complete this step.

## Review and transfer

Every change packet should contain its reason, exact changed source files, generated artifacts, input hashes, checks, remaining limitations and one next task. Read the latest [handoff](../../HANDOFF.md) and [ownership record](../../FILE_OWNERSHIP.md) before editing. Source generators and their outputs must move together in a later selective commit; no commit, upload or deployment is automatic.

The manual CI workflow runs dependency-free quality tests, optionally checks KiCad on a configured runner, and optionally compiles V1 without accessing hardware. It records evidence even when a gate fails. Local results are in the [quality handoff](../../reviews/codex/professionalization/QUALITY_HANDOFF.md), [firmware handoff](FIRMWARE_HANDOFF.md) and [procurement handoff](PROCUREMENT_HANDOFF.md).

## Next development packets

1. Resolve current V2 electrical/layout findings and all schematic-to-PCB discrepancies at a frozen revision.
2. Review the Stage A pin-checked diagnostic, finish electrical corrections and freeze the operational protocol before adding control drivers.
3. Compile and test the protocol/failsafe correction prototype, then integrate it through measured bench acceptance.
4. Complete the V2 connector atlas and exact-part datasheet coverage; approve a complete population and purchasing list.
5. Measure voice airtime, speech quality and the worst RC blocking interval before selecting handheld radio, codec or hardware. Voice, text and location remain required; no shared-radio coexistence claim is made yet.
