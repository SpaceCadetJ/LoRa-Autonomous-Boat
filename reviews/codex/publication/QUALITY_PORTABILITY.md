# Publication quality snapshot — 2026-09-17

The [new native review](native-review/REVIEW.md) captures only active CAD and its project libraries. It replaces candidate 04 as the current portable input-freshness record; [candidate 04](../professionalization/candidate-review-04/REVIEW.md) remains unchanged historical evidence of the schematic presentation work.

The earlier recursive capture included twelve files under the ignored local `hardware/kicad/_backup_2026-09-16/` directory. A fresh checkout does not contain those originals. The review tool now excludes explicitly named backup, build, cache, autosave and session artifacts. It still captures every active schematic, PCB, project setting, custom rule, symbol library, footprint library and library table. It deliberately does not use arbitrary Git ignore rules to decide which active CAD deserves review.

## Verification

- All 18 quality-tool tests pass. New tests verify exact-byte capture of active CAD and nested library footprints while excluding local derivatives, and preserve the restricted output-directory boundary.
- KiCad 9.0.7 reviewed 52 active input files, compared with candidate 04's 64. The only twelve removed paths are the ignored backup copies. **All 52 active input hashes match candidate 04**, and the originals and review copies stayed unchanged during the run.
- Review captured at `2026-09-17T21:17:01.962328+00:00`. [Raw report](native-review/review.json) SHA-256: `259dc17c1fac5fde8588a40af74b8ad026a5dc17a186d7f6bc541ec13b0b798c`.

| Check | V1 | V2 |
| --- | --- | --- |
| Component and pin preservation | PASS: 44 components, 172 pins | PASS: 114 electrical components, 361 pins |
| Net names, values and footprints | Unchanged | Unchanged |
| PCB/project preservation | PASS | PASS |
| ERC | 0 errors, 0 warnings | 0 errors, 1 existing warning |
| DRC violation errors / warnings | 0 / 67 | 0 / 101 |
| Unconnected entries | 0 | 3 |
| Schematic-parity entries | 139 | 212 |

The strict review gate remains **FAIL** because V2's existing U6 AD0 pin-type warning remains unresolved. Fabrication remains **NOT APPROVED**. No findings were suppressed, no electrical baseline was replaced, and no generator or firmware/hardware operation was run. This portability change does not claim a new circuit fix or a new visual review.

## Reproduction and next task

Use Python 3.10+ with KiCad CLI 9 installed; set `KICAD_CLI` or add `--kicad-cli <full-path>`:

```text
python -m unittest discover -s tools/quality -p "test_*.py" -v
python tools/quality/review.py --profile review --output reviews/codex/publication/new-review
```

Each review destination must be new or empty. The existing `native-review/` is evidence, not a rerun destination. Review output is restricted to subdirectories of `reviews/codex/professionalization/` or `reviews/codex/publication/`; the runner refuses active source directories.

Publication still requires byte-preserving Git attributes for recorded evidence and a check of the actual staged checkout. The next engineering task remains the read-only disposition of the three V2 ground-zone unconnected entries, followed by the U6 interface/pin-mode review. Neither issue should be presented as already resolved in a portfolio overview.
