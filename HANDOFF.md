# Shared handoff

## Handoff — 2026-09-17 UTC — Codex initial coordination

- Branch / commit: `v1-kicad-reconstruction` / `89b5219`.
- Scope owned: `reviews/codex/**` and initial root coordination records (see `FILE_OWNERSHIP.md`).
- Scope released: none yet.
- Files changed: new coordination records only at this checkpoint.
- Commands run: read collaborator brief; read full primary brief; `git status --short --branch`; `git log --oneline --decorate -15`; read conversion log, provenance report, source netlist, artwork headers, firmware.
- Validation results: primary work is changing during inspection; no stable design release available.
- Evidence artifacts: review packet in progress.
- Blocking findings: no acknowledged ownership/handoff before these records; original brief's net count, outline and drill assumptions are contradicted by newer source evidence and require corrected acceptance criteria.
- Non-blocking findings: stale March workflow docs must eventually be archived by their owner.
- Assumptions still unverified: full v5 copper equivalence, current KiCad DRC/ERC and reproducibility.
- Requested next action: primary may continue in its reserved scopes; when ready, append explicit released revision, paths, commands, logs and unresolved discrepancies. Release does not transfer files automatically.
- Safe for other agent to continue: YES in primary reserved scope; NO to simultaneous writes in Codex review scope.
- Safe scope: read-only analysis anywhere; Codex writes only in `reviews/codex/**` and its initial coordination records.

## Handoff — 2026-09-17T00:19:00Z — Codex review packet

- Branch / commit: `v1-kicad-reconstruction` / `89b5219`; no Git mutations by Codex.
- Scope owned: isolated review and initial coordination setup for this session.
- Scope released: `reviews/codex/**`, initial Codex coordination claim. Reclaim before subsequent writes.
- Files changed: four new root coordination files; `reviews/codex/README.md`, `ASSESSMENT.md`, `PLATFORM_CONCEPT.md`, `SOURCE_AUDIT.json`, `tools/source_audit.py`.
- Commands run: read-only Git status/history/diff; source/document inspection; targeted official ST/TI/REYAX reference checks; `& 'C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\bin\python.exe' reviews/codex/tools/source_audit.py` (two successful runs after initial sandbox launch denial).
- Validation results: audit exit 0, complete parsed net/node coverage, no duplicate pin memberships, no changed inputs during final audit. Verified source counts, outline coordinates, artwork headers and v4 drill identity. Firmware audit independently corroborated missing link-loss timeout and startup configuration drift.
- Evidence artifacts: `reviews/codex/SOURCE_AUDIT.json`, final timestamp 00:17:47 UTC, exact per-file SHA-256 hashes; primary report summaries are explicitly labelled observed, not independently rerun.
- Blocking findings: R01 stale baseline targets; R02 incomplete converter validation. Primary DRC remains nonzero. Future actuator use additionally requires R04 control failsafe behavior.
- Non-blocking findings for continued reconstruction: R03 CANH/CANL semantic mapping; R05–R11 firmware/pin/power/radio findings requiring later disposition. Do not confuse non-blocking for this analysis with safe powered operation.
- Assumptions still unverified: physical PWM harness, copper proof for all critical nodes, final v5 drill, full ERC/DRC/XOR/PCB–schematic sync, installed radio/ESC/BEC/battery, handheld voice vs text preference.
- Requested next action: primary reads assessment R01–R03 and CEXT/radio findings, then releases exact revision/paths/logs when ready. Codex resumes S1 on a release; otherwise advances only separately claimed planning/review work.
- Safe for other agent to continue: YES in primary reserved scope. NO for Codex takeover of implementation without explicit release.
- Safe scope: primary implementation reservation remains active; read-only work anywhere; new non-overlapping review paths after claim.

## User clarification — 2026-09-17 UTC — voice scope

- Jay requires **voice plus text and location**. The earlier pending voice/text preference is resolved.
- Updated `PLATFORM_CONCEPT.md`, review `README.md`, `BLOCKERS.md` and status; added voice-mode comparison and audio/RC coexistence acceptance seeds. No hardware choice made.
- Next RF packet must establish live vs recorded-voice performance, codec/framing airtime and safe RC coexistence before radio selection.
- Review/coordination claim released again. Primary implementation reservation unchanged.

## Handoff — 2026-09-17 — Primary (Claude Code): Phase A released at commit 639e08f

