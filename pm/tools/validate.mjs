// Validate generated viewer packaging without executing browser UI code.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const html=fs.readFileSync(path.join(root,'pm/index.html'),'utf8');
const data=JSON.parse(fs.readFileSync(path.join(root,'pm/status.json'),'utf8'));
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
assert.equal(scripts.length,2,'Exactly one embedded data script and one UI script');
assert.ok(!html.includes('/*__PROJECT_DATA__*/'),'Data placeholder replaced');
scripts.forEach((s,i)=>new vm.Script(s,{filename:`viewer-script-${i}`}));
const context={window:{}};
vm.runInNewContext(scripts[0],context,{timeout:1000});
assert.deepEqual(JSON.parse(JSON.stringify(context.window.PROJECT)),data,'Embedded data matches status.json, including literal firmware dollar sequences');
assert.deepEqual(data.inputs_changed_during_build,[],'Evidence changed during build; rebuild from stable inputs');
assert.equal(data.bom.length,44,'V1 part inventory');
assert.ok(data.bomV2.every(r=>/^\d+$/.test(r.Item)),'V2 excludes aggregate TOTAL row');
if(data.bomV2Total)assert.equal(data.bomV2.reduce((n,r)=>n+Number(r.Qty),0),Number(data.bomV2Total.Qty),'V2 component quantities agree with source total');
assert.equal(new Set(data.designFindings.map(x=>x.id)).size,data.designFindings.length,'Unique findings');
for(const c of data.connectors)for(const p of c.pins||[])for(const e of p.evidence||[])assert.ok(data.sources.some(s=>s.path===e.path)||data.documents.some(d=>d.path===e.path),`Atlas evidence not embedded: ${e.path}`);
for(const p of data.available_paths)assert.ok(fs.existsSync(path.join(root,p)),`Missing indexed path: ${p}`);
for(const c of data.independent?.checks||[])for(const p of c.evidence||[])assert.ok(fs.existsSync(path.join(root,p)),`Missing independent evidence: ${p}`);
assert.ok(html.includes("build:'Build & program'"),'Build/program navigation exists');
assert.equal(data.manufacturing.variants.length,2,'Separate V1/V2 manufacturing packages');
for(const variant of data.manufacturing.variants){assert.ok(variant.summary,'Manufacturing summary available');for(const name of ['distributor_candidates_1board.csv','distributor_candidates_fleet5.csv','holds.csv','external_parts_review.csv','orientation_review.csv','assembly_top.svg','assembly_bottom.svg'])assert.ok(data.available_paths.includes(`hardware/manufacturing/${variant.id}/${name}`),`Build artifact indexed: ${variant.id}/${name}`);}
for(const name of ['ORDERING','ASSEMBLY_V1','ASSEMBLY_V2','FLASHING_V1','FLASHING_V2','FIRMWARE_BUILD','FIRMWARE_HANDOFF'])assert.ok(data.documents.some(d=>d.path===`docs/build/${name}.md`),`Build guide embedded: ${name}`);
assert.ok(data.documents.every(d=>!d.path.includes('/inputs/')&&!d.path.includes('/quality-baseline/')),'Copied review inputs are excluded from document library');
assert.equal(data.firmwareBuild.v2_image_available,false,'No V2 release image implied');
if(data.quality){assert.ok(data.quality.report.gates,'Current quality gates captured');for(const c of data.quality.report.checks)for(const p of c.evidence||[])assert.ok(data.available_paths.includes(p),`Current quality evidence indexed: ${p}`);}
if(process.argv.includes('--http')){
  const paths=[...new Set([...data.available_paths,...(data.independent?.checks||[]).flatMap(c=>c.evidence||[]),'FILE_OWNERSHIP.md'])];
  const base=`http://127.0.0.1:${Number(process.env.LORA_VIEWER_PORT||8765)}`;
  for(const p of paths){const response=await fetch(base+'/'+p.split('/').map(encodeURIComponent).join('/'));assert.equal(response.status,200,`HTTP evidence link: ${p}`);await response.body.cancel();}
  for(const p of ['/.git/config','/firmware/Debug/reproducible_v1/boat_v1_unqualified.bin','/tools/not-allowed.txt']){const response=await fetch(base+p);assert.equal(response.status,403,`Unapproved root remains blocked: ${p}`);await response.body.cancel();}
  console.log(JSON.stringify({http_links:'PASS',paths:paths.length}));
}
console.log(JSON.stringify({result:'PASS',scripts:scripts.length,parts:data.bom.length,v2_bom_rows:data.bomV2.length,connectors:data.connectors.length,requirements:data.requirements.length,findings:data.designFindings.length,documents:data.documents.length,existing_paths:data.available_paths.length}));
