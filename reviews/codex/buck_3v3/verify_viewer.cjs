const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const{pathToFileURL}=require('node:url');const{chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});const checks=[],root=path.resolve(__dirname,'../../..');
try{for(const viewport of[{width:1440,height:1050},{width:390,height:844}]){
const page=await browser.newPage({viewport}),errors=[];page.on('pageerror',e=>errors.push(String(e)));
await page.goto(pathToFileURL(path.join(root,'pm/index.html')).href);
await page.locator('nav [data-page="design"]').click();await page.locator('#asset-revision').selectOption('v2');
await page.locator('#asset-choice').selectOption('reviews/codex/buck_3v3/v2_buck_3v3.svg');
const img=page.locator('#asset-image');await img.evaluate(e=>e.decode());assert.equal(await img.evaluate(e=>e.complete&&e.naturalWidth>0),true);
assert.equal(await page.getByRole('link',{name:'BUCK33-A1 candidate KiCad project',exact:true}).count(),1);
assert.match(await page.locator('#main').innerText(),/PCB integration pending/);
assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
await page.screenshot({path:path.join(__dirname,viewport.width>700?'viewer-desktop.png':'viewer-phone.png'),fullPage:true});
await page.locator('#zoom').fill('200');await page.locator('#zoom').dispatchEvent('input');assert.equal(await img.evaluate(e=>e.style.width),'200%');
await page.getByRole('button',{name:'Read 3.3 V converter guide and next task',exact:true}).click();const dialog=page.locator('dialog[open]');
assert.equal(await dialog.count(),1);const text=await dialog.innerText();assert.match(text,/complete first 3.3 V converter/);assert.match(text,/dielectric exceptions under review/);assert.match(text,/330/);assert.match(text,/5 V converter cell/);assert.equal(await dialog.evaluate(e=>e.scrollWidth<=e.clientWidth),true);
await page.screenshot({path:path.join(__dirname,viewport.width>700?'guide-desktop.png':'guide-phone.png'),fullPage:true});assert.deepEqual(errors,[]);
checks.push({viewport,svg_loaded:true,isolated_project_link:true,zoom_percent:200,guide_contract_and_holds_visible:true,horizontal_page_overflow:false,dialog_overflow:false,page_errors:errors});await page.close();}
fs.writeFileSync(path.join(__dirname,'viewer_check.json'),JSON.stringify({scope:'Local viewer navigation, SVG loading, zoom and guide layout; no circuit or hardware test',checks},null,2)+'\n');console.log(JSON.stringify(checks));
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
