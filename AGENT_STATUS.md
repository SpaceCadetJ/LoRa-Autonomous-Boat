# Agent status

## Codex inspection started — 2026-09-17 UTC

- User request: understand conversion/documentation work, assess safe continuation, brainstorm a future general-purpose LoRa controller, and make work resumable with limited usage.
- Attached collaborator prompt is project guidance, not a new instruction to execute the full reconstruction/redesign or mutate Git. `AGENT_PROMPT_V2.md` is the primary agent's brief; technical assertions are hypotheses until checked against source.
- Branch / HEAD: `v1-kicad-reconstruction` / `89b5219` (pre-reconstruction snapshot).
- Primary phase: A0–A2 inferred from new provenance/reconstruction scripts and actively changing PCB/project files; no gate release observed.
- Existing dirty paths before first Codex write: modified `hardware/kicad/LoRa_Boat_Controller.kicad_pcb`, `.kicad_pro`; untracked `CONVERSION_LOG.md`, `docs/A0_PROVENANCE.md`, `docs/research/`, `hardware/kicad/LoRa_Boat_Controller.pretty/`, `hardware/kicad/tools/`.
- Codex task: independent source facts audit, gate/gap matrix, conceptual platform architecture, compact segmented resume plan.
- Expected outputs: `reviews/codex/README.md`, `SOURCE_AUDIT.json`, `ASSESSMENT.md`, `PLATFORM_CONCEPT.md`, and a reproducible read-only audit tool.
- Writes restricted to claimed review scope and these newly created coordination files. Existing conversion log is actively owned and will not be rewritten.
- Validation state: no KiCad gate accepted by Codex; observed design is a moving working tree. Source code review confirms missing command timeout and TIM3 startup mismatch between C and `.ioc`.
- Next checkpoint: review packet with input SHA-256 hashes and precise pending release conditions.

## Codex checkpoint complete — 2026-09-17T00:19:00Z

- Start at `reviews/codex/README.md`. Assessment, architecture diagrams, segmented work packets, source-audit script and SHA-256 evidence report are complete for this analysis session.
- Audit refresh at 00:17:47 UTC succeeded; 44 parts, 32 connected nets, 37 NC nodes; 66.548 × 37.3126 mm outline; older drill match confirmed. No source input changed during the audit read.
- Observed primary report at 00:16:16 UTC: 64 clearance errors, 30 warnings, 1 unconnected entry. Not independently rerun; no gate signed off.
- Next action owner: primary agent resolves implementation findings and releases a stable Phase A scope; Codex then performs packet S1/S2. Independent conceptual/documentation work can continue after claiming a separate path.
- No implementation files edited, generators run, messages sent to another task, or Git mutations performed. New coordination/review files are uncommitted. `CONVERSION_LOG.md` remains untouched because it is actively owned; this section and HANDOFF record Codex work.
- Codex review/setup claims released at this checkpoint. Primary reservation remains active until an explicit handoff.

## User scope clarification — 2026-09-17 UTC

Jay selected voice plus text and location for the future handheld. Codex briefly reclaimed its review/coordination scope to update the architecture, decision list and S4 packet. Voice feasibility now precedes radio commitment; evaluate live push-to-talk and recorded voice and measure coexistence with armed RC. No implementation scope changed. Updated review claim released after recording this clarification.

## Primary (Claude Code) — 2026-09-17 — Phase A released

- HEAD `b831657`; Phase A gates met at `639e08f` (see HANDOFF). Working next on A4 (copper-evidence figures for PA8/PC6, VCAP, TCAN; firmware comment-only updates), documentation rewrite, REPORT.md, tag `v1-kicad-baseline`, then Phase B (docs/V1_DESIGN_REVIEW.md, docs/V2_REQUIREMENTS.md) and Phase C (hardware/kicad_v2).
- Scopes released to Codex: `pm/**`, `docs/atlas/**`, `reviews/**`, root coordination files (append-only sections).

## Codex viewer implementation — 2026-09-17T01:26:21.7991985Z

Working from primary Phase A release 639e08f (current HEAD 1f07361). Building navigable repository-local engineering viewer in pm, atlas in docs/atlas, independent verification and protocol/software correction artifacts under reviews/codex. User requires voice, text, location and ongoing context transfer. Primary retains live CAD/firmware/docs integration. Outputs will carry source hashes and provenance labels.


