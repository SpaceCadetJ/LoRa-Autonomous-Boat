> **ARCHIVED 2026-09-16.** This March-2026 CC/CD pipeline document is superseded by [README.md](../../README.md) and [REPORT.md](../../REPORT.md). Several statements in it are wrong (35 nets, 3 x 3 in board, DSN as source of truth); see docs/A0_PROVENANCE.md.

# DIRECTIVES — CD ↔ CC Pipeline
**Last updated:** 2026-03-31  
**Pipeline status:** ACTIVE  
**Session:** 1

---

## How This Works

1. **CD (Claude Desktop / KiCad MCP)** reads this file for tasks assigned to it
2. **CC (Claude Code / terminal)** reads this file for tasks assigned to it
3. When done, each updates STATUS.md and writes CHANGES_SESSION{N}.md
4. Neither edits the other's domain files directly

**CD domain:** `.kicad_sch`, `.kicad_pcb` (via MCP tools only)  
**CC domain:** Everything else (markdown, source, CSV, git, scripts)  
**JAY domain:** KiCad GUI operations (zones, net classes, manual routing, anything MCP can't handle)

---

## ACTIVE TASKS

### TASK 1: Wire schematic sub-sheets (CD)
**Assigned to:** CD  
**Files:** `CAN_Bus.kicad_sch`, `GPS_Module.kicad_sch`, `LoRa_Module.kicad_sch`, `MCU.kicad_sch`, `PowerSupply.kicad_sch`, `PWM_Outputs.kicad_sch`  
**Reference:** `docs/NETLIST.md` (authoritative pin-level connectivity)  
**Action:**  
- Wire all components in each sub-sheet per NETLIST.md
- Add power symbols (GND, +3V3, VIN_RAW) as proper KiCad power flags
- Ensure hierarchical pins on sub-sheets connect correctly to root schematic
- Run ERC when complete  
**Validation:** ERC passes with 0 errors. Net count matches NETLIST.md (35 named nets).

### TASK 2: Cross-reference verification (CC)
**Assigned to:** CC  
**Action:**  
- Parse KiCad schematic netlist and compare against `docs/NETLIST.md`
- Parse KiCad BOM and compare against `docs/BOM.csv`
- Flag any mismatches in component values, pin assignments, or net connectivity
- Document the PWM pin swap discrepancy with a recommendation  
**Output:** `VERIFICATION_REPORT.md`

### TASK 3: Update STATUS.md (CC — ALWAYS LAST)
**Assigned to:** CC  
**Action:** Update STATUS.md with results from all completed tasks this session.  
**Output:** Updated `STATUS.md` + `CHANGES_SESSION1.md`

---

## COMPLETED TASKS

_(none yet)_

---

## TEMPLATE FOR ADDING NEW TASKS

```markdown
### TASK N: [Specific task name] ([CC/CD/JAY])
**Assigned to:** [CC / CD / JAY]
**File:** [exact path(s)]
**Backup first:** cp "original" "original.bak_sessionN"
**Action:** [precise instructions]
**Validation:** [how to verify — ERC, grep, file size, diff]
```
