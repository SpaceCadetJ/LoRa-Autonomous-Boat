# Independent project assessment

Snapshot: 2026-09-17 UTC, branch `v1-kicad-reconstruction`, HEAD `89b5219`. The primary agent is actively modifying uncommitted files. This review does not approve Phase A or authorize manufacturing. See [source evidence and SHA-256 manifest](SOURCE_AUDIT.json).

## What the project needs

The immediate deliverable is an editable, faithful record of the fabricated boat controller with clear schematics and trustworthy navigation. The later deliverable is a safer, reusable LoRa platform. These need different acceptance gates: preserve V1's actual connections, including defects; improve them only in the successor design.

The attached collaborator prompt supplies useful coordination guidance. Its instruction to complete and commit the entire program is not the user's current request. This session performs review and conceptual design only. March workflow documents and even the newer primary brief contain assertions superseded by direct v5 evidence.

## Evidence-derived baseline

The independent audit uses standard-library Python and does not import the primary agent's converters. It checks complete net/node parsing, retains the NC list, inventories artwork headers, compares drills, and hashes every input. Exact invocation:

```powershell
& 'C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\bin\python.exe' reviews/codex/tools/source_audit.py
```

Initial successful run: 2026-09-17T00:12:06Z, exit 0. Final refresh: 2026-09-17T00:17:47Z, exit 0; no input changed during that read and no duplicate source pin memberships were found. This means source inventory completed, not that the design passed validation. The refresh includes observed primary validation summaries. Read the JSON timestamp and hashes for the exact final snapshot.

| Independently observed | Consequence |
|---|---|
| `pstxprt.dat`: 44 parts; `pstxnet.dat`: 32 electrical nets plus 37 NC nodes | The brief's 45 parts / 35 nets is not a valid v5 acceptance fixture. Compare pin sets, not a hard-coded count. NC entries must not become one connected net. |
| v5 outline centerline: 66.548 × 37.3126 mm | The 76.2 mm square is an earlier design assumption; enclosure and mounting decisions need the actual revision. |
| BOATCREW drill: 50 holes; identical to named v4 drill after removing only the filename comment; identical archived copy dated May 1, 2025 | v5 copper dated May 9 cannot be certified against that drill merely because filenames match. Inferred drill reconstruction must be labelled separately from verified manufacture data. |
| Current PCB text snapshot: 44 footprints, 367 segments, 27 vias, 3 zone objects | Reconstruction is progressing. Text counts do not prove parseability, connectivity, geometric fidelity, or manufacturability. |
| Six child schematics contain zero wire objects; root contains 84 | The readable wired hierarchy is not demonstrated. Labels can create connections without wires, so this is an inventory signal, not an ERC verdict. |

## Findings for the next handoff

Paths in the evidence column are repository-relative. `pstxnet` means `Allegro/hardware/allegro-original/Allegro v5/Allegro/pstxnet.dat`. Source pin memberships are verified; physical board continuity is still pending.

| ID / severity | Observation and evidence | Consequence / correction / owner / gate |
|---|---|---|
| R01 BLOCKING | Old acceptance counts, outline and drill provenance conflict with the table above | Primary and reviewer must update the baseline acceptance criteria explicitly. Do not alter source geometry to meet stale targets. A0/A2/A3. |
| R02 BLOCKING | At initial inspection, `tools/validate_pcb.py:45` reads expected net into `wnet` but never compares it; the final `return 0 if not errs else 1` (line 66 in the final snapshot) ignores unrouted count. It lacks a complete expected-vs-actual pad-set check. Observed `validate_pcb.json` has `unconnected: 1` and no pad errors. | A success exit is insufficient. Primary should enforce pin-set/net equality, missing pads, and zero unrouted; independently validate copper exports. A2. Do not run this script casually: default behavior saves the board, and `--no-save` still writes its report. |
| R03 MAJOR | `tools/gen_pcb.py:36` names N04855 CANH and N24691 CANL. Source `pstxnet:76–79` has N04855→U5-6 (CANL); `:385–388` has N24691→U5-7 (CANH). TI confirms these functions. | Correct semantic mapping and regenerate dependent labels after owner review. This is a naming defect; it alone does not prove copper was reversed. Primary, A2/A3/docs. |
| R04 BLOCKING for V2 actuator use | `main.c:454–486` has no command expiry. Thrust persists after loss of reception; `:736–742` does not explicitly stop PWM on error. | Define disarm/link-loss/error/reconnect behavior and verify output timing. Firmware owner, B/C and bench gate; preserve V1 behavior during reconstruction. |
| R05 MAJOR | C sets TIM3 startup to 1000 µs (`main.c:70–72,608`), while `.ioc:150` specifies 1500 | Regeneration could change startup throttle. Reconcile configuration in separate firmware work and scope startup pulses. Firmware owner, B/C. Actual ESC idle behavior needs confirmation. |
| R06 MAJOR | `pstxnet:238–244`: PA8→SPEEDCONTROLLER-2; `:270–276`: PC6→STEERINGSERVO-2. Code thrust→PC6, rudder→PA8 (`main.c:370–395`; MSP `:123–153`) | Netlist and firmware intent disagree. Primary must trace copper and record actual harness use before changing labels or behavior. A4/B. |
| R07 MAJOR | VCAP is correctly U3-30 (`pstxnet:365–368`), but CEXT-2 is on 3.3V (`:337`), not the source ground net | The old pin-30/PB11 allegation is refuted for STM32F446RE. Review both capacitor terminals against the regulator supply scheme and copper; correct pad identity alone does not settle capacitor wiring. Primary, A4/B. |
| R08 MAJOR | v5 has PA12→U5-1/TXD, PA11→U5-8/STB, PA10←U5-4/RXD (`pstxnet:56–89`) | TXD/STB package identities are not swapped as the old prose suggests. The remaining functional issue is RXD on PA10, which is not CAN1_RX in ST's AF table. Confirm copper and retain V1 as built. Primary, A4/B. |
| R09 MAJOR | `pstxnet:292–295` puts both actuator header pin 1s on 3.3V | Document actual harness/BEC wiring and separate actuator power in V2. Backfeed is a risk inference, not proof of the physical hookup. Hardware owner, B/C. |
| R10 MAJOR | Parser skips sender/length validation (`main.c:298–350`); UART ISR and main share buffers (`:268–273,460–465,694–726`); GPS has no fix age (`:477–482`) | Add strict framing, sender/session/freshness checks, bounded buffer handoff and stale-fix invalidation. Firmware owner, B/C. Source review is not a runtime test. |
| R11 MAJOR / model-dependent | Firmware requests `12,7,1,4` (`main.c:67,449`) without verifying module acceptance. Current RYLR998 guide lists SF5–11 and specific SF/BW combinations; SF12 is outside that guide. | Identify the actual RYLR model and firmware; capture acknowledgments and parameter readback. Do not treat RYLR896 and RYLR998 as interchangeable or calculate range from an unverified setting. RF owner, B. |

