# Internal Docs

Operational documentation for `is-ai-good-yet`. This directory is the canonical reference for agents and maintainers.

## Index

| Doc                                        | Contents                                                             |
| ------------------------------------------ | -------------------------------------------------------------------- |
| [architecture.md](./architecture.md)       | System design, data flow, pipeline phases, verdict scoring           |
| [guide.md](./guide.md)                     | Setup, usage, dev conventions, agent mandates, bun command reference |
| [troubleshooting.md](./troubleshooting.md) | Common issues: prefilter JSON, archive CAPTCHA, HN ID mismatch       |

## Project Overview

**Is AI "Good" Yet?** is a data-journalism project answering whether AI discourse — specifically around coding workflows — is shifting toward utility or skepticism. It scrapes thousands of Hacker News URLs, runs LLM-based sentiment analysis, and visualizes the verdict through a Python pipeline + SvelteKit frontend.

**The end goal:** a web dashboard featuring a "Verdict" (green/red/yellow), a timeline chart of positive/negative/neutral sentiment over time, and a sortable article explorer.

## Pipeline Phase Status

All backend phases are **complete**. Static JSON export enables a pure-frontend production deployment.

1. **Phase 1** — Ingestion & HN Resolution (Histre backfill, Algolia queries) ✅
2. **Phase 2** — Content Scraping (Playwright/camoufox + archive fallbacks) ✅
3. **Phase 2.5** — Data Cleaning & Ground-Truth Uptake ✅
4. **Phase 2.7** — Consistency Verification ✅
5. **Phase 3** — Pre-filtering, post-scrape (Groq API classification) ✅
6. **Phase 4** — LLM Sentiment Analysis (2-dimension: utility + trajectory) ✅
7. **Phase 5** — Theme Summarization ✅
8. **Phase 7** — Export & Static Data Generation ✅

Frontend is live with the verdict reveal, history chart, and article details. The pipeline CLI uses `rich` for UX, with catch-up and version-bumping workflows.

## Related Docs (repo root)

- [`../AGENTS.md`](../AGENTS.md) — agent guidance (single source of truth for agents)
- [`../README.md`](../README.md) — project README
- [`../CHANGELOG.md`](../CHANGELOG.md) — changelog (Keep a Changelog format)
- [`cli.md`](cli.md) — bun command reference
