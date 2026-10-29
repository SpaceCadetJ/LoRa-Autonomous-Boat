const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'../../..'),prefix='reviews/codex/power_sheet_polish/';
const url=p=>pathToFileURL(path.join(root,p)).href;
const record=JSON.parse(fs.readFileSync(path.join(__dirname,'validation.json'),'utf8'));
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});const checks=[];
 try{
  for(const viewport of [{width:1440,height:1050},{width:390,height:844}]){
   const suffix=viewport.width>700?'desktop':'phone',page=await browser.newPage({viewport}),errors=[];page.on('pageerror',e=>errors.push(String(e)));
   await page.goto(url(prefix+'index.html'));assert.deepEqual(await page.evaluate(()=>evidence),record);
   const sheet=page.locator('#sheet');await sheet.evaluate(e=>e.decode());assert.ok(await sheet.evaluate(e=>e.naturalWidth>0));
   assert.equal(await page.locator('#revised').getAttribute('aria-pressed'),'true');assert.match(await sheet.getAttribute('src'),/^native/);
   assert.match(await page.locator('#components').innerText(),/128/);assert.match(await page.locator('#pins').innerText(),/429/);
   await page.locator('#baseline').click();await sheet.evaluate(e=>e.decode());assert.match(await sheet.getAttribute('src'),/vservo_reservoir/);assert.equal(await page.locator('#baseline').getAttribute('aria-pressed'),'true');
   for(const zoom of ['200','400']){await page.locator('#zoom').selectOption(zoom);assert.equal(await sheet.evaluate(e=>e.style.width),zoom+'%');assert.ok(await page.locator('#viewport').evaluate(e=>e.scrollWidth>e.clientWidth));assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true)}
   await page.locator('#revised').click();await sheet.evaluate(e=>e.decode());await page.locator('#fit').click();assert.equal(await sheet.evaluate(e=>e.style.width),'100%');
   assert.match(await page.locator('#native-link').getAttribute('href'),/^native/);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   await page.screenshot({path:path.join(__dirname,'comparison-'+suffix+'.png'),fullPage:true});
   await page.goto(url('pm/index.html'));await page.locator('nav [data-page="design"]').click();await page.locator('#asset-revision').selectOption('v2');await page.locator('#asset-choice').selectOption(prefix+'native/svg/LoRa_Boat_Controller_V2-Power.svg');
   const image=page.locator('#asset-image');await image.evaluate(e=>e.decode());assert.ok(await image.evaluate(e=>e.naturalWidth>0));
   assert.match(await page.getByRole('link',{name:'POWER-DOC-01 presentation KiCad project',exact:true}).getAttribute('href'),/power_sheet_polish\/source\/hardware\/kicad_v2\/LoRa_Boat_Controller_V2.kicad_pro$/);
   assert.match(await page.getByRole('link',{name:'Compare native Power sheets',exact:true}).getAttribute('href'),/power_sheet_polish\/index.html$/);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);await page.screenshot({path:path.join(__dirname,'viewer-'+suffix+'.png')});
   await page.locator('#zoom').fill('200');await page.locator('#zoom').dispatchEvent('input');assert.equal(await image.evaluate(e=>e.style.width),'200%');
   await page.getByRole('button',{name:'Read Power sheet presentation review',exact:true}).click();const dialog=page.locator('dialog[open]');assert.match(await dialog.innerText(),/429/);assert.match(await dialog.innerText(),/independent local-shunt/);assert.equal(await dialog.evaluate(e=>e.scrollWidth<=e.clientWidth),true);await page.keyboard.press('Escape');
   assert.deepEqual(errors,[]);checks.push({viewport,before_after_native_images:true,comparison_zoom:[100,200,400],fit_resets:true,scroll_contained:true,embedded_validation_matches:true,pm_native_picker_and_project_link:true,pm_zoom:200,guide_dialog:true,horizontal_overflow:false,page_errors:errors});await page.close();
  }
  const files=['README.md','validation.json','index.html','viewer.template.html','build_view.py','verify_viewer.cjs','native/svg/LoRa_Boat_Controller_V2-Power.svg','native-power-preview.png','native-reservoir-detail.png','preview_native.cjs'].map(n=>prefix+n).concat('pm/index.template.html','pm/tools/build.mjs','reviews/codex/vservo_reservoir/native/svg/LoRa_Boat_Controller_V2-Power.svg');
  fs.writeFileSync(path.join(__dirname,'viewer_check.json'),JSON.stringify({scope:'Native Power sheet before/after UI and current PM integration; no hardware or complete project visual acceptance',input_sha256:Object.fromEntries(files.map(n=>[n,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,n))).digest('hex')])),checks},null,2)+'\n');console.log(JSON.stringify(checks));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
