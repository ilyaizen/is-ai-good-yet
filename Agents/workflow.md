# Repo workflow rules

## Default flow

1. Inspect the actual repo state.
2. Confirm the checkout path and remote.
3. Read the relevant repo-local docs: `docs_internal/` for project facts, `docs/` for prompts/specs, and `Agents/` for execution rules.
4. Use Claude Code as the default repo-local coding executor.
5. Make the smallest real change that fixes the workflow.
6. Verify it against the real entrypoint or command.
7. Mirror durable docs into HyperVault only after repo-local docs are correct.

## Repository identity checks

Expected production shape:

```bash
cd /srv/apps/is-ai-good-yet
git remote -v
# origin https://github.com/ilyaizen/is-ai-good-yet.git
```

`/tmp/is-ai-good-yet-public` was the temporary working checkout. Do not let docs fossilize that as the production location.

Legacy note: `ilyaizen/is-ai-good-yet.com` was the old private Python scraper/analysis repo. It is not the production repo identity.

## Non-negotiables

- don't invent commands that don't exist
- don't document a workflow that cannot be run
- don't hide missing artifacts behind vague prose
- don't route code changes through shortcuts when a real entrypoint exists
- don't use Bun for this repo's current runtime/deploy path
- don't treat `pipeline/run.py` as real orchestration until it calls the existing phase modules
- don't expose an unauthenticated admin route for pipeline control

## Handoff rule

If the work changes repo behavior, update the relevant repo docs first:

- `docs_internal/` for project architecture, setup, usage, task state, and troubleshooting
- `docs/` for prompt/spec changes
- `Agents/` for agent execution/workflow rules

Then mirror the matching files under `HyperVault/Projects/is-ai-good-yet/`.

## Verification baseline

Docs-only repo changes should still tolerate:

```bash
npm run check
npm run build
```

Pipeline work also needs Python checks from a repo-root venv once the checkout is in `/srv/apps/is-ai-good-yet` and dependencies are installed.
