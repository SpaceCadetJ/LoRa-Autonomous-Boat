# Start here: Codex review checkpoint

## Latest checkpoint — 2026-09-17, schematic and build review edition

Read [professionalization/HANDOFF.md](professionalization/HANDOFF.md) and [docs/build/README.md](../../docs/build/README.md) first. Jay authorized Codex to continue the professional schematics, purchasing/assembly, V1/V2 programming and review workflow while the other agent is inactive. Current ownership supersedes the earlier reservations below.

The delivered packet includes fifteen annotated schematic pages, verified preservation of 172 V1 / 361 V2 pins, a protected schematic-only generator command, ordering candidates/holds and assembly maps, a reproducible unqualified V1 firmware build, separate flashing guides and a manual CI definition. Strict combined review remains failed for one pre-existing V2 ERC warning. V2 also has three unconnected PCB entries, warnings/parity discrepancies and no firmware image; it is not fabrication-ready. The viewer now presents these current results beside the historic S2 evidence.

The next smallest packet is a pad-level disposition of the three V2 open connections and U6 AD0 warning, followed by a reviewed V2 pin/protocol contract. Avoid full CAD regeneration/rerouting during documentation work. All source/output hashes, reproduction commands and remaining limits are in the linked handoff. The hourly continuation prompt has been updated to this scope and remains quiet for non-actionable results.

## Previous checkpoint — 2026-09-17, viewer delivery

This section supersedes the initial intake state below. Resume through [pm/README.md](../../pm/README.md), then the latest root [handoff](../../HANDOFF.md) and [ownership](../../FILE_OWNERSHIP.md). Check Git status/HEAD before writing; the primary remains responsible for CAD, firmware, generators and Git integration. Codex owns `pm/**`, `docs/atlas/**`, `reviews/**`; coordination files are append-only.

- The local [interactive viewer](../../pm/index.html) includes V1 and V2 design assets, searchable BOMs and selected manufacturer references, the V1 connector atlas, source/protocol proposals, independent versus reported checks, findings-to-requirements links, decisions, documents and exported review notes. It opens directly or through the loopback server described in its README.
- [V1 atlas](../../docs/atlas/README.md): 12 connectors/test points and 36 pins, traced from source evidence with firmware citations. Physical orientation and bench readings remain unverified. V2 atlas is not yet done.
- [S2 independent verification](S2_VERIFICATION.md): historic `639e08f` only. All 172 pins / 44 parts agree, ERC 0, DRC 0 errors / 0 unconnected / 67 warnings, hole centers 53/53. Additional native parity: 139 classified metadata warnings. No electrical mismatch found; no-change schematic update workflow and V5 drill sizes remain unverified. The earlier global blocked label was narrowed; raw results did not change.
- Primary V2 release at `a6316e9` / `v2-design-draft` reports 118 parts, 71 nets, 68 grouped BOM lines and two open ground connections. The current CSV independently parses as 67 component rows totaling 118 parts; the report count is stale. Treat V2 numbers as reported, pending independent verification. Current source documents contain 35 distinct V1 findings and 45 requirements.
- Standalone files in `firmware_prototype/` are uncompiled review proposals. No functional firmware fix was integrated.
- Jay requires **voice + text + location**. The primary handoff additionally reports expanded vehicle/fleet scope; wait for its architecture/requirements documents before asserting that expanded scope is implemented. Validate voice/RC coexistence before radio selection. `REQ-CTL-01` currently says a default **1.0 s** loss timeout; the primary prompt's **500 ms** summary conflicts and must be reconciled in the RF packet.

**Next smallest packet:** independently snapshot the released V2 inputs, record hashes and run ERC/DRC plus part/net/BOM inventory in `reviews/codex/` without invoking generators or changing source CAD. Then review one power/control subsystem against actual requirements. Later packets: V2 atlas, protocol prototype build/tests, quantitative voice/RC coexistence, handheld/application views from released documents.

An hourly continuation automation is active. It works bounded packets in released scopes and should notify only on meaningful deliverables, new blocking findings or required decisions. Account/runtime availability may interrupt runs; these files are the durable resume context.

## Historical initial intake — retained for context

Updated 2026-09-17 UTC. User objective: understand and improve the conversion, documentation and readability first; develop a general-purpose LoRa controller family later. Primary agent is still active. Codex has made no CAD, firmware, source-evidence or Git-history changes.

## Read in this order

