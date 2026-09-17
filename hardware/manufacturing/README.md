# Ordering and assembly review exports

Start with [Ordering](../../docs/build/ORDERING.md). Assembly guides: [V1 existing board](../../docs/build/ASSEMBLY_V1.md) and [V2 vehicle-node draft](../../docs/build/ASSEMBLY_V2.md). The [handoff](../../docs/build/PROCUREMENT_HANDOFF.md) describes reproduction, checks and outstanding release decisions.

`run_manifest.json` is the single generated run record. `v1/` and `v2/` contain BOM reviews, held/external-part decisions, partial distributor candidate imports, position/orientation review tables and assembly pad maps. No files here are an authorized fabrication or purchase order.

Run `prepare_release.py --boards N` using KiCad's Python to refresh outputs; run it again with `--check`, then `check_package.py`, to verify them. `procurement_policy.json` records the reviewed selection holds and population options. These tools do not modify CAD or execute primary generators.

`render_assembly.mjs` is optional local visual QA using Playwright and Edge. It renders SVGs into `previews/`; the generated SVGs are the reproducible drawing artifacts. Preview PNGs are not manufacturing files and are outside the run manifest's released-data hash list.
