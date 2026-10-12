const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const assert=require('node:assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const dir=__dirname,root=path.resolve(dir,'../../..');
const sha=p=>require('node:crypto').createHash('sha256').update(fs.readFileSync(p)).digest('hex');
(async()=>{
const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
const report={schema:1,date:new Date().toISOString(),scope:'Local browser arithmetic, input rejection and navigation only',hardware_tested:false,checks:[]};
try{
const recorded=JSON.parse(fs.readFileSync(path.join(dir,'comparison.json'),'utf8'));
const cases=[];
for(const[name,l,s]of[['external_bec_logic_ceiling',1.2,0],['illustrative_mixed_load',.35,.5],['simultaneous_output_goals',1.2,2]])for(const v of[7,25.2])cases.push({args:[v,l,s,.02,.85,.85],expected:recorded.cases[name][String(v)]});
cases.push({args:[7,1.2,2,0,1,1],expected:recorded.ideal_simultaneous_without_aux_at_7v});
for(const viewport of[{width:1440,height:1000},{width:390,height:844}]){
const page=await browser.newPage({viewport});const errors=[];page.on('pageerror',e=>errors.push(String(e)));
await page.goto(pathToFileURL(path.join(dir,'load_budget.html')).href);
for(const item of cases){const actual=await page.evaluate(args=>window.powerBudget(...args),item.args);for(const[key,expected]of Object.entries(item.expected)){if(typeof expected==='boolean')assert.equal(actual[key],expected);else assert.ok(Math.abs(actual[key]-expected)<1e-12,`${key} differs`);}}
assert.equal(await page.evaluate(()=>{let rejects=0;for(const args of[[0,1,1],[NaN,1,1],[Infinity,1,1],[7,-1,1],[7,1,1,.02,0,.85],[7,1,1,.02,1.01,.85]])try{window.powerBudget(...args)}catch{rejects++}return rejects}),6);
await page.locator('#full').click();assert.match(await page.locator('#status').innerText(),/Exceeds the proposed 1 A/);assert.match(await page.locator('#status').innerText(),/2 A total/);assert.equal(await page.locator('#current').innerText(),'2.363 A');
await page.locator('#vin').fill('25.2');assert.equal(await page.locator('#current').innerText(),'0.656 A');assert.doesNotMatch(await page.locator('#status').innerText(),/1 A board-feed/);
for(const invalid of['','0','26']){await page.locator('#vin').fill(invalid);assert.equal(await page.locator('#results').isVisible(),false);assert.ok((await page.locator('#error').innerText()).length>0);}
await page.locator('#external').click();assert.equal(await page.locator('#results').isVisible(),true);assert.match(await page.locator('#status').innerText(),/Within both/);assert.match(await page.locator('#servo-room').innerText(),/0.378 A/);
assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
assert.equal(await page.locator('#chart').evaluate(e=>e.innerHTML.includes('NaN')||e.innerHTML.includes('Infinity')),false);
await page.screenshot({path:path.join(dir,`calculator-${viewport.width}.png`),fullPage:true});
await page.goto(pathToFileURL(path.join(root,'pm/index.html')).href);
await page.locator('nav [data-page="design"]').click();await page.locator('#asset-revision').selectOption('v2');
await page.locator('#asset-choice').selectOption('reviews/codex/power_topology/v2_power_topologies.svg');
await page.locator('#asset-image').evaluate(img=>img.decode());assert.ok(await page.locator('#asset-image').evaluate(img=>img.naturalWidth>0));
assert.equal(await page.getByText('Planning map; no candidate PCB',{exact:true}).count(),1);
assert.ok(await page.getByRole('link',{name:'Explore interactive load budget',exact:true}).count());
assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
assert.deepEqual(errors,[]);
report.checks.push({viewport,calculated_cases_compared:cases.length,numeric_tolerance:1e-12,invalid_model_cases:6,invalid_form_cases:3,presets_and_capacity_messages:'pass',chart_finite:'pass',horizontal_overflow:false,viewer_map_loaded:true,calculator_link_present:true,page_errors:errors});
await page.close();
}
report.input_sha256=Object.fromEntries(['load_budget.html','comparison.json','verify_viewer.cjs','v2_power_topologies.svg'].map(p=>['reviews/codex/power_topology/'+p,sha(path.join(dir,p))]));
fs.writeFileSync(path.join(dir,'viewer_check.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
}finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
