# Portfolio publication package — 2026-09-17

This package makes the engineering review edition portable and gives the portfolio editor a clear, evidence-backed project description. The destination is the existing [LoRa-Autonomous-Boat repository](https://github.com/SpaceCadetJ/LoRa-Autonomous-Boat). The repository landing page and `docs/portfolio/portfolio.json` are the portfolio entry points; no public website deployment is implied.

## What is included

- The reconstruction and design history already present on local `v2-design`, plus the reviewed schematic, assembly, build, viewer and documentation packet.
- [Portfolio case study](../../../docs/portfolio/README.md) and [structured project data](../../../docs/portfolio/portfolio.json), with captions and links to verified results. Individual original team contributions remain unspecified rather than inferred.
- The existing V2 PCB snapshot underlying the current review: 118 footprints, 1,074 track segments and 164 vias. It is a draft, with three ground-zone unconnected entries; it is not a new fabrication release.
- [Portable native review](QUALITY_PORTABILITY.md): all 52 active CAD/library inputs match the earlier presentation review; all 533 pins remain unchanged. One existing V2 ERC warning and the documented layout/parity findings remain open.
- Tracked, hashed V1 schematic inputs. All fifteen schematic files reproduce byte-for-byte in isolation without the old `_build` directories. The full reconstruction caller explicitly selects its newly generated inputs; it is not part of a documentation refresh.
- A tracked V1 build manifest and preserved primary reports, allowing the viewer to rebuild without ignored compiler/CAD caches. Executable firmware images remain ignored and unqualified.
- Byte-preserving attributes for hashed sources/evidence. Some index changes preserve the reviewed Windows line endings; they do not represent new firmware behavior or a V1 circuit change.
- Portable repository checks on pushes to main/design branches and on pull requests. Native KiCad and V1 compilation remain separately opted-in jobs requiring their toolchains. No job flashes hardware or approves fabrication.

## Deliberately excluded local work

The unfinished modifications to `hardware/kicad/tools/v1_design.py` and `hardware/kicad_v2/tools/route_v2.py` are left unstaged. The consumed V1 helper definitions are identical to their committed versions; the added helpers are not used by the current schematic generation. The local routing extension is not idempotent and requires a separate reviewed correction before publication. Neither excluded edit participates in the native CAD, assembly or viewer freshness manifests.

Generator-guard scratch copies, earlier candidate input/SVG duplicates and superseded preview images are excluded. Raw earlier reports, the baseline, final candidate-04 evidence, final page renders and the new active-input review remain available. Historical reports may name excluded local scratch paths; they are execution records, not current downloadable artifact indexes. The viewer filters those copies from its document library.

## Reproduction checks

From the repository root with Python 3.10+ and Node.js 20+:

```text
python -m unittest discover -s tools/quality -p "test_*.py" -v
python tools/quality/check_publication.py
python hardware/manufacturing/check_package.py
python docs/atlas/generate_atlas.py --check
node pm/tools/build.mjs
node pm/tools/validate.mjs
```

The publication check verifies 52 active native-review inputs, 22 schematic-export inputs, 17 PDF/SVG outputs, all 95 recorded V1 build inputs and portfolio/guide links. Manufacturing checks independently verify source/output hashes, all quantity modes, holds and assembly maps. A downloaded source archive can rebuild the viewer without Git; its revision label then reads `source-archive`.

Native checks were repeated with KiCad 9.0.7 and retain the strict failed review gate for the pre-existing V2 warning. That expected result is documented in [QUALITY_PORTABILITY.md](QUALITY_PORTABILITY.md). The publication-only checks must not hide or relabel the hardware gate as passed.

The staged-source archive was checked without `.git` or ignored build caches on 2026-09-17. All 186 recorded native/export/firmware hashes passed, both assembly packages reconciled, and the atlas verified 12 connectors / 36 pins against ten hashed sources. The rebuilt viewer passed with 60 documents, 200 indexed paths and 52 drawings/images. Eighteen acceptance tests also passed in an earlier staged archive with the same test sources. Git attributes preserve the reviewed source bytes, including the Allegro netlist and vendor firmware files; those byte-only index changes do not alter circuit connectivity or program logic. Final documentation-only handoff updates follow this checkpoint.

## Next engineering packet

Identify the actual isolated V2 ground islands and affected pads before proposing stitches; `(50,50)` in the native report is a zone anchor. Then resolve U6's AD0/interface and voltage-domain questions against the device datasheet. Freeze the V2 pin/protocol contract before building diagnostic firmware. Voice, text and location remain required for the future handheld, with voice/RC coexistence validation preceding hardware selection.
