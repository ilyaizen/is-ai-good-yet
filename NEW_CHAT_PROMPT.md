# is-ai-good-yet — admin page fixes + python content side-car

Repo: `D:\GitHub\is-ai-good-yet`. SvelteKit app at repo root (use npm/Node, **not** Bun; prod = `@sveltejs/adapter-node`). Python pipeline lives in `pipeline/`, venv at `pipeline/.venv` (Python 3.11). Note: `AGENTS.md` line 24 says "repo-root `.venv`" — that's **stale**; the real venv is `pipeline/.venv` (the code in `pipeline-runner.ts` is correct).

## Goals
1. Fix the admin page at `src/routes/admin` falsely reporting **"Venv Python — Missing"** and **"Groq key / Mistral key — Missing"** even though both keys are set in `.env` and the venv exists.
2. Get the **python side-car** working so the article details sheet shows the full scraped article text (the old repo's details page had 3 tabs: **Analysis / Prompts / Content**).
3. Fix the content table on the admin page so it looks + works right (clickable rows opening the details sheet).

## Bug 1 — both flags lie. One root cause: path/cwd resolution at module-load time
Status is computed in `src/lib/server/pipeline-runner.ts`:
- `getPipelineEnvironmentStatus()` reads **raw `process.env.GROQ_API_KEY` / `process.env.MISTRAL_API_KEY`** (not `$env/dynamic/private`).
- `VENV_PYTHON`, `PIPELINE_DIR`, `STORAGE_PATHS` are **module-load-time `const`s** derived from `process.cwd()` via `getPipelineStoragePaths()` in `src/lib/server/pipeline-storage.ts`.
- `.env` is parsed into `process.env` by an IIFE at the top of `src/hooks.server.ts` (uses `path.join(process.cwd(), ".env")`; comment notes adapter-node standalone doesn't load .env).

Verified in isolation from the repo root: venv resolves to `D:\GitHub\is-ai-good-yet\pipeline\.venv\Scripts\python.exe` and **EXISTS**; both keys **ARE** in repo-root `.env` (do not print them — treat as `[REDACTED]`).

So both symptoms point to **one** root cause: the running server's `process.cwd()` is not the repo root when the hook IIFE and the module-load consts run → `.env` isn't found (keys missing) **and** `pipeline/.venv` doesn't resolve (venv missing).
- Confirm by logging `process.cwd()` inside `getPipelineEnvironmentStatus()` and the hook IIFE.
- Fix: resolve paths from `import.meta.url` (`fileURLToPath`) instead of `process.cwd()`, **and** read the keys via `$env/dynamic/private` consistently so dev + prod both work. Keep the venv-path comment that already documents `pipeline/.venv` vs `bin`/`Scripts`.

## Where data lives (TWO sqlite DBs + content files)
- `pipeline/data/pipeline.db` (~19MB) — article data. The `urls` table has **NO content/text column** (only metadata, `classification_json`, `content_filter_json`, `sentiment_score`, `content_category`, `scraped_status`, etc.). DB access: `src/lib/server/db.ts` (`getUrlByHnId(hnId)` → row incl. `id` = url_id).
- `pipeline/data/admin.db` — pipeline run history (`pipeline_runs`, `pipeline_locks`), created/managed by `pipeline-runner.ts`.
- Full scraped text is **not** in the DB. It lives in two places:
  - `pipeline/data/articles/articles_*.parquet` — sharded parquet, keyed by `url_id` (the `urls.id`).
  - `pipeline/data/articles-text/<hn_id>.txt` — **11,342** raw text files keyed by `hn_id`, each starting `Title: …\nURL: …\n\n<article body>`.

## Python content side-car (already exists — reuse it)
- `pipeline/src/get_article.py` → `--id <url_id>`, scans the parquet shards, prints JSON for that article. Invoke with the venv python:
  `pipeline/.venv/Scripts/python.exe -m src.get_article --id <url_id>` (cwd = `pipeline/`).
- Spawn pattern already exists in `pipeline-runner.ts` `startPipelineRun()` (spawn `VENV_PYTHON`, `cwd: PIPELINE_DIR`, pass `{ ...process.env, PYTHONUNBUFFERED: "1" }`). Reuse the same `VENV_PYTHON`/`PIPELINE_DIR` resolution (after Bug 1's fix).
- Key mapping: the details sheet/API are keyed by `hn_id`; `get_article.py` wants `url_id`. Resolve `hn_id → url_id` via `getUrlByHnId()` from `db.ts` before spawning. (Fallback: read `pipeline/data/articles-text/<hn_id>.txt` directly — simpler, no spawn, but the user wants the python side-car wired up.)

## Current vs old details experience
- Old repo: details page had 3 tabs — **Analysis** (sentiment/utility/trajectory/topic/summary/quotes), **Prompts** (prefilter prompt+response; classifier system+user prompt+response), **Content** (full scraped text).
- Current `src/routes/details/[id]/+page.server.ts` reads **only** static data (`getStaticArticleById`), returns `text: null, text_missing: true`, `prompts: null`. The `AnalysisPrompts` type is already declared there.
- Current `src/routes/api/article-details/[id]/+server.ts`: for DB articles returns **`text: ""`** (empty); for static articles uses `excerpt`. Full content never reaches the UI. **Wire this to return text from the side-car.**
- `src/lib/components/landing/article-details-sheet.svelte` already has the collapsible "Article Content" section that renders `data.article.text` — just never populated.
- Prompts data: `pipeline/src/get_analysis_prompts.py` exists for the Prompts tab.

## Admin content table
- `src/routes/admin/+page.svelte` embeds `<ContentTable data={data.tableData} />` **without** `enableDetailLinks` → rows aren't clickable, no sheet opens. Pass `enableDetailLinks` (optionally `syncWithUrl`) so the sheet opens; then tidy the table styling.
- `src/lib/components/content-table.svelte` already opens `ArticleDetailsSheet` on row click when `enableDetailLinks` is set (it calls `openArticleSheet(item.hn_id)`).

## Next steps (in order)
1. Fix cwd/path resolution (`pipeline-runner.ts`, `pipeline-storage.ts`, hook `.env` loader) → Venv Python + keys show OK in dev **and** prod; switch key reads to `$env/dynamic/private`.
2. Add/extend the server endpoint to return full article text via the venv python `get_article.py` (resolve `hn_id → url_id` first; fallback to `articles-text/<hn_id>.txt`).
3. Make `/api/article-details/[id]` return that text; confirm the sheet's Content section populates.
4. On the admin page, enable `enableDetailLinks` on `<ContentTable>` so the sheet opens; clean up the table's look.
5. (Optional/next) restore the Prompts tab via `get_analysis_prompts.py`.

## Verify
```bash
npm run check
npm run build
# venv is pipeline/.venv (AGENTS.md's ".venv" path is stale):
pipeline/.venv/Scripts/python.exe -m pytest pipeline/tests -q   # Windows
```
