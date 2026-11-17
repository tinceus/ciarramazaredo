# Systems

Cleaned versions of automation systems I built at past jobs.

> **Details removed.** Company names, people, accounts and data were taken out. The logic is how I built it.

| System | Outcome | What it shows |
|---|---|---|
| [Trend Scoring Engine](trend-scoring-engine/) | Research in minutes, not days | Five-source trend pull, compliance filter, weighted scoring, cross-source dedup, three-tier fallback |
| [Transcript Harvester](transcript-harvester/) | Hours back every week | Resumable YouTube transcript harvest, caption engines with a local Whisper fallback, tamper check |
| [Sheet Push Router](sheet-push-router/) | Content that ships on time | Date-matched row writes into Google Sheets through one Apps Script router, clear validation errors |

Each code folder has its own README and offline tests that run on fictional fixtures. Where keys are needed, the README names them, and they go in a local `.env` file.
