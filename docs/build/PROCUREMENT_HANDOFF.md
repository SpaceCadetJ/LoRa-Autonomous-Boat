# Procurement and assembly handoff

This packet makes the existing source BOMs easier to review, quote and assemble while preserving a clear distinction between the V1 boat and V2 vehicle-node draft. It has not created a distributor cart, purchase order, fabrication job or assembly order.

## Start here

1. Read [Ordering](ORDERING.md), then choose [V1 assembly/repair](ASSEMBLY_V1.md) or [V2 assembly preparation](ASSEMBLY_V2.md).
2. Open [run_manifest.json](../../hardware/manufacturing/run_manifest.json). It is the single generated run record: source hashes, selected board count, quantity totals, matching checks, release limitations and every output hash.
3. Review `holds.csv` and `external_parts_review.csv` for the chosen version. These are the missing decisions that a partial candidate quote cannot settle.

## Reproduce the packet

The exporter uses Python's standard library and KiCad 9's `pcbnew` bindings. It reads existing BOMs and PCB files, extracts embedded pad positions, and writes only `hardware/manufacturing/v1/`, `v2/` and the run manifest. It does not save CAD, refill zones, run another generator, access the network or place orders.

```powershell
& 'C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/python.exe' hardware/manufacturing/prepare_release.py --boards 1
& 'C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/python.exe' hardware/manufacturing/prepare_release.py --boards 1 --check
& 'C:/Users/Jay/AppData/Local/Programs/KiCad/9.0/bin/python.exe' hardware/manufacturing/check_package.py
```

Use the installed KiCad Python equivalent on another machine. Set `--boards 5` or another positive quantity for `distributor_candidates_selected.csv`; one-board and fleet-five files remain available. `--check` fails if an artifact is absent/stale. If CAD/BOM inputs change during extraction, generation fails rather than issuing a mixed snapshot. The rectangular-outline extractor deliberately fails if a later revision uses an unsupported profile; update and review it for that geometry.

Selection rules live in [procurement_policy.json](../../hardware/manufacturing/procurement_policy.json). Resolve a hold by reviewing the source part/footprint and its requirements, recording the decision, and updating the source or policy intentionally. Do not turn off all holds to make the order list look complete.

## What is verified

| Check | Meaning |
|---|---|
| BOM reference coverage | Each listed reference occurs once and exactly matches the PCB footprint reference set |
| Source quantity reconciliation | A grouped BOM quantity matches its references; the V2 TOTAL row is excluded and reconciles to 118 |
| Purchase-feature separation | Test pads, battery solder pads and mounting holes are retained in review data but never treated as purchased parts |
| Part identity preservation | Manufacturer/MPN text comes from the source BOM; no substitute or supplier SKU is invented |
| Selected/fleet counts | Per-reference counts drive one-board, selected-count and five-board candidate imports; no hidden spares |
| Snapshot stability | SHA-256/byte counts record inputs and outputs; the extractor detects concurrent source edits |
| Drawing geometry | Pad coordinates, pad 1, side and raw rotation are extracted from the PCB; outline dimensions exclude drawing stroke width |

The generation and reproducibility check passed for both boards. Independent package checks passed for one-board, three-board and fleet-five quantities, exact preserved MPN strings, held-part exclusion, manifest hashes, position coverage, SVG parsing and local document links. The final selected quantity is one board. Both top maps were rendered in a local browser and visually inspected; the crowded V1 radio-filter labels were adjusted and rechecked. Bottom maps identify that the source boards have no bottom-side footprint population.

Package bodies, machine rotation conventions and physical orientations remain separate checks. A generated pad map is not a verified assembly process. Current stock, prices, lifecycle, exact order suffixes, procurement availability, electrical sign-off, fresh ERC/DRC, copper integrity and bench operation are not certified by this packet.

## Release record to complete

| Field | Record before release |
|---|---|
| Product / use | Existing V1 repair, V2 first article, or later fleet build |
| Board revision / source hash | Exact frozen PCB, schematic and BOM inputs |
| Firmware | Source revision, toolchain, binary hash and tested configuration |
| Electrical/layout acceptance | Reviewer, date, closed issues, accepted exceptions and validation file links |
| Population | Fitted/DNP reference list and source/BEC/clock decisions |
| Parts | Final manufacturer/MPN, supplier SKU, substitutions, quantity and dated quote |
| Mechanical | Connector mating parts, harness drawings, pin-1/polarity sign-off, enclosure and mounting |
| Fabrication | Stack-up, dimensions/drills, copper, finish, manufacturing files and independent plot review |
| Assembly | Stencil/profile, approved centroid convention and first-article orientation review |
| Bench acceptance | Board ID, supply plan, measured rails/current/ripple, interface and failsafe records |
| Authorization | Named person and date accepting the final concrete order package |

No release field should be marked complete merely because a CSV was exported. The next engineering steps are to resolve the held selections and electrical/layout findings, produce a frozen first-article release, then use that reviewed package for ordering and assembly.
