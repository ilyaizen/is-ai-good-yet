# Development Guide

## Environment on the Hetzner box

- Canonical path: `/srv/apps/is-ai-good-yet`
- Node: `>=22.12.0`
- Package manager: npm
- Python: 3.11 via repo-root `.venv`
- Deployment: Coolify/Nixpacks + SvelteKit adapter-node

## Tech stack

### Frontend

- SvelteKit 2
- Svelte 5 runes
- TypeScript 5
- Tailwind CSS 4
- Vite 7
- `@sveltejs/adapter-node`
- `better-sqlite3` for local/server DB helpers
- Convex for visitor counts
- UI/libs include lucide-svelte, bits-ui, mode-watcher, layerchart, TanStack table core, Number Flow, Vaul, Embla

### Pipeline

- Python 3.11
- Polars + PyArrow
- SQLite + text files + Parquet
- aiohttp, aiolimiter, tenacity
- trafilatura, newspaper3k
- Playwright + playwright-stealth-plus
- Selenium, SeleniumBase, undetected-chromedriver
- Groq + pydantic
- rich CLI output
- pytest + pytest-asyncio

## Frontend conventions

- Use Svelte 5 runes: `$state`, `$derived`, `$effect`.
- Prefer `onclick` over legacy `on:click`.
- Use `$app/state` instead of `$app/stores`.
- File names: `kebab-case`.
- Variables/functions: `camelCase`.
- Types/components: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- Use existing CSS/token architecture before adding one-off styles.
- Animation easing should preserve the current premium/swift feel: `cubic-bezier(0, 0.7, 0.1, 1)` unless there is a real reason not to.

## CSS architecture

```text
src/app.css
src/styles/
├── tokens.css
├── base.css
├── terminal.css
├── components.css
└── animations.css
```

`tokens.css` is the design-token source of truth. Do not scatter random OKLCH values through components unless the component is deliberately experimental and temporary.

## Pipeline conventions

- Use Polars, not pandas, unless a dependency forces a tiny local conversion.
- Run real phase modules from `pipeline/` with `python -m src.<module>`.
- Keep scraping conservative on the small Hetzner box. High-concurrency browser scraping can crush memory.
- Use `.venv/bin/python` for automation.
- Keep article text files as ground truth; Parquet is derived/cache.
- Do not commit `pipeline/data/pipeline.db`, scraped text, logs, or API secrets.

## Verification commands

```bash
npm run check
npm run build
source .venv/bin/activate && python -m pytest pipeline/tests -q
```

Run only what matches the change. But before committing runtime, config, or docs that claim commands work, verify them.

## Agent workflow

Hermes orchestrates. Claude Code is the default code executor for repo work on this box.

Before code changes:

1. Confirm current path is `/srv/apps/is-ai-good-yet`.
2. Read the relevant `docs_internal/` and `Agents/` files.
3. Check `git status --short --branch`.
4. Make the smallest correct change.
5. Verify.
6. Commit only coherent sets of changes.

No fake productivity. No invented nested frontend directory. No Bun commands.
