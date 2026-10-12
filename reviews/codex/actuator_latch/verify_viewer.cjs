const crypto=require('node:crypto');const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const{pathToFileURL}=require('node:url');const{chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});const checks=[],root=path.resolve(__dirname,'../../..');
try{for(const viewport of[{width:1440,height:1050},{width:390,height:844}]){
const page=await browser.newPage({viewport}),errors=[];page.on('pageerror',e=>errors.push(String(e)));
await page.goto(pathToFileURL(path.join(root,'pm/index.html')).href);
assert.match(await page.evaluate(()=>window.PROJECT.next[0]),/ACT-04/);await page.locator('nav [data-page="design"]').click();await page.locator('#asset-revision').selectOption('v2');
await page.locator('#asset-choice').selectOption('reviews/codex/actuator_latch/v2_actuator_latch.svg');
const img=page.locator('#asset-image');await img.evaluate(e=>e.decode());assert.equal(await img.evaluate(e=>e.complete&&e.naturalWidth>0),true);
assert.equal(await page.getByRole('link',{name:'ACT-04 candidate KiCad project',exact:true}).count(),1);
assert.match(await page.locator('#main').innerText(),/PCB integration pending/);
assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
await page.screenshot({path:path.join(__dirname,viewport.width>700?'viewer-desktop.png':'viewer-phone.png'),fullPage:true});
await page.locator('#zoom').fill('200');await page.locator('#zoom').dispatchEvent('input');assert.equal(await img.evaluate(e=>e.style.width),'200%');
await page.getByRole('button',{name:'Read ACT-04 latch and timing guide',exact:true}).click();const dialog=page.locator('dialog[open]');
assert.equal(await dialog.count(),1);const text=await dialog.innerText();assert.match(text,/TXU0102/);assert.match(text,/PC4/);assert.match(text,/396/);assert.match(text,/qualification source/);assert.match(text,/intentionally differs from ACT-03/);assert.equal(await dialog.evaluate(e=>e.scrollWidth<=e.clientWidth),true);
await page.screenshot({path:path.join(__dirname,viewport.width>700?'guide-desktop.png':'guide-phone.png'),fullPage:true});assert.deepEqual(errors,[]);
checks.push({viewport,svg_loaded:true,isolated_project_link:true,zoom_percent:200,guide_contract_and_holds_visible:true,horizontal_page_overflow:false,dialog_overflow:false,page_errors:errors});await page.close();}
fs.writeFileSync(path.join(__dirname,'viewer_check.json'),JSON.stringify({scope:'Local viewer navigation, SVG loading, zoom and guide layout; no circuit or hardware test',input_sha256:Object.fromEntries(['reviews/codex/actuator_latch/README.md','reviews/codex/actuator_latch/v2_actuator_latch.svg','reviews/codex/actuator_latch/verify_viewer.cjs','pm/index.template.html'].map(p=>[p,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')])),checks},null,2)+'\n');console.log(JSON.stringify(checks));
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
