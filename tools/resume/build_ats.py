#!/usr/bin/env python3
"""Writes the three plain (ATS) résumé sources from one shared work history.

  python3 tools/resume/build_ats.py         write resume-ats*.html
  python3 tools/resume/build_ats.py --check exit 1 if a file is out of date

The history block (employer, title, dates, bullets) is shared, so it is identical in all three.
Only the target line, summary, skills and the order of bullets inside a role differ.
Every fact comes from Resume/Ciarra_Mazaredo_Resume_ChiefOfStaff.md or a story live on the site.
Edit this file, never the HTML it writes. Then run: bash tools/build_resume.sh
"""
import html, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTACT = ['Mandaluyong City, Philippines | Remote | Available immediately | WhatsApp: wa.me/message/6D7T7R5ZGZVHL1',
           'ciarramazaredo@gmail.com | +63 956 623 8024 | ciarramazaredo.vercel.app | linkedin.com/in/ciarra-m']

# key: (title, org line, [(bullet id, text)])
JOBS = {
    'edgyvis': ('Head of People and Culture',
                'Eskola De Gracia Y Verdad International School (EDGYVIS), Dili, Timor-Leste (On-site) | Jun 2024 to Oct 2026', [
        ('smt', 'Served on the senior management team with delegated decision-making authority across people, operations and institutional affairs for a workforce of 50+ employees'),
        ('coord', 'Set project ownership, priorities and deadlines across functions; designed the processes, forms, reporting structures and meeting workflows that coordinated delivery'),
        ('reports', 'Prepared management reports, contributed to budgeting and financial oversight, and represented the school with external stakeholders'),
        ('hiring', 'Led recruitment and employee relations as the workforce grew from about 24 employees (Jan 2025) to 53 (Jan 2026)'),
        ('comms', 'Oversaw institutional correspondence, public announcements and reputation messaging; directed campaign planning, editorial calendars and final creative approvals')]),
    'yokly': ('Real Estate Marketing Operations Head',
              'Yokly, Tustin, California (Remote); client assignment: Executive Marketing Manager, Kidder Mathews | Aug 2023 to Feb 2024', [
        ('train', 'Trained 3 to 6 support staff and wrote the training manual that standardized their onboarding for client matching and assignments'),
        ('svp', 'Supported a Kidder Mathews Senior Vice President of Investment with transaction coordination, property listings, letters of intent, business correspondence and website updates')]),
    'kimbarber': ('Digital Marketing Specialist (Freelance)',
                  'Kim Barber Coaching, Kim Barber Realty Group and bossOwners, Ashburn, Virginia (Remote) | Mar 2022 to Dec 2023', [
        ('flows', 'Supported a real estate coach across three brands (coaching, brokerage and a business program), building six multi-touch email automation workflows that moved agent leads from cold to converted'),
        ('copy', 'Wrote email sequences with an 83.57% click-to-open rate and a 50+ page homebuyer guide adopted as the standard onboarding asset for new coaching clients')]),
    'gotham': ('SEO Analyst (Freelance)',
               'Gotham City Online (Pop Threads and Poster Foundry), Texas, United States (Remote) | Feb 2021 to Mar 2022', [
        ('seo', 'Ran product, competitor and keyword research for 100+ Amazon listings, supporting #1 category rankings in Apparel, Posters and Mugs')]),
    'rocky': ('Executive Assistant',
              'Rocky-CGM Construction Phils Inc., Dili, Timor-Leste and Isabel, Leyte (Hybrid) | Jul 2019 to Jan 2022', [
        ('ea', 'Coordinated executive calendars and appointments, organized financial records, and prepared stakeholder presentations with charts and graphs')]),
}
JOB_ORDER = ['edgyvis', 'yokly', 'kimbarber', 'gotham', 'rocky']  # reverse chronological by end date, same in all three
ADDITIONAL = [
    "Content Writer and Graphic Designer (Freelance), Botanacea Wellness (United States) | 2022 to 2024: ghostwrote and edited website copy and educational articles published under the client's byline",
    'Marketing Executive (Freelance), Trip Quest Travel and Tours (Philippines) | 2022 to 2024: marketing and content support for a travel agency',
    'Social Media Content Creator (Part-time), EDGYVIS | Apr 2016 to Dec 2018: built content calendars and introduced an online scheduling calendar',
]
EDUCATION = ['Master of Business Psychology and Leadership | Arden University | In progress',
             'BS Psychology | University of Baguio | 2023 | Magna Cum Laude | Leadership Awardee']
