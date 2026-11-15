/* Requires Playwright and its Chromium browser. */
const {chromium} = require('playwright');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
(async () => {
  const root = path.resolve(__dirname, '..');
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage();
    await page.goto(pathToFileURL(path.join(root,'tools/resume/resume-ats.html')).href);
    await page.pdf({path:path.join(root,'assets/Ciarra_Mazaredo_Resume_ATS.pdf'),preferCSSPageSize:true,printBackground:true});
    await page.addStyleTag({content:'h1,h2{color:#3D2BB3}h2{border-color:#3D2BB3}h3{break-after:avoid}.target{color:#3D2BB3}'});
    await page.pdf({path:path.join(root,'assets/Ciarra_Mazaredo_Resume_ChiefOfStaff.pdf'),preferCSSPageSize:true,printBackground:true});
    console.log('Built both résumé PDFs from shared source');
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
