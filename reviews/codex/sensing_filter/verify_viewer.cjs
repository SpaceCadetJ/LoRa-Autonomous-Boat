const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'../../..'),prefix='reviews/codex/sensing_filter/';
const candidate=prefix+'native/svg/LoRa_Boat_Controller_V2-Power.svg',baseline='reviews/codex/power_sheet_polish/native/svg/LoRa_Boat_Controller_V2-Power.svg';
const url=p=>pathToFileURL(path.join(root,p)).href;
const files=['README.md','RESULTS.md','filter_analysis.json','validation.json','verify_viewer.cjs','preview_native.cjs','native-power-preview.png','native-sensing-detail.png','native/svg/LoRa_Boat_Controller_V2-Power.svg','source/hardware/kicad_v2/LoRa_Boat_Controller_V2.kicad_pro'].map(n=>prefix+n).concat(baseline,'pm/index.template.html','pm/tools/build.mjs');
const hashes=()=>Object.fromEntries(files.map(n=>[n,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,n))).digest('hex')]));const before=hashes();
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_EXECUTABLE});const checks=[];
try{
 for(const viewport of [{width:1440,height:1050},{width:390,height:844}]){
 const page=await browser.newPage({viewport}),errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto(url('pm/index.html'));await page.locator('nav [data-page="design"]').click();
 await page.locator('#asset-revision').selectOption('v1');assert.equal(await page.locator('#asset-choice option[value="'+candidate+'"]').count(),0);
 await page.locator('#asset-revision').selectOption('v2');await page.locator('#asset-choice').selectOption(candidate);
 let img=page.locator('#asset-image');await img.evaluate(e=>e.decode());assert.ok(await img.evaluate(e=>e.naturalWidth>0));
 assert.match(await page.getByRole('link',{name:'SENSE-02 isolated candidate KiCad project',exact:true}).getAttribute('href'),/sensing_filter\/source\/hardware\/kicad_v2\/LoRa_Boat_Controller_V2.kicad_pro$/);
 assert.match(await page.locator('#main').innerText(),/PCB integration pending/);
 for(const choice of [baseline,candidate]){await page.locator('#asset-choice').selectOption(choice);await page.locator('#asset-image').evaluate(e=>e.decode());assert.match(await page.locator('#asset-image').getAttribute('src'),choice===candidate?/sensing_filter/:/power_sheet_polish/);}
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.screenshot({path:path.join(__dirname,'viewer-'+(viewport.width>700?'desktop':'phone')+'.png')});
 await page.locator('#zoom').fill('200');await page.locator('#zoom').dispatchEvent('input');assert.equal(await page.locator('#asset-image').evaluate(e=>e.style.width),'200%');assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 for(const [button,file,patterns] of [['Read SENSE-02 candidate guide','README.md',[/27 mutation/,/effective capacitance/,/not a clamp/]],['Inspect sensing filter results','RESULTS.md',[/433/,/1591\.549431/,/unqualified/]]]){
 const source=fs.readFileSync(path.join(__dirname,file),'utf8');assert.equal(await page.evaluate(p=>D.documents.find(d=>d.path===p).text,prefix+file),source);
 await page.getByRole('button',{name:button,exact:true}).click();const dialog=page.locator('dialog[open]'),text=await dialog.innerText();for(const pattern of patterns)assert.match(text,pattern);
 assert.equal(await dialog.evaluate(e=>e.scrollWidth<=e.clientWidth),true);if(file==='README.md')await page.screenshot({path:path.join(__dirname,'guide-'+(viewport.width>700?'desktop':'phone')+'.png')});await page.keyboard.press('Escape');
 }
 assert.deepEqual(errors,[]);checks.push({viewport,new_asset_v2_only:true,baseline_and_candidate_images:true,isolated_project_link:true,pcb_integration_pending:true,zoom_percent:200,embedded_guides_exact:true,guide_dialogs:2,horizontal_overflow:false,page_errors:errors});await page.close();
 }
 assert.deepEqual(hashes(),before,'Inputs changed during capture');
 fs.writeFileSync(path.join(__dirname,'viewer_check.json'),JSON.stringify({scope:'Current PM native candidate navigation and desktop/phone guides; native images visually reviewed separately; no hardware acceptance',input_sha256:before,checks},null,2)+'\n');console.log(JSON.stringify(checks));
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
