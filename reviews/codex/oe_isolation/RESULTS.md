# ACT-10 - OE discharge and timing screen

[Connection proposal and limits](README.md) | [Source conditions](sources.json) | [Annotated diagram](v2_oe_isolation.svg)

**The series-switch proposal is held.** Partial-power isolation and actual timing remain unqualified. No native circuit, hardware or production component is accepted. These calculations use explicit allocations and a single-pole model.

## R40 discharge after disconnection

R40 remains 10 kOhm. Allocated 1% tolerance gives Rmax=10100ohm. Initial OE is 3.6 V, the low target 0.8 V and total positive feed 5 uA. Feed equilibrium is0.0505 V. Capacitance is the whole node, including switch, receiver, routing and probing.

`Vfloor = Ifeed * R`

`V(t) = Vfloor + (Vinitial - Vfloor) * exp(-t / (R * C))`

`t_target = R * C * ln((Vinitial - Vfloor) / (Vtarget - Vfloor))`

If Vfloor is at or above the target, there is no finite guaranteed crossing; the model returns an unreachable result. The asymptotic feed ceiling is **79.207921uA**. Equality is not a usable design point. No actual leakage envelope is asserted.

## Downstream allocation

The optimistic screen is55 ns switch transition + full RC decay +36 ns translator disable. Other logic/guard delay is set to zero. Against the245 ns allocation:

| Total node C (pF) | RC to target (ns) | Downstream screen (ns) | Margin (ns) | Arithmetic disposition |
|---|---:|---:|---:|---|
| 8 | 125.657 | 216.657 | 28.343 | Fits arithmetic only |
| 10 | 157.071 | 248.071 | -3.071 | Exceeds allocation |
| 15 | 235.606 | 326.606 | -81.606 | Exceeds allocation |
| 20 | 314.141 | 405.141 | -160.141 | Exceeds allocation |
| 50 | 785.354 | 876.354 | -631.354 | Exceeds allocation |

The zero-margin total-capacitance ceiling is **9.804500pF**. Positive guard/logic delay or injected charge reduces this ceiling. Do not infer hardware failure from an allocated case or hardware acceptance from a positive margin.

The source switch timing measurement uses a fast control edge and200 ohm/15 pF load. Its supply-off test measures only the first10% output drop; it is not a logic-low time. The translator disable table uses a fast OE edge and5 pF output load. At the allocated target, the model's OE inverse slew (time per volt) is `R*C/(Vtarget-Vfloor)` in seconds/volt. It is much slower than the translator timing test. Adding the two table values therefore **does not establish a guaranteed end-to-end bound**. The actual partial-power waveform, switching injection, output load and threshold behavior remain open.

## Circuit decision

A series switch avoids adding a sink against U14's active output, but isolation must persist through every observer-supply state. Neither the permitted signal-voltage range below 1.5 V nor the zero-supply leakage endpoint proves arbitrary dwell/bounce isolation. The normal range also limits the signal to twice VDD: a 3.6 V request requires VDD>=1.8 V while VDD>=1.5 V. Charge injection is not maximally bounded by this screen. Thus every case keeps physical acceptance false regardless of arithmetic margin.

Next evaluate translator VCCA gating/discharge under its own supply-isolation conditions, with a separate supply-collapse timing contract. Never substitute the36 ns OE table value for supply-collapse response. Keep VCCB and U12/U13/U14 supplies unchanged. [Restart and remaining gates](README.md#next-smallest-circuit-task).