AWARDS = ['2nd Place (PHP 30,000 prize), Stage 0 Problem Validation Hackathon, Zero Vector Ventures | Apr 2026: evidence-led market research pitch',
          'Editor-in-Chief, Sparks Publication, University of Baguio | 2019 to 2021',
          'Public Relations Officer, UB Psyche Organization, and Publication Officer, UB Supreme Student Council | 2022 to 2023']

VARIANTS = {
    'resume-ats.html': {
        'target': 'Target roles: Chief of Staff | Executive Assistant to CEO | Operations Manager',
        'summary': ('Operations leader who served on the senior management team of a 50+ person international school, with delegated '
                    'decision-making authority across people, operations and institutional affairs. Runs the work behind the leader: '
                    'project coordination, priorities and deadlines across functions, SOPs and management reporting, recruitment, '
                    'budgeting support and stakeholder communication. Brings executive assistant experience supporting company leadership '
                    'and a Senior Vice President of Investment, plus a marketing background in automation, email and communications. '
                    'Works with AI tools such as ChatGPT and Claude. BS Psychology, Magna Cum Laude, with a Master of '
                    'Business Psychology and Leadership in progress.'),
        'skills': [
            ('Executive Operations and Project Coordination', 'Cross-functional project coordination, priorities, ownership and deadlines, process, form and SOP design, meeting workflows, management reporting, budgeting and financial oversight support, stakeholder and external relations, institutional correspondence'),
            ('Executive Support', 'Calendar and appointment management, business correspondence, transaction coordination, letters of intent, stakeholder presentations, financial records'),
            ('People and Culture (HR)', 'Recruitment, employee relations, onboarding and training manuals, staff training, team leadership'),
            ('Communications', 'Public announcements, reputation messaging, campaign planning, editorial calendars, email marketing and automation, copywriting and editing'),
            ('Tools', 'Google Workspace, Notion, Airtable, ClickUp, Asana, Trello, Monday, Slack, Zapier, GoHighLevel, ChatGPT, Claude, Gemini, Perplexity, NotebookLM, Canva')],
        'order': {'edgyvis': ['smt', 'coord', 'reports', 'hiring', 'comms'], 'yokly': ['svp', 'train']},
    },
    'resume-ats-marketing-ops.html': {
        'target': 'Target roles: Marketing Operations Specialist | Marketing Automation | Email Marketing',
        'summary': ('Marketing operations specialist who built six multi-touch email automation workflows for a real estate coach across '
                    'three brands, with email sequences reaching an 83.57% click-to-open rate. Plans campaigns and editorial calendars, '
                    'wrote a 50+ page homebuyer guide that converted at 25 to 30 percent on dedicated landing pages, and ran product, '
                    'competitor and keyword research for 100+ Amazon listings. Brings operations leadership from serving on a school senior management team, '
                    'including campaign planning and final creative approvals. BS Psychology, Magna Cum Laude.'),
        'skills': [
            ('Marketing Operations', 'Email marketing and automation, multi-touch email automation workflows, campaign planning, editorial calendars, lead magnet writing, conversion copywriting, product, competitor and keyword research'),
            ('Communications', 'Copywriting and editing, public announcements, reputation messaging, stakeholder presentations'),
            ('Operations', 'Cross-functional project coordination, priorities, ownership and deadlines, process, form and SOP design, management reporting'),
            ('Tools', 'GoHighLevel, MailerLite, kvCORE, Zapier, Canva, Notion, Airtable, ClickUp, Asana, Trello, Monday, Slack, Google Workspace, ChatGPT, Claude, Gemini, Perplexity, NotebookLM')],
        'order': {'edgyvis': ['comms', 'coord', 'smt', 'reports', 'hiring'], 'kimbarber': ['flows', 'copy'], 'yokly': ['train', 'svp']},
    },
    'resume-ats-ai-automation.html': {
        'target': 'Target roles: AI Automation Specialist | Operations Automation | Workflow Automation',
        'summary': ('Operations and marketing professional who built six multi-touch email automation workflows that moved agent leads '
                    'from cold to converted for a real estate coach. Works with ChatGPT, Claude, Gemini, Perplexity and NotebookLM, plus '
                    'Zapier and GoHighLevel. As a member of a school senior management team, designed the processes, forms, reporting '
                    'structures and meeting workflows. Placed 2nd in a problem validation hackathon with an evidence-led market research '
                    'pitch built with NotebookLM and Claude. Sample work: five workflow files on made-up data, each with a named '
                    'human check, at ciarramazaredo.vercel.app/workflows. BS Psychology, Magna Cum Laude.'),
        'skills': [
            ('Automation and AI', 'Multi-touch email automation workflows (MailerLite, kvCORE, GoHighLevel), AI-assisted research (NotebookLM, Claude)'),
            ('AI Tools', 'ChatGPT, Claude, Gemini, Perplexity, NotebookLM'),
            ('Process and Reporting', 'Process, form and SOP design, meeting workflows, management reporting, cross-functional project coordination, priorities, ownership and deadlines'),
            ('Tools', 'GoHighLevel, MailerLite, kvCORE, Zapier, Google Workspace, Notion, Airtable, ClickUp, Asana, Trello, Monday, Slack, Canva')],
        'order': {'edgyvis': ['coord', 'smt', 'reports', 'hiring', 'comms'], 'kimbarber': ['flows', 'copy']},
    },
}

