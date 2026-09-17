# MCU ground escape — independently checked candidate

The remaining U1 pin 12 ground island is connected in this isolated candidate. It builds on the [two-via ground correction](../ground/README.md), preserves all 118 footprints and their pad assignments, and introduces no new native DRC violations. This is a routing correction, not fabrication approval or hardware qualification.

## Exact candidate and changes

- Input PCB SHA-256: `1b959ee8c2499d2a65359b695a2f70efd5a588f05ffcaf11f32cf9de18d0cce9`.
- [Candidate PCB](candidate/LoRa_Boat_Controller_V2.kicad_pcb) SHA-256: `49a8aa88cf61e8b6272ce13a0d5a5a6a3c6b81aeba057ebcd4ca15a6262c37b2`.
- Move existing GND via `d5ca61cd-93b8-468a-be3a-6a8f5aa0d429` from **(92.0137, 68.5270)** to **(91.6500, 69.0000) mm**. Preserve its 0.6 mm diameter, 0.3 mm drill, through layers and GND assignment.
- Replace one B.Cu NRST segment `c9389eec-ff39-4a32-a348-e01f86895af3` with four 0.25 mm segments. Both original endpoints remain identical; the new path uses horizontal, vertical and approximately 45-degree segments. Full coordinates are in [candidate_manifest.json](candidate_manifest.json).
- Replacement NRST route length is **7.813660 mm**, replacing **6.852713 mm**: an increase of **0.960947 mm**. No timing-critical oscillator or RF trace is modified.
- Refill existing zones. The two earlier GND stitching vias remain present.

## Why this works

U1 pin 12 and its former via joined a narrow isolated B.Cu strip bounded by NRST and PWM_ESC_PC6. The F.Cu island was also bounded by nearby MCU fanout. A bounded 0.1 mm-grid search over 14 × 14 mm found no same-layer 0.15 mm escape at 0.17 mm clearance; that result is search evidence, not proof that every possible route is impossible.

The NRST detour creates space under the existing F.Cu ground copper for the relocated ground via to reach the main B.Cu ground fill. The native refill/connectivity engine then reports zero unconnected items. The via's old F.Cu ground-track endpoint remains connected through the same ground fill; it is not left electrically isolated.

## Verification and limitations

| Check | Two-via input | Final candidate |
|---|---:|---:|
| Native ordinary DRC errors | 0 | 0 |
| Silkscreen warnings | 101 | 101 |
| Unconnected items | 1 | **0** |
| Schematic parity issues | 212 | 212 |
| Footprints, pad assignments and geometry | baseline | identical |

The 101 warnings retain the same categories: 2 edge clearances, 61 silkscreen-over-copper and 38 overlaps. Parity issues are retained for the broader project review; this packet does not classify or waive them. The unchanged electrical circuit still requires the project-wide electrical audit and hardware validation. Native DRC rules were not weakened or suppressed.

The final candidate was generated twice with the identical hash above under **KiCad 9.0.7**. [comparison.json](comparison.json) records structural checks; [drc_after.json](drc_after.json) is the native report. `make_candidate.py` uses a fixed KiCad UUID seed so repeated runs remain reviewable. It writes only the candidate folder and evidence in this packet, and refuses a changed input hash. `compare_candidate.py` verifies all footprints/pads and restricts modified tracks to the declared change.

Reproduce with KiCad's bundled Python, then run:

```text
python reviews/codex/design_completion/mcu_ground/make_candidate.py
kicad-cli pcb drc --format json --severity-all --schematic-parity -o reviews/codex/design_completion/mcu_ground/drc_after.json reviews/codex/design_completion/mcu_ground/candidate/LoRa_Boat_Controller_V2.kicad_pcb
python reviews/codex/design_completion/mcu_ground/compare_candidate.py
```

The candidate folder includes the current project rules, schematic files and reference libraries for equivalent native checking. `local_0.png` / `local_1.png` and `local_geometry.json` show **the two-via input before this repair**, not final fabrication artwork. `search_escape.py` is an exploratory bounded search; its empty path does not certify routability or manufacturing limits.

## Integration handoff

Root may integrate only the candidate PCB after confirming its hash and the live board's expected pre-repair hash. Run the full project native review and update current manufacturing/viewer evidence from that result. This child task did not modify live CAD, live net assignments, original Allegro evidence, Git history or generator/routing tools. The next smallest task is the root's fresh full review of the integrated PCB, followed by explicit disposition of remaining electrical/parity and silkscreen findings.
