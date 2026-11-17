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
NAV = [('/#numbers', 'Numbers'), ('/#what-i-run', 'What I run'), ('/#experience', 'Experience'),
       ('/case-studies', 'Case studies'), ('/workflows', 'Workflows'), ('/test-me', 'Test me')]
FOOTER_LINKS = [('/how-i-work', 'How I work')]
REDIRECTS = {'/resume', '/resume-ats'}  # vercel.json
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


def header(route, subject, skip=('#main', 'Skip to content')):
    items = []
    for href, label in NAV:
        cur = href == route or (not href.startswith('/#') and href != '/' and route.startswith(href + '/'))
        items.append('        <li><a href="%s"%s>%s</a></li>' % (href, ' aria-current="page"' if cur else '', label))
    return '\n'.join([
        '<!-- shell:header -->',
        '<a class="skip-link" href="%s">%s</a>' % skip,
        '<header class="site-header">',
        '  <div class="nav-wrap">',
        '    <a href="/" class="logo">ciarra<span class="dot">.</span>mazaredo</a>',
        '    <nav aria-label="Primary">',
        '      <ul id="nav-menu">', *items, '      </ul>',
        '    </nav>',
        '    <a href="%s" class="nav-cta" data-book>Email me</a>' % mailto(subject),
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


def head(title, desc, route, extra=''):
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
<meta property="og:image:alt" content="{NAME}, Chief of Staff">
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

    <h2>See the same skills at work</h2>
    <ul class="next">
      <li><a href="/workflows#{wf}">Workflow: {wf_name}</a></li>
      <li><a href="/test-me#{task}">Trial task: {task_name}</a></li>
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
    rows = ['  <url><loc>%s%s</loc><lastmod>%s</lastmod></url>' % (BASE, p['route'], p['lastmod']) for p in pages if p['lastmod']]
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(rows) + '\n</urlset>\n'


def llms(pages):
    names = {'/': 'Home', '/case-studies': 'Case studies', '/workflows': 'Workflows', '/test-me': 'Test me', '/how-i-work': 'How I work'}
    lines = ['- [%s](%s%s): %s' % (names[p['route']], BASE, p['route'], p['llms']) for p in pages if p['llms']]
    stories = ['- [%s](%s%s): %s %s' % (plain(p['story']['title']), BASE, p['route'], plain(p['story']['headline']), plain(p['story']['headlineLabel']).lower())
               for p in pages if p.get('story')]
    return f"""# {NAME}

> Open to Chief of Staff, Executive Assistant to CEO and Operations Manager roles. Remote, based in Mandaluyong City, Philippines (UTC+8). Available immediately.

## Pages
""" + '\n'.join(lines) + f"""
- [Résumé (PDF)]({BASE}/resume) · [Plain résumé for job boards]({BASE}/resume-ats)

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
    for p in pages:
        if p.get('story'):
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
