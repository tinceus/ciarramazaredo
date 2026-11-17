#!/usr/bin/env python3
"""Parse tests for the three plain (ATS) résumés. Exit 1 on any failure.
Usage: python3 tools/test_resume.py

Per résumé, PDF and Word: name alone on the first line, email and phone, its role words,
five headings in order, no dashes or [CONFIRM. PDF: no Type 3 fonts, exactly 2 pages.
Sources: smallest font 10pt or more, the work history identical in all three, and every
number also in the Chief of Staff résumé or a live story. Prints a keyword report."""
import html, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESUME_MD = os.path.join(os.path.dirname(ROOT), 'Ciarra_Mazaredo_Resume_ChiefOfStaff.md')
HEADINGS = ['SUMMARY', 'CORE SKILLS', 'PROFESSIONAL EXPERIENCE', 'EDUCATION', 'LEADERSHIP AND AWARDS']
VARIANTS = [  # source, output base, role words, true keywords for that role
    ('resume-ats.html', 'Ciarra_Mazaredo_Resume_ATS', ['Chief of Staff', 'Executive Assistant to CEO', 'Operations Manager'],
     ['project coordination', 'priorities', 'deadlines', 'SOP', 'management reporting', 'meeting workflows', 'recruitment',
      'employee relations', 'onboarding', 'budgeting', 'stakeholder', 'calendar', 'correspondence', 'Google Workspace',
      'ChatGPT', 'Claude', 'Zapier', 'Notion', 'ClickUp', 'Slack']),
    ('resume-ats-marketing-ops.html', 'Ciarra_Mazaredo_Resume_ATS_MarketingOps', ['Marketing Operations', 'Marketing Automation'],
     ['email marketing', 'automation', 'campaign planning', 'editorial calendars', 'lead magnet', 'landing page', 'copywriting',
      'keyword research', 'click-to-open', 'GoHighLevel', 'Zapier', 'Canva', 'Notion', 'ChatGPT', 'Claude']),
    ('resume-ats-ai-automation.html', 'Ciarra_Mazaredo_Resume_ATS_AIAutomation', ['AI Automation', 'Workflow Automation'],
     ['automation', 'workflows', 'AI tools', 'ChatGPT', 'Claude', 'Gemini', 'Perplexity', 'NotebookLM', 'Zapier', 'GoHighLevel',
      'SOP', 'management reporting', 'process', 'MailerLite']),
]
fails = []


def check_text(label, text, roles):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines or lines[0] != 'Ciarra Amor G. Mazaredo':
        fails.append(f'{label}: first line is {lines[:1]}, expected the full name')
    for needle in ['ciarramazaredo@gmail.com', '+63 956 623 8024'] + roles:
        if needle not in text:
            fails.append(f'{label}: missing "{needle}"')
    pos = [text.upper().find(h) for h in HEADINGS]
    if -1 in pos or pos != sorted(pos):
        fails.append(f'{label}: headings missing or out of order {dict(zip(HEADINGS, pos))}')
    for bad in ['—', '–', '[CONFIRM']:
        if bad in text:
            fails.append(f'{label}: contains {bad!r}')


def history(src):
    """Employer, title, date and bullet lines of the experience block, as a set."""
    block = src.split('<h2>Professional Experience</h2>')[1].split('<h2>Education</h2>')[0]
    return {re.sub(r'<[^>]+>', '', m[1]) for m in re.findall(r'<(h3|p class="org"|li)>(.*?)</(?:h3|p|li)>', block)}


def numbers(text):
    t = re.sub(r'<[^>]+>', ' ', html.unescape(text))
    t = re.sub(r'\b(?:19|20)\d{2}\b', ' ', t)          # years: the history test covers dates
    t = re.sub(r'\+63 956 623 8024', ' ', t)
    return set(re.findall(r'\d[\d,.]*\d|\d', t))


def job_blocks(src):
    block = src.split('<h2>Professional Experience</h2>')[1].split('<h2>Education</h2>')[0]
    out = []
    for m in re.finditer(r'<div class="job"><h3>(.*?)</h3>\s*<p class="org">(.*?)</p>\s*<ul>(.*?)</ul></div>', block, re.S):
        out.append((html.unescape(m.group(1)), m.group(2), [html.unescape(re.sub(r'<[^>]+>', '', b)) for b in re.findall(r'<li>(.*?)</li>', m.group(3))]))
    return out


