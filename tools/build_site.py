#!/usr/bin/env python3
"""One source for the header, footer and checks on every page.

  python3 tools/build_site.py          write shell regions, case study pages, sitemap.xml, llms.txt
  python3 tools/build_site.py --check  write nothing; exit 1 on drift, a bad link, a thin page and more

Hand-written pages stay committed HTML. This script owns the regions between
<!-- shell:header --> and <!-- /shell:header -->, and the same for footer. Stdlib only.
"""
import html, json, os, re, subprocess, sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://ciarramazaredo.vercel.app'
NAME = 'Ciarra Amor G. Mazaredo'
EMAIL = 'ciarramazaredo@gmail.com'
NAV = [('/roles', 'Roles'), ('/case-studies', 'Case studies'), ('/workflows', 'Workflows'), ('/test-me', 'Test me'),
       ('/ai-sprint', 'AI Sprint'), ('/resume', 'Résumé')]
FOOTER_LINKS = [('/how-i-work', 'How I work'), ('/industries', 'Industries'), ('/contact', 'Contact')]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import site_pages  # noqa: E402  (copy for role and industry pages)
ROLE_LASTMOD = '2026-11-17'
REDIRECTS = {r['source'] for r in json.load(open(os.path.join(ROOT, 'vercel.json')))['redirects']}
IGNORED = ('tools/', 'systems/', 'README.md', 'tests/')  # .vercelignore: never served

# route, file, word floor, sitemap lastmod, header mail subject, llms.txt line
PAGES = [
    ('/', 'index.html', 300, '2026-10-25', 'Chief of Staff role', 'numbers, what I run, experience, recognition, testimonials, ways to work together'),
    ('/case-studies', 'case-studies.html', 150, '2026-11-17', 'Chief of Staff role', 'the situation, what I did and what changed'),
    ('/workflows', 'workflows.html', 150, '2026-11-17', 'Workflow for my business', 'automation workflows grouped by result, with free n8n files (labelled Sample or Parts tested)'),
    ('/test-me', 'test-me.html', 150, '2026-11-17', 'Chief of Staff role', 'six trial tasks, a scorecard, reference questions and a paid pilot week'),
    ('/how-i-work', 'how-i-work.html', 150, '2026-11-15', 'Chief of Staff role', 'communication, mistakes, AI use, first 90 days, fit'),
    ('/404', '404.html', 0, None, 'Chief of Staff role', None),
]
# Each story links to one workflow card and one trial task (plan task 3.5).
CASE_LINKS = {
    'edgyvis-people-ops': ('weekly-report', 'The Monday weekly report', 'task-ops-3', 'Screen sample applicants with a scorecard'),
    'yokly-onboarding': ('inbox-triage', 'Inbox triage and daily brief', 'task-ops-2', 'SOP from a recorded process'),
    'email-funnel': ('lead-to-booked-call', 'Lead to booked call', 'task-growth-2', 'Campaign brief into a four-week calendar'),
    'lead-magnet': ('lead-to-booked-call', 'Lead to booked call', 'task-growth-2', 'Campaign brief into a four-week calendar'),
    'hackathon': ('trend-scoring', 'Trend scoring engine for writers', 'task-growth-1', 'Clean a lead list and set scoring rules'),
}
CASE_LASTMOD = '2026-11-17'
LINKEDIN_SVG = ('<svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true"><path d="M20.45 20.45h-3.55v-5.57c0-1.33-.02-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.95v5.66H9.36V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.26 2.37 4.26 5.45v6.29zM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12zm1.78 13.02H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.72v20.56C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.72V1.72C24 .77 23.2 0 22.22 0z"/></svg>')


def esc(s):
    return html.escape(html.unescape(s), quote=True)


def plain(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s))


def mailto(subject):
    return 'mailto:%s?subject=%s' % (EMAIL, subject.replace(' ', '%20'))


def header(route, subject, skip=('#main', 'Skip to content'), label='Email me', attr='data-book'):
    items = []
    for href, text in NAV:  # keep `label` for the header button
        if href == '/ai-sprint' and site_pages.sprint_pending():
            continue  # held: the Sprint page stays out of the menu until her five answers are in
        cur = href == route or (not href.startswith('/#') and href != '/' and route.startswith(href + '/'))
        items.append('        <li><a href="%s"%s>%s</a></li>' % (href, ' aria-current="page"' if cur else '', text))
    return '\n'.join([
        '<!-- shell:header -->',
        '<a class="skip-link" href="%s">%s</a>' % skip,
        '<header class="site-header">',
        '  <div class="nav-wrap">',
        '    <a href="/" class="logo">ciarra<span class="dot">.</span>mazaredo</a>',
        '    <nav aria-label="Primary">',
        '      <ul id="nav-menu">', *items, '      </ul>',
        '    </nav>',
        '    <a href="%s" class="nav-cta" %s>%s</a>' % (mailto(subject), attr, label),
        '    <button type="button" class="nav-toggle" aria-expanded="false" aria-controls="nav-menu">Menu</button>',
        '  </div>',
        '</header>',
        '<!-- /shell:header -->'])


