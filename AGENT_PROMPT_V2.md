# AGENT PROMPT — LoRa Autonomous Boat Controller: KiCad Reconstruction + V2 Redesign

You are a senior hardware/firmware engineer working autonomously in this repository with a shell, Python, git, and a full KiCad 9 install on Jay's Windows PC. You have no prior context. This document is your complete brief. Read it fully before touching anything.

**Repo root:** `C:\Users\Jay\OneDrive\Desktop\LoRa Autonomous Boat\LoRa Autonomous Boat`
(OneDrive path with spaces — quote every path. If OneDrive locks a file, wait and retry once, then move on.)

**Owner:** Jay — EECS grad student, University of Arkansas Cognitive Robotics Lab. Ex-Army aviation electrician, ex-Bosch R&D QE. Wants deliverables, not plans. Wants reference images and working files, not essays. Every hour of his time you save is the point.

---

## 1. WHAT THIS PROJECT IS

An autonomous surface vessel (RC-boat scale) with three jobs:

1. **Long-range radio link** — 915 MHz LoRa (Reyax RYLR896/998 UART module, SF12 / BW125 kHz / CR4-5, network 18, boat = addr 1, handset = addr 2). Handset sends `THRUST,<0-100>` and `RUDDER,<0-100>`; boat sends `GPS,<lat>,<lon>` every 5 s.
2. **Motor and rudder control** — two 50 Hz servo-PWM outputs: a brushless ESC on the thrust channel (1000–2000 µs) and a rudder servo (1100–1900 µs), each on a 1×3 header (signal / power / GND).
3. **GPS localization** — generic NMEA module at 9600 baud on a 1×5 header; firmware parses `$GPRMC/$GNRMC` for position and validity.

**V1 (exists, fabricated, works)** — a 76.2 × 76.2 mm 2-layer board designed in OrCAD Capture + Allegro PCB Editor 22.1 (Cadence SPB), 45 components: STM32F446RET6 (LQFP-64), R1240N001B buck (battery → 3.3 V), TCAN1042HDRQ1 CAN transceiver (wired, never used by firmware), SB007-03Q ESD/TVS, LoRa and GPS headers, ESC/servo headers, 2×5 JTAG/SWD IDC, 4 test points, battery terminals. Firmware is bare-metal STM32 HAL (`firmware/Core/Src/main.c`, ~750 lines).

**V2 (your job)** — produce two things in KiCad 9, in this order:

- **Phase A — a faithful KiCad reconstruction of V1.** Copper, vias, outline, mask, silkscreen, and a fully wired hierarchical schematic that match the fabricated board. This is the baseline; nothing in V2 is credible without it.
- **Phase B/C — a V2 redesign.** Same mission, improved: a more robust radio link, safer motor control, better localization, and the reliability features V1 lacks. Grounded in a written review of V1's actual weaknesses, not generic advice.

Plus documentation and a report that a new team member (or Jay in six months) can navigate without you.

---

## 2. GROUND TRUTH — READ THIS BEFORE THE EXISTING DOCS

Several statements in the repo's existing docs (`README.md`, `docs/CONVERSION_NOTES.md`, `hardware/kicad/STATUS.md`, `SESSION_HANDOFF.md`, `DIRECTIVES.md`) are wrong or stale. These have been verified directly against the files:

