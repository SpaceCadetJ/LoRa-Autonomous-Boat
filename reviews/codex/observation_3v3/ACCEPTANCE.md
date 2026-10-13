# 3.3 V observation acceptance worksheet

This is a design-review worksheet. All results below are **unperformed** unless linked to a captured analytical or source result. It is not permission to power or flash hardware. Record exact board, component, firmware and instrument identities before later approved bench work.

| Case / boundary | Evidence needed before native acceptance | Current result |
|---|---|---|
| Normal extremes | Entire converter envelope including dynamic, noise, PFM and aging remains inside worst recovery bounds | Conditional arithmetic only; converter envelope incomplete |
| Divider/reference errors | Exact resistor MPNs, reference error at actual load/supply, BOX drift, solder, aging and leakage fit allocated totals | Values and total budgets proposed; no complete part proof |
| Comparator thresholds | Input offset, hysteresis, bias and common-mode/supply effects bounded across chosen temperature | Hysteresis maximum and application conditions missing |
| UV/OV monotone ramp | Declared start/end, direction, maximum slew, sense settling, minimum overdrive duration, load and temperature; valid detector max then total inhibit deadline | Conditional model at 0.01, 0.1 and 1 V/us; no waveform guarantee |
| Step through limit | Define allowed post-fault inhibit latency and whether independent clamp or supply isolation is needed | No pre-crossing response can be assumed |
| Short/ringing pulse | Captured pulse shape and detector acceptance; retained clear measured after every detected event | No glitch rejection or pulse-detection guarantee |
| Monitor and reference startup | Exact supply; IN/EN ramps, force/sense and bypass; output low until observer valid; ARM/ACK low | Unimplemented; reference slow-slew warning remains |
| Rail dies before observer | Maximum injection at both comparator inputs and all outputs; no phantom supply or false permission | Unimplemented |
| Observer dies before rail | Default-low local permission during every partial-power state, not merely at exactly0V | Unimplemented |
| Supply bounce / restart | Retain fault; complete reset before release; no ACK/ARM edge races | Unimplemented |
| Full permission | Combine5V,receiver-ready,watchdog,stop continuity and local observation through reviewed logic | QUAL_OK/ACK remain undriven low |
| Actuator response | Receiver-specific input behavior and accepted stop latency separate from translator OE | Receiver identities/tests unresolved |

For any later trace, record timebase, probe/load capacitance, voltage at the actual pins, output threshold, temperature and tolerance corner. Distinguish a measured sample from a worst-case guarantee. Source test conditions that are not reproduced need an explicit applicability argument. Do not promote assumed 400 ns allocation to measured latency or operational acceptance.
