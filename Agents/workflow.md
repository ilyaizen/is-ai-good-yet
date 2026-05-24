# Repo workflow rules

## Default flow

1. inspect the actual repo state
2. use the repo-local docs in `Agents/`
3. make the smallest real change that fixes the workflow
4. verify it against the real entrypoint or command
5. record durable notes in the vault when the change matters beyond the chat

## Non-negotiables

- don't invent commands that don't exist
- don't document a workflow that cannot be run
- don't hide missing artifacts behind vague prose
- don't route code changes through shortcuts when a real entrypoint exists

## Handoff rule

If the work changes repo behavior, update the repo docs here and the matching vault note in `HyperVault/Projects/is-ai-good-yet/`.