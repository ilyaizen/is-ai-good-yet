# Tasks

## Current corrected state

- [x] Canonical checkout is `/srv/apps/is-ai-good-yet`.
- [x] Public repo identity is `ilyaizen/is-ai-good-yet`.
- [x] Historical `.com` repo is treated as source history, not current identity.
- [x] Frontend uses npm/Node, not Bun.
- [x] SvelteKit uses `@sveltejs/adapter-node`.
- [x] Python dependencies install in root `.venv`.
- [x] `docs_internal/` and `docs/` exist in the repo checkout.

## Next work

- [ ] Restore or bootstrap `pipeline/data/pipeline.db`.
- [ ] Wire `pipeline/run.py` to real phase modules or retire it in favor of documented module commands.
- [ ] Add authenticated admin route for pipeline status/actions.
- [ ] Add single-run lock and run metadata/logging.
- [ ] Add schedule runner using systemd timer or Hermes cron.
- [ ] Define deploy/rebuild flow after `src.export` updates JSON.
