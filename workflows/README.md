# Workflows

Automations grouped by the result they bring. Each folder holds an importable n8n file, sample data, and a README with the steps, the human check, and setup.

> **Built on sample data.** Every business, lead, email and number in these folders is fictional. This is how I build them, not a client's live system. The files carry no logins: you connect your own accounts after import.

| Result | Workflow | What it does |
|---|---|---|
| Lead handoffs | [Lead to booked call](lead-to-booked-call/) | Saves and scores sample leads; fixed replies and one nurture follow-up |
| Booking support | [AI receptionist](ai-receptionist/) | Website chat that answers from a fixed FAQ, offers real times, books, and hands off to a person |
| Recurring admin support | [Inbox triage and daily brief](inbox-triage-daily-brief/) | Sorts every email, drafts replies (never sends), and emails a morning brief |
| Reviewable report drafts | [Weekly report](weekly-report-error-alerts/) | Compares this week with last in code, then drafts the update for a person to check |
| Workflow error alerts | [Error alerts](weekly-report-error-alerts/) | Assigned workflows attempt Slack and email notifications; delivery is unverified |

## How every workflow is built

1. **Save the data first.** Nothing is lost if a later step fails.
2. **Rules for numbers.** Scores and totals come from plain code anyone can read.
3. **Review is workflow-specific.** Inbox replies and KPI reports are drafts. Lead replies, internal briefs, alerts and calendar actions can run automatically. Inspect each sample before connecting accounts.
4. **Failures speak up.** Pair any workflow with Error alerts.

## Import one

n8n → **Workflows** → **Import from file** → pick the `.json`. Authored with node versions for n8n 2.47. Import and connected execution are not verified.

Past systems from earlier roles, with company details removed, are in [`../systems/`](../systems/).

Maintainer note: the JSON files are generated. Edit `tools/build_workflows.py` and run `python3 tools/build_workflows.py`.

## Evidence and configuration limits

Checked 2026-11-16. See `assets/workflow-evidence.json` at the repository root for the exact tested scope. These are inactive examples, not verified production deployments.

- Select an available model in every AI model node. `SELECT_A_MODEL_IN_N8N` is an intentional configuration placeholder, not a model name. The generator accepts `WORKFLOW_ANTHROPIC_MODEL`.
- Schedule timezone defaults to `Asia/Manila`; change it explicitly for the intended operator. The generator accepts `WORKFLOW_TIMEZONE`.
- Connect client-owned credentials and replace every sample recipient, channel, URL, sheet, label ID and calendar.
- Attach an error workflow in each workflow’s settings. Test notification failures separately.
- Use fictional data and isolated accounts first. External services and hosting incur their own charges.
- Human review is specific to each workflow: fixed lead replies and internal briefs send automatically; the receptionist can book events.

## Reuse

Original starter examples in this folder use the [scoped MIT license](LICENSE). Historical system artifacts elsewhere in the repository are excluded; see [ownership notes](../LICENSING.md).