| Claim in existing docs | Reality |
|---|---|
| "The DSN contains placement and netlist but **no routing**; traces must be re-routed manually." | **False.** `hardware/kicad/senior design v2.dsn` has a `(wiring …)` section with **186 `(wire` paths (145 TOP, 37 BOTTOM), 24 `(via`, and 3 polygon wires**. The routing was simply never converted. |
| The DSN is the source of truth for the final board. | The DSN header says it was exported from **`senior design v2.brd`** (`L:/SENIOR DESIGN/DESIGN 2/...`). The fabricated board is **v5** (`senior design v5DRL.brd`). Placement/routing may have changed between v2 and v5 — you must diff. |
| `BoatcrewArtwork/` = "Gerber exports". | Specifically: the `BOATCREW*.art` Gerbers (RS-274X, inches, 2.5 format, leading-zero suppression) were generated from **`senior design v5.brd` on 2025-05-09 17:41** — the same day as the `netrev.lst` import into v5. **These are the fabrication-final copper and the copper ground truth.** Films: `TOPL` (TOP etch + pins + vias), `BOTL`, `BOTTOM`, `MASK_TOP`, `MASK_BOT`, `SILK_TOP`, `OUTLINE`, plus `BOATCREWDRILL-1-2.drl` (Excellon, 5 tool sizes: 13 mil ×24, 23.62 mil ×2, 40 mil ×16, 49 mil ×4, 55.12 mil ×4). The other `.art` files in `Allegro v5/Allegro/` (`Filesv2*`, `TOP.art`, `Routing.art`, etc.) are from **v4** and are not the fab set. |
| `SENIORDESIGN_BOARD.png` is a board image. | It is a screenshot of the OrCAD Capture start page. Ignore it. |
| `pstxnet.dat` / `pstxprt.dat` / `pstchip.dat` are Allegro internals. | They are the **OrCAD-side packaged netlist that was imported into v5.brd** (see `netrev.lst`, "Drawing: senior design v5.brd", 2025-05-09). This is the most authoritative **netlist** in the repo — newer than the DSN's. Parse it. |
| The CC/CD pipeline in `DIRECTIVES.md` / `SESSION_HANDOFF.md` ("never edit `.kicad_*` as text", split roles). | **Superseded by this brief.** You are one agent with a shell and KiCad. Generating `.kicad_pcb`/`.kicad_sch` programmatically is expected — but you validate every generated file by round-tripping it through `kicad-cli` (and the pcbnew Python API for boards) before you trust it. |
| The existing KiCad PCB "has correct placement." | Plausible but unverified: `generate_kicad.py` transforms with `x_mm = 150 + (x_mil − cx)·0.0254`, `y_mm = 100 − (y_mil − cy)·0.0254` and a hard-coded `gr_rect` 111.9–188.1 mm outline (a plain 76.2 mm square from the DSN `(boundary (rect signal -1500 -1500 1500 1500))`). Verify against `BOATCREWOUTLINE.art` and pad flashes in `BOATCREWTOPL.art`. |
| The `.brd` files can be parsed. | They are proprietary binary. Do not attempt. If you truly need something only inside `v5DRL.brd`, write it to `BLOCKERS.md` as a precise export request (Jay can run Allegro in a VM, but it is painful — last resort only). |

Other facts you will need:

- Allegro units: DSN is `MIL 1000` resolution, Y-up. KiCad is mm, Y-down. Gerbers are inches with `FORMAT 2.5`, `SUPPRESS-LEAD-ZEROES YES` (see `art_param.txt`; apertures in `art_aper.txt`).
- Allegro net `0` is GND. Nets beginning with `'` (e.g. `'PA13`) are quoted names. Most signal nets have OrCAD auto-names (`N04355` etc.); `hardware/kicad/design_data.json` and `docs/NETLIST.md` carry a readable-name mapping (35 nets) — reuse it, but re-derive connectivity from `pstxnet.dat`, not from the markdown.
- Allegro footprint names carry `-M` / `-L` suffixes (IPC-7351 Most/Least density variants). The DSN `(library (image …) (padstack …))` section has the **actual pad geometry** used on the fabricated board. Prefer generating project-local footprints from it over KiCad standard-library approximations, and keep the mapping table in `CONVERSION_NOTES.md` as the record of what was substituted.
- Design rules from `senior design v2_rules.do`: width 12 mil; clearance 12 mil (wire-wire, wire-smd, wire-pin, smd-smd, smd-pin); 5 mil wire-via. Via: verify pad/drill from the DSN `(via …)` padstack definitions and the 13-mil drill count.
- Firmware pinout (`firmware/BoatTHISTIMEITSDIFFERENT.ioc`): UART4 PA0/PA1 (LoRa, 115200), USART3 PC10/PC11 (GPS, 9600), TIM1_CH1 **PA8** (rudder), TIM3_CH1 **PC6** (motor), PB0 GPIO output, SWD/JTAG PA13/PA14/PA15/PB3. TIM1/TIM3: prescaler 15, period 19999 → 50 Hz at 16 MHz. **No HSE crystal exists on the board** — the MCU runs on the HSI RC oscillator. No ADC, no CAN, no IWDG is initialised in firmware.
- Existing KiCad files (`hardware/kicad/`): `.kicad_pro`, `.kicad_pcb` (45 footprints, 0 tracks, 0 zones, 1 `gr_rect`), root `.kicad_sch` + six 5 kB sub-sheets (`MCU`, `PowerSupply`, `CAN_Bus`, `LoRa_Module`, `GPS_Module`, `PWM_Outputs`) that are essentially **empty**, a `.kicad_sym` with two custom symbols (R1240N001x, TCAN1042H-Q1 — unverified pinouts), `LoRa_Boat_Controller.pretty/`, three backup zips, a stale `~*.lck` lock file, and `.claude/settings.local.json` (should not be in the repo).

---

## 3. V1 DESIGN REVIEW — SEED FINDINGS (VERIFY EACH, THEN EXTEND)

These were observed from the netlist, BOM, and firmware. Each must be confirmed against the Gerber copper / `pstxnet.dat` / datasheets and written up with evidence in `docs/V1_DESIGN_REVIEW.md`. Add your own findings; the list below is a floor, not a ceiling.

**Radio link**
- The LoRa module sits on a plain 1×5 0.1" header; the antenna is whatever the RYLR module carries. No board-level control of antenna placement, ground clearance, or keep-out. Range is bounded by the module's ±3 dB variability and its proximity to the MCU, buck converter (1.5 MHz switcher), and ESC wiring.
- The link has **no failsafe**: `main.c` has no link-loss timeout. If the handset goes out of range, the last THRUST value persists indefinitely. For a long-range boat this is the single most important defect.
- SF12/BW125 gives roughly 300 bps air rate; `AT+SEND` of a ~30-byte GPS string takes ~1.5–2 s of air time every 5 s. Assess the duty cycle, collision behavior with the handset's commands, and whether SF9–SF10 with a proper antenna gives more usable range than SF12 with a bad one.
- LoRa supply is 3.3 V through two BLM15 ferrites (L3/L4) with 10 µF + 10 µF + 0.1 µF + 47 pF. RYLR998 TX peaks ~120–140 mA; check the R1240N (which is a **1 A-class** part — confirm from the datasheet) headroom with GPS + MCU + module.

