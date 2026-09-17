# S2 — independent verification of released V1

**Verdict: connectivity verified, with explicit evidence limits.** At released commit `639e08fe56c38d54becf086f4fd86ec20ecfcb90`, the source netlist, KiCad schematic and PCB agree on every physical pin and part. ERC has zero violations; PCB DRC has zero errors and zero unconnected items under the released rules. An additional native schematic-parity check finds **139 warnings**, so this report does not declare complete schematic/PCB synchronization. V5 hole centers match, but the supplied drill cannot establish V5 finished-hole sizes.

**Interpretation clarified after the primary's 2026-09-17 review:** the 139 warnings are classified value/name metadata differences, not failed electrical connectivity. They leave the no-change Update-PCB workflow unverified; they do not block use of this reconstruction as a documented V1 baseline. The initial viewer summary's global "transfer gate blocked" label was too broad and has been narrowed. Raw evidence and counts are unchanged. Any primary correction in a later revision needs a separate check before closing the historic finding.

This is a historical V1 review of the exact released commit, completed 2026-09-17 UTC. It does not assess the later `v2-design` branch or imply that these findings remain present in later revisions. No primary generator ran, no CAD input was edited, and no Git history was changed by this reviewer.

## Gates and evidence

| Gate | Result | Independent result |
| --- | --- | --- |
| Input identity | PASS | Files exported from the commit using `git show`; all recorded SHA-256 hashes still match after verification. |
| Net/pad membership | PASS | 44 parts and 172 physical pins in source, schematic and PCB; exact equality of all 31 multi-pin nets, singleton VBAT and 37 individually isolated NC pins. No duplicate pin membership. |
| Symbol/footprint identity | PASS | Explicit `Allegro_RefDes` fields used for both CAD representations. All component references, footprint libraries and symbol/footprint paths agree. |
| ERC | PASS | KiCad 9.0.7, `--severity-all`: 0 violations, root plus 7 functional sheets. |
| DRC errors/routing | PASS WITH WARNINGS | 0 errors, 0 unconnected; 67 warnings under the released project/custom rules. |
| Native schematic/PCB parity | OPEN | 139 warnings, fully classified below. Electrical pin-set agreement does not remove these metadata/synchronization differences. |
| V5 hole centers | PASS | 53/53: 26 drilled pads and 27 vias match round dark flashes common to both V5 copper films. |
| V5 drill dimensions | UNVERIFIED | Supplied BOATCREW drill equals V4 data except the `;FILE` header. V5 diameter/plating provenance remains unavailable. |
| Full film XOR / all pad geometry | NOT RUN | Primary-reported percentages and 172-pad geometry agreement were not independently reproduced here. |

Machine-readable results: [viewer summary](s2/summary.json), [complete analysis](s2/analysis.json), [connectivity comparison](s2/connectivity.json), [rule summary](s2/rule_summary.json), [hole comparison](s2/drill_comparison.json).

## New finding S2-01: native parity is not clean

Running DRC with `--schematic-parity` adds these **139 warning-level findings** to the separate 67 PCB warnings:

| Count | Difference | Interpretation at this revision |
| --- | --- | --- |
| 34 | Footprint value differs from symbol value | Example: footprint C12 value is `C12`, schematic value is `.1uf`. Board BOM-facing metadata needs synchronization. |
| 67 | Hierarchical net-name prefix | Example: board `SW_NODE`, schematic `/PowerSupply/SW_NODE`. Names differ although associated pin sets agree exactly. |
| 37 | PCB unassigned pad vs schematic generated unconnected name | Each source NC pin is independently isolated in both representations; native naming still differs. |
| 1 | PCB `VBAT` vs schematic `unconnected-(U3-VBAT-Pad1)` | Same single pin U3.1; no extra electrical connection was found. |

All 139 entries fit these categories; there are no unclassified parity findings. See [raw DRC with parity](s2/drc.json). These observations support the primary's narrower pin-set check, but that check is insufficient evidence for a clean, no-change **Update PCB from Schematic** workflow. The CLI returned exit code 0 because `--exit-code-violations` was not requested; the report contents, rather than the exit code, determine this verdict.

**Smallest follow-up for the implementation owner:** in a separately owned working copy of the intended maintained revision, align PCB values and exact schematic net identities, then repeat native parity and inspect the Update-PCB change list before applying it. Preserve source connectivity and copper geometry throughout. Do not silently waive these findings because the pin-set check passes. This reviewer made no implementation edits.

## DRC and ERC interpretation

The 67 PCB warnings reproduce the primary handoff exactly: 37 solder-mask bridges, 21 silk-over-copper, 6 silk-edge clearance issues and 3 isolated copper islands. [ERC](s2/erc.json) independently reproduces zero violations.

Zero DRC errors is conditional on the released `.kicad_pro` and `.kicad_dru`, both included in the hashed snapshot. The custom rules model the preserved artwork, including minimum 5 mil pour clearance, 7.5 mil track-to-track, 9.5 mil track-to-via and 3.3 mil track-to-pad clearance. This verifies that specific rule configuration; it is not evidence that a redesign meets a different fabricator's requirements. ERC and DRC also do not validate regulator/MCU application requirements, actuator behavior or firmware safety.

