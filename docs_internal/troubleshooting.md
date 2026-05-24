# Troubleshooting

## Wrong path

Use:

```bash
cd /srv/apps/is-ai-good-yet
```

Do not work from `/tmp/is-ai-good-yet-public`; that was a temporary migration path.

## Bun command fails

Good. Do not use Bun here.

Use npm:

```bash
npm install
npm run check
npm run build
npm run start
```

## Missing pipeline database

Error shape:

```text
Database file not found at .../pipeline/data/pipeline.db
```

Cause: the DB artifact is gitignored and absent in a fresh checkout.

Fix: restore a trusted `pipeline.db` artifact or run the pipeline phases that create/populate it. Do not "fix" this by changing SvelteKit public pages to require SQLite in production.

## Python module import errors

Use the repo-root venv and run real phase modules from `pipeline/`:

```bash
cd /srv/apps/is-ai-good-yet
source .venv/bin/activate
cd pipeline
python -m src.scraper --help
```

If dependencies are missing:

```bash
cd /srv/apps/is-ai-good-yet
source .venv/bin/activate
python -m pip install -r pipeline/requirements.txt
python -m playwright install chromium
```

## Playwright/browser errors

Reinstall Chromium for the active venv:

```bash
source /srv/apps/is-ai-good-yet/.venv/bin/activate
python -m playwright install chromium
```

On a small box, browser concurrency can exhaust memory. Reduce scraper `-c` before blaming the code.

## Groq/API failures

Check local environment, not committed files:

```bash
printenv GROQ_API_KEY
```

If empty, add it to the service/user environment used to run the pipeline. Do not commit secrets.

## SvelteKit build fails after docs-only changes

Docs should not affect build. Run:

```bash
npm run check
npm run build
```

If build fails because `pipeline/data/pipeline.db` is missing, that means a public route imported server DB code incorrectly. Public pages should use static JSON.

## Coolify starts but app is unreachable

Check that start command is still:

```bash
HOST=0.0.0.0 node build/index.js
```

Also verify Coolify deploys the repo root, not `pipeline/` and not an old nested frontend path.