**Motor / rudder control**
- `SPEEDCONTROLLER-1` and `STEERINGSERVO-1` are on the **+3V3 net**. ESCs normally supply a 5 V (or 6 V) BEC on that pin, and servos draw amps. Either the BEC is back-driving the 3.3 V rail through the buck's output, or the servo is being run from 3.3 V. Determine which from the copper and the parts, and flag it — this is likely a latent fault.
- PWM signals are bare 3.3 V MCU pins on unprotected headers going to a motor-noisy environment. No series resistor, no ESD, no level shift.
- **PWM pin assignment conflict**: the Allegro netlist puts motor PWM on U3-41 (PA8) and rudder on U3-37 (PC6); the firmware drives motor from PC6/TIM3 and rudder from PA8/TIM1. The board works, so the header labels or the firmware comments are wrong. **Resolve it from the Gerber copper** (trace PA8's pad to whichever header it reaches) and record the answer.
- No motor current sense, no battery current sense, no ESC telemetry input.

**GPS / localization**
- Generic NMEA at 1 Hz/9600 baud with no PPS, no backup power, no antenna consideration. Fine for logging, weak for autonomy.
- Course-over-ground from GPS is invalid below ~1 m/s; there is **no IMU / magnetometer**, so the boat has no heading estimate when slow or stationary — which is exactly when you need it for station-keeping or docking.
- The GPS header wiring is odd: PB0 (a plain GPIO output in firmware) goes to GPSMODULE-3, while USART3 TX/RX go to pins 5/4. Document what each header pin actually is.

**Power**
- Battery input has no reverse-polarity protection, no fuse, no TVS on VIN, no bulk input capacitance beyond CIN (10 µF). Battery terminals are single pads (`AMV_CON1`).
- The SB007-03Q (U1) is on the **switch node** (`SW_NODE`: U6-3, U1-3, C12-1, L1-1) with a 51 Ω / 0.1 µF snubber. Determine from the R1240N datasheet whether this part is a synchronous buck; if so U1 is doing ESD duty on the wrong node, and if not the board relies on a TVS as a catch diode. Either way, write it up.
- ADC battery divider (R5 30 k / R6 10 k → PA2) exists but the firmware never enables the ADC. No low-battery behavior.
- No status LEDs of any kind. No power LED, no link LED, no GPS-fix LED.

**MCU / debug**
- No HSE crystal. HSI ±1 % is adequate for UART but rules out USB, precise timing, and RTC; no LSE either.
- `VCAP1` net is recorded on U3-30 (PB11) in `NETLIST.md` with a note that it should be pin 31 (VCAP_1). Determine which pad the copper actually reaches. If CEXT is really on PB11, the MCU's internal regulator is running with no VCAP capacitor — which works, badly, and would explain flakiness.
- **TCAN1042H pinout appears swapped**: netlist has CAN_TX (PA11) → U5-8 and CAN_STB (PA12) → U5-1. On the SOIC-8 TCAN1042, pin 1 = TXD and pin 8 = STB. Confirm from the copper; since firmware never used CAN, this may be an undetected fault in V1.
- Also confirm: is PA11/PA12 wired as CAN1_RX/TX correctly for the STM32F446 (CAN1_RX = PA11, CAN1_TX = PA12)? The netlist labels PA11 as CAN_TX and PA10 as CAN_RX, which does not match any STM32F446 CAN mapping. Verify.
- 2×5 IDC JTAG header; SWO present. No USB, no UART console header for field debugging.

**Mechanical / assembly**
- Identify the four 55.12 mil (1.4 mm) and four 49 mil holes in the drill file — mounting holes or connector pins? If the board has no M3/M2.5 mounting holes, V2 needs them.
- No conformal-coating or enclosure considerations; this is a boat.

---

## 4. ENVIRONMENT — DO THIS FIRST

1. Locate KiCad 9: normally `C:\Program Files\KiCad\9.0\bin\`. Confirm `kicad-cli.exe version` and that `python.exe` in that folder can `import pcbnew`. Use **that** Python for anything touching `pcbnew`; use your normal Python for everything else.
2. `git status`, `git log --oneline | head`. Create branch `v1-kicad-reconstruction` for Phase A and `v2-design` for Phases B/C. Commit at every phase gate with a message that states what was validated.
3. `pip install gerbonara sexpdata kiutils` (gerbonara parses RS-274X/Excellon and can render/rasterize; kiutils reads/writes KiCad s-expression files; `generate_kicad.py` already contains a DSN parser you can extend). If a library fails, fall back to writing the parser yourself — the formats are simple.
4. Create `hardware/kicad/tools/` for every script you write. Every script must be re-runnable from the repo root and documented in a one-line header.
5. Back up `hardware/kicad/` to `hardware/kicad/_backup_<date>/` before the first write. Delete the stray `~LoRa_Boat_Controller.kicad_pcb.lck`. Add `.claude/`, `*.lck`, `_backup_*/`, `*-backups/` to `.gitignore`.

---

## 5. PHASE A — FAITHFUL V1 RECONSTRUCTION IN KICAD 9

### A0. Coordinate frame and provenance (gate: `docs/A0_PROVENANCE.md`)
- Parse every `.art` header (Layout Name, Origin Date, Film Name) and every `.drl` header in the repo. Produce a table: file → source board rev → date → layer. This settles "which artwork is v5" with evidence.
- Establish the transform between three frames: DSN mils (v2), Gerber inches (v5), and KiCad mm. Solve it from matched features — the LQFP-64 pad flashes, the 1×5 header pads, and the 24 via drills vs the 24 DSN vias. Report the residual (should be < 1 mil if placement did not move between v2 and v5; if it did, list which parts moved).
- Diff the DSN v2 wiring against the v5 Gerber copper by rasterizing both into the same frame (gerbonara render → numpy → XOR). Report per-layer mismatch. This tells you whether DSN wires (which carry net names) can be used directly or must be re-derived from the Gerbers.

### A1. Footprints
- Generate project-local footprints in `LoRa_Boat_Controller.pretty/` from the DSN `image`/`padstack` definitions (pad shape, size, position, layer, drill). Name them after the Allegro footprint. Keep courtyard/silk sensible but pads exact.
- Update `docs/CONVERSION_NOTES.md` mapping table: Allegro name → project footprint → nearest KiCad-lib equivalent → pad-geometry delta.

### A2. PCB (gate: DRC 0 errors, 0 unrouted, Gerber XOR match)
- Board outline from `BOATCREWOUTLINE.art` (Edge.Cuts). Stackup: 2 layer, 1.6 mm (confirm thickness from `shape_state.rpt` / DSN if present).
- Design rules from `senior design v2_rules.do` (§2). Net classes: default 12 mil / 12 mil; define a `Power` class if the copper shows wider traces on 3V3/VIN.
- Placement: from DSN, corrected by A0 findings. Rotation and back-side mirroring must be checked part-by-part against Gerber pad flashes.
- Copper: convert DSN `(wire (path LAYER width x y x y …) (net N))` to KiCad track segments with net assignment; DSN `(via …)` to vias; DSN polygon wires and any Gerber `G36/G37` regions to **zones** with the correct net (expect a GND pour; determine which layer(s)). Where A0 shows v2 ≠ v5, take geometry from the Gerber and assign nets by pad contact.
- Silkscreen: reference designators and text from `BOATCREWSILK_TOP.art` positions. Solder mask: KiCad-generated from pads; verify against `MASK_TOP/MASK_BOT` by XOR.
- **Validation (must all pass and be recorded in the report):**
  - `kicad-cli pcb drc --severity-all --exit-code-violations` → 0 errors (document any warnings and why they are acceptable).
  - Unrouted/ratsnest count = 0, all 35 nets present with the same pin membership as `pstxnet.dat`.
  - `kicad-cli pcb export gerbers` + `export drill` from the KiCad board, then XOR-rasterize against the `BOATCREW*` set at ≥ 1000 dpi: report % mismatched pixels per layer (copper target < 1 % after excluding silkscreen text; mask and outline similar). Hole-by-hole drill comparison: same count per tool size, positions within 1 mil.
  - `kicad-cli pcb export svg` per layer and `kicad-cli pcb render` (top/bottom, raytraced) into `docs/img/`.

### A3. Schematic (gate: ERC 0 errors, netlist == pstxnet.dat, PCB↔SCH sync clean)
- Hierarchy: root sheet + the six sub-sheets already named (MCU, PowerSupply, CAN_Bus, LoRa_Module, GPS_Module, PWM_Outputs) plus `Debug` for JTAG/test points if it keeps sheets readable. Match the original OrCAD block names from `seniordesign_board-PSpiceFiles/` (Power Supply, MCU power, MCU OUTPUTS, CANBUS module, LORA Module, Speed Controller, Steering Servo, JTAG Header) in the sheet descriptions so the lineage is obvious.
- Symbols: `MCU_ST_STM32F4:STM32F446RETx` from the KiCad library; passives from `Device:`; verify the two custom symbols (R1240N001x, TCAN1042H-Q1) pin-by-pin against the datasheets (search the web for the current Ricoh R1240N and TI TCAN1042H-Q1 datasheets; cite the revision).
- Wire everything from `pstxnet.dat` (parse it; do not hand-transcribe from `NETLIST.md`). Use the readable net names via net labels; hierarchical labels/pins between sheets; proper power symbols (`GND`, `+3V3`, and a named `VIN_RAW` power symbol); `PWR_FLAG` where needed. Keep the Allegro net name in each net's description/property so a reader can cross-reference.
- Footprint fields must point at the A1 project footprints; symbol↔footprint links must survive **Update PCB from Schematic** with zero changes (run it via the pcbnew API or `kicad-cli`, capture the diff).
- **Validation:** `kicad-cli sch erc --severity-all --exit-code-violations` → 0 errors; `kicad-cli sch export netlist` compared programmatically against `pstxnet.dat` (same nets, same pins, modulo the readable-name mapping); `kicad-cli sch export pdf` and `svg` into `docs/img/`; `kicad-cli sch export bom` → regenerate `docs/BOM.csv` with MPN, manufacturer, and description columns filled (the current BOM has MPNs for only 8 of 45 lines — fill the passives from the Allegro footprint vendor hints, e.g. `CAP_CL05_SAM` = Samsung CL05 series 0402, and mark anything you cannot pin down as `TBD` rather than guessing).

### A4. Phase A close-out
- Resolve the three open questions with copper evidence: PWM PA8/PC6 assignment, VCAP1 pin 30 vs 31, TCAN1042 pin 1/8. Update firmware **comments only** (do not change behavior in Phase A) and `README.md`.
- Commit. Tag `v1-kicad-baseline`.

---

## 6. PHASE B — V1 DESIGN REVIEW AND V2 REQUIREMENTS

Output: `docs/V1_DESIGN_REVIEW.md` and `docs/V2_REQUIREMENTS.md`.

- Take every seed finding in §3, confirm or refute it with evidence (copper, datasheet page, firmware line), rate severity (Safety / Functional / Reliability / Nice-to-have), and state the V2 disposition.
- Do the application analysis properly, with numbers:
  - **Link budget** for the 915 MHz LoRa link at SF7–SF12 with realistic antennas (module whip vs quarter-wave vs a 2–3 dBi external), TX power the RYLR module actually supports, fade margin over water, and the resulting range vs data-rate table. Recommend an SF/BW operating point and a telemetry cadence. Consider whether an SX1262-based module with a u.FL/SMA and a controlled-impedance feed should replace the RYLR header — give the trade (cost, firmware effort, range) and let Jay choose.
  - **Control loop**: what the boat needs for closed-loop heading hold and waypoint following — update rate, sensors (IMU + magnetometer, GPS with PPS at ≥ 5 Hz), and a failsafe policy (link-loss → throttle to idle within N s, rudder to neutral; low-battery → return or hold; watchdog).
  - **Power**: battery chemistry and voltage range Jay is actually using (ask in `BLOCKERS.md` if not in the repo), peak current with LoRa TX + GPS + IMU + MCU, servo/ESC power isolation (servo rail must not be the 3.3 V logic rail), reverse-polarity and fuse, TVS on VIN, bulk capacitance.
- Requirements must be numbered, testable, and traceable (`REQ-RF-01 …`, `REQ-CTL-…`, `REQ-PWR-…`, `REQ-NAV-…`, `REQ-DBG-…`, `REQ-MECH-…`). Keep V1's proven parts where they are not the problem (STM32F446, R1240N, TCAN1042, the 2-layer 3" form factor) unless the review gives a concrete reason.
- End with a **decision list for Jay** — at most ten binary/short questions whose answers change the V2 schematic (e.g. RYLR module vs SX1262; IMU choice; keep CAN or drop it; battery spec; connector family; mounting pattern). Write them to `BLOCKERS.md` under "Decisions needed". Then **proceed with your recommended defaults**, clearly labelled, so Phase C is not blocked.

---

## 7. PHASE C — V2 KICAD DESIGN

In `hardware/kicad_v2/` (a new KiCad project, `LoRa_Boat_Controller_V2`), derived from the Phase A project so lineage and library reuse are obvious.

- Schematic first, hierarchical, one sheet per subsystem, every sheet with a title block note stating which V2 requirements it satisfies.
- Minimum V2 content, pending Jay's decisions: HSE crystal (+ LSE if RTC/timestamping is wanted); status LEDs (power, link, GPS fix, fault); reverse-polarity + fuse + TVS on battery input; separate servo/ESC power rail with proper isolation from logic 3.3 V; series resistors / ESD on PWM and UART lines to headers; IMU (with magnetometer) footprint; GPS module with PPS and backup power; LoRa RF section per the Phase B recommendation with antenna keep-out; ADC battery monitoring actually usable (and current sense if cheap); IWDG in firmware; USB or a dedicated UART console header; SWD retained; M3 mounting holes on a stated pattern; CAN kept only if the review justifies it.
- PCB: place and route it. Keep 2-layer if the RF section allows a clean ground under the antenna feed; otherwise justify 4-layer. Apply the same DRC discipline as Phase A. Render it.
- Firmware: do **not** rewrite `main.c`. Produce `firmware/V2_FIRMWARE_PLAN.md` — the pin map for V2, the failsafe/watchdog behavior, the sensor drivers needed, and a link-loss test procedure. If you change the `.ioc`, do it as a new `firmware_v2/` project.
- Update `docs/BOM_V2.csv` with MPNs and a cost column with distributor pricing found via web search (note the date).

---

## 8. DOCUMENTATION AND NAVIGATION (RUNS THROUGHOUT)

The repo must be navigable by someone who has never seen it. Concretely:

- `README.md` rewritten: what the system is (one screen), the V1 → V2 story, a **clickable file map** (fix the current README — it says `hardware/allegro-original/` but the folder is `Allegro/hardware/allegro-original/`), how to open each project in KiCad 9, how to regenerate every artifact with the scripts in `hardware/kicad/tools/`, and an image strip: V1 top render, V1 schematic root, V2 top render.
- `docs/INDEX.md`: one table linking every document and image with a one-line purpose.
- `docs/img/`: all renders (PNG for photos of the board, SVG for schematics and layers), named `v1_pcb_top.png`, `v1_sch_<sheet>.svg`, `v1_layer_F.Cu.svg`, `v2_…` etc.
- `docs/NETLIST.md` regenerated from the KiCad netlist with the Allegro name, readable name, and pin list per net, plus a column "changed in V2?".
- Archive the stale pipeline files (`SESSION_HANDOFF.md`, `DIRECTIVES.md`, `STATUS.md`) to `docs/archive/` with a one-line note at the top of each saying they are superseded by `README.md` and `REPORT.md`.
- Every script writes its outputs to a path stated in its header; no output is produced by hand that a script could produce.

---

## 9. THE REPORT — `REPORT.md` AT THE REPO ROOT

Written for Jay and his lab, readable in five minutes, drillable for an hour. Markdown with embedded images from `docs/img/`. Required sections, in order:

1. **Outcome in three sentences** — what now exists, what was verified, what needs Jay.
2. **V1 reconstruction fidelity** — the table of validation results from A2/A3: DRC/ERC counts, per-layer Gerber XOR mismatch %, drill match, netlist match; side-by-side images of the fab Gerber vs the KiCad export for TOP and BOTTOM copper.
3. **Findings that matter** — the confirmed V1 defects ranked by severity, each with the evidence image or file/line reference; the resolved answers to PA8/PC6, VCAP1, TCAN1042.
4. **V2 in one page** — block diagram (draw it as SVG or Mermaid rendered to SVG), the requirement list summary, renders of the V2 board and root schematic, BOM cost delta vs V1.
5. **Decisions needed from Jay** — the list from `BLOCKERS.md`, each with your recommended default and what changes if he picks otherwise.
6. **Reproduction** — the exact commands to regenerate everything from a fresh clone.
7. **Session log** — dated, what changed, what was validated, commit hashes.

Keep an append-only `CONVERSION_LOG.md` as you work so the report's session log is a summary, not a reconstruction from memory.

---

## 10. RULES OF ENGAGEMENT

- **Phase A is fidelity, not improvement.** The fabricated board is the truth; the KiCad V1 must match it even where it is wrong. All improvements go into V2.
- **Evidence over inference.** Every claim in the review and report cites a file, a datasheet page, or an image you generated. If you cannot verify something, say so and put it in `BLOCKERS.md`.
- **Validate generated KiCad files immediately.** After writing any `.kicad_pcb`/`.kicad_sch`, load it with `kicad-cli` (and `pcbnew.LoadBoard` for boards) before doing anything else. A file KiCad will not open is worthless.
- **Never modify anything under `Allegro/`.** Read-only source material.
- **Do not change firmware behavior** in Phase A; comments and documentation only. V2 firmware is a plan plus an optional separate project.
- **Commit at every gate**; small, descriptive commits. Never force-push. Never commit backup folders or KiCad autosaves.
- **When stuck for more than ~30 minutes on one problem**, write the state to `BLOCKERS.md` with what you tried, and move to the next independent task. Do not burn hours on a Gerber parsing edge case when the DSN wires carry the same information with net names attached.
- **Ask Jay only through `BLOCKERS.md` and the report's decision list**, batched, precise, with defaults. He is the bottleneck; do not make him the scheduler.
- Web research is expected for datasheets, KiCad 9 CLI syntax, library part numbers, and distributor pricing. Cite what you used.

---

## 11. DEFINITION OF DONE

- [ ] `hardware/kicad/` opens cleanly in KiCad 9; DRC 0 errors; ERC 0 errors; 0 unrouted; schematic↔PCB sync produces no changes.
- [ ] Gerber XOR vs `BOATCREW*`: copper < 1 % mismatch per layer, drill hole-for-hole match, numbers in `REPORT.md`.
- [ ] Netlist from KiCad == `pstxnet.dat` (35 nets, all pins), proven by script.
- [ ] PA8/PC6, VCAP1, TCAN1042 questions answered with copper evidence.
- [ ] `docs/V1_DESIGN_REVIEW.md` and `docs/V2_REQUIREMENTS.md` complete with numbered, testable requirements and a link budget.
- [ ] `hardware/kicad_v2/` schematic complete and ERC clean; PCB placed and routed, DRC clean; renders in `docs/img/`.
- [ ] `docs/BOM.csv` (V1, MPNs filled) and `docs/BOM_V2.csv` (with pricing).
- [ ] `README.md`, `docs/INDEX.md`, `docs/NETLIST.md`, `docs/CONVERSION_NOTES.md` rewritten; stale pipeline docs archived.
- [ ] `REPORT.md` complete per §9; `BLOCKERS.md` lists every open decision with a default.
- [ ] All scripts in `hardware/kicad/tools/` rerun from a clean clone and reproduce every artifact.
- [ ] Everything committed on the two branches, tagged `v1-kicad-baseline` and `v2-design-draft`.

Start with §4, then A0. Go.