JOB_BLOCKS = {v[0]: job_blocks(open(os.path.join(ROOT, 'tools/resume', v[0]), encoding='utf-8').read()) for v in VARIANTS}
assert all(len(b) == 5 for b in JOB_BLOCKS.values()), 'expected five jobs per résumé'
allowed = numbers(open(RESUME_MD, encoding='utf-8').read() + open(os.path.join(ROOT, 'assets/case-studies.js'), encoding='utf-8').read())
histories, report = {}, []
for src_name, base, roles, keys in VARIANTS:
    src = open(os.path.join(ROOT, 'tools/resume', src_name), encoding='utf-8').read()
    sizes = [float(x) for x in re.findall(r'font-size:\s*([\d.]+)pt', src)]
    if not sizes or min(sizes) < 10:
        fails.append(f'{src_name}: smallest font-size {min(sizes) if sizes else None}pt, need 10pt or more')
    histories[src_name] = history(src)
    extra = numbers(src.split('<body>')[1]) - allowed
    if extra:
        fails.append(f'{src_name}: numbers not in the résumé or a live story: {sorted(extra)}')
    pdf = os.path.join(ROOT, 'assets', base + '.pdf')
    docx = os.path.join(ROOT, 'assets', base + '.docx')
    for f in (pdf, docx):
        if not os.path.isfile(f):
            fails.append(f'missing {f}')
    if not os.path.isfile(pdf) or not os.path.isfile(docx):
        continue
    pdf_text = subprocess.run(['pdftotext', pdf, '-'], capture_output=True, text=True, check=True).stdout
    check_text(base + '.pdf', pdf_text, roles)
    pages_text = pdf_text.split('\f')
    flat = lambda x: re.sub(r'\s+', ' ', x)
    for title, org, bullets in JOB_BLOCKS[src_name]:  # a job and its bullets stay on one page
        anchors = [html.unescape(re.sub(r'<[^>]+>', '', org))[:40]] + [x[:40] for x in bullets]  # the employer line is unique; the title may not be
        where = {i for i, pg in enumerate(pages_text) for b in anchors if b in flat(pg)}
        if len(where) > 1:
            fails.append(f'{base}.pdf: the "{title}" job is split across pages')
    for line in pdf_text.splitlines():  # a date range must not break across lines
        if re.search(r'(?:\| |to )(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*$', line.strip()) or re.search(r'\| (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} to\s*$', line.strip()):
            fails.append(f'{base}.pdf: date range breaks across lines: "{line.strip()[-40:]}"')
    if 'Type 3' in subprocess.run(['pdffonts', pdf], capture_output=True, text=True, check=True).stdout:
        fails.append(f'{base}.pdf: uses Type 3 fonts')
    pages = re.search(r'Pages:\s+(\d+)', subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout)
    if not pages or int(pages.group(1)) != 2:
        fails.append(f'{base}.pdf: page count {pages and pages.group(1)}, need exactly 2')
    docx_text = subprocess.run(['textutil', '-convert', 'txt', '-stdout', docx], capture_output=True, text=True, check=True).stdout
    check_text(base + '.docx', docx_text, roles)
    low = pdf_text.lower()
    hit = [k for k in keys if k.lower() in low]
    report.append(f'  {base}: {len(hit)} of {len(keys)} true keywords present' + (f' (missing: {", ".join(k for k in keys if k not in hit)})' if len(hit) < len(keys) else ''))

h = list(histories.values())
if any(x != h[0] for x in h[1:]):
    fails.append('work history differs between the three sources: ' + '; '.join(
        f'{n}: {sorted(histories[n] ^ h[0])[:2]}' for n in histories if histories[n] != h[0]))

print('keyword report:\n' + '\n'.join(report))
if fails:
    print('\n'.join(fails)); sys.exit(1)
print('resume parse test: PASS (3 résumés, PDF and Word, 2 pages each, one shared history)')