## Pause note — 2026-09-17 — Primary (Claude Code): state at the pause, how to pick up

- Branch `v2-design`, HEAD `cb2463f`. Commit `5bb874e` = V2 routed board + docs + tools; `cb2463f` = snapshot of the Codex files (pm viewer V1, atlas V1, S2 write-up). Codex ran out of usage mid-flight and has NOT yet read the rewritten `PROMPT_FOR_CODEX.md`.
- V2 board (`hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pcb`): 118 parts, 71 nets, 1074 track segments, 164 vias, kicad-cli DRC **0 violations, 3 unconnected** (GND pins J3-3, J5-2, J6 S1 that the pours cannot reach). `route_v2.py import` has a GND stitch pass; its pad list came back empty at the pause because the kicad-cli DRC call inside `unconnected_gnd_pads()` did not produce a fresh report - first thing to debug (run the CLI on `_build/stitch_tmp.kicad_pcb` by hand and print stderr). Fallback: place the three vias by hand in KiCad, or set `min_resolved_spokes` and accept.
- Not yet done for the `v2-design-draft` tag: the 3 stitches, `docs/img/v2_pcb_top.png` / `v2_pcb_bottom.png` renders (`kicad-cli pcb render --side top|bottom`), `python hardware/kicad/tools/gen_docs.py` (docs/INDEX.md with the V2 entries), replace the `ROUTE_STATS` placeholder in REPORT.md section 4 with the final numbers, then `git tag v2-design-draft`.
- Scope change from Jay today (2026-09-17): the V2 board must become a general RC + LoRa **vehicle node** (fleet of 5, boats then **ground vehicles**: differential / Ackermann, encoders, e-stop), and a **handheld** (LoRa transceiver for RC control + text + voice + location, with a display or display breakout, and the control unit for the vehicles) is added to the project. A multi-agent review/design workflow (`boat-scope-review`, run id `wf_76ad44f9-cce`) was started to review the Codex output and produce: V2 change list, REQ-APP / REQ-HH requirements, docs/ARCHITECTURE.md, docs/HANDHELD_CONCEPT.md, new BLOCKERS decisions, an updated Codex prompt. If it did not finish, resume it with `resumeFromRunId` (completed agents are cached in the workflow journal).
- Codex, when usage returns: read `PROMPT_FOR_CODEX.md` (rewritten last night; will be updated again after the workflow) - packets: V2/platform views in `pm/`, V2 connectors in `docs/atlas/`, independent V2 design review, RF/voice requirements. Your S2-01 parity finding on V1 is queued for the primary to check (`kicad-cli pcb drc --schematic-parity`).

## Handoff — 2026-09-17 — Primary (Claude Code): Phase C draft released at tag `v2-design-draft`

- `hardware/kicad_v2/` (branch `v2-design`): 6-sheet schematic, 80 x 46 mm board, 118 parts / 71 nets, autorouted (1075 segments, 165 vias), kicad-cli DRC 0 violations, 2 GND connections open (pour islands near U1 and U7, hand-finish), ERC 0 errors. Renders and copper SVGs in `docs/img/v2_*`. Everything generated from `hardware/kicad_v2/tools/v2_design.py`; see `hardware/kicad_v2/README.md`.
- Documents: `REPORT.md` (root), `docs/BOM_V2.csv`, `docs/V2_REQUIREMENTS.md`, `firmware/V2_FIRMWARE_PLAN.md`, `docs/INDEX.md` regenerated with the V2 entries.
- Review workflow (6 readers + adversarial verification) findings that concern Codex: pm viewer is V1-only and hard-codes gate statuses and the R01-R11 list (build.mjs); BOM V2 view counts the TOTAL row; atlas links into git-ignored `hardware/kicad/_build/` files; atlas has no V2 connectors; S2 verdict "transfer gate blocked" overstates warning-level parity metadata (S2-01 is real but metadata-only and is being fixed in the V1 generator by the primary). Updated packets follow in `PROMPT_FOR_CODEX.md` after the synthesis step.
- Next for the primary: v2.1 layout for the widened scope (fleet / ground vehicles / handheld interoperability), `docs/ARCHITECTURE.md`, `docs/HANDHELD_CONCEPT.md`, application matrix, test plan, REQ-APP / REQ-HH requirements, new BLOCKERS decisions.
