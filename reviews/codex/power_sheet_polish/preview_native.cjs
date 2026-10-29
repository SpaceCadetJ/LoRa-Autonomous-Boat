const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const dir=__dirname,svg=path.join(dir,'native/svg/LoRa_Boat_Controller_V2-Power.svg');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.BROWSER_EXECUTABLE});
 try{
  const page=await browser.newPage({viewport:{width:1680,height:1188},deviceScaleFactor:1});
  await page.goto(pathToFileURL(svg).href);
  await page.locator('svg').evaluate(el=>{el.style.margin='0';el.style.width='1680px';el.style.height='1188px';el.style.background='white';el.style.display='block'});
  await page.screenshot({path:path.join(dir,'native-power-preview.png')});
  await page.setViewportSize({width:1600,height:944});
  await page.locator('svg').evaluate(el=>{const v=el.viewBox.baseVal;let scale=v.width/420;el.setAttribute('viewBox',[208*scale,123*scale,200*scale,118*scale].join(' '));el.style.width='1600px';el.style.height='944px'});
  await page.screenshot({path:path.join(dir,'native-reservoir-detail.png')});
  console.log('Captured whole A3 Power sheet and enlarged reservoir detail');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
