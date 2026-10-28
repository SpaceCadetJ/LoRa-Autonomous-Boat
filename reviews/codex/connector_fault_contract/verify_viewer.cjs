const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'../../..'),prefix='reviews/codex/connector_fault_contract/';
const url=p=>pathToFileURL(path.join(root,p)).href;
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
 const checks=[];
 try{
  const diagram=await browser.newPage({viewport:{width:1280,height:980}});
  await diagram.goto(url(prefix+'v2_connector_fault_contract.svg'));
  assert.deepEqual(await diagram.locator('text').evaluateAll(es=>es.map(e=>({text:e.textContent,b:e.getBBox()})).filter(x=>x.b.x<0||x.b.x+x.b.width>1280||x.b.y+x.b.height>980).map(x=>x.text)),[]);
  await diagram.screenshot({path:path.join(__dirname,'diagram-preview.png')});await diagram.close();
  for(const viewport of [{width:1440,height:1050},{width:390,height:844}]){
   const suffix=viewport.width>700?'desktop':'phone',page=await browser.newPage({viewport}),errors=[];
   page.on('pageerror',e=>errors.push(String(e)));
   await page.goto(url('pm/index.html'));
   assert.match(await page.evaluate(()=>window.PROJECT.next[0]),/ACT-12/);
   await page.locator('nav [data-page="design"]').click();
   await page.locator('#asset-revision').selectOption('v2');
   await page.locator('#asset-choice').selectOption(prefix+'v2_connector_fault_contract.svg');
   const img=page.locator('#asset-image');await img.evaluate(e=>e.decode());assert.equal(await img.evaluate(e=>e.naturalWidth),1280);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   await page.screenshot({path:path.join(__dirname,'viewer-'+suffix+'.png')});
   await page.locator('#zoom').fill('200');await page.locator('#zoom').dispatchEvent('input');assert.equal(await img.evaluate(e=>e.style.width),'200%');
   for(const [name,patterns] of [['Read ACT-12 connector contract',[/electrical and copper delta: zero/,/Normal ARM-low disarm retains READY/]],['Inspect connector paths and timing',[/0.089899476/,/245 ns/]],['Read future fault measurement plan',[/NOT RUN/,/before the fault/]]]){
    await page.getByRole('button',{name,exact:true}).click();const dialog=page.locator('dialog[open]'),text=await dialog.innerText();
    for(const re of patterns)assert.match(text,re);
    assert.equal(await dialog.evaluate(e=>e.scrollWidth<=e.clientWidth),true);await page.keyboard.press('Escape');
   }
   const link=page.getByRole('link',{name:'Explore actuator fault requirements',exact:true});assert.match(await link.getAttribute('href'),/connector_fault_contract\/index.html$/);
   await page.goto(url(prefix+'index.html'));
   for(const [id,expected] of [['ramp','Fast inhibit'],['pulse','Fast inhibit'],['dwell','Continuous disabled hold'],['restore','Fresh rearm'],['remote','All three obligations']]){
    await page.locator('#scenario').selectOption(id);assert.equal(await page.locator('#phase').innerText(),expected);assert.ok((await page.locator('#case-details').innerText()).length>200);
   }
   assert.equal(await page.locator('#receivers .box').count(),2);assert.equal(await page.locator('#receivers li').count(),20);
   await page.locator('#rail').selectOption('OV');await page.locator('#slew').selectOption('0.1');assert.match(await page.locator('#residual').innerText(),/-4.040210 mV/);assert.match(await page.locator('#margin').innerText(),/exhausted/);
   await page.locator('#rail').selectOption('UV');assert.match(await page.locator('#residual').innerText(),/26.938003 mV/);assert.match(await page.locator('#margin').innerText(),/unqualified/);
   await page.locator('#slew').selectOption('boundary');assert.equal(await page.locator('#residual').innerText(),'0.000000 mV residual');assert.match(await page.locator('#margin').innerText(),/no positive margin/);
   await page.locator('#scenario').selectOption('restore');await page.screenshot({path:path.join(__dirname,'explorer-'+suffix+'.png'),fullPage:true});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);assert.deepEqual(errors,[]);
   checks.push({viewport,diagram_loaded:true,zoom_percent:200,three_guide_dialogs:true,five_fault_cases:true,twenty_missing_evidence_groups:true,UV_OV_and_zero_margin_cases:true,horizontal_overflow:false,page_errors:errors});await page.close();
  }
  const files=['README.md','MEASUREMENT_PLAN.md','RESULTS.md','analysis.json','index.html','explorer.template.html','v2_connector_fault_contract.svg','verify_viewer.cjs'].map(n=>prefix+n).concat('pm/index.template.html');
  fs.writeFileSync(path.join(__dirname,'viewer_check.json'),JSON.stringify({scope:'Local portable viewer and requirements explorer; no physical waveform, native or hardware tests',input_sha256:Object.fromEntries(files.map(p=>[p,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')])),checks},null,2)+'\n');console.log(JSON.stringify(checks));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