def footer():
    links = ' · '.join('<a href="%s">%s</a>' % l for l in FOOTER_LINKS)
    return '\n'.join([
        '<!-- shell:footer -->',
        '<footer class="site-footer">',
        '  <div class="footer-inner">',
        '    <span>© 2026 %s · Mandaluyong City, Philippines</span>' % NAME,
        '    <span class="footer-links">%s</span>' % links,
        '    <span class="footer-connect">Connect with me <a href="https://www.linkedin.com/in/ciarra-m/" target="_blank" rel="noopener" aria-label="LinkedIn" class="footer-icon">%s</a></span>' % LINKEDIN_SVG,
        '  </div>',
        '</footer>',
        '<!-- /shell:footer -->'])


def region(text, name):
    m = re.search(r'<!-- shell:%s -->.*?<!-- /shell:%s -->' % (name, name), text, re.S)
    return m.group(0) if m else None


def put(text, name, block):
    old = region(text, name)
    if old is not None:
        return text.replace(old, block)
    if name == 'header':  # first run: wrap the existing skip link and header
        m = re.search(r'<a class="skip-link"[^>]*>[^<]*</a>\s*<header>.*?</header>', text, re.S)
    else:
        m = re.search(r'<footer>.*?</footer>', text, re.S)
    if not m:
        raise SystemExit('no %s found to wrap' % name)
    return text[:m.start()] + block + text[m.end():]


