const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'../../..'), prefix='reviews/codex/rail_qualification/';
(async()=>{const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})}), checks=[];
try{for(const viewport of [{width:1440,height:1050},{width:390,height:844}]){
const page=await browser.newPage({viewport}),errors=[];page.on('pageerror',e=>errors.push(String(e)));
await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href);
assert.match(await page.locator('#edge-result').innerText(),/54.49.*Fails/);
assert.equal(await page.locator('#plot').getAttribute('viewBox'),viewport.width<600?'0 0 420 270':'0 0 820 270');
for(const rail of ['3.3','5'])for(const setting of ['high','low'])for(const history of ['quiet','recovery']){
await page.locator('#rail').selectOption(rail);await page.locator('#setting').selectOption(setting);await page.locator('#history').selectOption(history);
assert.match(await page.locator('#voltage-status').innerText(),/permission remains disabled/);
assert.equal(await page.locator('#metrics .metric').count(),6);
await page.locator('#lower').click();assert.equal(Number(await page.locator('#voltage').inputValue()).toFixed(3),rail==='3.3'?'3.220':'4.866');
await page.locator('#upper').click();assert.equal(Number(await page.locator('#voltage').inputValue()).toFixed(3),rail==='3.3'?'3.412':'5.190');
}
for(const id of ['resistance','capacitance']){
for(const value of ['','0','-1','0.001',id==='resistance'?'1001':'10001']){
await page.locator('#'+id).fill(value);assert.match(await page.locator('#edge-result').innerText(),/Enter positive values/);assert.equal(await page.locator('#edge-result').getAttribute('class'),'fail');}
await page.locator('#'+id).fill('10');}
await page.locator('#resistance').fill('1');assert.match(await page.locator('#edge-result').innerText(),/Passes this average-only screen; complete edge qualification remains open/);await page.locator('#resistance').fill('10');
await page.locator('#rail').selectOption('3.3');await page.locator('#setting').selectOption('high');await page.locator('#history').selectOption('recovery');
assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
const links=await page.locator('a').evaluateAll(es=>es.map(e=>e.getAttribute('href')));
for(const href of links.filter(s=>!s.includes('://')))assert.ok(fs.existsSync(path.resolve(__dirname,href)),href);
await page.screenshot({path:path.join(__dirname,viewport.width>700?'explorer-desktop.png':'explorer-phone.png'),fullPage:true});
await page.goto(pathToFileURL(path.join(root,'pm/index.html')).href);assert.match(await page.evaluate(()=>window.PROJECT.next[0]),/ACT-05/);
await page.locator('nav [data-page="design"]').click();await page.locator('#asset-revision').selectOption('v2');await page.locator('#asset-choice').selectOption(prefix+'v2_rail_qualification.svg');await page.locator('#asset-image').evaluate(e=>e.decode());
assert.match(await page.locator('#main').innerText(),/Planning map; no candidate PCB/);
await page.getByRole('button',{name:'Read ACT-05 review and next task',exact:true}).click();assert.match(await page.locator('dialog[open]').innerText(),/ACT-04 remains/);assert.equal(await page.locator('dialog[open]').evaluate(e=>e.scrollWidth<=e.clientWidth),true);
assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);assert.deepEqual(errors,[]);
await page.screenshot({path:path.join(__dirname,viewport.width>700?'workspace-desktop.png':'workspace-phone.png'),fullPage:true});
checks.push({viewport,rail_setting_history_cases:8,invalid_edge_cases:10,average_pass_remains_held:true,default_edge_fails:true,voltage_controls:true,local_links_exist:true,workspace_figure_and_guide:true,page_errors:errors,horizontal_overflow:false});await page.close();}
const inputs=['index.html','index.template.html','analysis.json','README.md','v2_rail_qualification.svg','verify_viewer.cjs'].map(s=>prefix+s).concat(['pm/index.template.html']);
fs.writeFileSync(path.join(__dirname,'viewer_check.json'),JSON.stringify({scope:'Local file-origin explorer and workspace checks; no circuit or hardware acceptance',input_sha256:Object.fromEntries(inputs.map(p=>[p,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')])),checks},null,2)+'\n');console.log(JSON.stringify(checks));
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