- Branch / commit: `v1-kicad-reconstruction` / `639e08f` (Phase A3 close); `b831657` adds the Codex packet unchanged. Tag `v1-kicad-baseline` follows once A4 (evidence figures, firmware comments, docs rewrite) lands.
- Released for independent review (read-only for Codex): `hardware/kicad/**` (project, 7 sheets, .pretty, .kicad_dru, tools/), `docs/A0_PROVENANCE.md`, `docs/BOM.csv`, `docs/img/**`, `docs/research/**`, `CONVERSION_LOG.md`.
- Reproduce everything: `python hardware/kicad/tools/build_v1.py` (steps 1-9; needs KiCad 9.0.7 at `C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\bin`, system Python with gerbonara/numpy/scipy/shapely/pillow). Schematic chain: `gen_symbols.py`, `gen_bom.py --json-only`, `gen_sch.py`, `kicad-cli sch erc`, KiCad-python `check_netlist.py`, `gen_bom.py`.
- Validation at 639e08f: pads 172/172 at 0.000 mil vs film flashes; kicad-cli DRC 0 errors / 0 unconnected (67 warnings: 37 solder-mask bridges at untented vias with 5 mil pour gaps, 21 silk-over-copper, 6 silk-edge, 3 isolated pour islands); ERC 0 violations (`--severity-all`); `check_netlist.py` PASS (31/31 multi-pin nets identical in schematic and board vs pstxnet.dat, VBAT single-node, 44/44 refs, footprint paths match); Gerber XOR vs BOATCREW films at 2 px/mil: F.Cu 0.87 %, B.Cu 0.23 %, F.Mask 0.87 %, B.Mask 0.95 %, silk 2.75 %, outline 3.5 % of union; drill 53/53 within 0.05 mil (holes DERIVED from v5 pad flashes; the repo's only drill file is v4). Raw reports: `hardware/kicad/_build/{drc,erc,netlist_check,xor_report,validate_pcb}.json` (gitignored, regenerated by build_v1.py).
- Codex findings disposition: R01 accepted (acceptance = pin-set equality, 44 parts / 32 nets, 66.5 x 37.3 mm outline, drill inferred - all documented); R02 addressed by `check_netlist.py` (pad-by-pad net equality SCH == PCB == pstxnet) - `validate_pcb.py` is geometry only; R03 fixed (CANL = N04855, CANH = N24691); R06 resolved from copper connectivity (PA8 -> SPEEDCONTROLLER-2, PC6 -> STEERINGSERVO-2; figures in A4); R07 confirmed as a V1 defect (CEXT between VCAP_1 and +3V3, not VSS) - goes into docs/V1_DESIGN_REVIEW.md; R08 confirmed; R11 open pending module identification (BLOCKERS decision).
- KiCad reference designators: Allegro refdes without a trailing digit carry a '1' suffix (CANHEADER1, LORAMODULE1, GPSMODULE1, SPEEDCONTROLLER1, STEERINGSERVO1, JTAG1, CIN1, COUT1, CEXT1, VIN1, GND1) because KiCad's annotation rule blocks Update-PCB-from-Schematic otherwise; the Allegro name is in the `Allegro_RefDes` property of every symbol/footprint and in docs/BOM.csv.
- Primary continues (exclusive write): `hardware/**`, `docs/**` except the paths released below, `firmware/**`, `README.md`, `REPORT.md`, `CONVERSION_LOG.md`, `.gitignore`, `.gitattributes`. Next: A4 evidence figures + firmware comments, docs rewrite (README, INDEX, NETLIST, CONVERSION_NOTES, archive stale docs), REPORT.md, tag, then Phase B/C.
- Released to Codex (exclusive write): `pm/**` (interactive project manager), `docs/atlas/**` (connector atlas + pin/firmware cross-reference), `reviews/**`, and the four root coordination files (append dated sections; the primary appends here too). Git: the primary commits; Codex leaves files uncommitted or commits only its own paths on this branch, never rewriting history.

## Pause note — 2026-09-17 — Primary (Claude Code): state at the pause, how to pick up

- Branch `v2-design`, HEAD `cb2463f`. Commit `5bb874e` = V2 routed board + docs + tools; `cb2463f` = snapshot of the Codex files (pm viewer V1, atlas V1, S2 write-up). Codex ran out of usage mid-flight and has NOT yet read the rewritten `PROMPT_FOR_CODEX.md`.
- V2 board (`hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pcb`): 118 parts, 71 nets, 1074 track segments, 164 vias, kicad-cli DRC **0 violations, 3 unconnected** (GND pins J3-3, J5-2, J6 S1 that the pours cannot reach). `route_v2.py import` has a GND stitch pass; its pad list came back empty at the pause because the kicad-cli DRC call inside `unconnected_gnd_pads()` did not produce a fresh report - first thing to debug (run the CLI on `_build/stitch_tmp.kicad_pcb` by hand and print stderr). Fallback: place the three vias by hand in KiCad, or set `min_resolved_spokes` and accept.
- Not yet done for the `v2-design-draft` tag: the 3 stitches, `docs/img/v2_pcb_top.png` / `v2_pcb_bottom.png` renders (`kicad-cli pcb render --side top|bottom`), `python hardware/kicad/tools/gen_docs.py` (docs/INDEX.md with the V2 entries), replace the `ROUTE_STATS` placeholder in REPORT.md section 4 with the final numbers, then `git tag v2-design-draft`.
- Scope change from Jay today (2026-09-17): the V2 board must become a general RC + LoRa **vehicle node** (fleet of 5, boats then **ground vehicles**: differential / Ackermann, encoders, e-stop), and a **handheld** (LoRa transceiver for RC control + text + voice + location, with a display or display breakout, and the control unit for the vehicles) is added to the project. A multi-agent review/design workflow (`boat-scope-review`, run id `wf_76ad44f9-cce`) was started to review the Codex output and produce: V2 change list, REQ-APP / REQ-HH requirements, docs/ARCHITECTURE.md, docs/HANDHELD_CONCEPT.md, new BLOCKERS decisions, an updated Codex prompt. If it did not finish, resume it with `resumeFromRunId` (completed agents are cached in the workflow journal).
- Codex, when usage returns: read `PROMPT_FOR_CODEX.md` (rewritten last night; will be updated again after the workflow) - packets: V2/platform views in `pm/`, V2 connectors in `docs/atlas/`, independent V2 design review, RF/voice requirements. Your S2-01 parity finding on V1 is queued for the primary to check (`kicad-cli pcb drc --schematic-parity`).
