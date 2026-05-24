# Project Plan & Roadmap

## Current objective

Make the public `ilyaizen/is-ai-good-yet` repo production-ready on the Hetzner/Coolify box while bringing the historical Python scraper/analysis pipeline forward from the old private `.com` repo.

## Completed/current foundation

- Repo canonical path set to `/srv/apps/is-ai-good-yet`.
- Runtime wiring uses npm/Node and SvelteKit adapter-node.
- Nixpacks build/start commands match the real Node output.
- Python `.venv` exists at the repo root and requirements install locally.
- Playwright Chromium is installed for the scraper.
- agent docs exist under `agents/`.
- `docs_internal/` and `docs/` are restored as real repo docs.

## Next implementation phases

### Phase 1 — Pipeline artifact readiness

Goal: make local pipeline commands work predictably on the box.

- Decide whether `pipeline/data/pipeline.db` is restored from old artifact or recreated from scratch.
- Add a documented DB bootstrap/restore procedure.
- Smoke-test key modules with `--help`, `--dry-run`, or small limits.
- Confirm required env vars for Groq/proxies.

### Phase 2 — Real pipeline runner

Goal: replace placeholder `pipeline/run.py` behavior with named, safe phase execution.

- Map `--phase ingest|scrape|analyze|all` to real modules.
- Use subprocess/module calls with explicit cwd and environment.
- Add dry-run output.
- Add basic tests for phase dispatch.

### Phase 3 — Admin page

Goal: expose pipeline visibility and safe controls through SvelteKit.

- Auth gate first.
- Read pipeline/admin status from SQLite/log files.
- Add named actions only: catch-up, scrape, clean, prefilter, sentiment, export.
- Enforce a single-run lock.
- Store run metadata separately from analysis data if practical.
- Stream or poll logs without stuffing huge logs into SQLite.

See `agents/pipeline-admin-plan.md`.

### Phase 4 — Scheduling

Goal: keep data fresh without manual babysitting.

- Prefer systemd timer for predictable local execution.
- Hermes cron is acceptable if human-readable summaries are useful.
- Never overlap runs.
- Export static JSON after successful analysis.
- Define what deploy/rebuild step publishes updated JSON.

### Phase 5 — Public polish

Goal: keep the site fast, clean, and useful.

- Public pages continue reading static JSON.
- Admin route stays private.
- Improve article/detail views only after data freshness is solved.
