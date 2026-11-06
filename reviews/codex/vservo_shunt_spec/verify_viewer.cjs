const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'../../..'),prefix='reviews/codex/vservo_shunt_spec/';
const url=p=>pathToFileURL(path.join(root,p)).href;
const analysis=JSON.parse(fs.readFileSync(path.join(__dirname,'analysis.json'),'utf8'));
const tracked=['README.md','RESULTS.md','analysis.json','model.py','viewer.template.html','index.html','v2_shunt_spec.svg','verify_viewer.cjs','build_packet.py'].map(n=>prefix+n).concat('pm/index.template.html','pm/tools/build.mjs');
const hashes=()=>Object.fromEntries(tracked.map(p=>[p,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')]));
const before=hashes();
async function displayMatches(page,id,result,fields){
 const target=page.locator(id);
 for(const field of fields){
  const text=await target.locator('[data-key="'+field+'"]').innerText();
  if(result.status==='unavailable')assert.equal(text,'Unavailable',id+'.'+field);
  else assert.ok(Math.abs(parseFloat(text)-result[field])<=0.00000051,`${id}.${field}: ${text} differs from ${result[field]}`);
 }
 if(id==='#branch-values')return;
 const positive=id==='#resistance-values'?'feasible':'positive_allocation',negative=id==='#resistance-values'?'infeasible':'no_margin';
 const boolField=Object.keys(result).find(k=>k.startsWith('strict_positive_'));
 assert.equal(await target.getAttribute('data-state'),result.status==='unavailable'?'unavailable':result[boolField]?positive:negative,id+' conditional state');
}
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
 const checks=[];
 try{
  const diagram=await browser.newPage({viewport:{width:1280,height:1100}}),diagramErrors=[];
  diagram.on('pageerror',e=>diagramErrors.push(String(e)));
  await diagram.goto(url(prefix+'v2_shunt_spec.svg'));
  const outside=await diagram.locator('text').evaluateAll(es=>es.map(e=>{const b=e.getBBox();return{text:e.textContent,x:b.x,y:b.y,width:b.width,height:b.height}}).filter(b=>b.x<0||b.y<0||b.x+b.width>1280||b.y+b.height>1100));
  assert.deepEqual(outside,[],'Diagram text must remain within view box');
  const resistorCaption=await diagram.locator('text').filter({hasText:/Unselected \/ pulse held|Pulse rating held/}).evaluate(e=>{const b=e.getBBox();return{x:b.x,right:b.x+b.width}});assert.ok(resistorCaption.x>=460&&resistorCaption.right<=640,'Resistor caption box: '+JSON.stringify(resistorCaption));
  const switchCaption=await diagram.locator('text').filter({hasText:'On-state bounds'}).evaluate(e=>{const b=e.getBBox();return{x:b.x,right:b.x+b.width}});assert.ok(switchCaption.x>=460&&switchCaption.right<=640,'Switch caption box: '+JSON.stringify(switchCaption));
  await diagram.screenshot({path:path.join(__dirname,'diagram-preview.png')});assert.deepEqual(diagramErrors,[]);await diagram.close();
  for(const viewport of [{width:1440,height:1050},{width:390,height:844}]){
   const suffix=viewport.width>700?'desktop':'phone',page=await browser.newPage({viewport}),errors=[];
   page.on('pageerror',e=>errors.push(String(e)));
   await page.goto(url('pm/index.html'));await page.locator('nav [data-page="design"]').click();
   await page.locator('#asset-revision').selectOption('v2');await page.locator('#asset-choice').selectOption(prefix+'v2_shunt_spec.svg');
   const img=page.locator('#asset-image');await img.evaluate(e=>e.decode());assert.equal(await img.evaluate(e=>e.naturalWidth),1280);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   await page.screenshot({path:path.join(__dirname,'viewer-'+suffix+'.png')});
   await page.locator('#zoom').fill('200');await page.locator('#zoom').dispatchEvent('input');assert.equal(await img.evaluate(e=>e.style.width),'200%');
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   for(const [name,patterns] of [['Read VSERVO-03 shunt specification',[/shunt/i,/reverse/i,/startup/i]],['Inspect shunt requirements and calculations',[/5\.789/,/9\.619/,/3\.883/]]]){
    await page.getByRole('button',{name,exact:true}).click();const dialog=page.locator('dialog[open]'),text=await dialog.innerText();for(const re of patterns)assert.match(text,re);
    assert.equal(await dialog.evaluate(e=>e.scrollWidth<=e.clientWidth),true);await page.keyboard.press('Escape');
   }
   assert.match(await page.getByRole('link',{name:'Explore local-shunt specification',exact:true}).getAttribute('href'),/vservo_shunt_spec\/index.html$/);
   await page.goto(url(prefix+'index.html'));assert.deepEqual(await page.evaluate(()=>evidence),analysis,'Embedded evidence equals captured analysis');
   assert.equal(await page.locator('#window-case').inputValue(),'unknown');assert.equal(await page.locator('#resistance-case').inputValue(),'unknown');
   for(const result of Object.values(analysis.actual)){
    assert.equal(result.status,'unavailable');assert.ok(result.missing_fields.length>0);assert.ok(Object.values(result.inputs).every(value=>value===null));
    assert.equal(result.hardware_accepted,false);assert.equal(result.device_release_approved,false);assert.equal(result.necessary_arithmetic_only,true);
   }
   assert.equal(Object.keys(analysis.actual).length,3);assert.equal(await page.locator('#actual-records .actual-card[data-status="unavailable"]').count(),3);
   assert.ok(((await page.locator('#actual-records').innerText()).match(/unavailable/gi)||[]).length>=3,'All three actual records visibly unavailable');
   for(const c of analysis.window_cases){
    await page.locator('#window-case').selectOption(c.id);
    await displayMatches(page,'#window-values',c.result,['release_margin_V','hysteresis_margin_V','protection_margin_V']);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   }
   for(const c of [{id:'unknown',result:analysis.actual.resistance_window},...analysis.resistance_cases]){
    await page.locator('#resistance-case').selectOption(c.id);
    await displayMatches(page,'#resistance-values',c.result,['nominal_lower_exclusive_ohm','nominal_upper_exclusive_ohm','nominal_interval_width_ohm']);
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   }
   await displayMatches(page,'#branch-values',analysis.branch_case,['sink_current_min_A','branch_current_max_A','sink_current_margin_A','resistor_instantaneous_upper_W','fet_on_state_conduction_upper_W']);
   for(const field of ['hardware_accepted','device_release_approved','parts_selected','native_commands_rerun','protection_qualified','fabrication_approved'])assert.equal(analysis[field],false);
   await page.locator('#window-case').selectOption('unknown');await page.locator('#resistance-case').selectOption('unknown');
   await page.screenshot({path:path.join(__dirname,'explorer-'+suffix+'.png'),fullPage:true});assert.deepEqual(errors,[]);
   checks.push({viewport,diagram_loaded:true,diagram_text_in_bounds:true,component_caption_bounds:true,pm_zoom_percent:200,two_guide_dialogs:true,actual_inputs_remain_null:true,three_actual_records_visible_unavailable:true,three_window_cases_match_analysis:true,three_resistance_cases_match_analysis:true,branch_current_and_power_bounds_match:true,unknown_defaults:true,embedded_analysis_matches:true,no_device_or_hardware_release:true,horizontal_overflow:false,page_errors:errors});await page.close();
  }
  assert.deepEqual(hashes(),before,'All browser inputs remain stable during capture');
  fs.writeFileSync(path.join(__dirname,'viewer_check.json'),JSON.stringify({scope:'Conditional local-shunt specification explorer and current viewer; no circuit insertion, selected device, waveform, SOA or hardware acceptance',input_sha256:before,checks},null,2)+'\n');
  console.log(JSON.stringify(checks));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
