const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'../../..'),prefix='reviews/codex/vservo_transients/';
const url=p=>pathToFileURL(path.join(root,p)).href;
const analysis=JSON.parse(fs.readFileSync(path.join(__dirname,'analysis.json'),'utf8'));
function near(actual,expected,label){assert.ok(Math.abs(actual-expected)<=0.00000051,label+': '+actual+' != '+expected)}
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
 const checks=[];
 try{
  const diagram=await browser.newPage({viewport:{width:1280,height:980}}),diagramErrors=[];
  diagram.on('pageerror',e=>diagramErrors.push(String(e)));
  await diagram.goto(url(prefix+'v2_vservo_transients.svg'));
  const outside=await diagram.locator('text').evaluateAll(es=>es.map(e=>{const b=e.getBBox();return{text:e.textContent,x:b.x,y:b.y,width:b.width,height:b.height}}).filter(x=>x.x<0||x.y<0||x.x+x.width>1280||x.y+x.height>980));
  assert.deepEqual(outside,[],'Annotated diagram text must stay in its view box');
  await diagram.screenshot({path:path.join(__dirname,'diagram-preview.png')});assert.deepEqual(diagramErrors,[]);await diagram.close();
  for(const viewport of [{width:1440,height:1050},{width:390,height:844}]){
   const suffix=viewport.width>700?'desktop':'phone',page=await browser.newPage({viewport}),errors=[];
   page.on('pageerror',e=>errors.push(String(e)));
   await page.goto(url('pm/index.html'));assert.match(await page.evaluate(()=>window.PROJECT.next[0]),/VSERVO-02/);
   await page.locator('nav [data-page="design"]').click();await page.locator('#asset-revision').selectOption('v2');
   await page.locator('#asset-choice').selectOption(prefix+'v2_vservo_transients.svg');
   const img=page.locator('#asset-image');await img.evaluate(e=>e.decode());assert.equal(await img.evaluate(e=>e.naturalWidth),1280);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   await page.screenshot({path:path.join(__dirname,'viewer-'+suffix+'.png')});
   await page.locator('#zoom').fill('200');await page.locator('#zoom').dispatchEvent('input');assert.equal(await img.evaluate(e=>e.style.width),'200%');
   for(const [name,patterns] of [['Read VSERVO-02 transient boundary',[/local dissipative shunt/,/maximum cumulative/,/reverse-voltage/]],['Inspect sink and clamp calculations',[/0\.210/,/0\.790/,/0\.062500 V/]]]){
    await page.getByRole('button',{name,exact:true}).click();const dialog=page.locator('dialog[open]'),text=await dialog.innerText();for(const re of patterns)assert.match(text,re);
    assert.equal(await dialog.evaluate(e=>e.scrollWidth<=e.clientWidth),true);await page.keyboard.press('Escape');
   }
   assert.match(await page.getByRole('link',{name:'Explore VSERVO protection limits',exact:true}).getAttribute('href'),/vservo_transients\/index.html$/);
   await page.goto(url(prefix+'index.html'));assert.equal(await page.locator('#window-case').inputValue(),'unknown');
   const embedded=await page.evaluate(()=>evidence),calculationOnly=data=>Object.fromEntries(Object.entries(data).filter(([key])=>!['topology','input_sha256'].includes(key)));
   assert.deepEqual(calculationOnly(embedded),calculationOnly(analysis),'Embedded model evidence must match recorded analysis');
   for(const result of Object.values(analysis.actual)){assert.equal(result.status,'unavailable');assert.ok(result.missing_fields.length>0);assert.ok(Object.values(result.inputs).every(value=>value===null));assert.equal(result.hardware_accepted,false)}
   assert.equal(await page.locator('#actual-records .actual-card[data-status="unavailable"]').count(),4);
   for(const c of analysis.window_cases){
    await page.locator('#window-case').selectOption(c.id);const r=c.result;assert.equal(await page.locator('#window-label').innerText(),c.label);
    if(r.status==='unavailable'){assert.equal(await page.locator('#off-margin').innerText(),'Unavailable');assert.equal(await page.locator('#protection-margin').innerText(),'Unavailable');assert.equal(await page.locator('#window-status').getAttribute('data-state'),'unavailable')}
    else{near(parseFloat(await page.locator('#off-margin').innerText()),r.off_margin_V,'off margin');near(parseFloat(await page.locator('#protection-margin').innerText()),r.protection_margin_V,'protection margin');assert.equal(await page.locator('#window-status').getAttribute('data-state'),r.strict_positive_arithmetic_margin?'positive_allocation':'no_margin')}
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
   }
   for(const c of analysis.sink_cases){await page.locator('#sink-case').selectOption(c.id);for(const [id,key] of [['storage-energy','capacitor_energy_window_J'],['event-sink','minimum_event_sink_J'],['reset-energy','repeated_events_same_start_require_local_sink_J'],['mean-sink','mean_local_sink_W']])near(parseFloat(await page.locator('#'+id).innerText()),c.result[key]*1000,id);assert.equal(c.result.endpoint_model_bounds_peak,false);assert.equal(c.result.minimum_event_sink_is_lower_bound,true);assert.equal(c.result.credits_later_absorption,false);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true)}
   near(parseFloat(await page.locator('#delay-rise').innerText()),analysis.delay_case.rise_V*1000,'delay rise');assert.equal(analysis.negative_case.strict_positive_arithmetic_margin,false);assert.match(await page.locator('#negative-status').innerText(),/Zero margin/);
   const text=await page.locator('body').innerText();for(const term of [/Turn-on is not full-current clamping voltage/,/maximum cumulative energy excursion/,/sole residual local sink/,/Actual remote and reverse-voltage envelopes remain unavailable/])assert.match(text,term);
   for(const field of ['hardware_accepted','component_selected_for_release','voltage_envelope_qualified','actual_load_known','sink_qualified','reverse_voltage_qualified','fabrication_approved'])assert.equal(analysis[field],false);
   await page.locator('#window-case').selectOption('unknown');await page.locator('#sink-case').selectOption(analysis.sink_cases[0].id);
   await page.screenshot({path:path.join(__dirname,'explorer-'+suffix+'.png'),fullPage:true});assert.deepEqual(errors,[]);
   checks.push({viewport,diagram_loaded:true,diagram_text_in_bounds:true,zoom_percent:200,two_guide_dialogs:true,actual_inputs_remain_null:true,three_window_cases_match_analysis:true,two_sink_cases_match_analysis:true,delay_and_zero_negative_boundary_match:true,endpoint_lower_bound_and_reset_scope_visible:true,no_hardware_acceptance:true,horizontal_overflow:false,page_errors:errors});await page.close();
  }
  const files=['README.md','RESULTS.md','analysis.json','model.py','explorer.template.html','index.html','v2_vservo_transients.svg','verify_viewer.cjs'].map(n=>prefix+n).concat('pm/index.template.html');
  fs.writeFileSync(path.join(__dirname,'viewer_check.json'),JSON.stringify({scope:'Portable requirements viewer and conditional transient arithmetic only; no new native capture, actual waveform or hardware test',input_sha256:Object.fromEntries(files.map(p=>[p,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex')])),checks},null,2)+'\n');console.log(JSON.stringify(checks));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
