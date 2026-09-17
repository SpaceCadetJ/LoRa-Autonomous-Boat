# Portable report evidence

These files preserve completed reports outside ignored build directories so a cloned or downloaded repository can rebuild the viewer without this workstation's caches.

- `v1-build-manifest.json` is the exact manifest from the two-build V1 reconstruction packet. Input and artifact hashes, compiler version and the **unqualified** status are retained. Executable images stay ignored; no firmware release is created here.
- `primary_reports/v1/` and `primary_reports/v2/` are preserved primary-agent report files originally stored under the respective CAD `_build/` directories. They remain reported/historical evidence; they do not supersede the current independent native review. Older V2 routing counts differ from the current three zone-to-zone entries.
- Current independent results are in [QUALITY_PORTABILITY.md](../../../reviews/codex/publication/QUALITY_PORTABILITY.md). Before/after CAD and presentation evidence remains in `reviews/codex/professionalization/`.

Byte-preserving Git attributes retain the input/report fingerprints across operating systems. `tools/quality/check_publication.py` verifies the committed native CAD inputs, displayed schematic exports and recorded firmware inputs. Its success establishes package consistency, not approval to manufacture or flash hardware.
