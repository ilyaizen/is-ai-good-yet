# CLAUDE.md

Claude Code repo instructions for `is-ai-good-yet`.

Read `agents/claude-code.md` first. It is the operational spec for Claude Code on this Hetzner box.

## Defaults

- Executor: Claude Code, coordinated by Hermes.
- Model: `anthropic/claude-opus-4-8` with reasoning=medium (explicit — 4.8 defaults to high).
- Do not downgrade to low-effort unless the task is trivial (typos, single-line fixes).
- Working directory: `/srv/apps/is-ai-good-yet`.
- Runtime: npm/Node, not Bun.
- App: repo-root SvelteKit 2 / Svelte 5 / Tailwind 4 app.
- Deploy target: `@sveltejs/adapter-node` via Coolify/Nixpacks.
- Pipeline: Python 3.11 in repo-root `.venv`, code under `pipeline/`.

## Before editing

1. Read `AGENTS.md`.
2. Read the relevant file in `agents/`.
3. Read the relevant project doc in `docs_internal/`.
4. Check git status.

Do not copy stale Bun-era, nested-frontend, Vercel/static-only, Mistral-current, or Windows-only assumptions into new work unless current code proves them.
