# Progress

## Current repo consolidation state

- Canonical checkout: `/srv/apps/is-ai-good-yet`.
- GitHub repo: `ilyaizen/is-ai-good-yet`.
- Historical private repo: `ilyaizen/is-ai-good-yet.com`.
- Frontend is at the repo root, not a nested `is-ai-good-yet/` directory.
- Runtime package manager is npm.
- Production target is Coolify/Nixpacks with SvelteKit adapter-node.
- Python pipeline lives in `pipeline/` and uses a repo-root `.venv` on the Hetzner box.
- `docs_internal/`, `docs/`, and `agents/` are all real repo documentation surfaces.

## Verified recently

- `npm run check` passes.
- `npm run build` passes.
- `python -m pytest pipeline/tests -q` passes after marking the async Playwright test correctly.

## Known remaining gap

`pipeline/data/pipeline.db` is absent in a fresh checkout. DB-backed pipeline/admin work needs either a restored artifact or a fresh bootstrap run.

## Next useful milestone

Wire a real local pipeline/admin workflow:

1. restore/bootstrap DB,
2. make `pipeline/run.py` dispatch real phases or replace it with documented module commands,
3. add authenticated SvelteKit admin route,
4. add single-run locking and logs,
5. add schedule runner,
6. export static JSON for public pages.
