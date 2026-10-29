# POWER-DOC-01 — readable native Power sheet

[Compare native sheets](index.html) | [Revised Power SVG](native/svg/LoRa_Boat_Controller_V2-Power.svg) | [Electrical equivalence](validation.json) | [Isolated KiCad project](source/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pro)

This presentation copy cleans up the Power sheet from the isolated VSERVO-01 candidate. It separates converter hierarchy, current/battery sensing, source selection, reservoir and test-point notes. C12's ground label no longer shares space with the diode notes. The sheet is formatted for A3 landscape. Only Power.kicad_sch changes; both converter child sheets and every component identity remain preserved.

**Expected electrical delta: zero.** This is a readable edition of VSERVO-01, not a new circuit or an assembly release. The live board, V1 source, firmware, purchasing data and original Allegro evidence remain unchanged. The independent validation compares all 128 component records, 429 pin memberships and node attributes, complete net membership, physical symbol definitions and sheet identities. Of 38 captured source files, the other 37 remain byte-identical. The ACT-01 population contract is also byte-identical.

## Navigate and review

1. Open the comparison above. Switch between **Revised** and **Baseline**, then increase the sheet zoom for small labels. The sheet viewport scrolls independently so the rest of the page remains usable on a phone. Fit resets the zoom.
2. Open the native SVG directly for a portable vector copy. The labels identify schematic node names; they do not prove measured rail voltages or physical harness orientation.
3. For editing, open the isolated KiCad project linked above and select **Power** from its hierarchy. Keep the complete source folder: it includes both converter sheets, the local libraries and C11's candidate land pattern. Do not replace the live project with this review copy.
4. Compare the validation record and native command log before accepting further edits. Changes to values, footprints, symbols, nets or population need a separate electrical contract; a layout cleanup cannot silently introduce them.

## Read the source-selection notes

| Proposed population | Fitted source diode | Absent diode | Servo supply path |
|---|---|---|---|
| BEC_ONLY | D9 | D4 | J2.2 BEC_IN → D9 → VSERVO / J3.2 |
| ONBOARD | D4 | D9 | Board +5V_BUCK → D4 → VSERVO / J3.2 |
| Review master | Neither; both marked DNP | D4 and D9 | No released assembly configuration |

The two populations are exclusive. Both converter rails are still required for board logic. Translator VCCB is supplied upstream of D4 from +5V_BUCK; an external BEC does not by itself power that logic. These are preserved schematic relationships from the [ACT-01 contract](population_contract.json), not a new wiring instruction or proof of receiver readiness.

C11 retains the held Panasonic EEEFK1C101P 100 uF / 16 V candidate and custom standard-D lands. C12 retains its existing 10 uF / 16 V identity without receiving effective-capacitance credit. The [VSERVO-01 identity/land review](../vservo_reservoir/README.md) and [VSERVO-02 transient boundary](../vservo_transients/README.md) remain the engineering basis. A readable drawing and a higher capacitor rating do not establish a permissible receiver voltage or a qualified energy sink.

## Evidence and limitations

[Expected contract](expected_contract.json), [input hashes](input_manifest.json), [native capture](native_manifest.json), [validation](validation.json), [browser check](viewer_check.json), [independent review](review_notes.json) and [packet manifest](packet_manifest.json) bind the review to exact files. Native KiCad netlist/ERC/SVG capture checks the copied project; portable checks replay those saved records. Browser screenshots and independent visual review assess this Power sheet only. Other sheets retain earlier layouts and their existing review limitations.

No routed PCB or copper was changed. Native ERC and successful rendering do not establish reservoir capacity, protection, temperature, pulse behavior, fabrication, assembly or hardware acceptance. Separate IMU2 is not integrated. Missing receiver/watchdog/stop/ACK qualifications remain disabled. The 6S requirement remains.

**Next smallest circuit task remains VSERVO-02's independent local-shunt specification:** define loaded clamp/current bounds, startup/control power, delay, recovery, hot-start pulse/repeated/continuous thermal limits, failed-open/short behavior and the separate reverse-voltage path for both populations. Keep actual unknown receiver/source limits symbolic; select no arbitrary parts. Full input-feed, leakage/damping, ADC and combined IMU2 gates remain open. Do not repeat unanswered receiver-identity questions.

V1 inspection, V2 vehicle applications and the future voice/text/location handheld remain distinct. Measured voice/RC coexistence must precede handheld hardware selection.

## Efficient restart

Inspect Git status, FILE_OWNERSHIP.md and the newest design-completion handoff first. Preserve the two unrelated v1_design.py and route_v2.py edits. Read-only replay:

```text
python -B reviews/codex/power_sheet_polish/test_equivalence.py
python -B reviews/codex/power_sheet_polish/verify_packet.py --check
python -B tools/quality/check_viewer_replay.py --check
python -B tools/quality/check_publication.py
node pm/tools/validate.mjs
```

The layout script and native runner are explicit reconstruction/capture tools for this isolated packet, not documentation refresh commands. Do not rerun primary generation or routing. Later viewer packets must capture their own PM template and update the current binding in tools/quality/viewer_replay.json; historical packets remain immutable.