## Independent comparison method

The review parser reads `pstxnet.dat` directly and checks full parsed node coverage. Schematic connectivity comes from KiCad's XML netlist export; PCB pads come from `pcbnew.LoadBoard`. References are resolved using the saved `Allegro_RefDes` properties, rather than deleting an assumed trailing digit. The PCB property reader consumes top-level footprint property blocks from the same hashed PCB because KiCad 9's Python footprint API does not expose the older `GetProperty` method.

The comparison includes **all 172 pins**, including every NC and VBAT pin. The source's NC list is split into 37 independent single-pin groups, because it denotes unconnected pins rather than a shared electrical net. Thus the source, schematic and PCB each produce the same **69 pin groups**: 31 multi-pin nets, one singleton VBAT net and 37 isolated pins. Duplicate memberships and missing/extra references, paths and library IDs are checked separately. This establishes declared connectivity; the separate DRC checks routed connectivity under the saved rules.

The hole check independently parses absolute RS-274X flash commands from the V5 `BOATCREWTOPL.art` and `BOATCREWBOTL.art`, retaining round flashes in dark polarity. Both yield the same 53 centers. After inverting Gerber Y, the independently solved common translation is +100 mm X and +100 mm Y. Bidirectional nearest-center comparison matches every board hole within 0.05 mil; measured maximum is approximately `7.9e-13` mil, i.e. numerical roundoff. No source drill diameter is inferred from a copper annulus. The supplied drill's identity with V4 was independently rechecked after removing only the `;FILE` line.

## Reproduction and provenance

Run from the repository root in PowerShell. Tool versions: KiCad **9.0.7**, bundled Python **3.11.5**. All output stays under `reviews/codex/s2/`.

```powershell
& 'C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\bin\python.exe' reviews/codex/s2/verify.py
& 'C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\bin\python.exe' reviews/codex/s2/analyze.py
```

`verify.py` uses `git rev-parse`, `git ls-tree` and `git show` to export the selected commit, then runs these exact CLI operations against the snapshot:

```powershell
& 'C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\bin\kicad-cli.exe' sch export netlist --format kicadxml --output reviews/codex/s2/netlist.xml reviews/codex/s2/snapshot/hardware/kicad/LoRa_Boat_Controller.kicad_sch
& 'C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\bin\kicad-cli.exe' sch erc --severity-all --format json --output reviews/codex/s2/erc.json reviews/codex/s2/snapshot/hardware/kicad/LoRa_Boat_Controller.kicad_sch
& 'C:\Users\Jay\AppData\Local\Programs\KiCad\9.0\bin\kicad-cli.exe' pcb drc --severity-all --schematic-parity --format json --output reviews/codex/s2/drc.json reviews/codex/s2/snapshot/hardware/kicad/LoRa_Boat_Controller.kicad_pcb
```

The actual full-path arguments, stdout and exit codes are in [commands.json](s2/commands.json). The first inventory attempt encountered a KiCad API difference; a later attempt required an explicit layer for `PCB_VIA.GetWidth`. The inventory was completed with the corrected script using `verify.py --resume-inventory`, without re-running the CAD checks. [run.json](s2/run.json) records the inventory completion/version and snapshot stability. `analyze.py` then completed successfully, including the additional duplicate/count checks. Neither script imports the primary converter.

Complete input hashes are in [input_manifest.json](s2/input_manifest.json), including every sheet, library, project rule and compared source file. Key SHA-256 hashes:

| Input | SHA-256 |
| --- | --- |
| PCB | `ec6bed5c721ed33bb8c6b88f40d2e60b12b2a180a92e1e845dd7ffb373587597` |
| Root schematic | `8af5beedd78649b91e4ae29dd99a0e7721ae9e9617cc53daf528e3db2f8df8ae` |
| V5 pstxnet.dat | `b88c36244bb3e3eb4d10712ce8ca39ddb5908e2c3225aa187155f9f4dca6b02c` |
| Custom rules | `7d5337c38b2be25b88bbe9782c88fd56e48c7ec7e023646d69ff9805f43dc82c` |

## Limits and handoff

Unperformed in this bounded packet: full copper/mask/silk/outline XOR, all-pad geometric matching, visual schematic review, Update-PCB GUI exercise, firmware compilation, physical measurements and powered-hardware tests. Independent hole-center agreement does not prove finished-hole diameter or plating. No result here establishes safe actuator operation or fabrication readiness.

Files changed by this review are confined to this report and `reviews/codex/s2/**`. The implementation owner can use the exact pin-set pass immediately as V1 conversion evidence, while tracking S2-01 and drill provenance as open transfer limitations. The next smallest verification packet should target one explicitly released maintained revision and its native schematic/PCB parity; it should not silently substitute a moving working tree for this hashed V1 baseline.
