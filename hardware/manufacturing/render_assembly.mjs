// Optional local visual QA. Requires Playwright and an installed Edge/Chromium.
// Writes only manufacturing/previews; does not change the generator's release manifest.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const modulePath = process.env.PLAYWRIGHT_MODULE || 'C:/Users/Jay/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
const {chromium} = await import(pathToFileURL(modulePath));
const browser = await chromium.launch({headless:true, channel:process.env.BROWSER_CHANNEL || 'msedge'});
try {
  const page = await browser.newPage({viewport:{width:1440,height:1100},deviceScaleFactor:1});
  await fs.mkdir(path.join(here,'previews'),{recursive:true});
  for (const variant of ['v1','v2']) {
    for (const side of ['top','bottom']) {
      const svg = await fs.readFile(path.join(here,variant,`assembly_${side}.svg`),'utf8');
      await page.setContent(`<html><body style="margin:0;background:#f8fafc">${svg}</body></html>`);
      await page.locator('svg').screenshot({path:path.join(here,'previews',`${variant}_assembly_${side}.png`)});
      console.log(`Rendered ${variant} ${side}`);
    }
  }
} finally {
  await browser.close();
}