Datasheet checks: [ST DS10693 Rev 11, May 2026](https://www.st.com/resource/en/datasheet/stm32f446re.pdf), Table 10 p50 (VCAP pin), Table 11 p58 (CAN AF), supply scheme p72; [TI SLLSES9D, October 2021](https://www.ti.com/lit/gpn/tcan1042h-q1), Table 6-1 p5; [REYAX RYLR998/498 guide, August 7 2025](https://reyax.com/upload/products_download/download_file/LoRa_AT_Command_RYLR998_RYLR498_EN.pdf), pp2–5. Retrieved 2026-09-17. Only targeted pin/configuration checks were performed; this is not a complete datasheet review.

## Phase and ownership gap matrix

| Phase | Present state | Missing evidence / next action | Owner |
|---|---|---|---|
| A0 provenance | Header report, reconstructed placement/connectivity and independent facts inventory exist | Explicit disposition of old drill; independently check coordinate residuals and v2/v5 geometry comparison. Generated connectivity is not independently validated here. | Primary implementation; Codex review |
| A1 footprints | Project footprint library now generated | Geometry/pad-number audit for changed v5 parts; resolve interchangeable-placement assignments against electrical identity and available silkscreen/ECO evidence | Primary |
| A2 PCB | Routed draft present; primary reports inspected | Final observed DRC (report dated 00:16:16 UTC) lists 64 clearance errors, 30 warnings and 1 unconnected entry. An earlier report had additional courtyard errors; the primary is making progress. This is a moving draft, not a final verdict. Need raw DRC, exact hashes, full copper/mask/outline XOR and drill evidence. | Primary until release |
| A3 schematic | Root and six child sheets exist | Wired hierarchy, ERC, full pin membership equivalence and UUID/PCB synchronization | Primary |
| A4 baseline release | No release/tag reviewed | Stable revision, known V1 defects, explicit scope release, reproduction commands | Primary then Codex verification |
| B review/requirements | Firmware review notes exist; concept below | Numbered measurable requirements, corrected defect evidence, actual battery/radio/harness facts, RF timing/link budget | Primary integration; isolated Codex requirements after claim |
| C successor design | Concept only in this review | Power/pin/interface decisions, schematic, routing, BOM, firmware plan and independent validations | Not started by Codex |
| Documentation | Existing README/netlist/BOM include stale assumptions | Owner to integrate a single entry map, connector atlas, sheet PDFs/SVGs, layer overlays, revision labels and generated evidence links | Primary; Codex information design |

## Acceptance discipline

Preserved V1 defects can conflict with clean ERC/DRC targets. Record inherited violations separately from conversion defects; retain raw reports and the rationale for each waiver. Never change V1 copper merely to make the report green. A relaxed clearance rule is a documented design-rule change, not proof that a geometrical mismatch was corrected.

For XOR, record registration, pixel scale, antialiasing, layer polarity, board crop, numerator and denominator. Report mismatch relative to the copper union as well as the comparison area; large blank margins can hide defects. Store every exclusion mask. Separate clearance/continuity evidence from pixel similarity.

Safe now: independent source analysis, conceptual design and owned review artifacts. Safe later: exact released paths at an identified revision after checking current status and claims. Agent silence, elapsed time, apparent completion, or a different branch is insufficient. This review does not interrupt the primary's implementation.
