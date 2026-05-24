# Usage Guide

## Canonical local path

```bash
cd /srv/apps/is-ai-good-yet
```

Use this path on the Hetzner box. Do not use `/tmp/is-ai-good-yet-public` for ongoing work.

## Prerequisites

- Node `>=22.12.0`
- npm
- Python `3.11.x`
- Chromium dependencies for Playwright/Selenium scraping
- Optional: Groq API key for analysis phases
- Optional: Convex env vars for visitor counter behavior

Do not use Bun for this repo unless a future explicit migration changes the docs and scripts.

## Install frontend dependencies

```bash
cd /srv/apps/is-ai-good-yet
npm install
```

## Install Python pipeline dependencies

Create the venv at the repo root:

```bash
cd /srv/apps/is-ai-good-yet
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r pipeline/requirements.txt
python -m playwright install chromium
```

On this Hetzner box the venv already exists at `.venv` and the requirements have been installed once. Re-run only when requirements change or the venv is broken.

## Environment variables

Frontend/public runtime currently uses `.env.example` as the visible contract:

```bash
PUBLIC_CONVEX_URL=...
VISITOR_IP_SALT=...
```

Pipeline secrets belong in local env only and must not be committed:

```bash
GROQ_API_KEY=...
PROXY_SERVER=...
PROXY_USERNAME=...
PROXY_PASSWORD=...
```

Keep frontend public env separate from pipeline/API secrets.

## Frontend commands

```bash
cd /srv/apps/is-ai-good-yet
npm run dev
npm run check
npm run build
npm run start
```

Meanings:

- `npm run dev` — Vite/SvelteKit dev server.
- `npm run check` — SvelteKit sync + `svelte-check`.
- `npm run build` — adapter-node build.
- `npm run start` — `HOST=0.0.0.0 node build/index.js`.

## Production deployment

Coolify/Nixpacks should deploy the repo root.

`nixpacks.toml` does this:

```toml
[variables]
NIXPACKS_NODE_VERSION = "22.12.0"
NPM_CONFIG_PRODUCTION = "false"

[phases.install]
cmds = ["npm install --include=dev"]

[phases.build]
cmds = ["npm run build"]

[start]
cmd = "HOST=0.0.0.0 node build/index.js"
```

## Pipeline commands

Most real pipeline modules should be run from `pipeline/` so `python -m src...` resolves cleanly:

```bash
cd /srv/apps/is-ai-good-yet
source .venv/bin/activate
cd pipeline
python -m src.catch_up -v
python -m src.backfill_histre --start 1 --end 10
python -m src.hn_resolver
python -m src.scraper -v --lean --stealth-mode=seleniumbase --no-headful-switch -b 50 -c 4
python src/clean_articles.py
python src/uptake_ground_truth.py
python src/check_consistency.py
python -m src.prefilter_content -v
python -m src.sentiment_analyzer -v
python -m src.summary_summarizer -v
python -m src.export -v
```

The root npm scripts currently call `python3 pipeline/run.py --phase ...`. Those scripts prove wiring and should eventually delegate to the real modules, but the manual operational commands above are the reliable reference until `pipeline/run.py` is upgraded.

## Database artifact

A fresh checkout may not contain:

```text
pipeline/data/pipeline.db
```

DB-backed scripts will fail until the DB is created/restored by a pipeline run or copied from a trusted artifact. That is expected, not a Node/SvelteKit failure.

## Tests and verification

```bash
cd /srv/apps/is-ai-good-yet
npm run check
npm run build
source .venv/bin/activate
python -m pytest pipeline/tests -q
```

Use `npm run build` before deploy or after runtime/config changes. For small frontend edits, `npm run check` is the cheaper first pass.
