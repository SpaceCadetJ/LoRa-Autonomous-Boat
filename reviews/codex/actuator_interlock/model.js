/* ACT-03 behavioral proposal; no hardware or timing qualification.
 * UMD API: createState(); step(state, inputs, now_ms, config?).
 * Eight named inputs must be own boolean fields, with no extra fields.
 * command_service_edge is a SAMPLED strobe: a false sample is required before
 * each accepted true edge. An edge represents new valid command processing;
 * this model cannot authenticate commands or distinguish stale IRQ strobes.
 * Defaults: qualify_ms=100, watchdog_ms=100 (illustrative). Config fields may
 * be omitted; supplied values and time must be nonnegative safe integers.
 * Equal timestamps are permitted; decreasing time is rejected. Changing
 * timing parameters starts a new LOCKED qualification epoch.
 * Every successful call returns a new frozen state. Invalid arguments throw
 * without mutating the old state or inputs. A hardware caller must DISABLE
 * on validation failure, not reuse an old enabled result as a new permission.
 * Public UI fields: enabled, phase, reason/reasons, qualifiedForMs,
 * serviceAgeMs (null before first accepted edge), acceptedServiceEdges,
 * lastServiceAt, lastUpdateAt, qualificationStartedAt. Underscore fields are
 * model bookkeeping, not hardware observations. createState always LOCKED;
 * do not restore a persisted enabled state to authorize real outputs.
 * This sampled maximum-age watchdog is not a TPS3430 window/timing model.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.ActuatorInterlock = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const INPUT_NAMES = Object.freeze(["logic_good", "driver_good", "esc_ready",
    "servo_ready", "stop_closed", "arm_request", "acknowledge", "command_service_edge"]);
  const HEALTH_NAMES = Object.freeze(INPUT_NAMES.slice(0, 5));
  const DEFAULT_CONFIG = Object.freeze({qualify_ms: 100, watchdog_ms: 100});
  const PHASES = ["LOCKED", "READY", "ARMED"];
  const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
  function requireValue(ok, message) { if (!ok) throw new TypeError(message); }
  function integer(value, name) {
    if (!Number.isSafeInteger(value) || value < 0) throw new RangeError(name + " must be a nonnegative safe integer");
  }
  function object(value, name) {
    requireValue(value !== null && typeof value === "object" && !Array.isArray(value), name + " must be an object");
  }
  function inputsValid(inputs) {
    object(inputs, "inputs");
    requireValue(Object.keys(inputs).length === INPUT_NAMES.length, "all eight inputs, and only those inputs, are required");
    INPUT_NAMES.forEach(name => requireValue(own(inputs, name) && typeof inputs[name] === "boolean", name + " must be a boolean"));
  }
  function configValid(value) {
    object(value, "config");
    requireValue(Object.keys(value).every(key => own(DEFAULT_CONFIG, key)), "unknown config field");
    const config = {...DEFAULT_CONFIG, ...value};
    integer(config.qualify_ms, "qualify_ms"); integer(config.watchdog_ms, "watchdog_ms");
    return config;
  }
  function stateValid(state) {
    object(state, "state");
    requireValue(PHASES.includes(state.phase) && state.enabled === (state.phase === "ARMED"), "invalid phase/enabled state");
    inputsValid(state._previousInputs);
    integer(state.qualifiedForMs, "qualifiedForMs"); integer(state.acceptedServiceEdges, "acceptedServiceEdges");
    for (const key of ["lastUpdateAt", "lastServiceAt", "qualificationStartedAt", "serviceAgeMs"]) {
      if (state[key] !== null) integer(state[key], key);
    }
    if (state._config !== null) {
      configValid(state._config);
      requireValue(Object.keys(state._config).length === 2 && own(state._config,"qualify_ms")
        && own(state._config,"watchdog_ms"), "incomplete timing history");
    }
    requireValue(Array.isArray(state.reasons) && state.reasons.length > 0 && state.reasons.every(x => typeof x === "string")
      && state.reason === state.reasons[0], "invalid reasons");
    if (state.lastUpdateAt === null) {
      requireValue(state.phase === "LOCKED" && state.lastServiceAt === null && state.serviceAgeMs === null
        && state.qualificationStartedAt === null && state.qualifiedForMs === 0 && state.acceptedServiceEdges === 0
        && state._config === null, "invalid startup state");
    } else {
      requireValue(state._config !== null, "missing timing history");
      requireValue(state.lastServiceAt === null ? state.serviceAgeMs === null :
        state.lastServiceAt <= state.lastUpdateAt && state.serviceAgeMs === state.lastUpdateAt - state.lastServiceAt,
        "invalid service history");
      requireValue(state.qualificationStartedAt === null ? state.qualifiedForMs === 0 && state.acceptedServiceEdges === 0 :
        state.qualificationStartedAt <= state.lastUpdateAt && state.qualifiedForMs === state.lastUpdateAt - state.qualificationStartedAt,
        "invalid qualification history");
    }
    // Reject inconsistent caller-supplied snapshots. These checks establish
    // model consistency only; they cannot authenticate historical observations.
    if (state.phase !== "LOCKED") {
      requireValue(HEALTH_NAMES.every(name => state._previousInputs[name]), "enabled phase has failed prior health");
      requireValue(state.qualificationStartedAt !== null && state.acceptedServiceEdges >= 2
        && state.qualifiedForMs >= state._config.qualify_ms, "enabled phase lacks qualification");
      requireValue(state.lastServiceAt !== null && state.serviceAgeMs !== null
        && state.serviceAgeMs < state._config.watchdog_ms, "enabled phase lacks fresh service");
      requireValue(state._previousInputs.arm_request === (state.phase === "ARMED"), "phase disagrees with prior arm request");
    }
  }
  function freeze(state) {
    Object.freeze(state.reasons); Object.freeze(state._previousInputs);
    if (state._config !== null) Object.freeze(state._config);
    return Object.freeze(state);
  }
  function createState() {
    return freeze({enabled: false, phase: "LOCKED", reason: "startup_locked", reasons: ["startup_locked"],
      qualifiedForMs: 0, serviceAgeMs: null, acceptedServiceEdges: 0,
      lastServiceAt: null, lastUpdateAt: null, qualificationStartedAt: null,
      _previousInputs: Object.fromEntries(INPUT_NAMES.map(name => [name, false])), _config: null});
  }
  function step(state, inputs, now_ms, config = DEFAULT_CONFIG) {
    // Complete validation before constructing any updated state.
    stateValid(state); inputsValid(inputs); integer(now_ms, "now_ms");
    if (state.lastUpdateAt !== null && now_ms < state.lastUpdateAt) throw new RangeError("time must be monotonic");
    const timing = configValid(config);
    const changedTiming = state._config !== null && (timing.qualify_ms !== state._config.qualify_ms
      || timing.watchdog_ms !== state._config.watchdog_ms);
    const pulse = inputs.command_service_edge && !state._previousInputs.command_service_edge;
    const ackEdge = inputs.acknowledge && !state._previousInputs.acknowledge;
    const armEdge = inputs.arm_request && !state._previousInputs.arm_request;
    const failures = HEALTH_NAMES.filter(name => !inputs[name]).map(name => name + "_false");
    // Evaluate the old deadline BEFORE accepting a new edge. Subtraction
    // avoids overflowing a safe-integer absolute timestamp plus interval.
    const oldLimit = state._config === null ? timing.watchdog_ms : state._config.watchdog_ms;
    const oldExpired = state.lastServiceAt !== null && now_ms - state.lastServiceAt >= oldLimit;
    const lastServiceAt = pulse ? now_ms : state.lastServiceAt;
    const serviceAgeMs = lastServiceAt === null ? null : now_ms - lastServiceAt;
    const fresh = serviceAgeMs !== null && serviceAgeMs < timing.watchdog_ms;
    const healthy = failures.length === 0;
    if (oldExpired) failures.push("service_deadline_expired");
    else if (!fresh) failures.push("no_fresh_command_service");
    if (changedTiming) failures.push("timing_changed_requalify");
    const resetEpoch = !healthy || !fresh || oldExpired || changedTiming;
    let qualificationStartedAt = resetEpoch ? null : state.qualificationStartedAt;
    let acceptedServiceEdges = resetEpoch ? 0 : state.acceptedServiceEdges;
    // A new pulse on an expired-gap step may start a NEW epoch. The fault
    // still wins below, including with zero qualification time and ACK high.
    if (healthy && fresh) {
      if (qualificationStartedAt === null) qualificationStartedAt = now_ms;
      if (pulse) acceptedServiceEdges = Math.min(Number.MAX_SAFE_INTEGER, acceptedServiceEdges + 1);
    }
    const qualifiedForMs = qualificationStartedAt === null ? 0 : now_ms - qualificationStartedAt;
    let phase = state.phase;
    let reasons;
    if (failures.length) {
      phase = "LOCKED"; reasons = failures;
    } else if (phase === "LOCKED") {
      reasons = [];
      if (qualifiedForMs < timing.qualify_ms) reasons.push("qualifying");
      if (acceptedServiceEdges < 2) reasons.push("two_service_edges_required");
      if (inputs.arm_request) reasons.push("arm_must_be_low");
      if (reasons.length === 0 && ackEdge) { phase = "READY"; reasons.push("acknowledged"); }
      else if (reasons.length === 0) reasons.push("new_acknowledge_required");
    } else if (phase === "READY") {
      if (armEdge) { phase = "ARMED"; reasons = ["armed"]; }
      else reasons = ["ready"];
    } else if (!inputs.arm_request) {
      phase = "READY"; reasons = ["disarmed"];
    } else reasons = ["armed"];
    return freeze({enabled: phase === "ARMED", phase, reason: reasons[0], reasons,
      qualifiedForMs, serviceAgeMs, acceptedServiceEdges, lastServiceAt, lastUpdateAt: now_ms,
      qualificationStartedAt, _previousInputs: {...inputs}, _config: timing});
  }
  return Object.freeze({createState, step, INPUT_NAMES, HEALTH_NAMES, DEFAULT_CONFIG});
});
