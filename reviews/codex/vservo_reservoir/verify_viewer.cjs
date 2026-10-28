const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'../../..'),prefix='reviews/codex/vservo_reservoir/';
const url=p=>pathToFileURL(path.join(root,p)).href;
const nativePower='native/svg/LoRa_Boat_Controller_V2-Power.svg';
const analysis=JSON.parse(fs.readFileSync(path.join(__dirname,'analysis.json'),'utf8'));
function near(actual,expected,label){assert.ok(Math.abs(actual-expected)<=0.00000051,label+': '+actual+' != '+expected)}
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
 const checks=[];
 try{
  const diagram=await browser.newPage({viewport:{width:1280,height:980}}),diagramErrors=[];
  diagram.on('pageerror',e=>diagramErrors.push(String(e)));
  await diagram.goto(url(prefix+'v2_vservo_reservoir.svg'));
  const outOfBounds=await diagram.locator('text').evaluateAll(es=>es.map(e=>{const b=e.getBBox();return{text:e.textContent,x:b.x,y:b.y,width:b.width,height:b.height}}).filter(x=>x.x<0||x.y<0||x.x+x.width>1280||x.y+x.height>980));
  assert.deepEqual(outOfBounds,[],'Annotated diagram text must remain in its view box');
  await diagram.screenshot({path:path.join(__dirname,'diagram-preview.png')});
  await diagram.goto(url(prefix+nativePower));
  assert.match(await diagram.locator('svg').textContent(),/C11/);
  await diagram.locator('svg').evaluate(e=>{e.style.width='1280px';e.style.height='906px';e.style.display='block';e.style.background='white'});
  await diagram.screenshot({path:path.join(__dirname,'native-power-preview.png')});
  assert.deepEqual(diagramErrors,[]);await diagram.close();
  for(const viewport of [{width:1440,height:1050},{width:390,height:844}]){
   const suffix=viewport.width>700?'desktop':'phone',page=await browser.newPage({viewport}),errors=[];
   page.on('pageerror',e=>errors.push(String(e)));
   await page.goto(url('pm/index.html'));
   assert.match(await page.evaluate(()=>window.PROJECT.next[0]),/VSERVO-01/);
   await page.locator('nav [data-page="design"]').click();
   await page.locator('#asset-revision').selectOption('v2');
   await page.locator('#asset-choice').selectOption(prefix+'v2_vservo_reservoir.svg');
   const img=page.locator('#asset-image');await img.evaluate(e=>e.decode());assert.equal(await img.evaluate(e=>e.naturalWidth),1280);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   await page.screenshot({path:path.join(__dirname,'viewer-'+suffix+'.png')});
   await page.locator('#zoom').fill('200');await page.locator('#zoom').dispatchEvent('input');assert.equal(await img.evaluate(e=>e.style.width),'200%');
   for(const [name,patterns] of [['Read VSERVO-01 C11 candidate',[/EEEFK1C101P/,/zero pin\/net changes/,/reservoir/i]],['Inspect reservoir calculations',[/125/,/56/,/4\.275/]]]){
    await page.getByRole('button',{name,exact:true}).click();const dialog=page.locator('dialog[open]'),text=await dialog.innerText();
    for(const re of patterns)assert.match(text,re);
    assert.equal(await dialog.evaluate(e=>e.scrollWidth<=e.clientWidth),true);
    if(name==='Inspect reservoir calculations')await page.screenshot({path:path.join(__dirname,'results-'+suffix+'.png')});
    await page.keyboard.press('Escape');
   }
   const link=page.getByRole('link',{name:'Explore VSERVO reservoir limits',exact:true});assert.match(await link.getAttribute('href'),/vservo_reservoir\/index.html$/);
   await page.goto(url(prefix+'index.html'));
   assert.equal(await page.locator('#capacity').inputValue(),'1');assert.equal(await page.locator('#energy').inputValue(),'1');
   const exactData=await page.evaluate(()=>evidence);const calculationOnly=data=>Object.fromEntries(Object.entries(data).filter(([key])=>!['native_summary','input_sha256'].includes(key)));assert.deepEqual(calculationOnly(exactData),calculationOnly(analysis),'Embedded explorer calculations must match analysis.json');
   const bodyText=await page.locator('body').innerText();for(const term of [/receiver voltage limits are unknown/,/16 V rating does not set/,/120 Hz/,/20 C/,/not an all-temperature/,/0 µF/,/360 mOhm/])assert.match(bodyText,term);
   for(let c=0;c<analysis.cases.length;c++){
    await page.locator('#capacity').selectOption(String(c));const step=analysis.cases[c].load_step;
    assert.equal(await page.locator('#capacity-condition').innerText(),analysis.cases[c].label);
    near(parseFloat(await page.locator('#step-voltage').innerText()),step.voltage_V,'step voltage');near(parseFloat(await page.locator('#step-margin').innerText()),step.headroom_V,'step headroom');
    assert.equal(await page.locator('#step-status').getAttribute('data-positive'),String(step.strict_positive_allocated_headroom));
    for(let e=0;e<analysis.cases[c].energy_cases.length;e++){
     await page.locator('#energy').selectOption(String(e));const energy=analysis.cases[c].energy_cases[e];
     near(parseFloat(await page.locator('#energy-voltage').innerText()),energy.voltage_V,'energy voltage');near(parseFloat(await page.locator('#energy-margin').innerText()),energy.headroom_V,'energy headroom');
     assert.equal(await page.locator('#energy-status').getAttribute('data-positive'),String(energy.strict_positive_allocated_headroom));
     const threshold=analysis.required_C_energy[e].required_capacitance_F*1e6;assert.ok((await page.locator('#energy-required').innerText()).includes(threshold.toFixed(6)));
     assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    }
   }
   for(const name of ['hardware_accepted','component_selected_for_release','voltage_envelope_qualified','actual_load_known','effective_capacitance_bound_qualified','reservoir_qualified'])assert.equal(analysis[name],false);
   await page.locator('#capacity').selectOption('1');await page.locator('#energy').selectOption('1');
   await page.screenshot({path:path.join(__dirname,'explorer-'+suffix+'.png'),fullPage:true});
   assert.deepEqual(errors,[]);
   checks.push({viewport,diagram_loaded:true,annotated_diagram_text_in_bounds:true,native_power_preview:true,zoom_percent:200,two_guide_dialogs:true,source_conditions_visible:true,three_load_steps_match_analysis:true,nine_energy_cases_match_analysis:true,strict_arithmetic_margin_only:true,physical_acceptance_flags_false:true,horizontal_overflow:false,page_errors:errors});await page.close();
  }
  const files=['README.md','RESULTS.md','analysis.json','model.py','index.html','explorer.template.html','v2_vservo_reservoir.svg',nativePower,'verify_viewer.cjs'].map(n=>prefix+n).concat('pm/index.template.html');
  fs.writeFileSync(path.join(__dirname,'viewer_check.json'),JSON.stringify({scope:'Local portable viewer, native drawing preview and allocated reservoir arithmetic; no waveform, load or hardware tests',input_sha256:Object.fromEntries(files.map(p=>[p,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')])),checks},null,2)+'\n');
  console.log(JSON.stringify(checks));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
