# Runtime and deployment

This repo is a Node deployment, not a Bun deployment.

## Canonical runtime

- package manager: `npm`
- production entrypoint: `build/index.js`
- start command: `HOST=0.0.0.0 node build/index.js`
- SvelteKit adapter: `@sveltejs/adapter-node`

## Pipeline layout

- source lives in `pipeline/`
- repo-side scripts call the pipeline through `python3 pipeline/run.py --phase ...`
- runtime helpers resolve the pipeline DB relative to the repo/module, not `cwd`
- DB-backed utilities expect `pipeline/data/pipeline.db` when that artifact exists

## Script rule

If a command runs the app, scripts, or deployment path, it should match the real runtime layout on this host. No fake shortcuts, no Bun-era cargo cult.

## Verification

- `npm run build`
- `npm run check`
- `npm run start`
- DB-backed scripts only after the pipeline DB artifact exists