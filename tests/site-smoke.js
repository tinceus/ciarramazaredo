/* Browser check for every page: status, one h1, one main, title, no sideways scroll,
   automated WCAG A/AA checks (axe), no dead local links, keyboard menu, no-JS menu.
   Routes come from tools/build_site.py. Run a local preview first (tools/serve.py).
     BASE_URL=http://127.0.0.1:8780 NODE_PATH=<dir with playwright and @axe-core/playwright> node tests/site-smoke.js
   Uses the installed Google Chrome, so no browser download is needed. */
const {chromium} = require('playwright');
const AxeBuilder = require('@axe-core/playwright').default;
const {execFileSync} = require('node:child_process');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const base = process.env.BASE_URL || 'http://127.0.0.1:8780';
const routes = JSON.parse(execFileSync('python3', [path.join(root, 'tools/build_site.py'), '--routes'], {encoding: 'utf8'}));
const fails = [];
const fail = msg => { fails.push(msg); console.log('FAIL ' + msg); };

(async () => {
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  const links = new Set();
  try {
    for (const width of [1440, 390]) {
      const context = await browser.newContext({viewport: {width, height: 900}, reducedMotion: 'reduce'});
      const page = await context.newPage();
      page.on('pageerror', e => fail(`page error at ${width}: ${e.message}`));
      for (const route of routes) {
        const res = await page.goto(base + route);
        const want = route === '/404' ? 404 : 200;
        if (res.status() !== 200 && !(route === '/404' && res.status() === want)) fail(`${route}: status ${res.status()}`);
        if (await page.locator('h1').count() !== 1) fail(`${route}: needs exactly one h1`);
        if (await page.locator('main').count() !== 1) fail(`${route}: needs exactly one main`);
        if (!(await page.title())) fail(`${route}: no title`);
        const layout = await page.evaluate(() => ({vw: innerWidth, sw: document.documentElement.scrollWidth}));
        if (layout.sw > layout.vw + 1) fail(`${route}: sideways scroll at ${width} (${layout.sw} > ${layout.vw})`);
        for (const href of await page.locator('a[href]').evaluateAll(ns => ns.map(n => n.href))) if (href.startsWith(base)) links.add(href.split('#')[0]);
        const axe = await new AxeBuilder({page}).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
        for (const v of axe.violations) fail(`${route} at ${width}: ${v.id} (${v.nodes.length}) ${v.nodes.slice(0, 3).map(n => n.target.join(' ')).join(' | ')}`);
      }
      if (width === 390) {
        await page.goto(base + '/workflows');
        const toggle = page.locator('.nav-toggle');
        await toggle.focus(); await page.keyboard.press('Enter');
        if (await toggle.getAttribute('aria-expanded') !== 'true') fail('menu does not open from the keyboard');
        await page.keyboard.press('Escape');
        if (await toggle.getAttribute('aria-expanded') !== 'false') fail('Escape does not close the menu');
        if (!(await toggle.evaluate(el => el === document.activeElement))) fail('focus does not return to the menu button');
      }
      await context.close();
    }
    const ctx = await browser.newContext();
    for (const href of links) {
      const r = await ctx.request.get(href, {maxRedirects: 0});
      if (r.status() >= 400) fail(`dead local link: ${href} (${r.status()})`);
    }
    await ctx.close();
    const plain = await browser.newContext({javaScriptEnabled: false, viewport: {width: 390, height: 844}});
    const p = await plain.newPage();
    for (const route of routes.filter(r => r !== '/404')) {
      await p.goto(base + route);
      if (!(await p.locator('nav a[href="/workflows"]').isVisible())) fail(`${route}: menu links hidden without JavaScript`);
      if (!(await p.locator('h1').isVisible())) fail(`${route}: h1 hidden without JavaScript`);
    }
    await p.goto(base + '/case-studies');
    if (!(await p.locator('.cs-static a').first().isVisible())) fail('/case-studies: story list hidden without JavaScript');
    await plain.close();
    // Stage 7 adds the AI Sprint and fit check flows here.
    console.log(fails.length ? `\nsite smoke: ${fails.length} problem(s)` : `site smoke: PASS (${routes.length} routes at 1440 and 390, axe WCAG A/AA, ${links.size} local links, keyboard menu, no-JS menu)`);
    process.exitCode = fails.length ? 1 : 0;
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
