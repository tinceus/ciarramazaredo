# Workflows

Automations grouped by the result they bring. Each folder holds an importable n8n file, sample data, and a README with the steps, the human check, and setup.

> **Built on sample data.** Every business, lead, email and number in these folders is fictional. This is how I build them, not a client's live system. The files carry no logins: you connect your own accounts after import.

| Result | Workflow | What it does |
|---|---|---|
| No lead left behind | [Lead to booked call](lead-to-booked-call/) | Saves, scores and answers every lead within a minute, then follows up until they book |
| More booked calls | [AI receptionist](ai-receptionist/) | Website chat that answers from a fixed FAQ, offers real times, books, and hands off to a person |
| Hours back every week | [Inbox triage and daily brief](inbox-triage-daily-brief/) | Sorts every email, drafts replies (never sends), and emails a morning brief |
| Reports that write themselves | [Weekly report](weekly-report-error-alerts/) | Compares this week with last in code, then drafts the update for a person to check |
| Nothing breaks silently | [Error alerts](weekly-report-error-alerts/) | Any failed run posts the step, error and link to Slack within a minute |

## How every workflow is built

1. **Save the data first.** Nothing is lost if a later step fails.
2. **Rules for numbers.** Scores and totals come from plain code anyone can read.
3. **A person checks.** AI drafts words. A person approves before anything goes out.
4. **Failures speak up.** Pair any workflow with Error alerts.

## Import one

n8n → **Workflows** → **Import from file** → pick the `.json`. Built and import-tested on n8n 2.47, and every node passes n8n's own parameter check. The only fields left blank are your own spreadsheet and calendar, which you pick after import.

Maintainer check: `N8N_MODULES=/path/to/n8n/node_modules node tools/check_n8n_params.js workflows/*/*.json`

Past systems from earlier roles, with company details removed, are in [`../systems/`](../systems/).

Maintainer note: the JSON files are generated. Edit `tools/build_workflows.py` and run `python3 tools/build_workflows.py`.
