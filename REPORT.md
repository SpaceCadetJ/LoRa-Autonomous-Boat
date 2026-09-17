# LoRa Autonomous Boat — reconstruction and V2 report

Written 2026-09-16 by the primary agent (Claude Code). Branches: `v1-kicad-reconstruction` (Phase A, tag `v1-kicad-baseline`) and `v2-design` (Phases B/C, tag `v2-design-draft`). The full document set is indexed in [docs/INDEX.md](docs/INDEX.md); the work log is [CONVERSION_LOG.md](CONVERSION_LOG.md); open decisions are in [BLOCKERS.md](BLOCKERS.md).

## 1. What was delivered

| Phase | Deliverable | Where | State |
|---|---|---|---|
| A | Faithful KiCad 9 reconstruction of the fabricated V1 board (v5 films + OrCAD netlist), hierarchical schematic, project libraries, as-fabricated rule file, generator scripts | `hardware/kicad/`, `hardware/kicad/tools/` | complete, tagged `v1-kicad-baseline` |
| A | Provenance, conversion notes, netlist, BOM with MPNs and prices, evidence figures, renders | `docs/A0_PROVENANCE.md`, `docs/CONVERSION_NOTES.md`, `docs/NETLIST.md`, `docs/BOM.csv`, `docs/img/` | complete |
| B | Evidence-based V1 design review (35 findings) and 45 numbered, testable V2 requirements with a decision list | `docs/V1_DESIGN_REVIEW.md`, `docs/V2_REQUIREMENTS.md` | complete |
| B | V1 firmware wiring notes (comment-only) and V2 firmware plan | `firmware/Core/Src/main.c` header, `firmware/V2_FIRMWARE_PLAN.md` | complete |
| C | V2 KiCad project: 6-sheet schematic (ERC clean), placed and autorouted 80 × 46 mm board (DRC 0 violations, 2 GND stitches to hand-finish), priced BOM, generator + autoroute chain | `hardware/kicad_v2/`, `docs/BOM_V2.csv` | draft, tagged `v2-design-draft` — needs hand tidy-up before fabrication (§4) |
| — | Interactive project manager / atlas / independent verification | `pm/`, `docs/atlas/`, `reviews/codex/` | Codex agent (see `PROMPT_FOR_CODEX.md`, `AGENT_STATUS.md`) |

## 2. Phase A fidelity numbers (V1 as fabricated)

| Check | Result | Evidence |
|---|---|---|
| Footprint pad positions vs film flashes | 172 / 172 pads within 0.000 mil | `validate_pcb.py` |
| Gerber XOR, KiCad export vs fabrication films | F.Cu 0.87 %, B.Cu 0.23 %, masks < 1 %, silk/outline < 1 % | `docs/A0_PROVENANCE.md` tables, `docs/img/v1_xor_*.png` |
| Drill | 53 / 53 holes within 0.05 mil of the v5 pad flashes (the shipped `.drl` is v4: 35 of its 50 holes do not exist on v5) | `A0_PROVENANCE.md` |
| Connectivity | Schematic netlist == `pstxnet.dat` == board pad nets (32 nets, 37 unconnected pins) | `check_netlist.py` PASS |
| DRC | 0 errors, 0 unconnected with the as-fabricated `.kicad_dru`; 67 documented warnings (the 7.6-mil LQFP fan-out and 37 mask bridges that are on the real board) | `hardware/kicad/_build/drc.rpt` |
| ERC | 0 violations | `_build/erc.rpt` |

Three wiring questions the old notes left open were answered from copper (`docs/img/v1_evidence_*.png`): PA8/TIM1 drives the SPEEDCONTROLLER header and PC6/TIM3 the STEERINGSERVO header; CEXT sits between VCAP_1 (pin 30) and +3V3, not ground; the CAN transceiver RXD is on PA10 (no CAN alternate function), so CAN never worked.

## 3. V1 findings that drive V2 (full list with evidence in `docs/V1_DESIGN_REVIEW.md`)

- **Safety:** no link-loss failsafe (last thrust persists), both actuator headers put +3V3 on the servo/ESC power pin, the ESC arms 10 ms after reset, no fuse / reverse-polarity / TVS on the battery input, no watchdog.
- **Functional:** SF12/BW125 gives about one command per second and the RYLR998 rejects SF12 outright; CAN unusable as wired; GPS header pin 3 held low by PB0; debug prints go into the GPS RX line.
- **Reliability:** VCAP returned to +3V3, VBAT/BOOT0 floating, no crystal (HSI only), no mounting holes (the 1.4 mm holes are live test points), 40 track pairs below the design rule of 12 mil, 37 untented-via mask bridges.

## 4. V2 in one page

**Kept:** STM32F446RET6 LQFP-64, R1240N 3.3 V buck (now with its catch diode, feedback and compensation network corrected), 2-layer board, Samtec 10-pin SWD header, Reyax RYLR UART module socket, 2.54 mm GNSS header.

