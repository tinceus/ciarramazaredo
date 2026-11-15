/* Run tools/serve.py first. BASE_URL overrides the local preview. */
const {chromium} = require('playwright');
const AxeBuilder = require('@axe-core/playwright').default;
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const base = process.env.BASE_URL || 'http://127.0.0.1:8781';
const routes = ['/', '/case-studies', '/workflows', '/roles', '/industries', '/contact', '/ai-sprint', '/sample-assessment', '/ai-notes', '/test-me', '/how-i-work',
  ...['roles','industries','case-studies'].flatMap(dir=>fs.readdirSync(path.join(root,dir)).filter(f=>f.endsWith('.html')).map(f=>'/'+dir+'/'+f.slice(0,-5)))];

(async()=>{
  const browser=await chromium.launch({headless:true});
  const errors=[], links=new Set();
  try {
    for(const width of [1440,390]){
      const context=await browser.newContext({viewport:{width,height:900},reducedMotion:'reduce'});
      const page=await context.newPage();
      page.on('pageerror',error=>errors.push(error.message));
      for(const route of routes){
        const response=await page.goto(base+route);
        assert.equal(response.status(),200,route);
        assert.equal(await page.locator('h1').count(),1,route+' has one primary heading');
        assert.equal(await page.locator('main').count(),1,route+' has a main landmark');
        assert(await page.title(),route+' title');
        assert(!/83\.57%|Available immediately|Nothing breaks silently|cold to converted/.test(await page.locator('body').innerText()),route+' unsupported legacy claim');
        const layout=await page.evaluate(()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth}));
        assert(layout.scroll<=layout.viewport+1,route+' overflow at '+width);
        for(const href of await page.locator('a[href]').evaluateAll(nodes=>nodes.map(n=>n.href))) if(href.startsWith(base))links.add(href);
        const results=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
        assert.deepEqual(results.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)})),[],route+' accessibility at '+width);
      }
      if(width===390){
        await page.goto(base+'/ai-sprint');
        await page.locator('a[href="#fit-check"]').click();
        assert((await page.locator('#fit-check h2').boundingBox()).y>=(await page.locator('header').boundingBox()).height,'fit heading clears sticky header');
        const toggle=page.locator('.nav-toggle');
        await toggle.focus();await page.keyboard.press('Enter');
        assert.equal(await toggle.getAttribute('aria-expanded'),'true');
        await page.keyboard.press('Escape');
        assert.equal(await toggle.getAttribute('aria-expanded'),'false');
        assert(await toggle.evaluate(el=>el===document.activeElement));
      }
      await context.close();
    }
    const context=await browser.newContext();
    const page=await context.newPage();
    await page.addInitScript(()=>{window.recorded=[];window.portfolioTrack=(name,props)=>window.recorded.push({name,props});});
    await page.goto(base+'/ai-sprint?workflow=weekly-report');
    assert.equal(await page.inputValue('#process'),'weekly-report');
    for(const [field,value] of Object.entries({frequency:'daily',systems:'supported',examples:'yes',actions:'draft'}))await page.selectOption('#'+field,value);
    const requests=[];page.on('request',r=>requests.push(r.url()));
    await page.locator('#fit-form button').click();
    assert.match(await page.locator('#fit-result').innerText(),/scoped setup/);
    assert.match(await page.locator('#fit-result a').getAttribute('href'),/weekly-report.*setup/);
    assert.equal(await page.locator('#fit-result').evaluate(el=>el===document.activeElement),true);
    await page.selectOption('#actions','write');await page.locator('#fit-form button').click();
    assert.match(await page.locator('#fit-result').innerText(),/feasibility sprint/);
    await page.selectOption('#examples','no');await page.locator('#fit-form button').click();
    assert.match(await page.locator('#fit-result').innerText(),/examples first/);
    await page.selectOption('#examples','yes');await page.selectOption('#actions','draft');await page.selectOption('#frequency','occasional');await page.locator('#fit-form button').click();
    assert.match(await page.locator('#fit-result a').getAttribute('href'),/workflows#weekly-report/);
    assert.equal(requests.length,0,'fit answers do not leave the page');
    const events=await page.evaluate(()=>window.recorded);
    assert.equal(events.filter(e=>e.name==='fit_check_result').length,4);
    assert(events.every(e=>Object.keys(e.props).every(k=>['route','path','workflow'].includes(k))));
    for(const configured of ['https://example.com/fit?source=portfolio','javascript:alert(1)']){
      await page.route('**/assets/site-config.js',r=>r.fulfill({contentType:'application/javascript',body:'window.SITE='+JSON.stringify({bookingUrl:'https://example.com/general',sprintBookingUrl:configured})}));
      await page.goto(base+'/ai-sprint?workflow=weekly-report');
      const href=await page.locator('[data-sprint-inquiry]').first().getAttribute('href');
      if(configured.startsWith('https')){assert.match(href,/example.com\/fit/);assert.match(href,/workflow=weekly-report/);}else assert(href.startsWith('mailto:'));
      await page.unroute('**/assets/site-config.js');
    }
    await page.goto(base+'/ai-sprint?workflow=%3Cscript%3E');
    assert.equal(await page.inputValue('#process'),'');
    assert(!(await page.locator('[data-sprint-inquiry]').first().getAttribute('href')).includes('script'));
    for(const href of links){
      const url=new URL(href);url.hash='';
      const response=await context.request.get(url.href);
      assert(response.ok(),'Broken local link: '+url.href+' '+response.status());
    }
    await context.close();
    const plain=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}});
    const plainPage=await plain.newPage();
    for(const route of ['/','/ai-sprint','/roles','/workflows','/case-studies/content-routing']){
      await plainPage.goto(base+route);
      assert(await plainPage.locator('nav a[href="/roles"]').isVisible(),route+' no-JS navigation');
      assert(await plainPage.locator('h1').isVisible());
    }
    await plainPage.goto(base+'/ai-sprint');
    assert.equal(await plainPage.locator('#fit-form').isVisible(),false);
    assert(await plainPage.locator('a[data-sprint-inquiry]').isVisible());
    await plain.close();
    assert.deepEqual(errors,[]);
    console.log(`PASS: ${routes.length} routes at desktop/mobile, WCAG automated checks, ${links.size} local links, four fit paths, context/config, no-JS access and keyboard menu.`);
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
