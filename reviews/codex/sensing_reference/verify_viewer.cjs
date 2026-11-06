const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'../../..'),prefix='reviews/codex/sensing_reference/';
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex');
const aliases={'pm/index.template.html':'reviews/codex/sensing_filter/viewer-template.snapshot.html','pm/tools/build.mjs':'reviews/codex/sensing_filter/viewer-builder.snapshot.mjs'};
for(const [live,archive] of Object.entries(aliases))assert.equal(sha(live),sha(archive),'Preserved PM renderer');
const names=['README.md','RESULTS.md','evidence.json','reference_boundary.svg','verify_viewer.cjs'].map(n=>prefix+n).concat(Object.values(aliases));
const hashes=()=>Object.fromEntries(names.map(n=>[n,sha(n)]));const before=hashes();
(async()=>{const browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_EXECUTABLE});const checks=[];
try{
 const diagram=await browser.newPage({viewport:{width:1200,height:800}});
 await diagram.goto(pathToFileURL(path.join(__dirname,'reference_boundary.svg')).href);
 const outside=await diagram.locator('text').evaluateAll(es=>es.map(e=>{const b=e.getBBox();return {text:e.textContent,x:b.x,y:b.y,r:b.x+b.width,b:b.y+b.height}}).filter(b=>b.x<0||b.y<0||b.r>1200||b.b>800));assert.deepEqual(outside,[]);
 await diagram.screenshot({path:path.join(__dirname,'diagram-preview.png')});await diagram.close();
 for(const viewport of [{width:1440,height:1050},{width:390,height:844}]){
 const page=await browser.newPage({viewport}),errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto(pathToFileURL(path.join(root,'pm/index.html')).href);
 await page.locator('nav [data-page="documents"]').click();
 for(const file of ['README.md','RESULTS.md']){
  const target=prefix+file;
  const source=fs.readFileSync(path.join(root,target),'utf8');
  assert.equal(await page.evaluate(p=>D.documents.find(d=>d.path===p).text,target),source,'Embedded guide source');
  await page.locator('#main button[data-doc="'+target+'"]').click();
  const dialog=page.locator('dialog[open]');assert.equal(await dialog.evaluate(e=>e.scrollWidth<=e.clientWidth),true);
  const text=await dialog.innerText();assert.match(text,/SENSE-03/);assert.match(text,/unqualified|unavailable/);
  if(file==='README.md'){assert.match(text,/VDD\+4/);assert.match(text,/−21\.257801/);await page.screenshot({path:path.join(__dirname,'guide-'+(viewport.width>700?'desktop':'phone')+'.png')});}
  else assert.match(text,/3\.241200045/);
  await page.keyboard.press('Escape');
 }
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);assert.deepEqual(errors,[]);
 checks.push({viewport,guide_and_results_open:true,embedded_markdown_matches:true,dialog_and_document_no_overflow:true,page_errors:errors});await page.close();
 }
 assert.deepEqual(hashes(),before,'Review inputs changed during browser capture');
 for(const [live,archive] of Object.entries(aliases))assert.equal(sha(live),sha(archive));
 fs.writeFileSync(path.join(__dirname,'viewer_check.json'),JSON.stringify({scope:'SENSE-03 auto-discovered guides and static reference-path drawing; historical PM renderer unchanged, no new application behavior',input_sha256:before,renderer_archive:aliases,generated_pm_sha256_at_capture:sha('pm/index.html'),checks,diagram_text_in_bounds:true,native_or_hardware_acceptance:false},null,2)+'\n');
 console.log(JSON.stringify(checks));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1});
