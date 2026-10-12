# ACT-03 — actuator interlock behavior and receiver observability

**The proposed arm interlock now has an executable contract and an interactive fault demonstrator.** [Open the prototype](index.html), [view the proposed circuit boundary](v2_actuator_interlock.svg), [inspect the behavioral contract](contract.json) or [read the captured connector evidence](observability.json).

This packet follows ACT-02 at `912007b11b01d47ef66e29483485d268b7f0e8f6`. Expected and actual CAD/copper delta is **zero**: ACT-02, both converter sheets, ACT-01 source populations, original Allegro/V1, source BOM and firmware remain preserved. The diagram is a functional proposal, not a native schematic or wiring instruction. No new native ERC/DRC, hardware timing, part selection, manufacturing approval or flash image is claimed.

## Use the demonstrator

1. Replay **Deliberate arm sequence**. Assumed healthy permissions and repeated command-service strobes qualify; acknowledge with PC4 low, then a later PC4 rising edge enables the model.
2. Replay **Rail loss and restoration**. Output permission drops and remains locked after the rail recovers, even while arm remains high.
3. Try **Command at exact deadline**, **Inherited arm / held acknowledge**, and **No servo-ready evidence**. Late service, a held button and one missing permission cannot bypass the lock.
4. Try **Blind spot: stale periodic strobes**. The model remains armed because it sees strobes, not packets. This is an intentional demonstration of a watchdog limitation, not a passing freshness result.
5. Reset and operate the controls manually. Each advance is 25 ms; service pulses return low between edges. All ready inputs begin false. Invalid UI updates discard the previous permission and reset the model to locked.

The **100 ms** qualification/watchdog settings are illustrative scenario values. They are not accepted vehicle deadlines or selected component delays. No simulation control communicates with hardware.

## What the existing circuit can observe

The [verifier](verify_observability.py) independently checks exact pin memberships, connector order, no-connect markers and DNP state against ACT-02's captured native netlist. It does not rerun a CAD generator.

| Point | Captured connection | Consequence |
|---|---|---|
| J2.2 / BEC_IN | J2.2 and D9.2 only | No MCU sensing; voltage here does not establish the ESC control supply or initialized state |
| J3.2 / VSERVO | C11.1, C12.1, D4.1, D9.1, J3.2, TP4.1 | Local power node, with no MCU sense path; not proof of voltage/readiness inside the remote servo |
| U2.4 / U3.16 | PG / PGOOD each explicitly no-connect | Available pins are not an implemented supervisor, and their operating guarantees still need review |
| ACT_EN_PC4 | R40.1, U1.24 and U4.6 | MCU request directly drives OE; no independent fault latch or freshness gate exists |

**BEC_ONLY** fits D9 and omits D4; **ONBOARD** fits D4 and omits D9. The master marks both DNP. In ONBOARD, the unused ESC BEC positive lead is isolated, and VSERVO derives from the board converter. In either variant, a measured voltage proves only the bounded voltage at that measured point. A qualified receiver-ready interface must account for internal control power, initialization, missing ground, harness loss and sensor failure.

## Proposed interlock contract

Inputs are qualified logical permissions, not raw rail voltages: `logic_good`, `driver_good`, `esc_ready`, `servo_ready`, and `stop_closed`. The first includes validity of the interlock's own supply. An unknown input is not permission. `arm_request` is PC4's request; `acknowledge` is a separate deliberate recovery event. `command_service_edge` is a sampled strobe level that must return low before another rising edge is recognized.

| State / event | Proposed response |
|---|---|
| Startup | LOCKED; no output permission |
| All permissions true, repeated service | Accumulate a stable interval; require at least two distinct service rises in the healthy epoch |
| Qualified, arm low, fresh acknowledge edge | READY; no output permission yet |
| Later arm rising edge from READY | ARMED, provided every permission still holds |
| Any health loss or expired service | LOCKED; fault wins over simultaneous acknowledge or arm |
| Fault condition disappears | Stay LOCKED; require low arm, fresh acknowledge and a later arm edge |
| Normal arm-low disarm with valid health | READY; output permission low |
| Invalid input/config/time | Reject update without producing a new permission; integration must inhibit, never reuse a previous enabled value |

A strobe at exactly the watchdog deadline is late. It may begin a new qualification epoch, but cannot erase the fault or immediately unlock. Holding ACK through a fault is not a new acknowledgement. A startup-high PC4 is not a fresh arm action.

The future circuit must split PC4 from U4.6, retain R40 on the OE node, and insert a fault-dominant latch and combinational inhibit. The intended relationship is `OE = qualified_permissions AND arm_latch AND PC4_request`. Power-on reset and any fault must clear arm/recovery state with priority. This equation and sampled model do **not** prove asynchronous clear timing, reset recovery/removal, metastability, glitches, partial-power behavior or single-fault tolerance.

