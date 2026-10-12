#!/usr/bin/env node
"use strict";
// Behavioral tests only. No firmware, physical watchdog or actuator is tested.
// --record is optional and writes only this packet's test_results.json.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const crypto = require("node:crypto");
const M = require("./model.js");
const results = [];
function test(name, fn) {
  try { fn(); results.push({name, status: "pass"}); }
  catch (error) { results.push({name, status: "fail", error: String(error.stack || error)}); }
}
function healthy() {
  return {logic_good:true, driver_good:true, esc_ready:true, servo_ready:true, stop_closed:true,
    arm_request:false, acknowledge:false, command_service_edge:false};
}
function machine(config = M.DEFAULT_CONFIG) {
  let state = M.createState(), inputs = healthy();
  return {get state(){return state;}, get inputs(){return inputs;},
    at(now, patch = {}) { inputs = {...inputs, ...patch}; state = M.step(state, inputs, now, config); return state; }};
}
function ready() {
  const m = machine();
  m.at(0,{command_service_edge:true}); m.at(20,{command_service_edge:false});
  m.at(40,{command_service_edge:true}); m.at(80,{command_service_edge:false});
  assert.equal(m.at(100,{acknowledge:true}).phase,"READY"); return m;
}
function armed() { const m = ready(); assert.equal(m.at(101,{arm_request:true}).enabled,true); return m; }
function rejectedUnchanged(state, inputs, now, config) {
  const old = JSON.stringify(state), originalInputs = JSON.stringify(inputs);
  assert.throws(() => M.step(state,inputs,now,config));
  assert.equal(JSON.stringify(state),old); assert.equal(JSON.stringify(inputs),originalInputs);
}

