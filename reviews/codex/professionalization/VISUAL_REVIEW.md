# Schematic visual review — 2026-09-17

All 15 pages of the final PDF pair were rendered with Poppler and visually inspected. V1 pages 1–3 and all V2 pages were inspected by the coordinating agent; an independent review subagent inspected V1 pages 4–8 and additionally checked dense V2 Power, MCU and Actuators pages. Final PNGs are retained in `reviews/codex/professionalization/renders/`.

| Artifact | Pages / sizes | SHA-256 |
| --- | --- | --- |
| [V1 schematic](../../../docs/img/v1_schematic.pdf) | 8 pages; PowerSupply and MCU A2, others A3 | `37b74e0a88f0609152c4ec3ad8f68873696b9b786f0e56dbb3a7651c4f17f363` |
| [V2 schematic](../../../docs/img/v2_schematic.pdf) | 7 pages; Power and MCU A2, others A3 | `27fa3745ee287070069cd7a02afb67c640735c75223be5e2a5afa71303e38093` |

The [export manifest](../../../docs/img/schematic_export_manifest.json) binds the two PDFs and fifteen SVGs to their CAD inputs. It was produced by KiCad 9.0.7 through `hardware/kicad/tools/export_review.py`; every input was unchanged during export. Final electrical preservation was checked separately in [candidate-review-04](candidate-review-04/REVIEW.md).

## Findings corrected

- Functional groups now have separate frames and annotation space; component properties are outside symbol bodies.
- Horizontal port labels face away from component pins. Root-sheet pin text is inside its box; matching root net labels remain outside, without collisions.
- Shared supply rails use segmented wires and explicit branch junctions. Unlike adjacent supply names are staggered into separate text rows.
- The V1 PWM connector label now clears its panel border. Short revision fields fit the title block on every page.
- Power flags sit in reserved space above the footer. Notes and drawing titles no longer run through the title block or off the sheet.

No remaining page clipping or overlapping labels/properties were observed in the final reviewed renders. This is a scoped visual observation, not an exhaustive glyph-collision proof or engineering approval.

## Practical limits

These are annotated named-net schematics. A future engineering drawing pass can replace selected regulator/interface groups with hand-composed point-to-point circuits to make current paths easier to follow. A2 sheets should be viewed at native size or enlarged in the viewer; reducing them to A4 makes pin names small. Sparse A3 pages deliberately retain consistent spacing and room for future measured annotations.

Physical connector orientation, actual supplied part/package polarity and cable mating views require assembly inspection. Text annotations contain expected or nominal values, not measured results. Known V1 electrical defects are preserved. V2 remains a draft with one pre-existing ERC warning, open ground-zone connections, layout/parity findings and no firmware image. This review does not approve fabrication, powering an uninspected board or programming hardware.
