# docs_internal

Internal repo docs pointer.

The real working notes live in `Agents/`. This folder is an index layer for humans and agents that expect a `docs_internal/` entrypoint.

## Current anchor points

- `Agents/README.md` — repo-local internal docs index.
- `Agents/claude-code.md` — default Claude Code repo-work lane on the Hetzner box.
- `Agents/runtime.md` — real Node/npm deployment shape plus Python pipeline setup.
- `Agents/workflow.md` — repo workflow rules.
- `Agents/pipeline-admin-plan.md` — plan for the SvelteKit admin page, Python subprocess runner, schedule, run logs, and locks.

## Repository identity

- public production repo: `ilyaizen/is-ai-good-yet`
- current checkout: `/srv/apps/is-ai-good-yet`
- old temporary migration checkout: `/tmp/is-ai-good-yet-public` (moved out of `/tmp`)
- legacy/private source repo: `ilyaizen/is-ai-good-yet.com`

Do not use the old `.com` repo name when documenting the production checkout.
