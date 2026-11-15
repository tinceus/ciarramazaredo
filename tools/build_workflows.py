#!/usr/bin/env python3
"""Writes the importable n8n workflow files under workflows/*/.
Edit this file (not the JSON), then run: python3 tools/build_workflows.py
Node versions match n8n 2.47. Credentials are left empty on purpose: you connect your own after import."""
import json, os, re, uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = os.path.join(ROOT, 'workflows')
MODEL = 'claude-sonnet-5-5'


def uid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'ciarra-workflows/' + name))


def node(name, type_, version, params, pos, **extra):
    n = {'parameters': params, 'id': uid(name), 'name': name, 'type': type_, 'typeVersion': version, 'position': pos}
    n.update(extra)
    return n


def note(name, text, pos, w=360, h=220, color=4):
    return node(name, 'n8n-nodes-base.stickyNote', 1, {'content': text, 'height': h, 'width': w, 'color': color}, pos)


def rl(value='', mode='list'):
    return {'__rl': True, 'mode': mode, 'value': value}


def cond(left, op_type, op, right=None):
    c = {'id': uid(left + op), 'leftValue': left, 'operator': {'type': op_type, 'operation': op}}
    if right is not None:
        c['rightValue'] = right
    if op in ('true', 'false', 'empty', 'notEmpty'):
        c['operator']['singleValue'] = True
    return {'conditions': {'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'loose', 'version': 2},
                           'conditions': [c], 'combinator': 'and'}, 'looseTypeValidation': True, 'options': {}}


def assign(pairs):
    return {'mode': 'manual', 'assignments': {'assignments': [
        {'id': uid(k), 'name': k, 'value': v, 'type': t} for k, v, t in pairs]}, 'options': {}}


def sheets(op, sheet, extra=None):
    p = {'operation': op, 'documentId': rl('', 'url'), 'sheetName': rl(sheet, 'name')}
    p.update(extra or {})
    return p


def link(conns, a, b, out=0, kind='main'):
    conns.setdefault(a, {}).setdefault(kind, [])
    lst = conns[a][kind]
    while len(lst) <= out:
        lst.append([])
    lst[out].append({'node': b, 'type': kind, 'index': 0})


def ai(conns, sub, parent, kind):
    link(conns, sub, parent, 0, kind)


def workflow(name, nodes, conns, tags):
    return {'name': name, 'nodes': nodes, 'connections': conns, 'active': False,
            'settings': {'executionOrder': 'v1', 'saveManualExecutions': True},
            'meta': {'templateCredsSetupCompleted': False},
            'tags': [{'name': t} for t in tags], 'pinData': {}}


