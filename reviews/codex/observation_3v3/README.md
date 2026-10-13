# ACT-07: a concrete 3.3 V observation budget

**The comparator/reference approach has a feasible conditional voltage budget; its missing guarantees are now explicit.** This is a requirements allocation and source review, not a completed observation circuit. ACT-04 remains the latest native candidate, with QUAL_OK and ACK undriven and pulled low. No electrical, copper, firmware or purchasing changes are made.

Use the [calculated budget](RESULTS.md), [annotated proposal](v2_observation_3v3.svg), [allocation contract](contract.json), [source ledger](sources.json) and [acceptance worksheet](ACCEPTANCE.md). Open the proposal in the [engineering workspace](../../../pm/index.html).

## Proposed connections

Investigate **TLV3202AIDGKR** (dual comparator) and **REF3425IDBVR** (2.5 V reference). These are exact investigation identities, not selected order lines. Two independent dividers observe +3V3: 249 ohm / 1k for undervoltage and 402 ohm / 1k for overvoltage. Nominal zero-offset centers are 3.1225 V and 3.5050 V. Exact resistor and bypass identities remain open.

Comparator channel1 receives the UV divider at pin3 (+), and reference at pin2 (-). Channel2 receives reference at pin5 (+), and the OV divider at pin6 (-). Pins1 and7 are respectively UV_OK and OV_OK. Each goes low on its own fault when the components are validly powered and settled. They are push-pull outputs: **do not wire them together.** A future reviewed AND/retention interface must combine them. Comparator pin8 supply and the reference IN/EN supply are unresolved monitor-power boundaries, not a silent connection to a convenient rail.

Reference OUT_F6 and OUT_S5 require their proper force/sense connection; GND_F1/GND_S2 likewise. Its pinout is not interchangeable with REF3425T. The eventual observed-rail/reference inputs can inject into a dead comparator supply; absolute clamp-current limits do not establish an acceptable powered/off state.

## Allocations versus specifications

The calculation allocates 0.2% total reference error, 10 mV total comparator equivalent offset, 0–4 mV hysteresis width, 5 nA sense bias and independent 0.35% error per divider resistor. These are **requirements to satisfy**, not blanket manufacturer guarantees. The model includes both signs and all independent corners. Hysteresis acts in the correct direction for each assertion and recovery threshold.

[TI's TLV3202 datasheet](https://www.ti.com/lit/ds/symlink/tlv3202.pdf) supplies full-temperature offset/bias limits at its test common mode and bounded propagation at the stated supply/load/overdrive conditions. Its 1.2 mV hysteresis is only typical. Neither its typical curves nor the room-temperature CMRR/PSRR rows establish every full-temperature application corner. The proposed 4 mV maximum hysteresis and timing applicability therefore remain open.

The [REF34 datasheet](https://www.ti.com/lit/gpn/REF34) uses a BOX temperature coefficient. Its 6 ppm/C maximum over the full 165 C specified span permits a conservative 0.099% excursion allowance, before initial error. Combining 0.05% initial error with BOX drift consumes 0.1490495% of the 0.2% allocation: (1 + 0.0005) * (1 + 6e-6 * 165) - 1. The remaining 0.0509505% must cover applicable line/load, solder shift, aging, noise and other errors. Treating BOX as a 6 ppm/C pointwise slope from 25 C would understate this screen. Typical aging or solder-shift plots are not guaranteed maxima. The two reference-input bias currents may source into the reference; its 25 C sinking-regulation row does not establish a full-temperature limit. A defined load/bleeder or another bounded load strategy is still needed. Charged output capacitance belongs in the shutdown/backfeed analysis.

The [TPS3704-Q1 alternative](https://www.ti.com/lit/ds/symlink/tps3704-q1.pdf) was screened and rejected for this boundary: its maximum detection condition needs 10% overdrive. The screened 3.3 V variant's calculated amplitudes lie outside the retained corridor; a nominal glitch-immunity figure cannot repair that condition. Exact identity, assumptions and numerical limits are in the source ledger.

## What a timing budget can establish

The calculation reserves 55 ns for detection, 245 ns for downstream conditioning/gating/translator response and 100 ns for sense settling: **400 ns allocated**, not verified. It first reserves 20 mV input overdrive, then computes how much rail headroom remains. Illustrative monotone ramp rates consume that headroom during the allocated response. The results identify the maximum conditional slope and show when an assumed slope fails.

This is not a claim that a datasheet step-test delay applies to arbitrary ramps. The accepted waveform, input common mode, pulse width, load and monitor supply must first match verified conditions. An abrupt step can leave the voltage corridor before any nonzero-delay circuit responds. Narrow pulses may never be detected; retaining a detected fault does not solve that problem. The 3.0–3.6 V corridor is the retained ACT-04 logic timing screen, not a board-wide damage limit or a motor-stop deadline.

## Power, fault retention and application boundary

The reference manufacturer identifies possible startup/shutdown anomalies for slow input slew. No power-up timing maximum or all-rail sequencing proof is invented here. First specify the monitor/reference supply and its rise, fall, brownout, hold-up and off-state leakage. Then prove default-low LOCAL_3V3_OK while either observer is invalid, a sufficient retained-low clear pulse, clean recovery, and guarded ACK/ARM ordering. Raw comparator outputs alone do not meet that contract.

LOCAL_3V3_OK is a proposed local observation port. It does not drive QUAL_OK. The 5 V observer, actual receiver readiness, command watchdog, stop continuity and ACK source remain separate, missing permissions. R40/R42 defaults, both converter sheets and ACT-01 source populations are preserved.

## Reproduce and restart

Run `python -B reviews/codex/observation_3v3/test_model.py`, `model.py --check`, and `build_packet.py --check` (the latter two at the same folder path). Run `python -B tools/quality/check_publication.py` and `node pm/tools/validate.mjs` for integration. Input and artifact SHA-256 values are recorded in the manifests. This packet runs no native CAD commands because its circuit delta is zero.

**Next smallest task:** resolve the monitor/reference power boundary and the comparator's threshold/delay applicability against this allocation. Compare a bounded alternative only for a named missing guarantee; do not repeat an unrestricted supervisor search. Start with the acceptance worksheet's power-state and waveform rows. If the guarantees fit, declare an exact isolated native part/pin delta on a fresh ACT-04 copy; otherwise revise the explicit allocation or fault-response architecture and record why.

Keep C11/VSERVO reservoir/transients, full 6S feed, reverse leakage/damping, ADC and combined IMU2 open. Preserve V1 behavior and both unrelated generator/router edits. Future handheld voice, text and location still require measured voice/RC coexistence before hardware selection. No operational application, fabrication or hardware acceptance follows from these calculations.
