# agents

Internal repo docs for working this codebase from the box.

## Canonical source

- repo-local source: `docs_internal/`, `docs/`, and `agents/`
- `agents/` scope: AI-agent execution specs only
- `docs_internal/` scope: project architecture, usage, development, plans, and task state
- `docs/` scope: prompt/spec docs used by the pipeline
- target/current checkout: `/srv/apps/is-ai-good-yet`
- old temporary migration checkout: `/tmp/is-ai-good-yet-public` (history only)
- vault mirror: `HyperVault/Projects/is-ai-good-yet/`

Repo-local docs win. Vault copies are mirrors and long-term notes, not the source of truth for executable workflow.

## What goes here

- repo-workflow rules that should not be buried in the public README
- runtime and deployment assumptions
- Claude Code lane notes
- pipeline/admin implementation specs
- future executor lanes like `pi` or `opencode`
- any repo-specific agent specs that need to survive compaction

## Current layout

- `claude-code.md` — default Claude Code operational lane for this box
- `runtime.md` — Node/npm, pipeline, Python venv, and deployment shape
- `workflow.md` — repo work rules and handoff expectations
- `pipeline-admin-plan.md` — plan for integrating the manual Python pipeline with the SvelteKit admin/scheduling workflow

## Default rule

If the task is code in this repo, inspect the actual repo state, read the relevant docs here, use Claude Code for repo-local code writing, and verify with real commands. Do not improvise from chat history.