def write(folder, fname, wf):
    path = os.path.join(W, folder, fname)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(wf, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print('wrote', os.path.relpath(path, ROOT), len(wf['nodes']), 'nodes')


# 1. Lead to booked call -------------------------------------------------------------------------
def lead_to_booked_call():
    js = open(os.path.join(W, 'lead-to-booked-call/score-lead.js'), encoding='utf-8').read()
    js = js.replace("if (typeof module !== 'undefined') module.exports = { scoreLead };", '').rstrip()
    js += "\n\nreturn $input.all().map(item => ({ json: { ...item.json, ...scoreLead(item.json), reasons: scoreLead(item.json).reasons.join('; ') } }));\n"
    booking = 'https://cal.com/your-name/intro-call'
    n, c = [], {}
    n.append(note('About this workflow', '## Lead to booked call\nEvery lead is saved before anything else runs, scored with plain rules, answered within a minute, and followed up until they book or the sequence ends.\n\nSample data and a test live in the repo folder. Connect Google Sheets, Gmail and Slack after import.', [-80, -300], 420, 200))
    n.append(node('New lead (form webhook)', 'n8n-nodes-base.webhook', 2.1, {'httpMethod': 'POST', 'path': 'new-lead', 'responseMode': 'onReceived', 'options': {}}, [0, 0], webhookId=uid('lead-hook')))
    n.append(node('Clean fields', 'n8n-nodes-base.set', 3.4, assign([
        ('created_at', '={{ $now.toISO() }}', 'string'),
        ('name', '={{ ($json.body.name || "").trim() }}', 'string'),
        ('email', '={{ ($json.body.email || "").trim().toLowerCase() }}', 'string'),
        ('phone', '={{ ($json.body.phone || "").trim() }}', 'string'),
        ('company', '={{ ($json.body.company || "").trim() }}', 'string'),
        ('source', '={{ $json.body.source || "website" }}', 'string'),
        ('budget', '={{ $json.body.budget || "" }}', 'string'),
        ('message', '={{ $json.body.message || "" }}', 'string'),
        ('status', 'new', 'string')]), [220, 0]))
    n.append(node('Save lead first', 'n8n-nodes-base.googleSheets', 4.6, sheets('append', 'Leads', {
        'columns': {'mappingMode': 'autoMapInputData', 'value': {}, 'matchingColumns': [], 'schema': []}, 'options': {}}), [440, 0]))
    n.append(node('Score lead', 'n8n-nodes-base.code', 2, {'jsCode': js}, [660, 0]))
    n.append(node('Record score', 'n8n-nodes-base.googleSheets', 4.6, sheets('update', 'Leads', {
        'columns': {'mappingMode': 'defineBelow', 'value': {'email': '={{ $json.email }}', 'score': '={{ $json.score }}', 'tier': '={{ $json.tier }}'},
                    'matchingColumns': ['email'], 'schema': []}, 'options': {}}), [880, 0]))
    n.append(node('Hot lead?', 'n8n-nodes-base.if', 2.2, cond('={{ $json.tier }}', 'string', 'equals', 'hot'), [1100, 0]))
    n.append(node('Reply with booking link', 'n8n-nodes-base.gmail', 2.1, {
        'sendTo': "={{ $('Score lead').item.json.email }}", 'subject': 'Your intro call',
        'emailType': 'text', 'message': "=Hi {{ $('Score lead').item.json.name.split(' ')[0] }},\n\nThanks for reaching out. You can pick a time that suits you here: " + booking + "\n\nIf none of the times work, reply with two that do and I will make it happen.\n\nTalk soon", 'options': {'appendAttribution': False}}, [1340, -120]))
    n.append(node('Alert owner on Slack', 'n8n-nodes-base.slack', 2.3, {
        'select': 'channel', 'channelId': rl('#new-leads', 'name'),
        'text': "=Hot lead: {{ $('Score lead').item.json.name }} ({{ $('Score lead').item.json.company }}), score {{ $('Score lead').item.json.score }}. Why: {{ $('Score lead').item.json.reasons }}", 'otherOptions': {}}, [1560, -120]))
    n.append(node('Helpful reply', 'n8n-nodes-base.gmail', 2.1, {
        'sendTo': '={{ $json.email }}', 'subject': 'Thanks, here is what happens next',
        'emailType': 'text', 'message': "=Hi {{ $json.name.split(' ')[0] }},\n\nThanks for getting in touch. When you are ready to talk it through, book a time here: " + booking + "\n\nTalk soon", 'options': {'appendAttribution': False}}, [1340, 140]))
    n.append(node('Wait 2 days', 'n8n-nodes-base.wait', 1.1, {'amount': 2, 'unit': 'days'}, [1560, 140], webhookId=uid('wait-2')))
    n.append(node('Check status', 'n8n-nodes-base.googleSheets', 4.6, sheets('read', 'Leads', {
        'filtersUI': {'values': [{'lookupColumn': 'email', 'lookupValue': "={{ $('Score lead').item.json.email }}"}]}, 'options': {}}), [1780, 140]))
    n.append(node('Still not booked?', 'n8n-nodes-base.if', 2.2, cond('={{ $json.status }}', 'string', 'notEquals', 'booked'), [2000, 140]))
    n.append(node('Follow-up email', 'n8n-nodes-base.gmail', 2.1, {
        'sendTo': '={{ $json.email }}', 'subject': 'Quick follow-up',
        'emailType': 'text', 'message': "=Hi {{ $json.name.split(' ')[0] }},\n\nChecking in once. If a short call would help, here is the link: " + booking + "\n\nIf the timing is wrong, no reply needed.", 'options': {'appendAttribution': False}}, [2220, 120]))
    # Second trigger: booking made
    n.append(node('Booking made (calendar webhook)', 'n8n-nodes-base.webhook', 2.1, {'httpMethod': 'POST', 'path': 'booking-made', 'responseMode': 'onReceived', 'options': {}}, [0, 420], webhookId=uid('booking-hook')))
    n.append(node('Mark as booked', 'n8n-nodes-base.googleSheets', 4.6, sheets('update', 'Leads', {
        'columns': {'mappingMode': 'defineBelow', 'value': {'email': '={{ ($json.body.payload?.attendees?.[0]?.email || $json.body.email || "").toLowerCase() }}', 'status': 'booked'},
                    'matchingColumns': ['email'], 'schema': []}, 'options': {}}), [220, 420]))
    n.append(node('Tell the team', 'n8n-nodes-base.slack', 2.3, {
        'select': 'channel', 'channelId': rl('#new-leads', 'name'), 'text': '=Booked: {{ $json.email }}', 'otherOptions': {}}, [440, 420]))
    for a, b in [('New lead (form webhook)', 'Clean fields'), ('Clean fields', 'Save lead first'), ('Save lead first', 'Score lead'),
                 ('Score lead', 'Record score'), ('Record score', 'Hot lead?'), ('Reply with booking link', 'Alert owner on Slack'),
                 ('Helpful reply', 'Wait 2 days'), ('Wait 2 days', 'Check status'), ('Check status', 'Still not booked?'),
                 ('Booking made (calendar webhook)', 'Mark as booked'), ('Mark as booked', 'Tell the team')]:
        link(c, a, b)
    link(c, 'Hot lead?', 'Reply with booking link', 0)
    link(c, 'Hot lead?', 'Helpful reply', 1)
    link(c, 'Still not booked?', 'Follow-up email', 0)
    write('lead-to-booked-call', 'workflow.json', workflow('Lead to booked call', n, c, ['No lead left behind']))


# 2. AI receptionist -----------------------------------------------------------------------------
def ai_receptionist():
    faq = open(os.path.join(W, 'ai-receptionist/sample-data/faq.md'), encoding='utf-8').read().strip()
    system = ("You are the front desk for the business described below. Be warm, brief and exact.\n\n"
              "Rules:\n"
              "1. Answer only from the knowledge below. If the answer is not there, say you will check and use the handoff tool.\n"
              "2. Never quote prices, diagnoses or guarantees.\n"
              "3. To book: ask for name, email and the reason for the visit, check availability, offer two times, then create the event.\n"
              "4. Hand off to a human for emergencies, complaints, or any request you are not sure about.\n"
              "5. Confirm every booking back to the visitor with the date, time and time zone.\n\n"
              "Knowledge:\n" + faq)
    n, c = [], {}
    n.append(note('About this workflow', '## AI receptionist\nAnswers questions from a fixed knowledge base, qualifies the visitor, offers real calendar times, books, and hands off to a person when it should.\n\nConnect Anthropic, Google Calendar and Slack after import. Edit the knowledge in the agent system message.', [-80, -300], 440, 200))
    n.append(node('Website chat', '@n8n/n8n-nodes-langchain.chatTrigger', 1.1, {'public': True, 'options': {
        'title': 'Front desk', 'subtitle': 'Questions or bookings, I can help.', 'initialMessages': 'Hi, how can I help you today?'}}, [0, 0], webhookId=uid('chat')))
    n.append(node('Receptionist agent', '@n8n/n8n-nodes-langchain.agent', 2.2, {'options': {'systemMessage': system}}, [260, 0]))
    n.append(node('Claude', '@n8n/n8n-nodes-langchain.lmChatAnthropic', 1.3, {'model': rl(MODEL, 'id'), 'options': {'temperature': 0.2}}, [140, 240]))
    n.append(node('Conversation memory', '@n8n/n8n-nodes-langchain.memoryBufferWindow', 1.3, {'contextWindowLength': 12}, [300, 240]))
    n.append(node('Check availability', 'n8n-nodes-base.googleCalendarTool', 1.3, {
        'descriptionType': 'manual', 'toolDescription': 'Check when the calendar is busy between two ISO date-times.',
        'resource': 'calendar', 'calendar': rl(''),
        'timeMin': "={{ $fromAI('start', 'ISO start of the window to check', 'string') }}",
        'timeMax': "={{ $fromAI('end', 'ISO end of the window to check', 'string') }}", 'options': {}}, [460, 240]))
    n.append(node('Book the visit', 'n8n-nodes-base.googleCalendarTool', 1.3, {
        'descriptionType': 'manual', 'toolDescription': 'Create the appointment once the visitor confirms a time.',
        'calendar': rl(''),
        'start': "={{ $fromAI('start', 'ISO start time of the appointment', 'string') }}",
        'end': "={{ $fromAI('end', 'ISO end time of the appointment', 'string') }}",
        'additionalFields': {'summary': "={{ $fromAI('title', 'Visitor name and reason', 'string') }}",
                             'attendees': ["={{ $fromAI('email', 'Visitor email', 'string') }}"]}}, [620, 240]))
    n.append(node('Hand off to a person', 'n8n-nodes-base.slackTool', 2.3, {
        'descriptionType': 'manual', 'toolDescription': 'Alert the team when a human should take over. Include the visitor contact and the reason.',
        'select': 'channel', 'channelId': rl('#front-desk', 'name'),
        'text': "={{ $fromAI('message', 'Who needs help, how to reach them, and why', 'string') }}", 'otherOptions': {}}, [780, 240]))
    link(c, 'Website chat', 'Receptionist agent')
    ai(c, 'Claude', 'Receptionist agent', 'ai_languageModel')
    ai(c, 'Conversation memory', 'Receptionist agent', 'ai_memory')
    for t in ['Check availability', 'Book the visit', 'Hand off to a person']:
        ai(c, t, 'Receptionist agent', 'ai_tool')
    write('ai-receptionist', 'workflow.json', workflow('AI receptionist', n, c, ['More booked calls']))


# 3. Inbox triage + daily brief ------------------------------------------------------------------
def inbox_triage():
    n, c = [], {}
    n.append(note('About this workflow', '## Inbox triage and daily brief\nEvery new email is sorted and labeled. Emails that need a reply get a draft, never a sent message. Each morning one short brief lists what needs the leader.\n\nConnect Gmail and Anthropic after import, and create the five labels.', [-80, -320], 440, 200))
    n.append(node('New email', 'n8n-nodes-base.gmailTrigger', 1.2, {
        'pollTimes': {'item': [{'mode': 'everyX', 'value': 5, 'unit': 'minutes'}]}, 'simple': False,
        'filters': {'labelIds': ['INBOX']}, 'options': {}}, [0, 0]))
    cats = [('Urgent', 'Needs action today: a deadline, an outage, a leader or client waiting.'),
            ('Needs reply', 'A real person asked a question or proposed something.'),
            ('Billing', 'Invoices, receipts, payments, subscriptions.'),
            ('FYI', 'Updates to read later with no action needed.'),
            ('Newsletter', 'Bulk or marketing email.')]
    n.append(node('Sort email', '@n8n/n8n-nodes-langchain.textClassifier', 1.1, {
        'inputText': '=From: {{ $json.from.text }}\nSubject: {{ $json.subject }}\n\n{{ $json.text }}',
        'categories': {'categories': [{'category': k, 'description': d} for k, d in cats]},
        'options': {'fallback': 'other'}}, [260, 0]))
    n.append(node('Claude (sorting)', '@n8n/n8n-nodes-langchain.lmChatAnthropic', 1.3, {'model': rl(MODEL, 'id'), 'options': {'temperature': 0}}, [260, 220]))
    ai(c, 'Claude (sorting)', 'Sort email', 'ai_languageModel')
    link(c, 'New email', 'Sort email')
    y = -260
    for i, (k, _) in enumerate(cats):
        name = f'Label: {k}'
        n.append(node(name, 'n8n-nodes-base.gmail', 2.1, {'operation': 'addLabels', 'messageId': '={{ $json.id }}', 'labelIds': [k]}, [560, y + i * 130]))
        link(c, 'Sort email', name, i)
    n.append(node('Draft a reply', '@n8n/n8n-nodes-langchain.chainLlm', 1.7, {
        'promptType': 'define',
        'text': "=Draft a short, polite reply for the leader to review. Match their tone, answer only what was asked, and mark anything you are unsure of with [CHECK].\n\nFrom: {{ $('New email').item.json.from.text }}\nSubject: {{ $('New email').item.json.subject }}\n\n{{ $('New email').item.json.text }}"}, [820, -130]))
    n.append(node('Claude (drafting)', '@n8n/n8n-nodes-langchain.lmChatAnthropic', 1.3, {'model': rl(MODEL, 'id'), 'options': {'temperature': 0.3}}, [820, 80]))
    ai(c, 'Claude (drafting)', 'Draft a reply', 'ai_languageModel')
    n.append(node('Save as draft (never send)', 'n8n-nodes-base.gmail', 2.1, {
        'resource': 'draft', 'subject': "=Re: {{ $('New email').item.json.subject }}", 'emailType': 'text',
        'message': '={{ $json.text }}', 'options': {'threadId': "={{ $('New email').item.json.threadId }}",
                                                  'sendTo': "={{ $('New email').item.json.from.value[0].address }}"}}, [1060, -130]))
    link(c, 'Label: Needs reply', 'Draft a reply')
    link(c, 'Draft a reply', 'Save as draft (never send)')
    # Morning brief
    n.append(node('Every weekday 7:30', 'n8n-nodes-base.scheduleTrigger', 1.2, {'rule': {'interval': [{'field': 'cronExpression', 'expression': '30 7 * * 1-5'}]}}, [0, 520]))
    n.append(node('Get last 24 hours', 'n8n-nodes-base.gmail', 2.1, {'operation': 'getAll', 'returnAll': True, 'simple': True,
                                                                     'filters': {'q': 'newer_than:1d (label:Urgent OR label:"Needs reply" OR label:Billing)'}, 'options': {}}, [260, 520]))
    n.append(node('List them', 'n8n-nodes-base.code', 2, {'jsCode': "const lines = $input.all().map(i => `- ${i.json.From || i.json.from}: ${i.json.Subject || i.json.subject}`);\nreturn [{ json: { list: lines.join('\\n'), count: lines.length } }];"}, [480, 520]))
    n.append(node('Write the brief', '@n8n/n8n-nodes-langchain.chainLlm', 1.7, {
        'promptType': 'define',
        'text': '=Write a morning brief of at most 8 lines for a busy leader. Group into Do today, Reply, Pay. Use only the emails listed. Never add items.\n\n{{ $json.list }}'}, [700, 520]))
    n.append(node('Claude (brief)', '@n8n/n8n-nodes-langchain.lmChatAnthropic', 1.3, {'model': rl(MODEL, 'id'), 'options': {'temperature': 0.2}}, [700, 740]))
    ai(c, 'Claude (brief)', 'Write the brief', 'ai_languageModel')
    n.append(node('Send brief to me', 'n8n-nodes-base.gmail', 2.1, {'sendTo': 'you@example.com', 'subject': "=Morning brief {{ $now.toFormat('ccc d LLL') }}",
                                                                   'emailType': 'text', 'message': '={{ $json.text }}', 'options': {'appendAttribution': False}}, [940, 520]))
    for a, b in [('Every weekday 7:30', 'Get last 24 hours'), ('Get last 24 hours', 'List them'), ('List them', 'Write the brief'), ('Write the brief', 'Send brief to me')]:
        link(c, a, b)
    write('inbox-triage-daily-brief', 'workflow.json', workflow('Inbox triage and daily brief', n, c, ['Hours back every week']))


# 4. Weekly report + error alerts ----------------------------------------------------------------
def weekly_report():
    calc = ("// Compare this week with last week for every metric. Status uses the target and the direction.\n"
            "const rows = $input.all().map(i => i.json);\n"
            "const weeks = [...new Set(rows.map(r => r.week_start))].sort();\n"
            "const [prev, cur] = weeks.slice(-2);\n"
            "const pick = (w, m) => rows.find(r => r.week_start === w && r.metric === m);\n"
            "const out = [...new Set(rows.map(r => r.metric))].map(m => {\n"
            "  const a = pick(cur, m), b = pick(prev, m);\n"
            "  const v = Number(a.value), t = Number(a.target), p = b ? Number(b.value) : null;\n"
            "  const good = a.direction === 'down' ? v <= t : v >= t;\n"
            "  return { metric: m, value: v, target: t, previous: p, change: p === null ? null : +(v - p).toFixed(2), status: good ? 'On track' : 'Watch' };\n"
            "});\n"
            "return [{ json: { week: cur, metrics: out, table: out.map(o => `${o.metric}: ${o.value} (target ${o.target}, last week ${o.previous}) ${o.status}`).join('\\n') } }];\n")
    n, c = [], {}
    n.append(note('About this workflow', '## Weekly report\nEvery Monday the numbers are pulled from one sheet, compared with last week, and turned into a short draft. The draft waits in Gmail for a person to check before it goes to the leader.\n\nNumbers are calculated in code. The AI only writes sentences around them.', [-80, -300], 440, 200))
    n.append(node('Every Monday 8:00', 'n8n-nodes-base.scheduleTrigger', 1.2, {'rule': {'interval': [{'field': 'cronExpression', 'expression': '0 8 * * 1'}]}}, [0, 0]))
    n.append(node('Read KPI sheet', 'n8n-nodes-base.googleSheets', 4.6, sheets('read', 'KPIs', {'options': {}}), [220, 0]))
    n.append(node('Compare weeks', 'n8n-nodes-base.code', 2, {'jsCode': calc}, [440, 0]))
    n.append(node('Write the summary', '@n8n/n8n-nodes-langchain.chainLlm', 1.7, {
        'promptType': 'define',
        'text': '=Write a weekly update of 5 to 7 short lines for the leadership team. Start with what improved, then what needs attention, then one suggested next step. Use only these numbers, exactly as written. Do not round or add figures.\n\nWeek of {{ $json.week }}\n{{ $json.table }}'}, [660, 0]))
    n.append(node('Claude', '@n8n/n8n-nodes-langchain.lmChatAnthropic', 1.3, {'model': rl(MODEL, 'id'), 'options': {'temperature': 0.2}}, [660, 220]))
    ai(c, 'Claude', 'Write the summary', 'ai_languageModel')
    n.append(node('Draft for review', 'n8n-nodes-base.gmail', 2.1, {
        'resource': 'draft', 'subject': "=Weekly update, week of {{ $('Compare weeks').item.json.week }}", 'emailType': 'text',
        'message': "={{ $json.text }}\n\nNumbers:\n{{ $('Compare weeks').item.json.table }}", 'options': {'sendTo': 'leader@example.com'}}, [900, 0]))
    n.append(node('Ping me to review', 'n8n-nodes-base.slack', 2.3, {
        'select': 'channel', 'channelId': rl('#ops', 'name'), 'text': '=Weekly update draft is ready in Gmail for review.', 'otherOptions': {}}, [1120, 0]))
    for a, b in [('Every Monday 8:00', 'Read KPI sheet'), ('Read KPI sheet', 'Compare weeks'), ('Compare weeks', 'Write the summary'),
                 ('Write the summary', 'Draft for review'), ('Draft for review', 'Ping me to review')]:
        link(c, a, b)
    write('weekly-report-error-alerts', 'weekly-report.json', workflow('Weekly report', n, c, ['Reports that write themselves']))

    n2, c2 = [], {}
    n2.append(note('About this workflow', '## Error alerts\nSet this as the error workflow for every other workflow (Workflow settings, Error workflow). When any run fails, the team hears about it within a minute, with a link to the failed run.', [-80, -280], 420, 180))
    n2.append(node('When any workflow fails', 'n8n-nodes-base.errorTrigger', 1, {}, [0, 0]))
    n2.append(node('Alert on Slack', 'n8n-nodes-base.slack', 2.3, {
        'select': 'channel', 'channelId': rl('#ops-alerts', 'name'),
        'text': '=Failed: {{ $json.workflow.name }}\nStep: {{ $json.execution.lastNodeExecuted }}\nError: {{ $json.execution.error.message }}\nRun: {{ $json.execution.url }}', 'otherOptions': {}}, [240, 0]))
    n2.append(node('Email backup alert', 'n8n-nodes-base.gmail', 2.1, {
        'sendTo': 'you@example.com', 'subject': '=Workflow failed: {{ $json.workflow.name }}', 'emailType': 'text',
        'message': '=Step: {{ $json.execution.lastNodeExecuted }}\nError: {{ $json.execution.error.message }}\nRun: {{ $json.execution.url }}', 'options': {'appendAttribution': False}}, [240, 200]))
    link(c2, 'When any workflow fails', 'Alert on Slack')
    link(c2, 'When any workflow fails', 'Email backup alert')
    write('weekly-report-error-alerts', 'error-alerts.json', workflow('Error alerts', n2, c2, ['Nothing breaks silently']))


if __name__ == '__main__':
    lead_to_booked_call()
    ai_receptionist()
    inbox_triage()
    weekly_report()
    # self-check: every connection points at a node that exists
    for folder in os.listdir(W):
        for f in os.listdir(os.path.join(W, folder)):
            if f.endswith('.json') and 'sample' not in f:
                p = os.path.join(W, folder, f)
                if not os.path.isfile(p):
                    continue
                wf = json.load(open(p))
                if 'nodes' not in wf:
                    continue
                names = {x['name'] for x in wf['nodes']}
                for a, kinds in wf['connections'].items():
                    assert a in names, (f, a)
                    for outs in kinds.values():
                        for out in outs:
                            for t in out:
                                assert t['node'] in names, (f, t['node'])
                assert len(names) == len(wf['nodes']), (f, 'duplicate node names')
    print('connections: PASS')
