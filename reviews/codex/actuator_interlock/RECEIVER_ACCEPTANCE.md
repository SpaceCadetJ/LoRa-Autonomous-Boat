# Receiver and actuator acceptance worksheet

One record per exact ESC/BEC/servo combination, harness and source population. Attach this to the existing [unit acceptance record](../../../docs/applications/ACCEPTANCE_RECORD.md). An empty field means unresolved; this worksheet authorizes no powering, flashing, ordering or vehicle operation.

## Identity and evidence

| Required field | Recorded value / source / reviewer |
|---|---|
| Board revision, netlist / BOM / firmware / profile hashes | Unresolved |
| D4/D9 fitted/omitted evidence; BEC_ONLY or ONBOARD | Unresolved |
| ESC manufacturer, model, hardware/firmware version, serial | Unresolved |
| BEC manufacturer/model, internal or separate, exact electrical limits | Unresolved |
| Servo manufacturer/model, hardware/firmware version, serial | Unresolved |
| Manuals/datasheets: revision, URL, saved hash, relevant pages | Unresolved |
| Harness: diagram, pin order, contacts, wire gauge/length, ground return | Unresolved |

## Power and signal contract

| Required limit | Evidence needed before selection |
|---|---|
| ESC propulsion supply versus control supply | Identify each source and whether BEC status predicts control readiness; an unsupported inference is not a specification |
| Servo supply at the receiver | Operating range, startup/stall current, harness drop and regenerative behavior |
| Signal input at powered and unpowered receiver | Thresholds, absolute voltage, injection/backfeed limit, clamps/pulls and required series impedance |
| Control waveform | Frequency, pulse/protocol range, arm, idle/neutral, reverse/brake and calibration procedure; do not assume 1000 µs means stop |
| Loss/fault response | Measured/documented no-pulse, stuck-high/low, last-command retention, reconnect and power-cycle behavior |
| Readiness observation | Exact sensed node and receiving pin; what it proves and cannot prove; missing-wire/ground, short and stuck-signal outcomes |
| Observation thresholds | Tolerance corners, hysteresis, deglitch, assertion/deassertion delay and bounded startup/initialization |
| Stop budget | Last accepted command to inhibit, signal change and actual actuator response; predeclared acceptance limits |

## Future qualification plan

Plan tests before execution and release through the project's existing hardware gates. Include each supply order, absent/unpowered receiver, slow collapse and brownout, disconnect/reconnect, signal backdrive, MCU stall, stale interrupt/DMA strobes, stuck request/watchdog/ready signals, bad/replayed traffic and worst specified load transients. Preserve synchronized raw traces, probe/instrument settings, temperatures, test loads, acceptance limits, pass/fail disposition and reviewer.

A local rail voltage, passing ERC, compiled image or successful software scenario does not fill these fields. If an input limit is absent from the receiver documentation, record the gap and resolve it through manufacturer evidence or a separately approved characterization plan.
