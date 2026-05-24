# Claude Code workflow

This repo uses Claude Code as the coding executor when Hermes is driving work from this box.

## Default posture

- executor: Claude Code CLI
- model: Opus 4.7
- reasoning: low
- workdir: repo root
- mode: print mode (`claude -p`) for one-shot tasks
- use interactive tmux only when the task genuinely needs iteration

## Why this exists

Hermes should orchestrate and review. Claude Code should do the repo-local code writing. That keeps the workflow reproducible instead of turning into a conversation-shaped guess.

## Rules

- start from the repo root unless the task needs a subdir
- keep tool access tight
- prefer minimal allowed tools for the task
- if a script or entrypoint is missing, wire one up instead of describing a workflow that doesn't run
- keep internal agent docs in `Agents/`, not scattered through random notes

## Example shape

```bash
claude -p "Fix the bug in scripts/verify-fix.ts" \
  --model claude-opus-4-7 \
  --effort low \
  --allowedTools 'Read,Edit,Bash' \
  --max-turns 6
```

## Future lanes

This folder can later grow sibling docs for opencode or pi. New lanes should be first-class docs, not one-off chat leftovers.