test("contract input names and illustrative defaults match", () => {
  const c = JSON.parse(fs.readFileSync(path.join(__dirname,"contract.json"),"utf8"));
  assert.deepEqual(M.INPUT_NAMES,c.inputs); assert.deepEqual(M.DEFAULT_CONFIG,c.demo_timing_ms);
});
test("browser UMD and CommonJS expose the same pure API", () => {
  const context = {}; vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname,"model.js"),"utf8"),context);
  assert.equal(typeof context.ActuatorInterlock.step,"function");
  assert.deepEqual(JSON.parse(JSON.stringify(context.ActuatorInterlock.createState())),JSON.parse(JSON.stringify(M.createState())));
});
test("startup ignores inherited physical-high assumptions and is immutable", () => {
  const s = M.createState({enabled:true,phase:"ARMED"});
  assert.equal(s.enabled,false); assert.equal(s.phase,"LOCKED");
  assert.equal(s.lastServiceAt,null); assert.equal(s.serviceAgeMs,null);
  assert.throws(() => {s.enabled=true;}); assert.throws(() => {s._previousInputs.arm_request=true;});
});
test("qualification, new ACK, subsequent ARM and normal disarm", () => {
  const m = ready(); assert.equal(m.state.acceptedServiceEdges,2); assert.equal(m.state.qualifiedForMs,100);
  assert.equal(m.at(101,{arm_request:true}).phase,"ARMED");
  assert.equal(m.at(102,{arm_request:false}).phase,"READY");
  assert.equal(m.at(103,{arm_request:true}).phase,"ARMED");
});
test("one startup pulse cannot qualify even with short qualification", () => {
  const m = machine({qualify_ms:10,watchdog_ms:1000});
  m.at(0,{command_service_edge:true});
  assert.equal(m.at(20,{acknowledge:true}).phase,"LOCKED");
  assert.equal(m.state.acceptedServiceEdges,1); assert.ok(m.state.reasons.includes("two_service_edges_required"));
});
test("zero qualification still needs two service rises and separate ARM", () => {
  const m = machine({qualify_ms:0,watchdog_ms:100});
  m.at(0,{command_service_edge:true}); m.at(1,{command_service_edge:false});
  assert.equal(m.at(2,{command_service_edge:true,acknowledge:true}).phase,"READY");
  assert.equal(m.at(3,{arm_request:true}).phase,"ARMED");
});
test("zero watchdog interval never yields fresh service", () => {
  const m = machine({qualify_ms:0,watchdog_ms:0});
  for(let t=0;t<12;t++) assert.equal(m.at(t,{command_service_edge:t%2===0,acknowledge:t%3===0,arm_request:t%4===0}).enabled,false);
});
test("ACK held through qualification is not a new acknowledgment", () => {
  const m = machine(); m.at(0,{command_service_edge:true,acknowledge:true});
  m.at(20,{command_service_edge:false}); m.at(40,{command_service_edge:true}); m.at(80,{command_service_edge:false});
  assert.equal(m.at(100).phase,"LOCKED");
  m.at(101,{acknowledge:false}); assert.equal(m.at(102,{acknowledge:true}).phase,"READY");
});
test("same-step ACK plus ARM cannot unlock or enable", () => {
  const m = machine(); m.at(0,{command_service_edge:true}); m.at(20,{command_service_edge:false});
  m.at(40,{command_service_edge:true}); m.at(80,{command_service_edge:false});
  assert.equal(m.at(100,{acknowledge:true,arm_request:true}).phase,"LOCKED");
  assert.equal(m.at(101,{arm_request:false}).phase,"LOCKED");
  m.at(102,{acknowledge:false}); assert.equal(m.at(103,{acknowledge:true}).phase,"READY");
  assert.equal(m.at(104,{arm_request:true}).enabled,true);
});
test("initial ARM-high cannot auto-enable on qualification", () => {
  const m = machine(); m.at(0,{arm_request:true,command_service_edge:true}); m.at(20,{command_service_edge:false});
  m.at(40,{command_service_edge:true}); m.at(80,{command_service_edge:false});
  assert.equal(m.at(100,{acknowledge:true}).phase,"LOCKED"); assert.equal(m.state.enabled,false);
});
for(let bits=0;bits<32;bits++) test("all health combinations while armed: "+bits.toString(2).padStart(5,"0"), () => {
  const m = armed(), patch = {};
  M.HEALTH_NAMES.forEach((key,index) => {patch[key]=Boolean(bits & (1<<index));});
  const s=m.at(110,patch); assert.equal(s.enabled,bits===31); assert.equal(s.phase,bits===31?"ARMED":"LOCKED");
});
test("every health fault wins over simultaneous new ACK and ARM", () => {
  for(const name of M.HEALTH_NAMES) {
    const m=ready(); m.at(101,{acknowledge:false});
    const s=m.at(102,{[name]:false,acknowledge:true,arm_request:true,command_service_edge:true});
    assert.equal(s.phase,"LOCKED"); assert.ok(s.reasons.includes(name+"_false"));
  }
});
test("rail return and held ACK cannot rearm; explicit recovery succeeds", () => {
  const m=armed(); m.at(110,{driver_good:false});
  m.at(120,{driver_good:true,arm_request:false,command_service_edge:true});
  m.at(140,{command_service_edge:false}); m.at(170,{command_service_edge:true}); m.at(190,{command_service_edge:false});
  assert.equal(m.at(220,{command_service_edge:true}).phase,"LOCKED");
  m.at(221,{acknowledge:false,command_service_edge:false});
  assert.equal(m.at(222,{acknowledge:true}).phase,"READY"); assert.equal(m.at(223,{arm_request:true}).phase,"ARMED");
});
test("health gap resets qualification and accepted service count", () => {
  const m=machine(); m.at(0,{command_service_edge:true}); m.at(20,{command_service_edge:false});
  const lost=m.at(30,{esc_ready:false}); assert.equal(lost.acceptedServiceEdges,0); assert.equal(lost.qualifiedForMs,0);
  m.at(40,{esc_ready:true}); assert.equal(m.state.acceptedServiceEdges,0);
  m.at(50,{command_service_edge:true}); m.at(80,{command_service_edge:false}); m.at(90,{command_service_edge:true});
  assert.equal(m.at(140,{acknowledge:true}).phase,"READY"); assert.equal(m.state.qualifiedForMs,100);
});
test("watchdog boundary: before deadline allowed, exactly deadline locked", () => {
  const m=armed(); assert.equal(m.at(139).enabled,true);
  const s=m.at(140); assert.equal(s.phase,"LOCKED"); assert.equal(s.serviceAgeMs,100);
  assert.ok(s.reasons.includes("service_deadline_expired"));
});
test("new pulse at deadline cannot conceal old expiry", () => {
  const m=armed(); m.at(102,{acknowledge:false});
  const s=m.at(140,{command_service_edge:true,acknowledge:true,arm_request:false});
  assert.equal(s.phase,"LOCKED"); assert.equal(s.lastServiceAt,140); assert.equal(s.serviceAgeMs,0);
  assert.equal(s.acceptedServiceEdges,1); assert.equal(s.qualifiedForMs,0);
  assert.ok(s.reasons.includes("service_deadline_expired"));
  m.at(141,{command_service_edge:false,acknowledge:false});
  assert.equal(m.at(150,{command_service_edge:true,acknowledge:true}).phase,"LOCKED");
});
test("long sampling gap plus fresh pulse cannot inherit qualification", () => {
  const m=armed(); const s=m.at(5000,{command_service_edge:true,arm_request:false,acknowledge:true});
  assert.equal(s.phase,"LOCKED"); assert.equal(s.qualificationStartedAt,5000); assert.equal(s.qualifiedForMs,0);
  assert.equal(s.acceptedServiceEdges,1);
});
test("stuck-high heartbeat is only one edge and eventually expires", () => {
  const m=machine({qualify_ms:10,watchdog_ms:100});
  m.at(0,{command_service_edge:true}); m.at(20,{acknowledge:true});
  assert.equal(m.state.acceptedServiceEdges,1); assert.equal(m.at(100).phase,"LOCKED");
  assert.equal(m.state.lastServiceAt,0); assert.equal(m.at(1000).enabled,false);
});
test("stopped command processing locks an armed model", () => {
  const m=armed(); assert.equal(m.at(140,{command_service_edge:false}).enabled,false);
});
test("COUNTEREXAMPLE: periodic stale IRQ strobes can fool the watchdog", () => {
  const m=armed();
  // No command payload, sequence number, validity or freshness is observed.
  // These artificial alternating strobes intentionally keep permission alive.
  for(let t=110;t<=1010;t+=10) assert.equal(m.at(t,{command_service_edge:(t/10)%2===1}).enabled,true);
  assert.ok(m.state.acceptedServiceEdges>2);
});
test("COUNTEREXAMPLE: faults entirely between samples are unobserved", () => {
  const m=armed();
  // A real fault between t=101 and t=110 is absent from all model inputs.
  assert.equal(m.at(110,{command_service_edge:true}).enabled,true);
});
test("unknown or missing receiver-ready input is rejected atomically", () => {
  const m=armed(), old=m.state;
  for(const bad of [undefined,null,"unknown",0,1]) rejectedUnchanged(old,{...m.inputs,servo_ready:bad},110);
  const missing={...m.inputs}; delete missing.esc_ready; rejectedUnchanged(old,missing,110);
  assert.equal(old.enabled,true); // Caller must disable on rejection; no new permission was produced.
});
test("every input rejects truthy/falsy coercion and extra fields", () => {
  const s=M.createState();
  for(const name of M.INPUT_NAMES) for(const bad of [0,1,"true","false",null,undefined,NaN,[],{}])
    rejectedUnchanged(s,{...healthy(),[name]:bad},0);
  rejectedUnchanged(s,{...healthy(),surprise:true},0);
  for(const bad of [null,[],"inputs",true]) rejectedUnchanged(s,bad,0);
});
test("invalid time/config, including backward time, cannot mutate state", () => {
  const m=armed();
  for(const now of [-1,1.2,NaN,Infinity,Number.MAX_SAFE_INTEGER+1,"110",100]) rejectedUnchanged(m.state,m.inputs,now);
  for(const key of ["qualify_ms","watchdog_ms"]) for(const bad of [-1,1.2,NaN,Infinity,Number.MAX_SAFE_INTEGER+1,"100",null])
    rejectedUnchanged(m.state,m.inputs,110,{...M.DEFAULT_CONFIG,[key]:bad});
  for(const bad of [null,[],true,{unexpected:1}]) rejectedUnchanged(m.state,m.inputs,110,bad);
});
test("equal timestamps and maximum safe integer time are well-defined", () => {
  const s=M.step(M.createState(),healthy(),Number.MAX_SAFE_INTEGER);
  assert.equal(M.step(s,healthy(),Number.MAX_SAFE_INTEGER).phase,"LOCKED");
  const near=machine(); near.at(Number.MAX_SAFE_INTEGER-100,{command_service_edge:true});
  assert.ok(near.at(Number.MAX_SAFE_INTEGER).reasons.includes("service_deadline_expired"));
});
test("timing changes lock and requalify rather than inherit permission", () => {
  const m=armed(); const s=M.step(m.state,m.inputs,110,{qualify_ms:0,watchdog_ms:1000});
  assert.equal(s.phase,"LOCKED"); assert.equal(s.acceptedServiceEdges,0);
  assert.ok(s.reasons.includes("timing_changed_requalify"));
});
test("successful updates are pure and do not freeze caller-owned inputs", () => {
  const s=M.createState(), inputs=healthy(), before=JSON.stringify(s), config={qualify_ms:10,watchdog_ms:50};
  const next=M.step(s,inputs,0,config);
  assert.notEqual(next,s); assert.equal(JSON.stringify(s),before);
  assert.equal(Object.isFrozen(inputs),false); assert.equal(Object.isFrozen(config),false);
  inputs.arm_request=true; config.qualify_ms=0;
  assert.equal(next._previousInputs.arm_request,false); assert.equal(next._config.qualify_ms,10);
});
test("inconsistent READY/ARMED snapshots cannot bypass qualification", () => {
  for (const source of [ready().state, armed().state]) {
    const mutations = [
      s => {s.acceptedServiceEdges=0;},
      s => {s.acceptedServiceEdges=1;},
      s => {s.qualificationStartedAt=null; s.qualifiedForMs=0; s.acceptedServiceEdges=0;},
      s => {s._config.qualify_ms=s.qualifiedForMs+1;},
      s => {s.lastServiceAt=s.lastUpdateAt-s._config.watchdog_ms; s.serviceAgeMs=s._config.watchdog_ms;},
      s => {s.lastServiceAt=null; s.serviceAgeMs=null;},
      s => {s._previousInputs.arm_request=!s._previousInputs.arm_request;},
      s => {delete s._config.qualify_ms;},
      ...M.HEALTH_NAMES.map(key => s => {s._previousInputs[key]=false;})
    ];
    for (const mutate of mutations) {
      const forged=JSON.parse(JSON.stringify(source)); mutate(forged);
      rejectedUnchanged(forged,healthy(),source.lastUpdateAt+1);
    }
  }
});
test("consistent serialized READY/ARMED snapshots remain model-readable", () => {
  // Serialization is for scenario replay, not authorization of real hardware.
  for (const source of [ready().state, armed().state]) {
    const snapshot=JSON.parse(JSON.stringify(source));
    const next=M.step(snapshot,{...source._previousInputs},source.lastUpdateAt+1);
    assert.equal(next.phase,source.phase);
  }
});
test("deterministic 5000-step property trace enforces enable invariants", () => {
  let seed=0x194d03, s=M.createState(), now=0, enabledSteps=0;
  function rnd(n){seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed%n;}
  for(let i=0;i<5000;i++) {
    now+=rnd(9); const inputs=healthy();
    M.HEALTH_NAMES.forEach(key => {inputs[key]=rnd(200)!==0;});
    inputs.command_service_edge=i%4===0; inputs.acknowledge=i%9===0; inputs.arm_request=i%10>=5;
    const old=s; s=M.step(s,inputs,now);
    assert.equal(s.enabled,s.phase==="ARMED"); assert.equal(Object.isFrozen(s),true);
    if(M.HEALTH_NAMES.some(key=>!inputs[key]) || (old.lastServiceAt!==null && now-old.lastServiceAt>=100)) assert.equal(s.enabled,false);
    if(s.enabled) {
      enabledSteps++; assert.ok(M.HEALTH_NAMES.every(key=>inputs[key])); assert.ok(s.serviceAgeMs<100);
      assert.ok(s.acceptedServiceEdges>=2); assert.ok(s.qualifiedForMs>=100);
      assert.ok(inputs.arm_request); assert.ok(old.phase==="ARMED" || (old.phase==="READY" && !old._previousInputs.arm_request));
    }
  }
  assert.ok(enabledSteps>20,"property trace must actually exercise enabled states");
});

const hash = file => crypto.createHash("sha256").update(fs.readFileSync(path.join(__dirname,file))).digest("hex");
const summary = {schema:1,revision:"ACT-03",classification:"behavioral_proposal_tests_not_hardware",
  model_sha256:hash("model.js"),contract_sha256:hash("contract.json"),test_runner_sha256:hash("test_model.cjs"),
  tests:results.length,passed:results.filter(x=>x.status==="pass").length,failed:results.filter(x=>x.status==="fail").length,
  results,hardware_tested:false,firmware_tested:false};
if(process.argv.slice(2).some(x=>x!=="--record")) throw new Error("Only --record is supported");
if(process.argv.includes("--record")) fs.writeFileSync(path.join(__dirname,"test_results.json"),JSON.stringify(summary,null,2)+"\n");
process.stdout.write(JSON.stringify(summary)+"\n");
if(summary.failed) process.exitCode=1;