Output permission only controls the translator. OE low produces high impedance under ACT-02's specified conditions; it neither proves zero signal voltage nor establishes that an unidentified ESC stops. Receiver no-pulse/stuck-signal behavior is a separate acceptance requirement.

## Watchdog and firmware boundary

Stage A toggles its diagnostic heartbeat in SysTick every 500 ms; its main loop waits and implements no radio parser, actuator PWM or command watchdog. V1's timer PWM can retain compare values without command reception. Neither is a suitable command-service source. [Stage A source](../../../firmware_v2/src/main.c), [V1 source](../../../firmware/Core/Src/main.c).

A future service strobe must be emitted only after the reviewed command pipeline accepts a new permitted command and completes the required control work. A timer, DMA channel or unconditional interrupt toggle can continue after application failure. Hardware edge timing cannot prove sender/session identity, packet correctness, sequence freshness or actuator-state policy; those require a reviewed protocol and software contract. The stale-strobe scenario makes this blind spot visible.

Existing documents are not a frozen timing implementation: [V2 requirements](../../../docs/V2_REQUIREMENTS.md) propose a 1000 ms command-loss threshold plus a response bound, while the [firmware plan](../../../firmware/V2_FIRMWARE_PLAN.md) also discusses a roughly 500 ms watchdog and a less-than-200 ms arming age. The [software correction prototype](../firmware_prototype/lora_control.c) accepts a caller-supplied timeout and expires at `age >= timeout`; the plan's `age > T_loss` differs at the boundary. CRC-8 versus CRC-16 is another already documented specification mismatch. Do not promote the prototype's synthetic 100 ms tests, or this demonstrator, into a hardware timeout. Preserve the stated requirements until explicitly reconciled.

For eventual timing selection, bound command age plus scheduler/jitter, watchdog maximum detection, inhibit propagation, signal transition and actual actuator response. Include radio loss/retry behavior and measured worst cases. A watchdog interval chosen solely to fit a component is not a vehicle stop budget.

## Hardware family screening — no selection

| Family | Useful capability | Open selection constraints |
|---|---|---|
| TPS386000 | Four undervoltage channels; one channel supports a voltage window | One device does not independently provide both 3.3 V and 5 V UV/OV windows. Divider tolerance, delay, supervisor power collapse and output loading require explicit limits. [TI SBVS105F](https://www.ti.com/lit/ds/symlink/tps386000.pdf) |
| TPS3430 | Window watchdog with external timing options | WDO high can occur while disabled or below normal operating supply. Startup/first-edge qualification, fixed enabled mode, early/late interval corners and a separate sticky fault are required. Its physical falling-edge/window behavior is not implemented by this maximum-age model. [TI SBVS366A](https://www.ti.com/lit/ds/symlink/tps3430.pdf) |

Neither family, package, exact orderable part, divider, timing capacitor nor purchasing entry is selected. A stuck WDI can time out, but a stuck-high/open WDO path is not diagnosed by the same single watchdog channel. Any future fault-tolerance claim must identify and test its covered fault set.

## Evidence, limitations and restart

`model.js` is shared by Node tests and the browser. `test_model.cjs` passes 61 tests, covering all 32 health combinations, adverse events, rejected state histories and a 5,000-step property trace; [test results](test_results.json) record model scope. [Viewer checks](viewer_check.json) verify desktop/phone interaction and local links. [Packet hashes](packet_manifest.json) bind source observations, model, diagram and documentation. These are software and captured-evidence results, not analog or hardware proofs. Events between samples, noise, propagation delay and actuator response are outside the model.

**Next smallest circuit packet:** implement the fault-dominant latch/OE gate on a new ACT-02 copy, with an explicit PC4-to-OE electrical delta and default-disabled qualification ports. Select exact latch/gate parts against power-up, partial-power, fault priority and recovery/removal limits; record native pin/identity comparison and checks. Keep receiver observation, rail-supervisor selection and command timing unresolved until their own interfaces and limits are justified. Do not wire an unqualified permission permanently high to make the prototype arm.

Use the [receiver acceptance worksheet](RECEIVER_ACCEPTANCE.md) to capture real ESC/BEC/servo identities and input/power behavior before choosing receiver interfaces. C11/VSERVO reservoir/transients, full 6S input feed, leakage/damping, ADC and combined IMU2 remain open. V1 inspection, V2 vehicle operation and the future voice/text/location handheld remain separate; measure voice/RC coexistence before handheld hardware selection.

Checks: `node reviews/codex/actuator_interlock/test_model.cjs`; `python -B reviews/codex/actuator_interlock/verify_observability.py --check`; `python -B tools/quality/check_publication.py`; `node pm/tools/validate.mjs`. Run `verify_viewer.cjs` after UI changes. No primary generator/router is needed.