**Added / changed (REQ ids in `docs/V2_REQUIREMENTS.md`):** XT30 battery input with 3 A fuse, P-FET reverse protection, SMAJ33A TVS and 47 µF bulk (REQ-PWR-01..03); 20 mΩ shunt + INA180 current sense and a filtered battery divider on the ADC (REQ-PWR-06/07); TPS54202 5 V servo buck OR-ed with the ESC BEC through SS34 diodes, so the actuator headers carry 5 V, never the logic rail (REQ-CTL-02); ESC/servo signals through 74AHCT1G125 level shifters with series resistors and PESD clamps on JST XH connectors (REQ-CTL-03/04); 8 MHz HSE and 32.768 kHz LSE crystals, NRST RC, VBAT/BOOT0 terminated (REQ-MCU-01..04); four status LEDs (REQ-DBG-02); USB-C CDC console with USBLC6 protection (REQ-DBG-01); ICM-20948 IMU on I2C with interrupt, GNSS PPS on PB0 (REQ-NAV-01..03); LoRa supply filter returned to ground, module reset driven by PA3 (REQ-RF-02/03); CAN dropped (frees PA11/PA12 for USB); four M3 mounting holes on a 72 × 38 mm pattern (REQ-MECH-01); seven test points.

**Numbers:** 118 parts, 71 nets, 68 BOM lines, board-only parts cost **$53.80 at qty 1** (`docs/BOM_V2.csv`, catalogue estimates dated 2026-09-16; the LoRa and GNSS modules, PCB and assembly are extra). Board 80 × 46 mm, 2 layers, Default class 0.25 mm track / 0.15 mm clearance, Power class 0.6 mm / 0.2 mm, vias 0.6/0.3 and 0.8/0.4 mm. Routing (freerouting 2.1.0 through `route_v2.py`, B.Cu pour as the routing plane): 1075 track segments, 165 vias, kicad-cli DRC **0 violations**; **2 GND connections still open** (two small pour islands near the LQFP fan-out at (42, 18.5) mm and near the USB block at (55.7, 9.2) mm that the automatic stitcher could not reach with a straight or L-shaped track; hand-finish with one via each in KiCad, or leave to the next layout); 101 silkscreen warnings (reference text over pads) left for the hand tidy-up. ERC 0 errors, 1 accepted warning (U6 SDO/AD0 tied to GND).

**Before fabrication (hand work the generator does not do):** tighten the two buck-converter switching loops (U2/L1/D3/C5-C6 and U3/L2/D4/C8-C9) and the crystal traces, route the USB pair as a pair, review the autorouter via placement near the XT30 and the LoRa header, add an assembly drawing. The placement is intended to stay; only the copper needs tidying.

## 5. Decisions needed from Jay (defaults in use; details in `BLOCKERS.md`)

1. LoRa module variant (default RYLR998_M4 with u.FL, antenna on a pigtail, no on-board keep-out).
2. Battery chemistry / cell count and whether the ESC is fed through the board (default 2S-6S LiPo, ESC direct from the battery, board ≤ 3 A).
3. Servo power source (default ESC BEC through the header OR-ed with the on-board 5 V buck).
4. Keep CAN? (default dropped).
5. IMU choice (default ICM-20948).
6. Connector family (default JST XH power/actuators, 2.54 mm module headers).
7. Mounting pattern / enclosure (**revised default 72 × 38 mm on 80 × 46 mm**; the 70 × 40 mm first cut did not fit).
8. Debug console (default USB-C CDC).
9. Handheld voice mode and whether voice shares the boat channel.
10. Whether the fab-house zip (real v5 drill, stack-up) exists.
11. On the working V1 harness, which header the ESC is plugged into and whether its +3V3 pin is connected.

## 6. Reproduce

- V1: `python hardware/kicad/tools/build_v1.py` from the repo root (KiCad 9.0.7 + Python 3.12 with gerbonara/numpy/scipy/shapely/pillow/sexpdata/kiutils) rebuilds board, schematic, validations, images and generated docs.
- V2: `python hardware/kicad_v2/tools/gen_v2.py` then `route_v2.py all` with the KiCad `python.exe` (Java 21 + freerouting 2.1.0). `hardware/kicad_v2/README.md` lists every step and check.
- Every script states its inputs/outputs in its header; intermediate files go to the git-ignored `_build/` folders.

## 7. Session log (commits on `v2-design`, newest first)

| Commit | Content |
|---|---|
| (tag `v2-design-draft`) | V2 routed board, renders, BOM_V2, REPORT.md, docs index |
| 0aa4920 | Codex snapshot: pm viewer scaffold, S2 verification packet, firmware protocol prototype |
| c06307f | Phase C: V2 schematic (6 sheets, ERC clean) + placed, DRC-clean unrouted PCB + tools |
| 2319972 | gen_sch.py Sheet class made reusable; V2 project skeleton |
| 679a9c7 | Phase A4 + B: README, design review, V2 requirements, firmware plan, generated docs, archived stale docs |
| 87a336c | Copper-evidence figures, firmware comment-only wiring notes, Codex prompt |
| 1f07361, b831657 | Coordination with the Codex agent (HANDOFF, FILE_OWNERSHIP, AGENT_STATUS, LF attributes) |
| 639e08f (tag `v1-kicad-baseline`) | Phase A3 close: CANH/CANL corrected, BOM with MPNs, DSN-v2 comparison, schematic exports |
| 4f855ba | Phase A3: hierarchical V1 schematic from pstxnet.dat, ERC clean, netlist == pstxnet |
| 65c9d14 | Phase A2: faithful V1 PCB reconstruction from the v5 films |
| 89b5219 | Snapshot of the pre-reconstruction state |
