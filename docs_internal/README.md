# Internal Documentation

This directory is part of the repository. It is not just a pointer layer.

`docs_internal/` holds project-facing operational knowledge: architecture, usage, development conventions, plans, task status, and troubleshooting. `docs/` holds prompt specs and task-specific artifacts that may be useful to the pipeline itself.

## Canonical locations

- Canonical checkout on the Hetzner box: `/srv/apps/is-ai-good-yet`
- Public GitHub repo: `ilyaizen/is-ai-good-yet`
- Old private/history repo: `ilyaizen/is-ai-good-yet.com`
- Vault mirror: `/root/workspace/HyperVault/Projects/is-ai-good-yet`

The repo-local files are the source of truth for implementation work. The vault mirrors them for planning, review, and cross-session recall.

## Read order

1. `docs_internal/project_overview.md` — what the project is.
2. `docs_internal/architecture.md` — how data moves through the system.
3. `docs_internal/usage.md` — exact local commands.
4. `docs_internal/development.md` — stack, conventions, verification.
5. `Agents/claude-code.md` — how Claude Code should work on this box.
6. `Agents/pipeline-admin-plan.md` — planned admin/scheduler integration.

## Current correction

Earlier docs incorrectly treated `Agents/` as the only canonical docs directory. That is wrong for this repo. `Agents/` is for agent execution specs. `docs_internal/` and `docs/` remain real repo docs and must stay in the checkout.
