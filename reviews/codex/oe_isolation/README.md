# ACT-10 - interrupting the actuator permission path

**Disposition: held for power-state and timing qualification.** The proposed TMUX1511 series switch is not inserted into CAD. ACT-04 remains the native candidate. Missing QUAL_OK, receiver, watchdog, stop and ACK sources remain disabled. This packet follows [ACT-09](../observer_retention/README.md) and records a specific circuit screen rather than another permission-state simulation.

[Annotated connection proposal](v2_oe_isolation.svg) | [Numerical screen](RESULTS.md) | [Exact contract](contract.json) | [Source ledger](sources.json)

## Proposed connections and intended behavior

Candidate **TMUX1511PWR, PW/TSSOP14**, channel 1, would interrupt the connection from U14.4 to TXU0102 U4.6. In the proposal U14.4 drives S1 pin2 through a new ACT_OE_REQUEST net. D1 pin3 stays with U4.6 and **existing R40.1** on ACT_OE. R40 remains 10 kOhm to ground. No output clamp is connected against U14's push-pull output. The switch's VDD pin 14 would use ACT-09's proposed observer island; GND pin 7 uses common ground. SEL1 pin1 needs an independently qualified ISLAND_PERMIT and an external 10 kOhm pulldown. Proposed local bypass is100 nF, with exact parts/effective values unselected. Unused SEL2/3/4 pins4/10/13 and unused signal pins5/6/8/9/11/12 would be grounded. These are review connections, not a released assembly instruction.

Permission is high only when both the main logic and the island's authority are valid. Opening the switch removes U14 drive; R40 then discharges OE. The island guard must open it before U14 loses validity, hold isolation through bounce and prevent re-enable until the fresh-ACK sequence. A low SEL request is not proof that the physical switch remains off at an unspecified supply. Missing authority defaults low and cannot be replaced with local VSERVO or a timer.

**Expected and actual electrical/copper delta: zero.** No new reference designator, native pin membership, PCB trace, BOM population or firmware behavior changes. The proposed split is explicitly unimplemented. Both converter sheets, ACT-01 exclusive source populations, U12/U13/U14 power, R40/R42, corrected copper, original Allegro and V1 evidence are preserved in the inherited input hashes.

## Why this specific switch is not accepted

The [TMUX1511 datasheet](https://www.ti.com/lit/ds/symlink/tmux1511.pdf) allows signal voltage with low supply, but its zero-supply leakage test does not bound arbitrary intermediate-supply dwell or bounce. A signal voltage allowance and fail-safe control input cannot prove continuous isolation after the observer island expires. The source ledger retains the supply-off test's waveform, load and measurement endpoint; its endpoint is not logic-low acceptance.

The separate control-off path also has an external discharge interval. Its tabulated transition time describes the start of the output change; treating it as complete OE discharge would miss R40 and total capacitance. The existing translator has documented glitch-free supply sequencing. That provision does not make an invalid upstream enable safe. Its disable-time test also uses a faster OE edge than this RC proposal. See the [TXU0102 source](https://www.ti.com/lit/ds/symlink/txu0102.pdf).

The normal signal range is 0..min(2*VDD,5.5 V). A 3.6 V request therefore requires at least 1.8 V supply within that regime. The 1.5..1.8 V interval is an additional signal-range hold; do not skip directly from valid3.005 V island operation to the zero-supply endpoint.

Three holds are independent: (1) continuous isolation at partial power, (2) the actual OE waveform, feed and switching injection, and (3) applicability of end-to-end disable timing. Passing an arithmetic budget cannot close the others. TMUX1101 was screened only as a possible small alternative and rejected because its signal path lacks the needed stated protection; no part is selected for purchase.

## How to use the screen

The model allocates R40 tolerance of 1%, initial OE 3.6 V, low target 0.8 V and total positive feed 5 uA. These are requirements/sensitivity inputs, not verified production values. R40's native value is10 kOhm; its exact resistor tolerance and identity remain unqualified. The 0.8 V target is for screening the valid main-rail corridor, not arbitrary supply collapse. The 5 uA feed must eventually include switch, OE, PCB contamination and other paths; an endpoint leakage specification does not establish it at every voltage.

Total OE capacitance includes switch drain, TXU input, routing and any probe. Cases8/10/15/20/50 pF intentionally expose sensitivity. Source table capacitances have stated bias/frequency conditions and do not prove the complete dynamic load. The model conservatively ignores helpful internal pulldowns. Positive charge injection is unbounded here; no peak/glitch claim is made.

The 245 ns downstream allocation comes from ACT-07. This optimistic screen spends55 ns on switch transition and36 ns on translator disable, with **zero** additional logic/guard delay. It adds the full RC decay from the starting voltage. This is an arithmetic screen using source timing numbers, not a guaranteed worst-case timing sum. Its output is translator high impedance, not actuator stop or remote receiver readiness. High-level loss and U14 loading also require review before a native change.

## Evidence and reproduction

[source ledger](sources.json) distinguishes document limits from typical data; [analysis.json](analysis.json) binds the model and allocations. [review notes](review_notes.json) record independent source review and limits. [input manifest](input_manifest.json) preserves279 prior-file hashes, including ACT-04 and ACT-09; [packet manifest](packet_manifest.json) binds this packet. [viewer checks](viewer_check.json) cover the diagram, zoom and guide on desktop/phone.

```text
python -B reviews/codex/oe_isolation/test_model.py
python -B reviews/codex/oe_isolation/model.py --check
python -B reviews/codex/oe_isolation/build_packet.py --check
python -B tools/quality/check_publication.py
node pm/tools/validate.mjs
```

No native command is rerun for a zero-delta rejected/held proposal. Test success means arithmetic and evidence preservation only. No hosted CI, measured waveform, fabrication, assembly, flashing or operational application is accepted.

## Next smallest circuit task

Evaluate one explicit alternative using **TXU0102's own supply-isolation behavior with a separately switched/discharged VCCA**. First establish the supply-state truth table, actual VCCA discharge/disable deadline, input backfeed and recovery/ACK behavior from source conditions. Keep U12/U13/U14 on original main 3V3, VCCB on the ACT-01 actuator rail and both exclusive source populations unchanged. Do not treat the below100 mV isolation condition as instantaneous, or native power-sequencing prose as a complete external-switch guarantee. A disconnected load switch is not automatically the specified floating supply (which limits external leakage to10 nA). The 36 ns OE delay cannot be reused as a supply-collapse delay; no maximum for that path was established by this review. Compare against this held series-switch proposal; do not reopen a broad catalog search. If the alternative cannot establish continuous disable, state the necessary response-architecture revision before any native insertion.

Only a closed contract justifies a new isolated ACT-04 copy, an explicit expected pin/net delta and captured native checks. Island charge/reverse-blocking/OV/reference shutdown, receiver/local 5V/watchdog/stop/ACK sources remain open. So do C11/VSERVO transients, full 6S input feed, leakage/damping, ADC and combined IMU2. V1 inspection, V2 vehicle applications and the future voice/text/location handheld remain distinct; measured voice/RC coexistence precedes handheld selection.