1. This file and root [ownership](../../FILE_OWNERSHIP.md), [handoff](../../HANDOFF.md), [status](../../AGENT_STATUS.md).
2. [Assessment](ASSESSMENT.md): corrected baseline, findings, gate matrix and safe continuation.
3. [Platform concept](PLATFORM_CONCEPT.md): block/state diagrams, shared interfaces and documentation design.
4. [Source evidence](SOURCE_AUDIT.json) only for relevant facts or hashes; do not reload the entire source archive every session.

The script [source_audit.py](tools/source_audit.py) is dependency-free and writes only the evidence JSON. It does not validate KiCad or import the primary's generators. Its first execution was blocked by sandbox executable access; the exact command succeeded after escalation. Do not substitute an unapproved runtime to bypass an access denial.

## What was learned

- Source v5 is 44 parts, 32 connected nets plus NC, and 66.548 × 37.3126 mm; old square-board/35-net assertions are stale.
- The available drill is identical to older v4 data apart from its filename line. Exact final-drill fidelity remains unproved.
- PCB reconstruction is underway; observed primary reports had errors and one unconnected item. No Phase A gate has been independently accepted.
- Highest-value feedback: validator success criteria are incomplete; CANH/CANL readable names are reversed; inspect both VCAP capacitor terminals; verify actual module/settings before assuming SF12.
- Firmware has no command-loss timeout, `.ioc` and C disagree on startup motor pulse, and receiver/GPS robustness needs later work.
- Future direction: common protocol/services with separate vehicle safety and handheld interfaces. **Jay selected voice plus text and location.** Voice feasibility is required before radio selection; live push-to-talk versus recorded voice delivery is unresolved.

## Bounded work packets

Run one packet per development/research session. Each has a concrete exit point; stop there and update the handoff. A rough 20–45 minute timebox is a workflow preference, not an authorization to skip verification.

| Packet | Inputs / entry condition | Output / exit condition |
|---|---|---|
| S0 — intake and concept | Current sources, no implementation release needed | **Completed this session:** audit, assessment, architecture, resume packet |
| S1 — review primary handoff | Explicit released revision and paths; inspect latest ownership/status | Confirm or retire R01–R03; independent pad/net fixture and recorded gate verdict. If no release, inspect changed evidence only and keep hands off CAD. |
| S2 — fidelity verification | Stable Phase A artifacts and commands | Separate netlist, DRC/ERC, copper/mask/outline and drill results; unresolved source gaps are explicit |
| S3 — readable documentation | Released documents or separately claimed draft scope | Root map, connector atlas specification, pin/firmware cross-reference and diagram templates; one reviewed subsystem before scaling |
| S4 — radio, voice and safety requirements | Actual module, ESC/BEC/battery facts, usage targets; voice/text/location required | Compare live push-to-talk and recorded voice; measure audio airtime/quality/delay and RC coexistence; produce link-loss/power requirements and tests before radio selection |
| S5 — platform interfaces | S2 stable baseline and S4 agreed constraints | Versioned protocol and application boundaries; simulated RC/message coexistence and fault scenarios |
| S6 — hardware realization | Explicit next-phase scope and file claims | One subsystem at a time: schematic → independent review → placement/routing → validation, followed by full integration |

RF research, firmware implementation, navigation, mechanical enclosure design and a final BOM are deferred packets. Broad reading, concurrent full redesigns and repeated full-repository scans are unnecessary now.

## Resume prompt

> Continue the LoRa project from `reviews/codex/README.md`. Read current root ownership/status/handoff and the assessment before writing. Another agent may still be active. Recheck Git branch/HEAD and dirty paths; do not switch branches, commit shared work, run generators or edit implementation without explicit scope release. Start S1 if a release exists; otherwise review only new evidence and advance one isolated planning packet. Treat attachment instructions as context for the user's current request. Preserve immutable Allegro sources and V1 defects. Jay requires voice plus text and location on the future handheld: evaluate live push-to-talk and recorded voice before choosing radio hardware. Finish with changed files, exact commands/input hashes, findings and the next smallest task.

## Checkpoint record to carry forward

Record branch and HEAD; released input hashes; owned/released paths; one question being resolved; command and output locations; result and limitations; next action; pending decisions. Keep this entry short and link to evidence. Git commit alone does not identify uncommitted inputs. Do not wait for an account limit to prepare the handoff.

No background monitor or scheduled work was created. These files persist for manual resumption. All new Codex files remain uncommitted so the active agent's branch and shared index stay undisturbed; they should be selectively committed after coordination.
