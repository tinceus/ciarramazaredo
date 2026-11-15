# Inbox triage and daily brief

**Outcome: Hours back every week.** Every new email is sorted and labeled. Emails that need a reply get a draft. Each weekday morning, one short brief lists what needs the leader.

> **Built on sample data.** The emails are fictional. This is how I build it, not a client's live system.

## What it does

```mermaid
flowchart LR
  A[New email] --> B[Sort into 5 labels]
  B --> U[Urgent] & R[Needs reply] & P[Billing] & F[FYI] & N[Newsletter]
  R --> D[Draft a reply] --> S[Save as draft, never send]
  T[Weekdays 7:30] --> G[Get last 24 hours] --> L[List them] --> W[Write the brief] --> M[Email the brief]
```

## The human check

- **It never sends a reply.** Drafts wait in Gmail for the leader or assistant to edit and send.
- Anything the AI is unsure of is marked `[CHECK]` in the draft.
- The brief may only use the emails it was given. It is told never to add items.

## Set it up

1. In n8n: **Import from file** → `workflow.json`.
2. Connect Gmail and Anthropic.
3. In Gmail, create five labels: Urgent, Needs reply, Billing, FYI, Newsletter. Pick each one in its matching Label node.
4. Change `you@example.com` in **Send brief to me**.

## Try it on the sample

`sample-data/emails.json` holds five fictional emails, one per label. Pin them to the trigger in n8n to test the sorting without a real inbox.

## Files

| File | What it is |
|---|---|
| `workflow.json` | Importable n8n workflow (n8n 2.47) |
| `sample-data/emails.json` | Fictional emails for testing |
