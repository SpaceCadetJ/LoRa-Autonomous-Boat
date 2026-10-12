const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const{pathToFileURL}=require('node:url');
const{chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
(async()=>{
const browser=await chromium.launch({headless:true,...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE}:{})});
const root=path.resolve(__dirname,'../../..'),checks=[];
try{for(const viewport of[{width:1440,height:1000},{width:390,height:844}]){
 const page=await browser.newPage({viewport}),errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto(pathToFileURL(path.join(root,'pm/index.html')).href);
 await page.locator('nav [data-page="design"]').click();await page.locator('#asset-revision').selectOption('v2');
 await page.locator('#asset-choice').selectOption('reviews/codex/input_stage/v2_input_stage.svg');
 await page.locator('#asset-image').evaluate(img=>img.decode());assert.ok(await page.locator('#asset-image').evaluate(img=>img.naturalWidth>0));
 const project=page.getByRole('link',{name:'INPUT-A1 candidate KiCad project',exact:true});assert.equal(await project.count(),1);assert.match(await project.getAttribute('href'),/input_stage\/source/);
 assert.equal(await page.getByText('PCB integration pending',{exact:true}).count(),1);assert.equal(await page.getByText('Planning map; no candidate PCB',{exact:true}).count(),0);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.getByRole('button',{name:'Read input-stage guide and limits',exact:true}).click();
 assert.equal(await page.locator('dialog[open]').count(),1);assert.match(await page.locator('dialog[open]').innerText(),/discharged-output reverse leakage/);
 assert.equal(await page.locator('dialog[open]').evaluate(e=>e.scrollWidth<=e.clientWidth),true);
 assert.deepEqual(errors,[]);checks.push({viewport,image_loaded:true,correct_candidate_project:true,pcb_pending_label:true,guide_opened:true,page_errors:errors,horizontal_overflow:false});await page.close();
}
fs.writeFileSync(path.join(__dirname,'viewer_check.json'),JSON.stringify({date:new Date().toISOString(),scope:'Local viewer navigation only; native schematic validation is separate',checks},null,2)+'\n');console.log(JSON.stringify(checks));
}finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
