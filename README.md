# ciarramazaredo.vercel.app

Portfolio site of Ciarra Amor G. Mazaredo: operations, executive support, marketing and AI workflows. Plain HTML, CSS and JavaScript; generated pages are committed, so deployment needs no build step.

- Preview locally: `python3 tools/serve.py 8780`, then open http://localhost:8780 (mimics Vercel clean URLs and the 404 page).
- Case studies live in `assets/case-studies.js`; the home page count, the Numbers tiles and the case-studies page all read it.
- Check copy before publishing: `python3 tools/copy_gate.py`.
- Deploys: pushes to `main` deploy to production on Vercel (project `ciarramazaredo`).

- Implementation, configuration and evidence boundaries: [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md).
- Reuse rights are scoped; see [LICENSING.md](LICENSING.md).
- Browser checks: `npm ci`, `npx playwright install chromium`, start `python tools/serve.py 8781`, then `npm run test:site`.
- Component checks: `npm test`.
- Résumés: install `python-docx`, run `python tools/build_resume.py`, `npm run resume:pdf`, then `python tools/test_resume.py` (requires Poppler).
