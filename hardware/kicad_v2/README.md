# LoRa Boat Controller V2 — KiCad 9 project (Phase C draft)

Electrical intent is generated from `tools/v2_design.py`; schematic presentation is controlled by `../kicad/tools/schematic_layout.py` and the shared renderer. Keep source and generated outputs together. The [build guide](../../docs/build/README.md), [schematic editing procedure](../../docs/build/SCHEMATICS.md) and [current independent checks](../../reviews/codex/professionalization/QUALITY_HANDOFF.md) describe the latest review packet. Existing PCB routing is preserved by schematic-only commands.

| File | What it is |
|---|---|
| `LoRa_Boat_Controller_V2.kicad_pro` | project: netclasses (Default 0.25 mm / 0.15 mm, Power 0.6 mm / 0.2 mm), DRC severities, board rules (0.127 mm min clearance / track, 0.3 mm edge, 0.6 mm min via) |
| `LoRa_Boat_Controller_V2.kicad_sch` + `Power/MCU/Radio/Navigation/Actuators/Debug.kicad_sch` | root sheet with hierarchical pins + six sub-sheets (ERC: 0 errors, 1 accepted warning — U6 SDO/AD0 tied to GND) |
| `LoRa_Boat_Controller_V2.kicad_pcb` | 80 × 46 mm 2-layer board, 118 footprints, GND pours both sides, autorouted with freerouting (see `tools/route_v2.py`) |
| `LoRa_Boat_Controller_V2.kicad_sym` / `.pretty/` | project symbols (VSERVO) and footprints (QFN-24 3 × 3 mm 0.4 mm no-EP for the ICM-20948) |
| `fp-lib-table`, `sym-lib-table` | project libraries: `LoRa_Boat_Controller` (reused V1 footprints/symbols from `../kicad/`) and `LoRa_Boat_Controller_V2` |
| `_build/` | (git-ignored) DSN/SES, freerouting log, DRC/ERC reports, placement report, BOM JSON |

## Tool chain (run from the repo root)

```bash
python hardware/kicad_v2/tools/gen_v2.py check                                   # design-rule sanity: every pin either in a net or in NC_PINS
python hardware/kicad_v2/tools/gen_v2.py sch                                     # schematic-only refresh; preserves PCB/project/BOM
python hardware/kicad/tools/export_review.py                                    # PDF/SVG rendering only; no CAD generation
"C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/python.exe" hardware/kicad_v2/tools/placement_check.py   # courtyard overlaps / parts off the board
"C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/kicad-cli.exe" sch erc --severity-all -o hardware/kicad_v2/_build/erc.rpt hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_sch
"C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/python.exe" hardware/kicad_v2/tools/route_v2.py all     # DSN (B.Cu GND plane only) -> freerouting -> SES import -> pour fill
"C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/kicad-cli.exe" pcb drc --severity-error -o hardware/kicad_v2/_build/drc.rpt hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pcb
```

`gen_v2.py pcb` explicitly replaces the PCB with an unrouted board; `gen_v2.py all` (also the legacy no-argument default) regenerates libraries, schematic, project, unrouted PCB and BOM. Use those only for an intentional full rebuild. `check`, `bom` and `sch` have separate scopes; `sch` no longer destroys routing. An isolated regression test verifies that separation.

`route_v2.py` needs Java 21 and `freerouting-2.1.0.jar` at `%LOCALAPPDATA%\freerouting\` (or `FREEROUTING_JAR`). Routing is separate from schematic presentation; do not reroute merely to refresh drawings. The routing command above remains an explicit board mutation, outside the presentation-only workflow.

## Design source (`tools/v2_design.py`)

- `PARTS`: ref -> (symbol, footprint, value, MPN, manufacturer, sheet, description). `NETS`: net -> pins as `REF-number` or `REF.pinname`. `NC_PINS`: pins deliberately left open (everything else must be in a net, `gen_v2.py check` fails otherwise).
- `POWER_NETS`: which nets are drawn with power symbols; `SHEETS`: sheet names/paper/descriptions; `PLACE`: ref -> (x, y, rotation) in board mm from the top-left corner; `MOUNT_HOLES`, `BOARD_W/H`, `KEEPOUTS`.
- `PRICE_USD` / `PRICE_DATE`: qty-1 catalogue prices used by `docs/BOM_V2.csv` (estimates; re-quote at order time).

Requirement traceability is in the schematic sheet descriptions and in `docs/V2_REQUIREMENTS.md` (REQ-xx ids); the design decisions still open for Jay are in `BLOCKERS.md`.

## Known state of this draft

Current independent results supersede the historical routing count below: **3 unconnected entries, 101 DRC warnings, 212 schematic-parity entries**, zero DRC errors; ERC has one pre-existing U6 AD0 pin-type warning. No fabrication acceptance. [Assembly maps and procedures](../../docs/build/ASSEMBLY_V2.md) are now available; physical orientation and device/footprint qualification remain open.

- DRC 0 violations, **2 unconnected GND connections**: two pour islands (near U1 at board (42, 18.5) mm and near U7 at (55.7, 9.2) mm) are fenced in by other-net tracks on both layers. `route_v2.py import` stitches what it can (one of three islands on this layout); the last two need a hand-placed via each in KiCad (or a rip-up of the fencing track). The next layout pre-places a GND via next to every fine-pitch GND pad before routing to avoid this.
- Autorouted, not hand-optimised: expect to tidy the buck-converter loops (U2/L1/D3/C5-C6 and U3/L2/D4/C8-C9), the crystal traces and the USB pair before fabrication; keep the placement.
- Silkscreen is reference designators only; no assembly drawing yet.
- Footprints for new parts come from the KiCad 9 standard library on this machine (`KICAD_FOOTPRINT_DIR`), embedded into the board at generation time.
