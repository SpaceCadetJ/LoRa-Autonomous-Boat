# Independent V2 Stage A review — 2026-09-17

**Verdict: the diagnostic implementation is consistent with its limited purpose; one build-contract validation gap needs correction.** This is a source and compiled-image review, not hardware approval. No device was connected, powered or programmed. The electrical blockers in [README.md](README.md) remain open.

Reviewed `firmware_v2/src/main.c`, `board_contract.json`, `tools/build.py`, `tests/test_contract.py`, `README.md`, the reused ST startup/system/linker files, and the existing local Stage A ELF/BIN. The reviewed binary is 1,328 bytes, SHA-256 `c95f9b0352e05971dd269cfaee4962d08d611866886a2e57ab7b403347f5afcd`. All inputs in its recorded build manifest matched during review. Root's repeated-build result was not independently rerun; the checks below were.

## Actionable findings

| ID | Finding | Required correction |
|---|---|---|
| A-01, medium | The contract accepts an arbitrary `target` field. An isolated fixture changed it to `STM32F103C8T6`; `pin_contract` still passed. The compiler and linker remain F446-specific, but the resulting manifest would report the substituted target. | Require `schema == 1` and `target == STM32F446RET6` before accepting the contract; reject changed expected pin modes too. Add tests for these contract changes. [Machine evidence](stage_a_review.json) records `wrong_target_rejected: false` for the reviewed revision. |
| A-02, documentation | “Fault handlers hold the MCU actuator pins low” is stronger than a C fault handler can guarantee. A stacking failure or an inaccessible peripheral bus can prevent those writes. The surrounding guide correctly excludes an operational failsafe. | Say the handlers **attempt** to set MCU outputs low before stopping. Keep external reset/brownout behavior and watchdog recovery explicitly unqualified. No new fault-recovery implementation is needed for this bounded diagnostic. |

No correctness change to GPIO, SysTick or vector code is requested based on this review.

## Independently checked

- Six existing pin-contract tests passed; the current contract check passed. They verify electrical pin membership and stale evidence rejection, not firmware execution or connector orientation.
- Binary vector table starts at `0x08000000`, initial stack is `0x20020000`, reset vector is `0x08000461`. Reset, NMI, HardFault, MemManage, BusFault, UsageFault and SysTick vector words match their linked Thumb handler addresses.
- Actual disassembly shows PC6 and PA8 BSRR reset writes before enabling GPIO output mode. GPIO register updates mask only the selected pin fields. PA13/PA14 SWD configuration is preserved.
- GPIOA/C clock enable is followed by the required readback before use. The five output pins are on these ports. PC1 heartbeat, PC2 off and PC3 marker agree with the native netlist and LED resistor connections.
- ST startup copies `.data`, clears `.bss`, calls constructors and reaches `main`. The diagnostic record therefore starts cleared. The built `SystemInit` only enables the FPU; it does not secretly configure V1 drivers or clocks.
- At the accepted 16 MHz nominal clock, `SysTick_Config(16000)` emits LOAD=15999, processor-clock selection, tick interrupt and counter enable. The handler toggles PC1 each 500 ticks. The source does not initialize actuator timers, radio, IMU, USB, UART, ADC or watchdog. [Arm SysTick API](https://arm-software.github.io/CMSIS_6/main/Core/group__SysTick__gr.html).

GPIO and reset reasoning uses the preserved ST CMSIS definitions and [ST RM0390](https://www.st.com/st-web-ui/static/active/en/resource/technical/document/reference_manual/DM00135183.pdf). Disassembly and pin membership are local artifact evidence. No exact timing, LED illumination or actuator-header voltage has been observed on hardware.

## Conditions retained

Start from a real hardware reset with main Flash selected by BOOT0. The build leaves VTOR at reset state and relies on Flash's boot alias. A debugger jump from another image, remapped memory, inherited interrupt masks or a changed vector base is outside the documented procedure; the HSI check alone cannot detect all such inherited state.

Reset flags are a raw register snapshot and can contain accumulated reset causes. Use them as evidence with the power/reset history, not a unique last-reset diagnosis. C fault handling cannot prove low outputs before application startup, while a buffer supply is invalid, during brownout or after a stack/bus failure.

The build requires a GNU Arm installation that includes the selected newlib nano/nosys specifications. The checked Windows installation has them; cross-platform compilation was not exercised. Preflight failures can exit before a build manifest exists; the nonzero exit status remains authoritative. Existing output directories are rejected, preventing an old image from being silently replaced or mistaken for a new success.

Reproduction helper: `python reviews/codex/design_completion/electrical/review_stage_a.py`. It checks the existing local Stage A binary and performs the wrong-target mutation only in a disposable review fixture. It does not compile firmware, modify live source, or access hardware. The result is [stage_a_review.json](stage_a_review.json); preserve this report as the pre-correction snapshot if root applies A-01.

## Correction verification addendum — 2026-09-17

**A-01 and A-02 are addressed.** This addendum supersedes their open dispositions above while preserving the original review and reproduction snapshot.

Independently inspected the revised builder: `pin_contract` now rejects a schema other than 1 or a target other than `STM32F446RET6` before processing evidence, and compares the complete pin-mode mapping with the reviewed modes. New tests cover an F103 target, schema 2, and SWDIO changed to output mode. Root reports all nine tests passing; this follow-up verified the code and test changes without rerunning the old mutation helper or compiling again.

The README now says fault handlers **attempt** to hold outputs low and explicitly explains that a corrupted stack or bus fault may prevent completion. The operational, reset and electrical limitations remain visible.

Reviewed revised source identities:

| File | SHA-256 |
|---|---|
| `firmware_v2/tools/build.py` | `81890dfe7668320ff37484eb7a6e13806e3608a359a88ee76974ac28f1e10416` |
| `firmware_v2/tests/test_contract.py` | `e7418f20dae33b45c39acfa0d42c6341e08b63a66aedf08760b29cd0acdde302` |
| `firmware_v2/README.md` | `a57fbf708325ea82431be6e71e87460798062799adc9440bcddfe51a770fd477` |

The ELF, BIN and HEX files in `stage_a_final` and `stage_a_final_repeat` were independently hashed: each pair matches, each matches the refreshed tracked build manifest, and the image hashes match the original reviewed executable. These guard/documentation changes therefore preserve the examined machine code. No remaining actionable software finding from this bounded Stage A review is open; hardware operation and all electrical release gates remain unqualified.
