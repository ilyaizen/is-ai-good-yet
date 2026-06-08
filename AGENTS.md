# AGENTS.md

Repository guidance for AI agents working on `is-ai-good-yet`.

## Canonical checkout

- Path on the Hetzner box: `/srv/apps/is-ai-good-yet`
- GitHub repo: `ilyaizen/is-ai-good-yet`
- Legacy/private history repo: `ilyaizen/is-ai-good-yet.com`

## Required reading

1. `agents/README.md` — agent execution index.
2. `agents/workflow.md` — repo workflow rules.
3. `agents/claude-code.md` — Claude Code operating spec for this box.
4. `docs_internal/agent_context.md` — project context and stale-doc warnings.
5. `docs_internal/architecture.md` and `docs_internal/usage.md` — stack and runtime facts.

## Hard rules

- Use npm/Node, not Bun.
- Frontend is the repo-root SvelteKit app, not a nested `frontend/` directory.
- Production deploy uses `@sveltejs/adapter-node`.
- Pipeline code stays in `pipeline/` and uses the repo-root `.venv` with Python 3.11.
- Do not preserve or print secrets. Replace credentials with `[REDACTED]`.
- Update repo-local docs first, then mirror durable notes to HyperVault as plain markdown mirrors. Do not symlink repo docs into the vault or depend on the rclone mount preserving symlink targets.

## Verification

Use the narrowest relevant checks:

```bash
npm run check
npm run build
. .venv/bin/activate && python -m pytest pipeline/tests -q
```

DB-backed pipeline commands may fail in a fresh checkout until `pipeline/data/pipeline.db` exists.