# ------------------------------------------------------------------ case study pages
def stories():
    js = os.path.join(ROOT, 'assets/case-studies.js')
    out = subprocess.run(['node', '-e', "global.window={};require(process.argv[1]);process.stdout.write(JSON.stringify(window.CASE_STUDIES))", js],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def head(title, desc, route, extra='', alt=NAME + ', Chief of Staff', noindex=False):
    url = BASE + route
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta name="author" content="{NAME}">
<meta name="theme-color" content="#5B3FE9">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/img/apple-touch-icon.png">
<meta property="og:type" content="article">
<meta property="og:site_name" content="{NAME}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/assets/img/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{alt}">
{'<meta name="robots" content="noindex">' + chr(10) if noindex else ''}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{BASE}/assets/img/og.jpg">
<script>document.documentElement.classList.add('js');</script>
<script src="/assets/site-config.js"></script>
<script>window.va = window.va || function () {{ (window.vaq = window.vaq || []).push(arguments); }};</script>
<script defer src="/_vercel/insights/script.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/shell.css">
<link rel="stylesheet" href="/assets/page.css">
{extra}</head>
<body>
'''


def case_page(cs):
    route = '/case-studies/' + cs['id']
    title = '%s · Case study · %s' % (plain(cs['title']), NAME)
    desc = '%s: %s %s. A case study by %s: the situation, what I did and what changed.' % (
        plain(cs['title']), plain(cs['headline']), plain(cs['headlineLabel']).lower(), NAME)
    crumbs = json.dumps({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': BASE + '/'},
        {'@type': 'ListItem', 'position': 2, 'name': 'Case studies', 'item': BASE + '/case-studies'},
        {'@type': 'ListItem', 'position': 3, 'name': plain(cs['title']), 'item': BASE + route}]}, ensure_ascii=False)
    wf, wf_name, task, task_name = CASE_LINKS[cs['id']]
    metrics = '\n'.join('      <div><dt>%s</dt><dd>%s</dd></div>' % (m['value'], m['label']) for m in cs['metrics'])
    quotes = ''
    if cs['testimonials']:
        quotes = '    <h2>What the client said about it</h2>\n' + '\n'.join(
            '    <figure class="quote"><blockquote>%s</blockquote><figcaption>%s</figcaption></figure>' % (esc(t['quote']), t['author'])
            for t in cs['testimonials'])
    tools = ('<p class="tools"><strong>Tools:</strong> %s</p>' % cs['tools']) if cs['tools'] else ''
    body = f'''{header(route, 'Chief of Staff role')}

<main id="main">
  <article class="case container">
    <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a> <span aria-hidden="true">/</span> <a href="/case-studies">Case studies</a> <span aria-hidden="true">/</span> <span aria-current="page">{cs['title']}</span></nav>
    <p class="eyebrow">{cs['tag']} · {cs['client']}</p>
    <h1>{cs['title']}</h1>
    <p class="client">{cs['clientType']}</p>
    <p class="headline"><span class="num">{cs['headline']}</span> <span class="label">{cs['headlineLabel']}</span></p>

    <h2>Who the work was for</h2>
    <p>{cs['about']}</p>
    <h2>The problem to solve</h2>
    <p>{cs['problem']}</p>
    <h2>What I did about it</h2>
    <p>{cs['move']}</p>
    <h2>What changed as a result</h2>
    <dl class="metrics">
{metrics}
    </dl>
    <p>{cs['result']}</p>
{quotes}
    <h2>Skills and tools used here</h2>
    <ul class="skills">{''.join('<li>%s</li>' % s for s in cs['skills'])}</ul>
    {tools}

    <div class="cta-row">
      <a class="btn btn-primary" href="{mailto('Chief of Staff role')}" data-book>Email me about a role like this</a>
    </div>
    <h2>See the same skills at work</h2>
    <ul class="next">
      <li><a href="/workflows#{wf}">Workflow: {wf_name}</a></li>
      <li><a href="/test-me#{task}">Trial task: {task_name}</a></li>
      <li><a href="/roles/{site_pages.CASE_ROLE[cs['id']]}">Role: {role_name(site_pages.CASE_ROLE[cs['id']])}</a></li>
      <li><a href="/case-studies">All case studies</a></li>
    </ul>
  </article>
</main>

{footer()}

<script src="/assets/site.js"></script>
</body>
</html>
'''
    return route, title, head(title, desc, route, '<script type="application/ld+json">%s</script>\n' % crumbs) + body


def role_name(slug):
    return [r['role'] for r in site_pages.ROLES if r['slug'] == slug][0]


def crumbs_ld(trail):
    return json.dumps({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': BASE + u} for i, (n, u) in enumerate(trail)]}, ensure_ascii=False)


def crumbs_nav(trail):
    parts = ['<a href="%s">%s</a>' % (u, esc(n)) for n, u in trail[:-1]] + ['<span aria-current="page">%s</span>' % esc(trail[-1][0])]
    return '<nav class="crumbs" aria-label="Breadcrumb">' + ' <span aria-hidden="true">/</span> '.join(parts) + '</nav>'


def detail_page(item, hub_route, stories_by_id):
    """A role or industry page, in the order the plan sets for stage 4."""
    hub = site_pages.HUBS[hub_route]
    route = hub['prefix'] + item['slug']
    title = '%s · %s' % (item['title'], NAME)
    trail = [('Home', '/'), (hub['crumb'], hub_route), (item['title'], route)]
    eyebrow = ('Open to · ' + item['role']) if hub_route == '/roles' else ('Industry · ' + item['role'])
    values = '\n'.join('      <li><strong>%s.</strong> %s</li>' % (esc(a), esc(b)) for a, b in item['values'])
    nums = '\n'.join('      <div><dt>%s</dt><dd>%s</dd></div>' % (esc(v), esc(l)) for v, l in item['numbers'])
    plate = '\n'.join('      <li>%s</li>' % esc(x) for x in item['plate'])
    links = ['<li><a href="/case-studies/%s">Case study: %s<span class="sub">%s %s</span></a></li>' % (
        c, stories_by_id[c]['title'], stories_by_id[c]['headline'], stories_by_id[c]['headlineLabel'].lower()) for c in item['cases']]
    steps = list(site_pages.START)
    if item['slug'] in site_pages.START_FIRST:
        steps[0] = (steps[0][0], site_pages.START_FIRST[item['slug']])
    start = '\n'.join('      <li><strong>%s.</strong> %s</li>' % (esc(a), esc(b)) for a, b in steps)
    links.append('<li><a href="/test-me#%s">Paid trial task: %s</a></li>' % (item['task'][0], esc(item['task'][1])))
    links.append('<li><a href="/workflows#%s">Workflow: %s</a></li>' % (item['workflow'][0], esc(item['workflow'][1])))
    if item.get('extra_link'):
        links.append('<li><a href="%s">%s</a></li>' % (item['extra_link'][0], esc(item['extra_link'][1])))
    quote = ''
    if item.get('quote'):
        quote = '    <figure class="quote"><blockquote>%s</blockquote><figcaption>%s</figcaption></figure>\n' % (esc(item['quote'][0]), esc(item['quote'][1]))
    body = f'''{header(route, item['subject'])}

<main id="main">
  <article class="detail container">
    {crumbs_nav(trail)}
    <p class="eyebrow">{esc(eyebrow)}</p>
    <h1>{esc(item['h1'])}</h1>
    <p class="lede">{esc(' '.join(item['lede']))}</p>
    <div class="cta-row">
      <a class="btn btn-primary" href="{mailto(item['subject'])}" data-book>Email me about this role</a>
      <a class="btn" href="/test-me">See the free hiring kit</a>
    </div>
    <p class="objection">{esc(item['objection'])}</p>
    <ul class="values">
{values}
    </ul>
    <dl class="metrics">
{nums}
    </dl>
    <h2>What I take off your plate</h2>
    <ul class="plate">
{plate}
    </ul>
{quote}    <h2>See the proof for yourself</h2>
    <ul class="next">
      {"""
      """.join(links)}
    </ul>
    <p class="tools"><strong>Tools I use:</strong> {item['tools']}</p>
    <h2>How I would start with you</h2>
    <ol class="start">
{start}
    </ol>
    <p>Each day can end with a short written update. More on my habits is on <a href="/how-i-work">how I work</a>.</p>
    <h2>Talk about the role with me</h2>
    <p>Email me with the role and your hours. I reply with when I can start and one question about your team.</p>
    <div class="cta-row">
      <a class="btn btn-primary" href="{mailto(item['subject'])}" data-book>Email me about this role</a>
      <a class="btn" href="{item.get('resume', '/resume')}">Download my résumé</a>
    </div>
  </article>
</main>

{footer()}

<script src="/assets/site.js"></script>
</body>
</html>
'''
    return route, head(title, item['desc'], route, '<script type="application/ld+json">%s</script>\n' % crumbs_ld(trail)).replace('og:type" content="article"', 'og:type" content="website"') + body


def hub_page(hub_route, stories_by_id):
    hub = site_pages.HUBS[hub_route]
    title = '%s · %s' % (hub['title'], NAME)
    trail = [('Home', '/'), (hub['crumb'], hub_route)]
    cards = '\n'.join(f'''    <li class="hub-card"><a href="{hub['prefix']}{it['slug']}"><strong>{esc(it['title'])}</strong></a><span>{esc(it['h1'])} {esc(it['proof_line'])}</span></li>''' for it in hub['items'])
    body = f'''{header(hub_route, 'Which role fits')}

<main id="main">
  <article class="detail container">
    {crumbs_nav(trail)}
    <h1>{esc(hub['h1'])}</h1>
    <p class="lede">{esc(' '.join(hub['lede']))}</p>
    <div class="cta-row">
      <a class="btn btn-primary" href="{mailto('Which role fits')}" data-book>Email me the job post</a>
      <a class="btn" href="/test-me">See the free hiring kit</a>
    </div>
    <ul class="hub">
{cards}
    </ul>
    <h2>Not sure which one fits</h2>
    <p>Email me with the job post. I will tell you which of these it matches and what I would do first.</p>
    <div class="cta-row">
      <a class="btn btn-primary" href="{mailto('Which role fits')}" data-book>Email me the job post</a>
      <a class="btn" href="/test-me">See the free hiring kit</a>
    </div>
  </article>
</main>

{footer()}

<script src="/assets/site.js"></script>
</body>
</html>
'''
    return head(title, hub['desc'], hub_route, '<script type="application/ld+json">%s</script>\n' % crumbs_ld(trail)).replace('og:type" content="article"', 'og:type" content="website"') + body


def lis(items, cls=''):
    return '<ul%s>\n%s\n    </ul>' % (' class="%s"' % cls if cls else '', '\n'.join('      <li>%s</li>' % esc(x) for x in items))


def page_shell(route, title, desc, subject, main, extra_head='', scripts='', alt=NAME + ', Chief of Staff', noindex=False, sprint_header=False):
    hdr = header(route, subject, label='Book a fit call', attr='data-sprint-inquiry') if sprint_header else header(route, subject)
    return head(title, desc, route, extra_head, alt=alt, noindex=noindex).replace('og:type" content="article"', 'og:type" content="website"') + f"""{hdr}

<main id="main">
{main}
</main>

{footer()}

<script src="/assets/site.js"></script>
{scripts}</body>
</html>
"""


def sprint_page():
    S, T = site_pages.SPRINT, site_pages.SPRINT_TERMS
    route = '/ai-sprint'
    title = '%s · %s' % (S['title'], NAME)
    fit_mail = mailto('AI Sprint fit call')
    vals = '\n'.join('      <li><strong>%s.</strong> %s</li>' % (esc(a), esc(b)) for a, b in S['values'])
    steps = '\n'.join('      <li><strong>%s.</strong> %s</li>' % (esc(a), esc(b)) for a, b in S['steps'])
    price_lines = [T['price']['text'], T['second_half']['text']] + ([T['refund']['text']] if T['refund']['text'] else []) + ([T['credit']['text']] if T['credit']['text'] else [])
    svc = {'@context': 'https://schema.org', '@type': 'Service', 'name': 'AI Sprint', 'provider': {'@type': 'Person', 'name': NAME},
           'description': S['lede'], 'url': BASE + route, 'areaServed': 'Worldwide'}
    if not T['price']['pending']:  # price data only once she confirms the price (task 7.5)
        svc['offers'] = {'@type': 'Offer', 'price': T['price']['amount'], 'priceCurrency': 'USD'}
    service = json.dumps(svc, ensure_ascii=False)
    fit_form = """    <form id="fit-form" class="fit-form" hidden>
      <label for="process">The process</label>
      <select id="process" name="process" required><option value="">Choose a process</option><option value="lead-to-booked-call">Lead follow-up</option><option value="weekly-report">Weekly reporting</option><option value="content-routing">Approved content into a calendar</option><option value="inbox-triage">Inbox and replies</option><option value="ai-receptionist">Website chat and bookings</option><option value="error-alerts">Failure alerts</option><option value="trend-scoring">Research and topic briefs</option><option value="transcript-harvester">Video transcripts</option><option value="other">Another process</option></select>
      <label for="frequency">How frequently it runs</label>
      <select id="frequency" name="frequency" required><option value="">Choose one</option><option value="occasional">Now and then</option><option value="weekly">Weekly</option><option value="daily">Daily</option></select>
      <label for="systems">The tools involved</label>
      <select id="systems" name="systems" required><option value="">Choose the closest fit</option><option value="supported">Only the tools in the matching free workflow</option><option value="custom">Other tools, or a custom connection</option><option value="unknown">Not sure yet</option></select>
      <label for="examples">Real examples you can share</label>
      <select id="examples" name="examples" required><option value="">Choose one</option><option value="yes">Yes, with private details removed</option><option value="no">Not yet</option></select>
      <label for="actions">What it would do</label>
      <select id="actions" name="actions" required><option value="">Choose one</option><option value="draft">Draft things for a person to review</option><option value="write">Send, book or change records</option></select>
      <button class="btn btn-primary" type="submit">Find my next step</button>
    </form>
    <div id="fit-result" class="fit-result" tabindex="-1" aria-live="polite" hidden></div>
    <p class="fine">Your answers stay in this browser. This suggests a next step. It is not a quote.</p>
    <p class="nojs-fit">The quick check needs JavaScript. You can still email me a short description of your process.</p>"""
    main = f"""  <article class="detail sprint container">
    {crumbs_nav([('Home', '/'), ('AI Sprint', route)])}
    <p class="eyebrow">{esc(S['eyebrow'])}</p>
    <h1>{esc(S['h1'])}</h1>
    <p class="lede">{esc(S['lede'])}</p>
    <div class="cta-row">
      <a class="btn btn-primary" href="{fit_mail}" data-sprint-inquiry>Book a free 15-minute fit call</a>
      <a class="btn" href="/sample-assessment">See a sample brief</a>
    </div>
    <ul class="values">
{vals}
    </ul>
    <h2>The costly part comes first</h2>
    <p>{esc(' '.join(S['problem']))}</p>
    <h2>{esc(site_pages.sprint_fmt(S['h2_gets']))}</h2>
    {lis(S['gets'], 'plate')}
    <p class="tools"><strong>Scope:</strong> {esc(S['scope'])} {esc(T['size']['text'])}</p>
    <h2>How the Sprint works, step by step</h2>
    <ol class="start">
{steps}
    </ol>
    <h2>Who the Sprint is for</h2>
    {lis(S['fit'], 'plate')}
    <h2>When it is not a fit</h2>
    {lis(S['notfit'], 'plate')}
    <p>{esc(S['near_fit'])}</p>
    <h2>Who does the work for you</h2>
    <div class="who"><img src="/assets/img/ciarra-mazaredo.jpg" alt="Ciarra Amor G. Mazaredo" width="120" height="120"><p>{esc(' '.join(S['who']))} More on my habits is on <a href="/how-i-work">how I work</a>.</p></div>
    <h2>The price and what it covers</h2>
    <p class="price">{esc(price_lines[0])}</p>
    <p>{esc(' '.join(price_lines[1:]))}</p>
    <p>{esc(site_pages.sprint_fmt(S['price_reason']))} {esc(S['no_build'])}</p>
    <div class="cta-row">
      <a class="btn btn-primary" href="{fit_mail}" data-sprint-inquiry>Book a free 15-minute fit call</a>
    </div>
    <h2>What happens after the brief</h2>
    {lis(S['after'], 'plate')}
    <h2>The terms, in plain words</h2>
    {lis(S['terms'], 'plate')}
    <h2>See a sample brief first</h2>
    <p>The sample uses a made-up property manager, so you can see the real layout. <a href="/sample-assessment">Open the sample brief</a>.</p>
    <h2 id="fit-check">Check your fit in one minute</h2>
{fit_form}
    <div class="cta-row">
      <a class="btn btn-primary" href="{fit_mail}" data-sprint-inquiry>Book a free 15-minute fit call</a>
      <a class="btn" href="/workflows">See the free workflows</a>
    </div>
    <p class="objection">{esc(S['ways_out'])}</p>
  </article>"""
    return page_shell(route, title, site_pages.sprint_fmt(S['desc']), 'AI Sprint', main, '<script type="application/ld+json">%s</script>\n<script type="application/ld+json">%s</script>\n' % (service, crumbs_ld([('Home', '/'), ('AI Sprint', route)])),
                      '<script src="/assets/portfolio.js"></script>\n', alt=NAME, noindex=site_pages.sprint_pending(), sprint_header=True)


def sample_page():
    S = site_pages.SAMPLE
    route = '/sample-assessment'
    main = f"""  <article class="detail container">
    {crumbs_nav([('Home', '/'), ('AI Sprint', '/ai-sprint'), ('Sample brief', route)])}
    <p class="eyebrow">Sample · made-up business and numbers</p>
    <h1>Sample brief: owner reports, simplified.</h1>
    <p class="lede">This is the layout an AI Sprint brief follows. The business, Harbor Lane Property Management, is made up. So is every number.</p>
    <h2>The process we looked at</h2>
    <p>Each Monday, a property manager builds a report for 14 owners. She copies rent, occupancy and work orders from three systems into a sheet. Then she writes a short note to each owner.</p>
    <h2>What we used to judge it</h2>
    <ul class="plate">
      <li>Twelve past owner reports, with tenant names removed</li>
      <li>A screen recording of one Monday report, from start to send</li>
      <li>The three systems involved, and who has access to each</li>
    </ul>
    <h2>The recommendation: simplify first</h2>
    <p>Do not build yet. Two of the three systems already export the numbers in the same layout. Fix the sheet so it takes those exports as they are. Then reassess in four weeks.</p>
    <p>A build would need a paid connection to the third system, and its data format keeps changing. That is where automations break.</p>
    <h2>The measure, before and after</h2>
    <p>Before: about four hours each Monday, by the manager's own log. Target after the sheet fix: under two hours. She logs the time for four Mondays, and the number decides the next step.</p>
    <h2>Risks and the human check</h2>
    <ul class="plate">
      <li>Owner notes stay written by a person. AI may draft them, and the manager checks every one.</li>
      <li>If an export changes, the sheet shows a clear error instead of a wrong number.</li>
    </ul>
    <h2>If the answer later becomes build</h2>
    <p>The builder gets the fields, the approval step, the recovery steps and the test cases from this brief. The build is quoted as a fixed price. Accounts stay in the owner's name.</p>
    <h2>Want a brief like this</h2>
    <div class="cta-row">
      <a class="btn btn-primary" href="{mailto('AI Sprint fit call')}" data-sprint-inquiry>Book a free 15-minute fit call</a>
      <a class="btn" href="/ai-sprint">Back to the AI Sprint</a>
    </div>
  </article>"""
    return page_shell(route, '%s · %s' % (S['title'], NAME), S['desc'], 'AI Sprint', main,
                      '<script type="application/ld+json">%s</script>\n' % crumbs_ld([('Home', '/'), ('AI Sprint', '/ai-sprint'), ('Sample brief', route)]),
                      '<script src="/assets/portfolio.js"></script>\n', alt=NAME, noindex=site_pages.sprint_pending(), sprint_header=True)


def contact_page():
    C = site_pages.CONTACT
    route = '/contact'
    main = f"""  <article class="detail container">
    {crumbs_nav([('Home', '/'), ('Contact', route)])}
    <h1>Two ways to work with me.</h1>
    <p class="lede">Most people write to me about a role. Some want one process reviewed. Pick the path that fits, and the email opens with the right subject.</p>
    <h2>About a role on your team</h2>
    <p>I am open to remote Chief of Staff, Executive Assistant to CEO and Operations Manager roles. I am also open to Marketing Operations and AI Automation roles.</p>
    <p>Tell me the role, your hours and the first problem you want solved. A link to the job post helps. If you want proof first, the free hiring kit has six paid trial tasks.</p>
    <div class="cta-row">
      <a class="btn btn-primary" href="{mailto('Chief of Staff role')}" data-book>Email me about a role</a>
      <a class="btn" href="/test-me">See the free hiring kit</a>
    </div>
    <ul class="plate">
      <li><a href="/roles">The five roles I am open to</a></li>
      <li><a href="/resume">My résumé (PDF)</a>, or the <a href="/resume-ats">plain résumé for job boards</a></li>
    </ul>
    <h2>About one process to automate</h2>
    <p>The AI Sprint reviews one process{'' if site_pages.SPRINT_TERMS['size']['pending'] else ' in ' + site_pages.SPRINT_TERMS['size']['days']}. It ends in a written brief that says build, simplify, use what you have, or wait.</p>
    <p>Tell me the process, how many times a week it runs and the tools it touches. A short screen recording of the steps helps too. Do not send passwords or private client records.</p>
    <div class="cta-row">
      <a class="btn" href="{mailto('AI Sprint fit call')}" data-sprint-inquiry>Book a free 15-minute fit call</a>
      <a class="btn" href="/ai-sprint">Read about the AI Sprint</a>
    </div>
    <h2>What happens after you write</h2>
    <p>For a role, I reply with when I can start and one question about your team.</p>
    <p>If it is about a process, I reply with times for the fit call. If the Sprint is not a fit, I say so and say why. I point you to a free workflow if one fits.</p>
    <h2>Where I am and how I work</h2>
    <p>I am based in Mandaluyong City, Philippines, and I work remotely. I write first and call when a decision needs talking through. You can also find me on <a href="https://www.linkedin.com/in/ciarra-m/" target="_blank" rel="noopener">LinkedIn</a>.</p>
    <p>My email is <a href="mailto:{EMAIL}">{EMAIL}</a>. More on how I keep you informed is on <a href="/how-i-work">how I work</a>.</p>
  </article>"""
    return page_shell(route, '%s · %s' % (C['title'], NAME), C['desc'], 'Chief of Staff role', main,
                      '<script type="application/ld+json">%s</script>\n' % crumbs_ld([('Home', '/'), ('Contact', route)]), alt=NAME)


def case_list(all_cs):
    rows = []
    for cs in all_cs:
        line = re.split(r'(?<=[.])\s', plain(cs['result']).strip())[0]
        rows.append(f'''    <li id="{cs['id']}"><a href="/case-studies/{cs['id']}">{cs['title']}</a> <span class="line"><span class="num">{cs['headline']}</span> {cs['headlineLabel']}. {esc(line)}</span></li>''')
    return '<!-- shell:caselist -->\n<section class="cs-static" aria-label="All case studies">\n  <div class="container">\n  <h2>Every story on its own page</h2>\n  <ul>\n' + '\n'.join(rows) + '\n  </ul>\n  </div>\n</section>\n<!-- /shell:caselist -->'


# ------------------------------------------------------------------ parsing for checks
class Facts(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=True)
        s.ids, s.hrefs, s.h1, s.skip, s.inmain, s.words = set(), [], 0, 0, 0, 0
        s.title, s.desc, s.canon, s._t = '', '', '', False

    def handle_starttag(s, t, a):
        a = dict(a)
        if a.get('id'):
            s.ids.add(a['id'])
        if t == 'a' and a.get('href'):
            s.hrefs.append(a['href'])
        if t == 'h1':
            s.h1 += 1
        if t in ('script', 'style', 'svg', 'noscript'):
            s.skip += 1
        if t == 'main':
            s.inmain += 1
        if t == 'title':
            s._t = True
        if t == 'meta' and a.get('name') == 'description':
            s.desc = a.get('content', '')
        if t == 'link' and a.get('rel') == 'canonical':
            s.canon = a.get('href', '')

    def handle_endtag(s, t):
        if t in ('script', 'style', 'svg', 'noscript'):
            s.skip -= 1
        if t == 'main':
            s.inmain -= 1
        if t == 'title':
            s._t = False

    def handle_data(s, d):
        if s._t:
            s.title += d
        if s.inmain and not s.skip:
            s.words += len(d.split())


def all_pages(cs_list):
    pages = [dict(route=r, file=f, floor=fl, lastmod=lm, subject=sub, llms=ll) for r, f, fl, lm, sub, ll in PAGES]
    for r, f, fn in (('/ai-sprint', 'ai-sprint.html', 'sprint'), ('/sample-assessment', 'sample-assessment.html', 'sample'), ('/contact', 'contact.html', 'contact')):
        pages.append(dict(route=r, file=f, floor=300, lastmod=ROLE_LASTMOD, subject='AI Sprint', llms=None, gen=fn))
    for hub_route, hub in site_pages.HUBS.items():
        pages.append(dict(route=hub_route, file=hub_route.lstrip('/') + '.html', floor=150, lastmod=ROLE_LASTMOD,
                          subject='Chief of Staff role', llms=None, hub=hub_route))
        for it in hub['items']:
            pages.append(dict(route=hub['prefix'] + it['slug'], file=hub['prefix'].lstrip('/') + it['slug'] + '.html', floor=300,
                              lastmod=ROLE_LASTMOD, subject=it['subject'], llms=None, detail=(it, hub_route)))
    for cs in cs_list:
        pages.append(dict(route='/case-studies/' + cs['id'], file='case-studies/%s.html' % cs['id'], floor=150,
                          lastmod=CASE_LASTMOD, subject='Chief of Staff role', llms=None, story=cs))
    return pages


def resolve(path):
    """File served for a clean URL path, or None."""
    if path in REDIRECTS:
        return '<redirect>'
    p = path.lstrip('/')
    if p.startswith(IGNORED):
        return None
    for cand in ([p + '.html', p, p + '/index.html'] if p else ['index.html']):
        f = os.path.join(ROOT, cand)
        if os.path.isfile(f):
            return cand
    return None


def sitemap(pages):
    held = {'/ai-sprint', '/sample-assessment'} if site_pages.sprint_pending() else set()
    rows = ['  <url><loc>%s%s</loc><lastmod>%s</lastmod></url>' % (BASE, p['route'], p['lastmod']) for p in pages if p['lastmod'] and p['route'] not in held]
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(rows) + '\n</urlset>\n'


def llms(pages):
    names = {'/': 'Home', '/case-studies': 'Case studies', '/workflows': 'Workflows', '/test-me': 'Test me', '/how-i-work': 'How I work'}
    lines = ['- [%s](%s%s): %s' % (names[p['route']], BASE, p['route'], p['llms']) for p in pages if p['llms']]
    stories = ['- [%s](%s%s): %s %s' % (plain(p['story']['title']), BASE, p['route'], plain(p['story']['headline']), plain(p['story']['headlineLabel']).lower())
               for p in pages if p.get('story')]
    roles = ['- [%s](%s%s): %s' % (it['title'], BASE, hub['prefix'] + it['slug'], it['proof_line'])
             for hub in site_pages.HUBS.values() for it in hub['items']]
    return f"""# {NAME}

> Open to Chief of Staff, Executive Assistant to CEO and Operations Manager roles. Also open to Marketing Operations and AI Automation roles. Remote, based in Mandaluyong City, Philippines (UTC+8). Available immediately.

## Pages
""" + '\n'.join(lines) + f"""
{'' if site_pages.sprint_pending() else '- [AI Sprint](' + BASE + '/ai-sprint): one process reviewed in ' + site_pages.SPRINT_TERMS['size']['days'] + ', ending in a written brief (sample: ' + BASE + '/sample-assessment)' + chr(10)}- [Contact]({BASE}/contact): a role, or one process to automate
- [Résumé (PDF)]({BASE}/resume) · [Plain résumé for job boards]({BASE}/resume-ats) · [Marketing Operations résumé]({BASE}/resume-marketing-ops) · [AI Automation résumé]({BASE}/resume-ai-automation)

## Roles and industries
""" + '\n'.join(roles) + """

## Case studies
""" + '\n'.join(stories) + f"""

## Contact
- Email: {EMAIL}
- LinkedIn: https://www.linkedin.com/in/ciarra-m/
"""


def build():
    """Return {file: text} for every file this script owns or edits."""
    cs_list = stories()
    pages = all_pages(cs_list)
    out = {}
    by_id = {c['id']: c for c in cs_list}
    for p in pages:
        if p.get('gen'):
            text = {'sprint': sprint_page, 'sample': sample_page, 'contact': contact_page}[p['gen']]()
        elif p.get('hub'):
            text = hub_page(p['hub'], by_id)
        elif p.get('detail'):
            _, text = detail_page(p['detail'][0], p['detail'][1], by_id)
        elif p.get('story'):
            _, _, text = case_page(p['story'])
        else:
            text = open(os.path.join(ROOT, p['file']), encoding='utf-8').read()
            skip = ('#case-wrap', 'Skip to the case study') if p['file'] == 'case-studies.html' else ('#main', 'Skip to content')
            text = put(text, 'header', header(p['route'], p['subject'], skip))
            text = put(text, 'footer', footer())
            if p['file'] == 'case-studies.html':
                block = case_list(cs_list)
                text = text.replace(region(text, 'caselist'), block) if region(text, 'caselist') else text.replace('<section class="strip-wrap">', block + '\n\n<section class="strip-wrap">', 1)
        out[p['file']] = text
    out['sitemap.xml'] = sitemap(pages)
    out['llms.txt'] = llms(pages)
    return pages, out


def check(pages, out):
    errs = []
    facts = {}
    for p in pages:
        f = Facts()
        f.feed(out[p['file']])
        facts[p['route']] = f
    titles, descs, inbound = {}, {}, {p['route']: set() for p in pages}
    for p in pages:
        f, text, r = facts[p['route']], out[p['file']], p['route']
        disk = os.path.join(ROOT, p['file'])
        if not os.path.isfile(disk) or open(disk, encoding='utf-8').read() != text:
            errs.append('%s: out of date (run tools/build_site.py)' % p['file'])
        for need in ('<!-- shell:header -->', '<!-- shell:footer -->', '/assets/shell.css', '/assets/site.js'):
            if need not in text:
                errs.append('%s: missing %s' % (p['file'], need))
        if r != '/404':
            for need in ("classList.add('js')", '/_vercel/insights/script.js'):
                if need not in text:
                    errs.append('%s: missing %s' % (p['file'], need))
            want = BASE + ('/' if r == '/' else r)
            if f.canon != want:
                errs.append('%s: canonical %r, want %r' % (p['file'], f.canon, want))
        btn = re.search(r'<a href="[^"]*" class="nav-cta"[^>]*>([^<]*)</a>', text)
        want_btn = 'Book a fit call' if p['route'] in ('/ai-sprint', '/sample-assessment') else 'Email me'
        if not btn or btn.group(1) != want_btn:
            errs.append('%s: header button reads %r, want %r' % (p['file'], btn and btn.group(1), want_btn))
        if f.h1 != 1:
            errs.append('%s: %d h1 (need exactly 1)' % (p['file'], f.h1))
        t = f.title.strip()
        if NAME not in t:
            errs.append('%s: title lacks the full name: %r' % (p['file'], t))
        if t in titles:
            errs.append('%s: same title as %s' % (p['file'], titles[t]))
        titles[t] = p['file']
        if r != '/404':
            if not f.desc:
                errs.append('%s: no meta description' % p['file'])
            elif f.desc in descs:
                errs.append('%s: same description as %s' % (p['file'], descs[f.desc]))
            descs[f.desc] = p['file']
        if f.words < p['floor']:
            errs.append('%s: %d words in <main>, floor %d' % (p['file'], f.words, p['floor']))
        for h in f.hrefs:
            if h.startswith(BASE):
                h = h[len(BASE):] or '/'
            if re.match(r'^(https?:|mailto:|tel:)', h):
                continue
            path, _, frag = h.partition('#')
            path = path.split('?')[0]
            target_route = r if not path else ('/' if path == '/' else path.rstrip('/'))
            if path:
                served = resolve(path)
                if served is None:
                    errs.append('%s: dead link %s' % (p['file'], h))
                    continue
            if frag:
                tf = facts.get(target_route)
                if tf is None:
                    continue  # a file such as a PDF or JSON; no ids to check
                if frag not in tf.ids:
                    errs.append('%s: missing anchor %s' % (p['file'], h))
            if target_route in inbound and target_route != r:
                inbound[target_route].add(r)
    for p in pages:
        if p['route'] not in ('/', '/404') and not inbound[p['route']]:
            errs.append('%s: no page links to it' % p['file'])
    for name in ('sitemap.xml', 'llms.txt'):
        disk = os.path.join(ROOT, name)
        if not os.path.isfile(disk) or open(disk, encoding='utf-8').read() != out[name]:
            errs.append('%s: out of date (run tools/build_site.py)' % name)
    return errs


def main():
    if '--ship' in sys.argv:  # stage 7 gate: the Sprint page never ships with a guessed term
        pending = [v['ask'] for v in site_pages.SPRINT_TERMS.values() if v['pending']]
        for a in pending:
            print('  waiting on her answer:', a)
        print('ship gate: %s' % ('PASS' if not pending else '%d answer(s) needed' % len(pending)))
        sys.exit(1 if pending else 0)
    if '--routes' in sys.argv:  # for tests/site-smoke.js
        print(json.dumps([p['route'] for p in all_pages(stories())]))
        return
    pages, out = build()
    if '--check' not in sys.argv:
        for name, text in out.items():
            path = os.path.join(ROOT, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if not os.path.isfile(path) or open(path, encoding='utf-8').read() != text:
                with open(path, 'w', encoding='utf-8') as fh:
                    fh.write(text)
                print('wrote', name)
    errs = check(pages, out)
    for e in errs:
        print('  ' + e)
    print('build_site check: %s' % ('PASS' if not errs else '%d problem(s)' % len(errs)))
    sys.exit(1 if errs else 0)


if __name__ == '__main__':
    main()
