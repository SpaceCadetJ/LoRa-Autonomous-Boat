# ACT-11 - supply-state and discharge evidence

[Decision and proposed connections](README.md) | [Primary-source conditions](sources.json) | [Annotated review](v2_vcca_shutdown.svg)

## Supply-state applicability

These are source conditions and a logical restart counterexample, not simulated or measured waveforms. No supply-collapse deadline is qualified.

| Condition | Source result / inference | Limitation |
|---|---|---|
| Both supplies within valid ranges; OE valid low | Outputs high impedance through OE control | OE timing depends on specified edge and load; this does not bound supply collapse. |
| VCCA <100mV; VCCB valid | Documented static supply isolation | No maximum entry time established. Hold the rail below the condition against feed. |
| VCCA undriven, external leakage<=10nA; VCCB valid | Documented disconnected-supply isolation | A QOD-connected rail is not the floating test case. Low inputs recommended; Ioff-float test ports atGND. |
| VCCA between isolation endpoint and valid range, or bouncing | Glitch-free sequencing documented; no fast-inhibit deadline established | Do not grant operation or claim the <100mV condition before it is reached. |
| VCCB outside its applicable range | Single-rail isolation condition cannot be applied without its prerequisites | Assess both rails and external feed; default permission stays disabled. |
| TPS22919 IN drops below1.6V during shutdown | Outside recommended switch input range | Cannot assume QOD24ohm or continuous discharge persists. |
| Only U4 VCCA was interrupted; U12-U14 remained powered and QUAL/ARM/READY high | Old enable request is retained and can resume on restoration | Power cycling U4 does not clear READY. Separate fault clear and fresh ACK are required. |

## Scale illustration using typical QOD resistance

Keep nominal C13 = 100 nF. With R = 24 ohm (typical only), starting voltage 3.6 V and an allocated 80 mV target, use ACT-10's tested constant-feed decay function:

`Vfloor = I * R; t = R*C*ln((Vstart-Vfloor)/(Vtarget-Vfloor))`

| Allocated positive feed (mA) | Modeled floor (mV) | Time to 80 mV after ideal disconnection (us) |
|---|---:|---:|
| 0.000 | 0.000 | 9.135990 |
| 0.100 | 2.400 | 9.207492 |
| 1.000 | 24.000 | 9.975956 |
| 4.000 | 96.000 | Unreachable |

The zero-feed illustration takes **9.135990 us** after ideal disconnection, before adding switch-control and translator supply-isolation delays. It uses no 100 ohm external load. This is neither a best-case lower bound nor a worst-case upper bound. Actual effective C, QOD resistance and feed vary and remain unqualified. The 4 mA example approaches 96 mV: it misses the allocated 80 mV guard target, although that modeled floor is below the source's 100 mV static condition. It does not prove failure or success of actual isolation.

For nominal C13, removing charge from 3.6 V to 80 mV requires **352.000 nC**. Doing that within the entire 245 ns downstream allocation requires an average **net** sink of **1.436735 A**, even with instantaneous disconnection and zero subsequent propagation delay. This requirement calculation is not a current rating or a suggested circuit. Removing bypass to improve this arithmetic is not justified.

The finite-crossing feed ceiling for this typical resistance is **3.333333 mA**, strictly exclusive at equality. It is not an accepted leakage allowance. TPS22919's supply shutdown current does not establish total current feeding VCCA_SW through all pins and paths.

## Decision and restart consequence

The reviewed VCCA-gating option is **not accepted as the primary fast inhibit**. Source response maxima are missing; the typical scale is far longer than the inherited allocation. It remains only a possible secondary de-energization mechanism after an independent fast inhibit. That secondary role is also unqualified while input power, backfeed, transient output state and restoration remain open.

Cycling U4 alone leaves U12's separately powered READY state intact. With QUAL, ARM and READY still high, U14 can request enable again when U4 is repowered. Therefore fault handling must clear READY independently and require a new healthy interval and fresh ACK before later ARM. A completed discharge or fixed delay cannot grant rearm.

Do not silently replace the 400 ns total / 245 ns downstream allocation with a slower limit. First write a connector-level fault envelope distinguishing fast inhibit, indefinite disabled hold, and rearm; keep unknown receiver acceptance held. [Next bounded task](README.md#next-smallest-task).
