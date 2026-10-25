# ciarramazaredo.vercel.app

Portfolio site of Ciarra Amor G. Mazaredo (Chief of Staff version). Plain HTML, CSS and JS, no build step.

- Preview locally: `python3 tools/serve.py 8780`, then open http://localhost:8780 (mimics Vercel clean URLs and the 404 page).
- Case studies live in `assets/case-studies.js`; the home page count, the Numbers tiles and the case-studies page all read it.
- Check copy before publishing: `python3 tools/copy_gate.py`.
- Deploys: pushes to `main` deploy to production on Vercel (project `ciarramazaredo`).
