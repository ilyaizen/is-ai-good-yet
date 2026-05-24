# Project Overview

`is-ai-good-yet` is a public data-journalism dashboard that asks a narrow question: are developer-facing AI tools actually useful yet, according to Hacker News discourse?

The project has two cooperating parts:

1. **Python pipeline** in `pipeline/` — collects HN-linked articles, scrapes content, classifies relevance, scores sentiment, synthesizes themes, and exports static JSON.
2. **SvelteKit site** at the repo root — renders the public dashboard from exported JSON and can later expose an authenticated local/admin pipeline UI.

## Repository identity

- Current canonical repo: `ilyaizen/is-ai-good-yet`
- Current canonical checkout on this box: `/srv/apps/is-ai-good-yet`
- Historical/private source repo: `ilyaizen/is-ai-good-yet.com`
- Temporary migration checkout `/tmp/is-ai-good-yet-public` is obsolete and must not appear in new docs except as history.

## Current status

- Frontend runtime is Node/npm, not Bun.
- Production adapter is `@sveltejs/adapter-node` for Coolify/Nixpacks.
- `npm run check` and `npm run build` pass in the current checkout.
- Python dependencies install into a root `.venv` with Python 3.11.
- Playwright Chromium is installed locally for the scraper.
- DB-backed scripts require `pipeline/data/pipeline.db`; that artifact is not present in a fresh checkout.
- `pipeline/run.py` exists for npm script wiring but still needs to be wired to the real phase modules before it becomes the serious orchestration entrypoint.

## Documentation map

- `README.md` — public-facing project summary and quick start.
- `docs_internal/` — operational project docs.
- `docs/` — prompt/spec docs used by the pipeline.
- `Agents/` — AI-agent execution docs, especially Hermes/Claude Code workflow.
