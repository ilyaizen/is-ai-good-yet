# Agent Context & Mandates

## Project identity

- Project: `is-ai-good-yet`
- Repo: `ilyaizen/is-ai-good-yet`
- Box path: `/srv/apps/is-ai-good-yet`
- Historical private repo: `ilyaizen/is-ai-good-yet.com`

## Core rule

This repo has three real documentation surfaces:

- `docs_internal/` — operational project docs
- `docs/` — prompt/spec docs
- `Agents/` — AI-agent execution specs

Do not collapse them into one directory. Do not treat `docs_internal/` as a pointer-only layer.

## Work mode

- Hermes is the orchestrator.
- Claude Code is the default executor for repo changes.
- Use low-effort Opus for routine repo tasks unless the task genuinely needs deeper reasoning.
- Use npm/Node, not Bun.
- Use Python 3.11 `.venv` for pipeline work.

## Quality rules

- Follow SOLID, YAGNI, KISS, and DRY.
- Prefer boring boundaries: Python pipeline for scraping/analysis, SvelteKit for UI/admin orchestration.
- No unauthenticated admin controls.
- No arbitrary shell execution from the web UI.
- No public route should require `pipeline/data/pipeline.db` to exist.
- Verify libraries in `package.json` / `pipeline/requirements.txt`; do not assume.
- Keep comments sparse and explain why, not what.

## Required checks by change type

- Frontend/runtime: `npm run check`; usually `npm run build` before commit/deploy.
- Pipeline: activate `.venv`, then targeted pytest or module smoke test.
- Docs: ensure paths and commands match the current repo layout.

## Known traps

- Older docs mention a nested `is-ai-good-yet/` frontend directory. Current public repo has SvelteKit at the root.
- Older docs mention Bun. Current public repo uses npm.
- Older docs mention Vercel/static-only deployment. Current deployment target is Coolify/Nixpacks with adapter-node, while public data still comes from static JSON exports.
- `pipeline/data/pipeline.db` is gitignored/missing in fresh checkout.
