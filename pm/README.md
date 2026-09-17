# LoRa engineering workspace

Open [index.html](index.html) directly in a browser. The generated page contains its data and application code; no install or build step is required to view it. Keep it in this repository so images, schematics and evidence links resolve.

For the local HTTP viewer, run from the repository root:

```powershell
node pm/tools/serve.mjs
```

Then open <http://127.0.0.1:8765/pm/>. The server binds only to this computer, serves selected project paths and does not modify repository files. Stop it with Ctrl+C. This does not publish the project.

## What to explore

- Overview: phases, evidence gates and the next review tasks.
- Design: V1/V2 schematic sheets, available PCB renders, PDF drawings and source KiCad files. Choose a view and zoom to inspect it.
- BOM: searchable V1/V2 parts, component details and selected manufacturer datasheets. An unmapped part explicitly says its exact datasheet is not yet linked. Prices are dated source estimates.
- Connector atlas: V1 connector pins, firmware cross-references, voltage expectations and known defects. Bench readings are expectations, not measurements.
- Software: current source and proposed correction files, clearly separated from integrated firmware.
- Verification: independent V1 checks, primary reports and input fingerprints.
- Traceability: V1 findings linked to the primary's V2 requirements and acceptance methods.
- Decisions: working defaults, open choices and private browser notes. Notes stay in this browser; export the handoff to save a copy. They are not written back to project files.
- Documents: searchable embedded documentation and the repository file map.

## Refresh evidence

Only after checking [ownership](../FILE_OWNERSHIP.md), current [handoff](../HANDOFF.md), Git status and primary release notes:

```powershell
node pm/tools/build.mjs
node pm/tools/validate.mjs
```

The builder reads evidence and writes only `pm/index.html` and `pm/status.json`. It never invokes CAD/firmware generators. In HTTP mode use Refresh after building; with a directly opened file, reload the page. Editing `index.html` directly loses changes on rebuild; edit `index.template.html` instead.

The snapshot records branch/HEAD and SHA-256 hashes of consumed text/report inputs. Working files may differ from HEAD. Changed-during-build detection covers hashed inputs, not a repository lock or a full media/CAD archive. Images and CAD links load current files from the repository; independent S2 results refer to the separately identified historic snapshot.

## Current limits and next packet

V1 independent review is at `639e08f`: all 172 pin memberships agree, ERC has zero violations, and DRC has zero errors/zero unconnected with 67 warnings. Native schematic/PCB comparison adds 139 value/name warnings; V5 drill diameters and independent whole-film XOR remain unresolved. See [S2 verification](../reviews/codex/S2_VERIFICATION.md).

V2 is a primary-agent draft, not independently accepted for fabrication. Firmware correction files are proposals; no firmware integration, compilation or bench result is implied. V2 connector coverage and complete datasheet mapping are subsequent packets.

The next smallest verification packet is a read-only V2 snapshot inventory with ERC/DRC, BOM and requirements checks. Keep voice + text + location in scope: establish voice airtime and RC coexistence before choosing handheld hardware. The primary's current `REQ-CTL-01` text governs proposed deadlines; summaries may be stale.

Resume through this file and [Codex checkpoint](../reviews/codex/README.md). Work one bounded packet in owned paths, record exact evidence and limitations, then append the next task to the handoff.
