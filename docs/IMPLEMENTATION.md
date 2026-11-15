# Portfolio and service implementation

This branch adds equal employment and consulting paths, five role views, three industry views, six readable case studies, an applied experiment note, a scoped AI sprint, and a browser-local fit check. The complete approved master, source plans, research workbook, commercial playbook, and private evidence ledger are delivered separately. They are intentionally not published in this repository.

## Generate and verify

- `python tools/build_portfolio.py`: new static role, industry, contact, service, sample and case pages.
- `python tools/build_workflow_evidence.py`: evidence metadata embedded in workflow cards for no-JavaScript access.
- `python tools/build_workflows.py`: sample n8n files from maintained sources.
- `python tools/copy_gate.py`: all public HTML and case-study prose.
- `node --test tests/fit-check.test.js workflows/weekly-report-error-alerts/report.test.js`
- `node workflows/lead-to-booked-call/score-lead.test.js`
- `python tools/serve.py 8780`: local clean-URL preview.

Existing system tests remain in each `systems/*/tests` directory.

## Configuration

General booking and sprint booking are separate. Sprint URLs preserve an allowlisted workflow identifier. Newsletter and storefront destinations are optional and are not activated until verified. The inquiry fallback uses the existing public email address. The fit check sends no form answers and stores no personal data.

A host may provide `window.portfolioTrack(name, properties)` to receive bounded event metadata. Events describe clicks and routing, never confirmed leads or purchases. Actual business outcomes belong in a private register. Without an adapter the new tracking hook is a no-op.

## Evidence boundaries

Offline tests are not connected integration tests. Historical employment and marketing accounts are identified as self-reported where source records are unavailable. No production reliability, financial result, savings, or delivery latency is inferred from a sample. Client-derived system rights require separate review; the starter-workflow license is scoped.

## Release

A push to main deploys production. Review this branch and preview before merging. Live connected tests, legal adaptation, buyer interviews, paid pilots and independent product setup tests remain explicit release gates for their respective claims and offers.

## Verification record

Checked 2026-11-16 with Node 24.22.1, Python 3.12 and Playwright 1.62.1 Chromium.

- 23 routes at 1440px and 390px; automated WCAG A/AA checks pass.
- 75 local links resolve; four fit routes, workflow context, configured booking/fallback, keyboard menu and no-JavaScript access pass.
- 12 Node tests pass for reporting/error normalization and fit routing; lead-scoring fixture checks pass.
- Existing offline suites: trend scoring 35, transcript harvester 4, sheet router 6 pass.
- Copy gate passes; both résumé formats parse and the PDFs have two pages.
- Static page, workflow JSON and evidence generators reproduce identical outputs.

Run `npm ci`, install Playwright Chromium, and start the local server on 8781 before `npm run test:site`. `BASE_URL` overrides the preview URL. The accessibility suite is automated coverage, not a complete manual accessibility certification. No n8n connected execution is included in these results.

The résumé authoring source is `tools/resume/resume-ats.html`. Build DOCX with `tools/build_resume.py` (python-docx), then both PDFs with `tools/build_resume.js` (Playwright). The established presentation-PDF filename is retained for existing download links.
