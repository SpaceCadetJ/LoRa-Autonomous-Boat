# V2 ground connectivity correction candidate

This review localizes three real ground islands and reconnects two with **two through vias**. The candidate still has one missing ground connection at U1 pad 12. It is **not approved for fabrication**.

The live design and pre-existing routing script were inspected without modification. The correction is isolated in [candidate/LoRa_Boat_Controller_V2.kicad_pcb](candidate/LoRa_Boat_Controller_V2.kicad_pcb). Root integration must preserve this evidence and regenerate the active review, assembly-source hashes and viewer before publication.

## Exact result

| Native KiCad 9.0.7 check | Source | Candidate |
|---|---:|---:|
| Missing connections | 3 | **1** |
| Other DRC errors | 0 | 0 |
| Other DRC warnings | 101 | 101 |
| Schematic parity findings | 212 | 212 |
| Footprints | 118 | 118 |
| Track segments | 1,074 | 1,074 |
| Through vias | 164 | 166 |

[Structural verification](verification.json) passes: every original footprint, track, via, net, board outline, rule/setup and zone setting is unchanged. The ordinary DRC findings and schematic-parity findings are exactly equal before and after. The only added objects are the two specified GND vias, followed by a zone refill. No warnings were suppressed or rule limits relaxed. [Before DRC](drc_before.json) and [after DRC](drc_after.json) include all track errors and schematic parity.

Coordinates below are absolute KiCad board coordinates in millimetres. The board origin is `(50, 50)`. The repeated `(50, 50)` coordinates in native unconnected reports are zone anchors, not the locations needing repair.

| Isolated circuit | Original affected pads | Correction |
|---|---|---|
| STM32 digital ground / R16 ground | U1.18 `(92.750,72.675)`, U1.31 `(99.250,72.675)`, R16.2 `(96.825,76.000)` | GND via at **`(93.700,74.000)`** |
| USB protection ground | U7.2 `(106.8625,59.500)`; U7 is USBLC6-2SC6 | GND via at **`(108.000,59.000)`** |
| Remaining MCU ground | U1.12 `(90.325,68.750)`; existing island via `(92.0137,68.527)` | Open; requires a separate local routing correction |

Both added vias span F.Cu and B.Cu, with a **0.60 mm copper diameter and 0.30 mm drill**, matching the existing default via geometry. Each joins a pad-bearing isolated front copper region to the main back ground region. Their stable UUIDs and source/candidate hashes are in [candidate_manifest.json](candidate_manifest.json).

- Source SHA-256: `6595d3b58e4a54b1d3ecbf93a69c93202503dbabcf9d279a6a578df1601d0d26`.
- Candidate SHA-256: `1b959ee8c2499d2a65359b695a2f70efd5a588f05ffcaf11f32cf9de18d0cce9`.
- Repeated generation with a fixed native UUID seed produced this candidate byte-for-byte twice. UUID replacement alone was insufficient because random object order affected the refill; the fixed seed resolves that reproducibility issue.

## Evidence and reproduction

[Ground localization before](ground_before.json) and [after](ground_after.json) contain filled contour geometry, pad/via UUIDs and positions. The geometric model joins filled polygons through plated pads, vias and GND track endpoints. It is a localization aid; native DRC remains authoritative. The small F.Cu contour near `(118,88.6)` has no contained pad or via and persists outside this model's main cluster; this does **not** identify a fourth native unconnected item. Center-containment and endpoint-only geometry cannot prove complete connectivity of every copper shape.

The generator uses the existing immutable [publication source snapshot](../../publication/native-review/inputs/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pcb), whose bytes match the live board examined at the start of this packet. It rejects a source hash mismatch. This preserves reproduction after the live design changes. The copied candidate project/libraries retain the source settings, including its sibling V1 footprint-library reference.

From the repository root using KiCad 9's Python and CLI:

```text
python reviews/codex/design_completion/ground/make_candidate.py
kicad-cli pcb drc --format json --all-track-errors --schematic-parity --severity-all --output reviews/codex/design_completion/ground/drc_after.json reviews/codex/design_completion/ground/candidate/LoRa_Boat_Controller_V2.kicad_pcb
python reviews/codex/design_completion/ground/verify_candidate.py
```

`make_candidate.py` always creates a new candidate from the frozen source and replaces the candidate output; it does not add repeated vias to an existing candidate. It never writes live CAD. The deterministic KiCad UUID seed applies only to this helper process. Running the full primary router is unnecessary.

## Next smallest task

Correct the remaining U1.12 island while retaining the two verified vias. Its front copper bounds are `x=88.907152–93.692477`, `y=66.519317–69.424500`; its back bounds are `x=87.787763–92.951346`, `y=64.920400–69.947490`. The existing through via is UUID `d5ca61cd-93b8-468a-be3a-6a8f5aa0d429` at `(92.0137,68.527)`.

A bounded search found no default through-via site joining this island directly to the main copper, no clear straight bridge within 3 mm from its pad/via, and no clear bridge within 1.5 mm from the copper edge with a 0.25 mm or 0.15 mm trace. Clearance prechecks used 0.17 mm as a search margin; final DRC used unchanged native project rules. These searches are not proof that no route exists. Inspect the local fencing signal routes and make a minimal reviewed escape or reroute; do not extend this result into blanket stitching, smaller drills or relaxed clearances. `find_via_sites.py`, `find_bridge.py` and `find_edge_bridge.py` retain the search method.

After a remaining-ground fix, rerun native connectivity, all track errors, parity and exact structural-change review. The pre-existing schematic warning, circuit/voltage-domain holds, 101 layout warnings and 212 parity findings still require their own dispositions before any fabrication release. None of this packet demonstrates electrical operation on hardware.
