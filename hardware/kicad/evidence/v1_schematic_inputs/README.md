# Captured V1 schematic inputs

These three files are byte-for-byte copies of existing local reconstruction outputs captured on September 17, 2026. They make a fresh checkout's schematic-only regeneration independent of the ignored `_build` directory. The original Allegro files remain the source evidence; this capture does not replace them or constitute a new reconstruction verification.

| File | Original producer | Purpose |
|---|---|---|
| `v5_board.json` | `hardware/kicad/tools/v5_reconstruct.py` | Component identities, values and pad/net membership used by V1 schematics; the original complete output is retained without filtering. |
| `netmap.json` | `hardware/kicad/tools/gen_pcb.py` | Allegro-to-KiCad net names. |
| `mpn.json` | `hardware/kicad/tools/gen_bom.py` | Existing manufacturer, part number and description properties. Confidence/value conflicts and historical prices remain unqualified. |

[manifest.json](manifest.json) records each original path, byte count, SHA-256 and capture limitations. Source hashes matched before copying, in the copy and after copying. No source converter, PCB generator, BOM generator or Allegro mutation was performed to create these captures. Original reconstruction methods and limitations remain in [A0_PROVENANCE.md](../../../../docs/A0_PROVENANCE.md).

`gen_sch.py` uses this coherent set by default and verifies all three captured hashes before writing. To consume a newly reconstructed set instead, explicitly pass `--input-dir hardware/kicad/_build`. Do not silently mix captured and local files. The explicit mode retains the old optional `mpn.json` behavior; omit it only when intentionally generating without researched MPN properties.

For another operating system or KiCad installation, set `KICAD_SYMBOL_DIR` to the installed KiCad 9 standard-symbol directory. The tracked project symbol library and generator inputs are sufficient for schematic generation; rendering and electrical review additionally require KiCad CLI. Standard library updates can change embedded symbols, so inspect output diffs and rerun electrical/visual review even when generation succeeds.

See [SCHEMATICS.md](../../../../docs/build/SCHEMATICS.md) for commands and the isolated regeneration result. Snapshot updates require their own source provenance, refreshed hashes and review; changing the hash merely to accept unexplained byte drift is not a validation procedure.
