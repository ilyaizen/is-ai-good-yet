# Architecture & Data Flow

## Summary

The project is a data pipeline plus a SvelteKit dashboard. The pipeline produces static JSON artifacts. The site consumes those artifacts at build/runtime through SvelteKit modules.

This is intentionally boring. Boring is good here: Python owns scraping/analysis; SvelteKit owns presentation and admin controls; SQLite is the local operational datastore.

## Current repository shape

```text
/srv/apps/is-ai-good-yet/
├── src/                       # SvelteKit app at repo root
│   ├── lib/
│   │   ├── data/              # exported JSON consumed by the site
│   │   ├── server/db.ts       # SQLite helpers for local/server-side tooling
│   │   ├── static-data.ts     # JSON data loader for public pages
│   │   └── components/        # UI components
│   ├── routes/                # public SvelteKit routes and API handlers
│   └── styles/                # design tokens and CSS architecture
├── pipeline/                  # Python data pipeline
│   ├── src/                   # phase modules
│   ├── data/                  # gitignored db/cache/runtime artifacts
│   ├── requirements.txt
│   └── tests/
├── docs/                      # prompt/spec docs used by the pipeline
├── docs_internal/             # repo-local operational docs
├── agents/                    # agent execution specs
├── convex/                    # visitor counter backend
├── scripts/                   # TypeScript operational scripts
├── package.json
├── svelte.config.js           # adapter-node
└── nixpacks.toml              # Coolify/Nixpacks build/start commands
```

There is no nested `is-ai-good-yet/` frontend directory in the current public checkout. Older docs that mention one are historical drift.

## Runtime stack

### Frontend / public site

- Node `>=22.12.0`
- npm scripts
- SvelteKit 2 + Svelte 5
- Tailwind CSS 4 via `@tailwindcss/vite`
- `@sveltejs/adapter-node`
- `better-sqlite3` for server-side/local DB access helpers
- Convex for public visitor counting
- Coolify/Nixpacks deployment using `npm install --include=dev`, `npm run build`, `HOST=0.0.0.0 node build/index.js`

### Pipeline

- Python 3.11 in repo-root `.venv`
- SQLite for mutable metadata: `pipeline/data/pipeline.db`
- Text files for human-editable scraped article ground truth: `pipeline/data/articles-text/*.txt`
- Parquet for derived/cache content: `pipeline/data/articles/*.parquet`
- Polars + PyArrow for data processing
- Playwright, playwright-stealth-plus, trafilatura, newspaper3k, Selenium/SeleniumBase/undetected-chromedriver for scraping and fallbacks
- Groq for content prefiltering and sentiment analysis
- Ollama remains listed as an optional/local dependency, not the current default analysis path

## Data flow

```text
Histre / Algolia / HN
        │
        ▼
Python pipeline modules in pipeline/src/
        │
        ├─► SQLite: pipeline/data/pipeline.db
        ├─► text ground truth: pipeline/data/articles-text/*.txt
        └─► parquet cache: pipeline/data/articles/*.parquet
        │
        ▼
python -m src.export
        │
        ▼
src/lib/data/*.json
        │
        ▼
SvelteKit public routes via src/lib/static-data.ts
```

## Pipeline phase model

The real modules live in `pipeline/src/`:

1. `backfill_histre.py` — collect candidate article URLs from Histre.
2. `algolia_discover.py` / `hn_resolver.py` — resolve URLs to HN metadata using Algolia.
3. `scraper.py` — scrape article content with direct/browser/archive fallbacks.
4. `clean_articles.py` — normalize text files.
5. `uptake_ground_truth.py` / `rebuild_parquet.py` — sync text ground truth back into derived stores.
6. `check_consistency.py` — detect/fix mismatches between DB/text/parquet.
7. `prefilter_content.py` — classify article relevance with Groq.
8. `sentiment_analyzer.py` — score utility/trajectory sentiment with Groq.
9. `summary_summarizer.py` — synthesize themes from analyzed content.
10. `export.py` — export static JSON for the SvelteKit app.
11. `catch_up.py` / `initial_e2e.py` — higher-level orchestration paths.

`pipeline/run.py` is currently a wrapper target for repo npm scripts. Treat it as wiring, not as the canonical detailed pipeline implementation until it is connected to the phase modules above.

## Public site data model

The public routes should prefer `src/lib/static-data.ts`, which imports JSON from `src/lib/data/`:

- `articles.json`
- `verdict.json`
- `historical.json`
- `weekly.json`
- theme/metric JSON when exported and used by the UI

This keeps the user-facing site deployable without requiring the mutable pipeline database to exist in production.

## Local/admin data model

`src/lib/server/db.ts` can read SQLite directly when `pipeline/data/pipeline.db` exists. That is useful for local admin tooling and future authenticated pipeline controls.

Do not make public pages depend on `pipeline/data/pipeline.db`. A fresh production checkout may not have it.

## Planned admin/scheduler architecture

See `agents/pipeline-admin-plan.md` for implementation details. The intended shape:

- authenticated admin route, not public
- SvelteKit server actions/API endpoints start named pipeline jobs only
- Node uses subprocess execution against `.venv/bin/python` with cwd `pipeline/`
- single-run lock prevents overlapping scrape/analyze runs
- run metadata in SQLite, logs as files under `pipeline/data/logs/`
- systemd timer or Hermes cron triggers scheduled catch-up runs
- export step updates `src/lib/data/*.json`, then deployment/rebuild can publish new data

No arbitrary shell command textbox. That would be stupid and unsafe.