STYLE = """  @page { size: Letter; margin: 0.6in 0.7in; }
  body { font-family: Arial, Helvetica, sans-serif; font-size: 10.5pt; line-height: 1.36; color: #000; margin: 0; }
  h1 { font-size: 18pt; margin: 0 0 2pt; }
  .target { font-size: 11pt; font-weight: bold; margin: 0 0 4pt; }
  .contact1 { margin: 0; }
  .contact { margin: 0 0 10pt; }
  h2 { font-size: 11pt; text-transform: uppercase; letter-spacing: 0.5pt; border-bottom: 1px solid #000; margin: 12pt 0 5pt; padding-bottom: 2pt; }
  h3 { font-size: 10.5pt; margin: 8pt 0 0; }
  p { margin: 0 0 4pt; }
  ul { margin: 2pt 0 4pt; padding-left: 16pt; }
  li { margin: 0 0 2pt; }
  .org { margin: 0 0 2pt; break-inside: avoid; }
  h2, h3 { break-after: avoid; }
  .d { white-space: nowrap; }
  .job { break-inside: avoid; }"""


def e(s):
    return html.escape(s, quote=False)


def history(order):
    out = []
    for key in JOB_ORDER:
        title, org, bullets = JOBS[key]
        by_id = dict(bullets)
        ids = order.get(key, [b for b, _ in bullets])
        assert sorted(ids) == sorted(by_id), key  # reorder only: never drop or add a bullet
        place, _, dates = org.rpartition(' | ')
        out.append('<div class="job"><h3>%s</h3>\n<p class="org">%s | <span class="d">%s</span></p>\n<ul>\n%s\n</ul></div>' % (
            e(title), e(place), e(dates), '\n'.join('  <li>%s</li>' % e(by_id[i]) for i in ids)))
    return '\n\n'.join(out)


def render(v):
    skills = '\n'.join('<p><b>%s:</b> %s</p>' % (e(a), e(b)) for a, b in v['skills'])
    return f"""<!doctype html>
<!-- Generated by tools/resume/build_ats.py. Edit that file, not this one. -->
<html lang="en">
<head>
<meta charset="utf-8">
<title>Ciarra Amor G. Mazaredo - Resume</title>
<style>
{STYLE}
</style>
</head>
<body>
<h1>Ciarra Amor G. Mazaredo</h1>
<p class="target">{e(v['target'])}</p>
<p class="contact1">{CONTACT[0]}</p>
<p class="contact">{CONTACT[1]}</p>

<h2>Summary</h2>
<p>{e(v['summary'])}</p>

<h2>Core Skills</h2>
{skills}

<h2>Professional Experience</h2>
{history(v['order'])}

<h3>Additional Experience</h3>
<ul>
{chr(10).join('  <li>%s</li>' % e(a) for a in ADDITIONAL)}
</ul>

<h2>Education</h2>
{chr(10).join('<p>%s</p>' % e(x) for x in EDUCATION)}

<h2>Leadership and Awards</h2>
<ul>
{chr(10).join('  <li>%s</li>' % e(a) for a in AWARDS)}
</ul>
</body>
</html>
"""


def main():
    stale = []
    for name, v in VARIANTS.items():
        text = render(v)
        path = os.path.join(HERE, name)
        cur = open(path, encoding='utf-8').read() if os.path.exists(path) else None
        if cur != text:
            stale.append(name)
            if '--check' not in sys.argv:
                open(path, 'w', encoding='utf-8').write(text)
                print('wrote', name)
    if '--check' in sys.argv and stale:
        print('out of date:', ', '.join(stale)); sys.exit(1)


if __name__ == '__main__':
    main()
